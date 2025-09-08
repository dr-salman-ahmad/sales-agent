"""
Root Agent - Main orchestrator for the Drive Automation Agent
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
from .prompts import SYSTEM_PROMPT
from utils.auth import oauth_manager
from utils.supabase_client import supabase_client
from utils.data_models import AgentResponse

logger = logging.getLogger(__name__)

# Session service for the agent
session_service = InMemorySessionService()


def create_root_agent() -> Agent:
    """Create the root orchestrator agent with all MCP tools"""

    # MCP Tools for external integrations
    mcp_tools = []

    # Supabase MCP Tool for OAuth management
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

    # Google Drive MCP Tool
    drive_tool = MCPToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command="python",
                args=["-m", "mcp_tools.google_drive"],
                env={
                    "GOOGLE_CLIENT_ID": os.getenv("GOOGLE_CLIENT_ID", ""),
                    "GOOGLE_CLIENT_SECRET": os.getenv("GOOGLE_CLIENT_SECRET", ""),
                },
            ),
            timeout=60,
        ),
    )
    mcp_tools.append(drive_tool)

    # Create the root agent
    root_agent = Agent(
        model="gemini-2.5-flash",
        name="drive_automation_root_agent",
        instruction=SYSTEM_PROMPT,
        tools=mcp_tools,
    )

    return root_agent


class DriveAutomationOrchestrator:
    """Main orchestrator for drive automation workflows"""

    def __init__(self):
        self.agent = create_root_agent()
        self.runner = Runner(
            agent=self.agent,
            app_name="drive_automation",
            session_service=session_service,
        )

    async def process_request(
        self, user_id: str, message: str, folder_id: str = None, user_email: str = None
    ) -> AgentResponse:
        """Process a user request and route to appropriate workflow"""
        try:
            logger.info(f"Processing request from user {user_id}: {message}")

            # Get user credentials from Supabase
            from mcp_tools.supabase_client import get_oauth_connection

            oauth_response = await get_oauth_connection(
                {"user_id": user_id, "provider": "google"}
            )

            # Parse the JSON response
            import json

            if isinstance(oauth_response, list) and len(oauth_response) > 0:
                oauth_data = json.loads(oauth_response[0].text)
            else:
                return AgentResponse(
                    success=False,
                    message="Please connect your Google account to use the drive automation agent.",
                    errors=["No Google credentials found"],
                )

            if oauth_data.get("is_expired", True):
                return AgentResponse(
                    success=False,
                    message="Your Google access token has expired. Please reconnect your Google account.",
                    errors=["Expired Google credentials"],
                )

            # Validate folder_id
            if not folder_id:
                return AgentResponse(
                    success=False,
                    message="Please provide a folder_id to search in.",
                    errors=["Missing folder_id"],
                )

            # Get or create a session
            session = await self._get_or_create_session(user_id)

            # Create content object for the runner
            from google.genai import types

            content = types.Content(
                role="user",
                parts=[
                    types.Part.from_text(
                        text=message + f"\nUser ID: {user_id}\nFolder ID: {folder_id}"
                    )
                ],
            )

            # Use the agent to process the request
            events = []
            async for event in self.runner.run_async(
                user_id=user_id,
                session_id=session.id,
                new_message=content,
            ):
                events.append(event)

            # Extract response from events
            response_text = ""
            for event in events:
                if hasattr(event, "content") and event.content and event.content.parts:
                    text_parts = []
                    for part in event.content.parts:
                        if hasattr(part, "text") and part.text:
                            text_parts.append(part.text)
                    if text_parts:
                        response_text = " ".join(text_parts)

            return AgentResponse(
                success=True,
                message=response_text,
                data={
                    "source": "drive_agent",
                    "folder_id": folder_id,
                    "oauth_data": {
                        "provider": "google",
                        "provider_email": oauth_data.get("provider_email"),
                        "expires_at": oauth_data.get("expires_at"),
                    },
                },
            )

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
                app_name="drive_automation",
                user_id=user_id,
            )

            # If sessions exist, use the most recent one
            if list_response.sessions:
                logger.info(
                    f"Found {len(list_response.sessions)} existing sessions for user {user_id}"
                )
                return list_response.sessions[-1]

            # No existing sessions, create a new one
            logger.info(
                f"No existing sessions found for user {user_id}, creating new session"
            )
            session = await session_service.create_session(
                app_name="drive_automation",
                user_id=user_id,
            )
            return session

        except Exception as e:
            logger.error(f"Error getting or creating session for user {user_id}: {e}")
            # Fallback to creating a new session
            return await session_service.create_session(
                app_name="drive_automation",
                user_id=user_id,
            )


# Global orchestrator instance
drive_agent = DriveAutomationOrchestrator()
runner = drive_agent.runner
root_agent = drive_agent.agent
