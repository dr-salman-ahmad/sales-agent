"""
Root Agent - Main orchestrator for the Sales Automation Agent
"""

import os
import logging
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

load_dotenv()
from google.adk.agents import Agent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters
from google.adk.tools.mcp_tool import StdioConnectionParams
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from .prompts import get_root_agent_instructions
from utils.auth import oauth_manager
from utils.supabase_client import supabase_client
from utils.data_models import TaskRequest, AgentResponse
from utils.helpers import extract_json_from_text

logger = logging.getLogger(__name__)

# Session service for the agent
session_service = InMemorySessionService()


def create_root_agent() -> Agent:
    """Create the root orchestrator agent with all MCP tools"""

    # MCP Tools for external integrations
    mcp_tools = []

    # Azure Logic App MCP Tool
    azure_tool = MCPToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command="python",
                args=["-m", "mcp_tools.azure_logic_app"],
                env={"AZURE_LOGIC_APP_URL": os.getenv("AZURE_LOGIC_APP_URL", "")},
            ),
            timeout=60,
        ),
    )
    mcp_tools.append(azure_tool)

    # Hunter.io MCP Tool
    hunter_tool = MCPToolset(
        connection_params=StdioServerParameters(
            command="python",
            args=["-m", "mcp_tools.hunter_io"],
            env={"HUNTER_API_KEY": os.getenv("HUNTER_API_KEY", "")},
        ),
    )
    mcp_tools.append(hunter_tool)

    # Airtable CRM MCP Tool
    airtable_tool = MCPToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command="python",
                args=["-m", "mcp_tools.airtable_crm"],
            ),
            timeout=60,
        ),
    )
    mcp_tools.append(airtable_tool)

    # Gmail MCP Tool
    gmail_tool = MCPToolset(
        connection_params=StdioServerParameters(
            command="python",
            args=["-m", "mcp_tools.gmail_sender"],
        ),
    )
    mcp_tools.append(gmail_tool)

    # Web Scraper MCP Tool
    web_scraper_tool = MCPToolset(
        connection_params=StdioServerParameters(
            command="python",
            args=["-m", "mcp_tools.web_scraper"],
        ),
    )
    mcp_tools.append(web_scraper_tool)

    # OpenAI MCP Tool
    openai_tool = MCPToolset(
        connection_params=StdioServerParameters(
            command="python",
            args=["-m", "mcp_tools.openai_client"],
            env={"OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", "")},
        ),
    )
    mcp_tools.append(openai_tool)

    # Supabase MCP Tool
    supabase_tool = MCPToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command="python",
                args=["-m", "mcp_tools.supabase_client"],
                env={
                    "SUPABASE_URL": os.getenv("SUPABASE_URL", ""),
                    "SUPABASE_KEY": os.getenv("SUPABASE_KEY", ""),
                },
            ),
            timeout=60,
        ),
    )

    mcp_tools.append(supabase_tool)

    # Create the root agent
    root_agent = Agent(
        model="gemini-2.5-flash",
        name="sales_automation_root_agent",
        instruction=get_root_agent_instructions(),
        tools=mcp_tools,
    )

    return root_agent


