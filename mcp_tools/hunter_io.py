"""
Hunter.io MCP Server for email discovery
"""

import os
import logging
import asyncio
from typing import Any, Sequence, Dict
import httpx
from dotenv import load_dotenv

load_dotenv()
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

logger = logging.getLogger(__name__)

# Create MCP server
server = Server("hunter-io-server")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="find_emails",
            description="Find email addresses for a domain using Hunter.io",
            inputSchema={
                "type": "object",
                "properties": {
                    "domain": {
                        "type": "string",
                        "description": "Domain to search for emails (e.g., 'company.com')",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of emails to return",
                        "default": 10,
                    },
                },
                "required": ["domain"],
            },
        ),
        Tool(
            name="verify_email",
            description="Verify if an email address is valid using Hunter.io",
            inputSchema={
                "type": "object",
                "properties": {
                    "email": {
                        "type": "string",
                        "description": "Email address to verify",
                    }
                },
                "required": ["email"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> Sequence[TextContent]:
    """Handle tool calls."""
    if name == "find_emails":
        return await find_emails(arguments)
    elif name == "verify_email":
        return await verify_email(arguments)

    raise ValueError(f"Unknown tool: {name}")


async def find_emails(arguments: Dict[str, Any]) -> Sequence[TextContent]:
    """Find emails for a domain using Hunter.io"""
    try:
        api_key = os.getenv("HUNTER_API_KEY")
        if not api_key:
            return [
                TextContent(type="text", text="Error: HUNTER_API_KEY not configured")
            ]

        domain = (
            arguments.get("domain", "")
            .replace("https://", "")
            .replace("http://", "")
            .replace("www.", "")
        )
        limit = arguments.get("limit", 10)

        if not domain:
            return [TextContent(type="text", text="Error: Domain is required")]

        logger.info(f"Searching emails for domain: {domain}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://api.hunter.io/v2/domain-search",
                params={"domain": domain, "api_key": api_key, "limit": limit},
            )

            if response.status_code == 200:
                data = response.json()

                if data.get("data") and data["data"].get("emails"):
                    emails = data["data"]["emails"]

                    # Format email results
                    results = []
                    for email_data in emails:
                        email_info = {
                            "email": email_data.get("value", ""),
                            "first_name": email_data.get("first_name", ""),
                            "last_name": email_data.get("last_name", ""),
                            "position": email_data.get("position", ""),
                            "verification_status": email_data.get(
                                "verification", {}
                            ).get("result", ""),
                            "confidence": email_data.get("confidence", 0),
                        }
                        results.append(email_info)

                    # Return formatted results
                    result_text = f"Found {len(results)} emails for {domain}:\n\n"
                    for i, email_info in enumerate(results, 1):
                        result_text += f"{i}. {email_info['email']}\n"
                        if email_info["first_name"] or email_info["last_name"]:
                            result_text += f"   Name: {email_info['first_name']} {email_info['last_name']}\n"
                        if email_info["position"]:
                            result_text += f"   Position: {email_info['position']}\n"
                        result_text += (
                            f"   Verification: {email_info['verification_status']}\n"
                        )
                        result_text += f"   Confidence: {email_info['confidence']}%\n\n"

                    return [TextContent(type="text", text=result_text)]
                else:
                    return [
                        TextContent(
                            type="text", text=f"No emails found for domain: {domain}"
                        )
                    ]
            else:
                error_msg = f"Hunter.io API request failed with status {response.status_code}: {response.text}"
                logger.error(error_msg)
                return [TextContent(type="text", text=f"Error: {error_msg}")]

    except Exception as e:
        error_msg = f"Error calling Hunter.io API: {str(e)}"
        logger.error(error_msg)
        return [TextContent(type="text", text=f"Error: {error_msg}")]


async def verify_email(arguments: Dict[str, Any]) -> Sequence[TextContent]:
    """Verify an email address using Hunter.io"""
    try:
        api_key = os.getenv("HUNTER_API_KEY")
        if not api_key:
            return [
                TextContent(type="text", text="Error: HUNTER_API_KEY not configured")
            ]

        email = arguments.get("email", "")
        if not email:
            return [TextContent(type="text", text="Error: Email is required")]

        logger.info(f"Verifying email: {email}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://api.hunter.io/v2/email-verifier",
                params={"email": email, "api_key": api_key},
            )

            if response.status_code == 200:
                data = response.json()

                if data.get("data"):
                    verification_data = data["data"]

                    result_text = f"Email verification for {email}:\n\n"
                    result_text += (
                        f"Status: {verification_data.get('result', 'unknown')}\n"
                    )
                    result_text += f"Score: {verification_data.get('score', 0)}\n"
                    result_text += f"Regexp: {verification_data.get('regexp', False)}\n"
                    result_text += (
                        f"Gibberish: {verification_data.get('gibberish', False)}\n"
                    )
                    result_text += (
                        f"Disposable: {verification_data.get('disposable', False)}\n"
                    )
                    result_text += (
                        f"Webmail: {verification_data.get('webmail', False)}\n"
                    )
                    result_text += (
                        f"MX Records: {verification_data.get('mx_records', False)}\n"
                    )
                    result_text += (
                        f"SMTP Server: {verification_data.get('smtp_server', False)}\n"
                    )
                    result_text += (
                        f"SMTP Check: {verification_data.get('smtp_check', False)}\n"
                    )
                    result_text += (
                        f"Accept All: {verification_data.get('accept_all', False)}\n"
                    )
                    result_text += f"Block: {verification_data.get('block', False)}\n"

                    return [TextContent(type="text", text=result_text)]
                else:
                    return [
                        TextContent(
                            type="text",
                            text=f"No verification data available for: {email}",
                        )
                    ]
            else:
                error_msg = f"Hunter.io verification failed with status {response.status_code}: {response.text}"
                logger.error(error_msg)
                return [TextContent(type="text", text=f"Error: {error_msg}")]

    except Exception as e:
        error_msg = f"Error verifying email: {str(e)}"
        logger.error(error_msg)
        return [TextContent(type="text", text=f"Error: {error_msg}")]


async def main():
    """Run the Hunter.io MCP server."""
    logger.info("Starting Hunter.io MCP Server...")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream, server.create_initialization_options()
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
