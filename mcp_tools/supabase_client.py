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

logger = logging.getLogger(__name__)

# Create MCP server
server = Server("supabase-client-server")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="get_user_credentials",
            description="Get user's OAuth credentials (Gmail, Airtable) from Supabase",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User ID to get credentials for",
                    }
                },
                "required": ["user_id"],
            },
            # inputSchema={"type": "object", "properties": {}},
        ),
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
        Tool(
            name="update_oauth_tokens",
            description="Update OAuth tokens for a user and provider",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User ID to update tokens for",
                    },
                    "provider": {
                        "type": "string",
                        "description": "OAuth provider (gmail, airtable)",
                        "enum": ["gmail", "airtable"],
                    },
                    "access_token": {
                        "type": "string",
                        "description": "New access token",
                    },
                    "refresh_token": {
                        "type": "string",
                        "description": "New refresh token (optional)",
                    },
                    "expires_in": {
                        "type": "integer",
                        "description": "Token expiration time in seconds",
                        "default": 3600,
                    },
                },
                "required": ["user_id", "provider", "access_token"],
            },
        ),
        Tool(
            name="check_token_expiry",
            description="Check if a user's token is expired for a specific provider",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User ID to check",
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
        Tool(
            name="get_user_profile",
            description="Get user profile information from Supabase",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User ID to get profile for",
                    }
                },
                "required": ["user_id"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> Sequence[TextContent]:
    """Handle tool calls."""
    if name == "get_user_credentials":
        return await get_user_credentials(arguments)
    elif name == "get_oauth_connection":
        return await get_oauth_connection(arguments)
    elif name == "update_oauth_tokens":
        return await update_oauth_tokens(arguments)
    elif name == "check_token_expiry":
        return await check_token_expiry(arguments)
    elif name == "get_user_profile":
        return await get_user_profile(arguments)

    raise ValueError(f"Unknown tool: {name}")


async def get_user_credentials(
    arguments: Dict[str, Any],
) -> Sequence[TextContent]:
    """Get all user credentials organized by provider"""
    try:
        from supabase import create_client

        # logger.info(f"userId123456789: {user_id}")

        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")

        if not supabase_url or not supabase_key:
            return [
                TextContent(
                    type="text", text="Error: Supabase credentials not configured"
                )
            ]

        user_id = arguments.get("user_id")

        if not user_id:
            return [TextContent(type="text", text="Error: User ID is required")]

        client = create_client(supabase_url, supabase_key)

        # Get all OAuth connections for the user
        response = (
            client.table("oauth_connections")
            .select("*")
            .eq("user_id", user_id)
            .eq("is_active", True)
            .execute()
        )

        if not response.data:
            return [
                TextContent(
                    type="text", text=f"No active credentials found for user {user_id}"
                )
            ]

        credentials = {}
        for row in response.data:
            provider = row["provider"]
            token_expires_at = datetime.fromisoformat(
                row["token_expires_at"].replace("Z", "+00:00")
            )
            is_expired = datetime.now(timezone.utc) >= token_expires_at

            credentials[provider] = {
                "access_token": row["access_token"],
                "refresh_token": row["refresh_token"],
                "provider_email": row["provider_email"],
                "expires_at": row["token_expires_at"],
                "is_expired": is_expired,
            }

        import json

        result = {
            "user_id": user_id,
            "credentials": credentials,
            "total_providers": len(credentials),
        }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        error_msg = f"Error getting user credentials: {str(e)}"
        logger.error(error_msg)
        return [TextContent(type="text", text=f"Error: {error_msg}")]


async def get_oauth_connection(arguments: Dict[str, Any]) -> Sequence[TextContent]:
    """Get specific OAuth connection for a user and provider"""
    try:
        from supabase import create_client

        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")

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

        response = (
            client.table("oauth_connections")
            .select("*")
            .eq("user_id", user_id)
            .eq("provider", provider)
            .eq("is_active", True)
            .execute()
        )

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

        import json

        result = {
            "user_id": user_id,
            "provider": provider,
            "access_token": row["access_token"],
            "refresh_token": row["refresh_token"],
            "provider_email": row["provider_email"],
            "expires_at": row["token_expires_at"],
            "is_expired": is_expired,
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        error_msg = f"Error getting OAuth connection: {str(e)}"
        logger.error(error_msg)
        return [TextContent(type="text", text=f"Error: {error_msg}")]


async def update_oauth_tokens(arguments: Dict[str, Any]) -> Sequence[TextContent]:
    """Update OAuth tokens for a user and provider"""
    try:
        from supabase import create_client
        from datetime import timedelta

        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")

        if not supabase_url or not supabase_key:
            return [
                TextContent(
                    type="text", text="Error: Supabase credentials not configured"
                )
            ]

        user_id = arguments.get("user_id")
        provider = arguments.get("provider")
        access_token = arguments.get("access_token")
        refresh_token = arguments.get("refresh_token")
        expires_in = arguments.get("expires_in", 3600)

        if not user_id or not provider or not access_token:
            return [
                TextContent(
                    type="text",
                    text="Error: User ID, provider, and access token are required",
                )
            ]

        client = create_client(supabase_url, supabase_key)

        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        update_data = {
            "access_token": access_token,
            "token_expires_at": expires_at.isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        if provider == "airtable" and refresh_token:
            update_data["refresh_token"] = refresh_token

        response = (
            client.table("oauth_connections")
            .update(update_data)
            .eq("user_id", user_id)
            .eq("provider", provider)
            .execute()
        )

        if response.data:
            return [
                TextContent(
                    type="text",
                    text=f"Successfully updated {provider} tokens for user {user_id}",
                )
            ]
        else:
            return [
                TextContent(
                    type="text",
                    text=f"No {provider} connection found to update for user {user_id}",
                )
            ]

    except Exception as e:
        error_msg = f"Error updating OAuth tokens: {str(e)}"
        logger.error(error_msg)
        return [TextContent(type="text", text=f"Error: {error_msg}")]


async def check_token_expiry(arguments: Dict[str, Any]) -> Sequence[TextContent]:
    """Check if a user's token is expired for a specific provider"""
    try:
        from supabase import create_client

        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")

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

        response = (
            client.table("oauth_connections")
            .select("token_expires_at")
            .eq("user_id", user_id)
            .eq("provider", provider)
            .eq("is_active", True)
            .execute()
        )

        if not response.data:
            return [
                TextContent(
                    type="text",
                    text=f"No active {provider} connection found for user {user_id}",
                )
            ]

        token_expires_at = datetime.fromisoformat(
            response.data[0]["token_expires_at"].replace("Z", "+00:00")
        )
        is_expired = datetime.now(timezone.utc) >= token_expires_at

        import json

        result = {
            "user_id": user_id,
            "provider": provider,
            "expires_at": response.data[0]["token_expires_at"],
            "is_expired": is_expired,
            "expires_in_minutes": (
                int(
                    (token_expires_at - datetime.now(timezone.utc)).total_seconds() / 60
                )
                if not is_expired
                else 0
            ),
        }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        error_msg = f"Error checking token expiry: {str(e)}"
        logger.error(error_msg)
        return [TextContent(type="text", text=f"Error: {error_msg}")]


async def get_user_profile(arguments: Dict[str, Any]) -> Sequence[TextContent]:
    """Get user profile information from Supabase"""
    try:
        from supabase import create_client

        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")

        if not supabase_url or not supabase_key:
            return [
                TextContent(
                    type="text", text="Error: Supabase credentials not configured"
                )
            ]

        user_id = arguments.get("user_id")
        if not user_id:
            return [TextContent(type="text", text="Error: User ID is required")]

        client = create_client(supabase_url, supabase_key)

        response = client.table("profiles").select("*").eq("id", user_id).execute()

        if not response.data:
            return [
                TextContent(type="text", text=f"No profile found for user {user_id}")
            ]

        import json

        profile = response.data[0]

        return [TextContent(type="text", text=json.dumps(profile, indent=2))]

    except Exception as e:
        error_msg = f"Error getting user profile: {str(e)}"
        logger.error(error_msg)
        return [TextContent(type="text", text=f"Error: {error_msg}")]


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