class SalesAutomationOrchestrator:
    """Main orchestrator for sales automation workflows"""

    def __init__(self):
        self.agent = create_root_agent()
        self.runner = Runner(
            agent=self.agent,
            app_name="sales_automation",
            session_service=session_service,
        )

    async def process_request(
        self, user_id: str, message: str, user_email: str = None
    ) -> AgentResponse:
        """Process a user request and route to appropriate workflow"""
        try:
            logger.info(f"Processing request from user {user_id}: {message}")

            # Get user credentials
            credentials = await oauth_manager.get_user_credentials(user_id)

            if not credentials:
                return AgentResponse(
                    success=False,
                    message="Please connect your Gmail and Airtable accounts to use the sales automation agent.",
                    errors=["No user credentials found"],
                )

            # Parse the user request to understand intent
            task_info = await self._parse_user_request(message, user_id)

            if not task_info:
                return AgentResponse(
                    success=False,
                    message="I couldn't understand your request. Please try rephrasing it.",
                    errors=["Failed to parse user request"],
                )

            # Check if this is a conversational response (no task or N/A task) or a task request
            task_value = task_info.get("task")
            if "task" not in task_info or task_value is None or task_value == "N/A":
                # This is a conversational response, return it directly
                return AgentResponse(
                    success=True,
                    message=task_info.get(
                        "response", "I'm here to help with your sales automation needs!"
                    ),
                    data=task_info,
                    leads_processed=0,
                )

            # Route to appropriate workflow
            if isinstance(task_info.get("task"), list):
                # Multiple tasks
                return await self._handle_multiple_tasks(
                    task_info, user_id, credentials
                )
            else:
                # Single task
                return await self._handle_single_task(task_info, user_id, credentials)

        except Exception as e:
            logger.error(f"Error processing request: {e}")
            return AgentResponse(
                success=False,
                message=f"An error occurred while processing your request: {str(e)}",
                errors=[str(e)],
            )

    async def _get_or_create_session(self, user_id: str):
        """Get existing session for user or create a new one if none exists"""
        try:
            # First, try to get existing sessions for this user
            list_response = await session_service.list_sessions(
                app_name="sales_automation",
                user_id=user_id,
            )

            # If sessions exist, use the most recent one (last in the list)
            if list_response.sessions:
                logger.info(
                    f"Found {len(list_response.sessions)} existing sessions for user {user_id}"
                )
                # Return the most recent session (sessions are typically ordered by creation time)
                return list_response.sessions[-1]

            # No existing sessions, create a new one
            logger.info(
                f"No existing sessions found for user {user_id}, creating new session"
            )
            session = await session_service.create_session(
                app_name="sales_automation",
                user_id=user_id,
            )
            return session

        except Exception as e:
            logger.error(f"Error getting or creating session for user {user_id}: {e}")
            # Fallback to creating a new session
            return await session_service.create_session(
                app_name="sales_automation",
                user_id=user_id,
            )

    async def _run_agent_with_prompt(self, prompt: str, user_id: str) -> str:
        """Helper method to run agent with a prompt and return response"""
        try:
            # Get or create a session for this user
            session = await self._get_or_create_session(user_id)

            # Create content object for the runner
            from google.genai import types

            content = types.Content(
                role="user",
                parts=[types.Part.from_text(text=prompt)],
            )

            # Use the agent to run the prompt
            events = []
            async for event in self.runner.run_async(
                user_id=user_id,
                session_id=session.id,
                new_message=content,
            ):
                events.append(event)

            # Get the last response from events
            response = ""
            for event in events:
                if hasattr(event, "content") and event.content and event.content.parts:
                    # Extract text from all parts
                    text_parts = []
                    for part in event.content.parts:
                        if hasattr(part, "text") and part.text:
                            text_parts.append(part.text)
                    if text_parts:
                        response = " ".join(text_parts)

            logger.info(f"Response from agent: {response}")
            return response

        except Exception as e:
            logger.error(f"Error running agent with prompt: {e}")
            return ""

    async def _parse_user_request(
        self, message: str, user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Parse user request to extract task information"""
        try:
            from .prompts import get_task_parsing_prompt

            parsing_prompt = f"""
            {get_task_parsing_prompt()}
            
            User request: "{message}"
            User ID: {user_id}
            """

            # Use the agent to parse the request
            response = await self._run_agent_with_prompt(parsing_prompt, user_id)

            # Extract JSON from response
            task_info = extract_json_from_text(response)

            return task_info

        except Exception as e:
            logger.error(f"Error parsing user request: {e}")
            return None

    async def _handle_single_task(
        self, task_info: Dict[str, Any], user_id: str, credentials: Dict[str, Any]
    ) -> AgentResponse:
        """Handle a single task workflow"""
        task_type = task_info.get("task")

        if task_type == "prospecting":
            return await self._handle_prospecting(task_info, user_id, credentials)
        elif task_type == "enrichment":
            return await self._handle_enrichment(task_info, user_id, credentials)
        elif task_type == "qualify":
            return await self._handle_qualification(task_info, user_id, credentials)
        elif task_type == "personalize":
            return await self._handle_personalization(task_info, user_id, credentials)
        else:
            return AgentResponse(
                success=False,
                message=f"Unknown task type: {task_type}",
                errors=[f"Unsupported task: {task_type}"],
            )

    async def _handle_multiple_tasks(
        self, task_info: Dict[str, Any], user_id: str, credentials: Dict[str, Any]
    ) -> AgentResponse:
        """Handle multiple tasks in sequence"""
        tasks = task_info.get("task", [])
        results = []
        errors = []

        for task_type in tasks:
            task_result = await self._handle_single_task(
                {**task_info, "task": task_type}, user_id, credentials
            )

            results.append(task_result)
            if not task_result.success:
                errors.extend(task_result.errors or [])

        # Combine results
        total_leads = sum(r.leads_processed or 0 for r in results)
        success_count = sum(1 for r in results if r.success)

        return AgentResponse(
            success=success_count == len(tasks),
            message=f"Completed {success_count}/{len(tasks)} tasks successfully. Processed {total_leads} leads total.",
            leads_processed=total_leads,
            errors=errors if errors else None,
            data={"task_results": [r.dict() for r in results]},
        )

    async def _handle_prospecting(
        self, task_info: Dict[str, Any], user_id: str, credentials: Dict[str, Any]
    ) -> AgentResponse:
        """Handle prospecting workflow"""
        try:
            # Get Airtable credentials
            airtable_creds = credentials.get("airtable")
            if not airtable_creds:
                return AgentResponse(
                    success=False,
                    message="Airtable connection required for prospecting. Please connect your Airtable account.",
                    errors=["No Airtable credentials"],
                )

            # Build prospecting query
            query_parts = []
            if task_info.get("industry"):
                query_parts.append(f"in {task_info['industry']}")
            if task_info.get("location"):
                query_parts.append(f"located in {task_info['location']}")
            if task_info.get("min_employees"):
                query_parts.append(f"with {task_info['min_employees']}+ employees")

            num_companies = task_info.get("num_companies", 5)
            query = f"Find {num_companies} companies " + " ".join(query_parts)

            # Use agent to execute prospecting
            prospecting_prompt = f"""
            Execute a prospecting workflow:
            1. Use the Azure Logic App tool to search for companies with this query: "{query}"
            2. Get the user's Airtable base ID using access token: {airtable_creds['access_token']}
            3. Parse and structure the company data
            4. Create lead records in the user's Airtable CRM
            5. Provide a summary of results
            
            User ID: {user_id}
            """

            response = await self._run_agent_with_prompt(prospecting_prompt, user_id)

            return AgentResponse(
                success=True,
                message=response,
                leads_processed=num_companies,  # Approximate
                data={"query": query, "task_type": "prospecting"},
            )

        except Exception as e:
            logger.error(f"Error in prospecting workflow: {e}")
            return AgentResponse(
                success=False, message=f"Prospecting failed: {str(e)}", errors=[str(e)]
            )

    async def _handle_enrichment(
        self, task_info: Dict[str, Any], user_id: str, credentials: Dict[str, Any]
    ) -> AgentResponse:
        """Handle enrichment workflow"""
        try:
            # Get required credentials
            airtable_creds = credentials.get("airtable")
            if not airtable_creds:
                return AgentResponse(
                    success=False,
                    message="Airtable connection required for enrichment.",
                    errors=["No Airtable credentials"],
                )

            enrichment_prompt = f"""
            Execute an enrichment workflow:
            1. Get the user's Airtable base ID using access token: {airtable_creds['access_token']}
            2. Search for unenriched leads (Enriched = false or empty)
            3. For each lead with a website:
               - Use Hunter.io to find email addresses
               - Use web scraper to extract company information and insights
               - Update the lead record with enriched data
            4. Mark leads as enriched
            5. Provide a summary of enrichment results
            
            User ID: {user_id}
            """

            response = await self._run_agent_with_prompt(enrichment_prompt, user_id)

            return AgentResponse(
                success=True, message=response, data={"task_type": "enrichment"}
            )

        except Exception as e:
            logger.error(f"Error in enrichment workflow: {e}")
            return AgentResponse(
                success=False, message=f"Enrichment failed: {str(e)}", errors=[str(e)]
            )

    async def _handle_qualification(
        self, task_info: Dict[str, Any], user_id: str, credentials: Dict[str, Any]
    ) -> AgentResponse:
        """Handle lead qualification workflow"""
        try:
            airtable_creds = credentials.get("airtable")
            if not airtable_creds:
                return AgentResponse(
                    success=False,
                    message="Airtable connection required for qualification.",
                    errors=["No Airtable credentials"],
                )

            qualification_prompt = f"""
            Execute a lead qualification workflow:
            1. Get the user's Airtable base ID using access token: {airtable_creds['access_token']}
            2. Get the user's ICP (Ideal Customer Persona) from the Personas table for user: {user_id}
            3. Search for enriched leads without scores (Enriched = true AND Score = empty)
            4. For each lead:
               - Use OpenAI to score the lead against ICP criteria
               - Parse the scoring results (Hot/Warm/Cold + reasoning)
               - Update the lead record with score and reasoning
            5. Provide a summary with score distribution
            
            User ID: {user_id}
            """

            response = await self._run_agent_with_prompt(qualification_prompt, user_id)

            return AgentResponse(
                success=True, message=response, data={"task_type": "qualification"}
            )

        except Exception as e:
            logger.error(f"Error in qualification workflow: {e}")
            return AgentResponse(
                success=False,
                message=f"Qualification failed: {str(e)}",
                errors=[str(e)],
            )

    async def _handle_personalization(
        self, task_info: Dict[str, Any], user_id: str, credentials: Dict[str, Any]
    ) -> AgentResponse:
        """Handle email personalization workflow"""
        try:
            airtable_creds = credentials.get("airtable")
            gmail_creds = credentials.get("gmail")

            if not airtable_creds:
                return AgentResponse(
                    success=False,
                    message="Airtable connection required for personalization.",
                    errors=["No Airtable credentials"],
                )

            send_emails = task_info.get("send_emails", False)
            if send_emails and not gmail_creds:
                return AgentResponse(
                    success=False,
                    message="Gmail connection required for sending emails.",
                    errors=["No Gmail credentials"],
                )

            personalization_prompt = f"""
            Execute an email personalization workflow:
            1. Get the user's Airtable base ID using access token: {airtable_creds['access_token']}
            2. Search for Hot/Warm leads without personalized content
            3. For each lead:
               - Use OpenAI to generate a personalized email opener based on company insights
               - Use OpenAI to generate a compelling subject line
               - Update the lead record with personalized content
               {"- Send the email using Gmail API with access token: " + gmail_creds['access_token'] if send_emails and gmail_creds else ""}
            4. Provide a summary of personalization results
            
            User ID: {user_id}
            Sender Email: {gmail_creds.get('provider_email', 'user@example.com') if gmail_creds else 'user@example.com'}
            Send Emails: {send_emails}
            """

            response = await self._run_agent_with_prompt(
                personalization_prompt, user_id
            )

            return AgentResponse(
                success=True,
                message=response,
                data={"task_type": "personalization", "send_emails": send_emails},
            )

        except Exception as e:
            logger.error(f"Error in personalization workflow: {e}")
            return AgentResponse(
                success=False,
                message=f"Personalization failed: {str(e)}",
                errors=[str(e)],
            )


# Global orchestrator instance
sales_orchestrator = SalesAutomationOrchestrator()
runner = sales_orchestrator.runner
root_agent = sales_orchestrator.agent
