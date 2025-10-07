"""
Root Agent - Main orchestrator for the Sales Automation Agent
"""

import os
import logging
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

load_dotenv()
from google.adk.agents import Agent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from .prompts import get_root_agent_instructions

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
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command="python",
                args=["-m", "mcp_tools.hunter_io"],
                env={"HUNTER_API_KEY": os.getenv("HUNTER_API_KEY", "")},
            ),
            timeout=60,
        ),
    )
    mcp_tools.append(hunter_tool)

    # Supabase CRM MCP Tool
    supabase_crm_tool = MCPToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command="python",
                args=["-m", "mcp_tools.supabase_crm"],
                env={
                    "SUPABASE_URL": os.getenv("SUPABASE_URL", ""),
                    "SUPABASE_KEY": os.getenv("SUPABASE_KEY", ""),
                },
            ),
            timeout=60,
        ),
    )
    mcp_tools.append(supabase_crm_tool)

    # Gmail MCP Tool
    gmail_tool = MCPToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command="python",
                args=["-m", "mcp_tools.gmail_sender"],
            ),
            timeout=60,
        ),
    )
    mcp_tools.append(gmail_tool)

    # Web Scraper MCP Tool
    web_scraper_tool = MCPToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command="python",
                args=["-m", "mcp_tools.web_scraper"],
            ),
            timeout=60,
        ),
    )
    mcp_tools.append(web_scraper_tool)

    # OpenAI MCP Tool
    openai_tool = MCPToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command="python",
                args=["-m", "mcp_tools.openai_client"],
                env={"OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", "")},
            ),
            timeout=60,
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
                    "GMAIL_CLIENT_ID": os.getenv("GMAIL_CLIENT_ID", ""),
                    "GMAIL_CLIENT_SECRET": os.getenv("GMAIL_CLIENT_SECRET", ""),
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


# Global orchestrator instance
sales_orchestrator = SalesAutomationOrchestrator()
runner = sales_orchestrator.runner
root_agent = sales_orchestrator.agent
