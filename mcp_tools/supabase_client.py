"""
Supabase MCP Server for user credential management
"""

import os
import logging
import asyncio
from typing import Any, Sequence, Dict
from datetime import datetime, timezone
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from dotenv import load_dotenv

load_dotenv()

# Setup loggers
logger = logging.getLogger(__name__)

# Create MCP server
server = Server("supabase-client-server")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="get_oauth_connection",
            description="Get specific OAuth connection for a user and provider",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User ID to get connection for",
                    },
                    "provider": {
                        "type": "string",
                        "description": "OAuth provider (gmail, airtable)",
                        "enum": ["gmail", "airtable"],
                    },
                },
                "required": ["user_id", "provider"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> Sequence[TextContent]:
    """Handle tool calls."""
    if name == "get_oauth_connection":
        return await get_oauth_connection(arguments)

    raise ValueError(f"Unknown tool: {name}")


async def get_oauth_connection(arguments: Dict[str, Any]) -> Sequence[TextContent]:
    """Get specific OAuth connection for a user and provider, with automatic token refresh"""
    try:
        from supabase import create_client
        import base64
        import httpx

        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        gmail_client_id = os.getenv("GMAIL_CLIENT_ID")
        gmail_client_secret = os.getenv("GMAIL_CLIENT_SECRET")
        airtable_client_id = os.getenv("AIRTABLE_CLIENT_ID")
        airtable_client_secret = os.getenv("AIRTABLE_CLIENT_SECRET")

        if not supabase_url or not supabase_key:
            return [
                TextContent(
                    type="text", text="Error: Supabase credentials not configured"
                )
            ]

        user_id = arguments.get("user_id")
        provider = arguments.get("provider")

        if not user_id or not provider:
            return [
                TextContent(
                    type="text", text="Error: User ID and provider are required"
                )
            ]

        client = create_client(supabase_url, supabase_key)

        # Prepare request details
        url = f"{supabase_url}/rest/v1/oauth_connections"
        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json",
        }
        params = {
            "select": "*",
            "user_id": f"eq.{user_id}",
            "provider": f"eq.{provider}",
            "is_active": "eq.true",
        }

        # Execute request
        response = (
            client.table("oauth_connections")
            .select("*")
            .eq("user_id", user_id)
            .eq("provider", provider)
            .eq("is_active", True)
            .execute()
        )
        import asyncio

        await asyncio.sleep(3)

        if not response.data:
            return [
                TextContent(
                    type="text",
                    text=f"No active {provider} connection found for user {user_id}",
                )
            ]

        row = response.data[0]
        token_expires_at = datetime.fromisoformat(
            row["token_expires_at"].replace("Z", "+00:00")
        )
        is_expired = datetime.now(timezone.utc) >= token_expires_at

        # If token is expired, try to refresh it
        if is_expired:
            logger.info(f"Token expired for {provider}. Attempting to refresh...")

            try:
                if provider == "gmail" and gmail_client_id and gmail_client_secret:
                    # Refresh Gmail token
                    async with httpx.AsyncClient() as http_client:
                        refresh_response = await http_client.post(
                            "https://oauth2.googleapis.com/token",
                            data={
                                "grant_type": "refresh_token",
                                "refresh_token": row["refresh_token"],
                                "client_id": gmail_client_id,
                                "client_secret": gmail_client_secret,
                            },
                        )

                        if refresh_response.status_code == 200:
                            token_data = refresh_response.json()
                            # Update tokens in database
                            try:
                                updated_data = await update_oauth_tokens(
                                    user_id=user_id,
                                    provider=provider,
                                    access_token=token_data["access_token"],
                                    refresh_token=token_data.get(
                                        "refresh_token", row["refresh_token"]
                                    ),
                                    expires_in=token_data.get("expires_in", 3600),
                                )
                                row["access_token"] = updated_data["access_token"]
                                if "refresh_token" in updated_data:
                                    row["refresh_token"] = updated_data["refresh_token"]
                                token_expires_at = datetime.fromisoformat(
                                    updated_data["token_expires_at"].replace(
                                        "Z", "+00:00"
                                    )
                                )
                                is_expired = False
                            except Exception as e:
                                logger.error(
                                    f"Failed to update {provider} tokens in database: {e}"
                                )
                                raise

                elif (
                    provider == "airtable"
                    and airtable_client_id
                    and airtable_client_secret
                ):
                    # Refresh Airtable token
                    async with httpx.AsyncClient() as http_client:
                        refresh_response = await http_client.post(
                            "https://airtable.com/oauth2/v1/token",
                            headers={
                                "Content-Type": "application/x-www-form-urlencoded",
                                "Authorization": "Basic Mzk3ZTYxZTMtZTUyZC00MDY3LTk5ODUtODgwZjE5MWUzNTIzOmY5MmQ2NjdlZGJlMDFjZmJkMmM3OTFiMDUyYmZmMDE2NDgxODg2YmNmZjQwYmJmNTQ5ZWE2ODEwNmQ3ZDJhYjU=",
                            },
                            data={
                                "grant_type": "refresh_token",
                                "refresh_token": row["refresh_token"],
                            },
                        )

                        if refresh_response.status_code == 200:
                            token_data = refresh_response.json()
                            # Update tokens in database
                            try:
                                updated_data = await update_oauth_tokens(
                                    user_id=user_id,
                                    provider=provider,
                                    access_token=token_data["access_token"],
                                    refresh_token=token_data.get(
                                        "refresh_token", row["refresh_token"]
                                    ),
                                    expires_in=token_data.get("expires_in", 3600),
                                )
                                row["access_token"] = updated_data["access_token"]
                                if "refresh_token" in updated_data:
                                    row["refresh_token"] = updated_data["refresh_token"]
                                token_expires_at = datetime.fromisoformat(
                                    updated_data["token_expires_at"].replace(
                                        "Z", "+00:00"
                                    )
                                )
                                is_expired = False
                            except Exception as e:
                                logger.error(
                                    f"Failed to update {provider} tokens in database: {e}"
                                )
                                raise

            except Exception as refresh_error:
                logger.error(f"Error refreshing {provider} token: {refresh_error}")

        import json

        result = {
            "user_id": user_id,
            "provider": provider,
            "access_token": row["access_token"],
            "refresh_token": row["refresh_token"],
            "provider_email": row["provider_email"],
            "expires_at": token_expires_at.isoformat(),
            "is_expired": is_expired,
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        error_msg = f"Error getting OAuth connection: {str(e)}"
        logger.error(error_msg)
        return [TextContent(type="text", text=f"Error: {error_msg}")]


async def update_oauth_tokens(
    user_id: str,
    provider: str,
    access_token: str,
    refresh_token: str = None,
    expires_in: int = 3600,
) -> Dict[str, Any]:
    """Helper function to update OAuth tokens in Supabase

    Args:
        user_id (str): The user ID
        provider (str): OAuth provider (gmail, airtable)
        access_token (str): New access token
        refresh_token (str, optional): New refresh token. Defaults to None.
        expires_in (int, optional): Token expiration time in seconds. Defaults to 3600.

    Returns:
        Dict[str, Any]: Updated token data or None if update fails
    """
    try:
        from supabase import create_client
        from datetime import timedelta

        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")

        if not supabase_url or not supabase_key:
            raise ValueError("Supabase credentials not configured")

        if not user_id or not provider or not access_token:
            raise ValueError("User ID, provider, and access token are required")

        client = create_client(supabase_url, supabase_key)

        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        update_data = {
            "access_token": access_token,
            "token_expires_at": expires_at.isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        if provider == "airtable" and refresh_token:
            update_data["refresh_token"] = refresh_token

        # Prepare request details
        url = f"{supabase_url}/rest/v1/oauth_connections"
        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

        # Execute request
        response = (
            client.table("oauth_connections")
            .update(update_data)
            .eq("user_id", user_id)
            .eq("provider", provider)
            .execute()
        )

        import asyncio

        await asyncio.sleep(3)

        if response.data:
            return response.data[0]
        else:
            raise ValueError(
                f"No {provider} connection found to update for user {user_id}"
            )

    except Exception as e:
        logger.error(f"Error updating OAuth tokens: {str(e)}")
        raise


async def main():
    """Run the Supabase MCP server."""
    logger.info("Starting Supabase MCP Server...")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream, server.create_initialization_options()
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
