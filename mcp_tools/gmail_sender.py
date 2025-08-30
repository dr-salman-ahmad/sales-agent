"""
Gmail MCP Server for sending emails
"""

import os
import logging
import asyncio
import base64
from typing import Any, Sequence, Dict
import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

logger = logging.getLogger(__name__)

# Create MCP server
server = Server("gmail-sender-server")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="send_email",
            description="Send an email using Gmail API",
            inputSchema={
                "type": "object",
                "properties": {
                    "access_token": {
                        "type": "string",
                        "description": "User's Gmail access token",
                    },
                    "from_email": {
                        "type": "string",
                        "description": "Sender email address",
                    },
                    "to_email": {
                        "type": "string",
                        "description": "Recipient email address",
                    },
                    "subject": {"type": "string", "description": "Email subject"},
                    "body": {"type": "string", "description": "Email body content"},
                    "is_html": {
                        "type": "boolean",
                        "description": "Whether the body is HTML format",
                        "default": False,
                    },
                },
                "required": [
                    "access_token",
                    "from_email",
                    "to_email",
                    "subject",
                    "body",
                ],
            },
        ),
        Tool(
            name="create_draft",
            description="Create a draft email in Gmail",
            inputSchema={
                "type": "object",
                "properties": {
                    "access_token": {
                        "type": "string",
                        "description": "User's Gmail access token",
                    },
                    "from_email": {
                        "type": "string",
                        "description": "Sender email address",
                    },
                    "to_email": {
                        "type": "string",
                        "description": "Recipient email address",
                    },
                    "subject": {"type": "string", "description": "Email subject"},
                    "body": {"type": "string", "description": "Email body content"},
                    "is_html": {
                        "type": "boolean",
                        "description": "Whether the body is HTML format",
                        "default": False,
                    },
                },
                "required": [
                    "access_token",
                    "from_email",
                    "to_email",
                    "subject",
                    "body",
                ],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> Sequence[TextContent]:
    """Handle tool calls."""
    if name == "send_email":
        return await send_email(arguments)
    elif name == "create_draft":
        return await create_draft(arguments)

    raise ValueError(f"Unknown tool: {name}")


def create_mime_message(
    from_email: str, to_email: str, subject: str, body: str, is_html: bool = False
) -> str:
    """Create MIME email message and encode it for Gmail API"""
    content_type = "text/html" if is_html else "text/plain"

    mime_message = (
        f"From: {from_email}\r\n"
        f"To: {to_email}\r\n"
        f"Subject: {subject}\r\n"
        f'Content-Type: {content_type}; charset="UTF-8"\r\n'
        f"\r\n"
        f"{body}"
    )

    # Encode to base64 URL-safe
    return base64.urlsafe_b64encode(mime_message.encode()).decode()


async def send_email(arguments: Dict[str, Any]) -> Sequence[TextContent]:
    """Send an email using Gmail API"""
    try:
        access_token = arguments.get("access_token")
        from_email = arguments.get("from_email")
        to_email = arguments.get("to_email")
        subject = arguments.get("subject")
        body = arguments.get("body")
        is_html = arguments.get("is_html", False)

        if not all([access_token, from_email, to_email, subject, body]):
            return [
                TextContent(type="text", text="Error: All email fields are required")
            ]

        logger.info(f"Sending email from {from_email} to {to_email}")

        # Create MIME message
        raw_message = create_mime_message(from_email, to_email, subject, body, is_html)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={"raw": raw_message},
            )

            if response.status_code == 200:
                data = response.json()
                message_id = data.get("id", "unknown")

                return [
                    TextContent(
                        type="text",
                        text=f"Email sent successfully! Message ID: {message_id}",
                    )
                ]
            else:
                error_msg = (
                    f"Failed to send email: {response.status_code} - {response.text}"
                )
                logger.error(error_msg)
                return [TextContent(type="text", text=f"Error: {error_msg}")]

    except Exception as e:
        error_msg = f"Error sending email: {str(e)}"
        logger.error(error_msg)
        return [TextContent(type="text", text=f"Error: {error_msg}")]


async def create_draft(arguments: Dict[str, Any]) -> Sequence[TextContent]:
    """Create a draft email in Gmail"""
    try:
        access_token = arguments.get("access_token")
        from_email = arguments.get("from_email")
        to_email = arguments.get("to_email")
        subject = arguments.get("subject")
        body = arguments.get("body")
        is_html = arguments.get("is_html", False)

        if not all([access_token, from_email, to_email, subject, body]):
            return [
                TextContent(type="text", text="Error: All email fields are required")
            ]

        logger.info(f"Creating draft email from {from_email} to {to_email}")

        # Create MIME message
        raw_message = create_mime_message(from_email, to_email, subject, body, is_html)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://gmail.googleapis.com/gmail/v1/users/me/drafts",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={"message": {"raw": raw_message}},
            )

            if response.status_code == 200:
                data = response.json()
                draft_id = data.get("id", "unknown")

                return [
                    TextContent(
                        type="text",
                        text=f"Draft created successfully! Draft ID: {draft_id}",
                    )
                ]
            else:
                error_msg = (
                    f"Failed to create draft: {response.status_code} - {response.text}"
                )
                logger.error(error_msg)
                return [TextContent(type="text", text=f"Error: {error_msg}")]

    except Exception as e:
        error_msg = f"Error creating draft: {str(e)}"
        logger.error(error_msg)
        return [TextContent(type="text", text=f"Error: {error_msg}")]


async def main():
    """Run the Gmail MCP server."""
    logger.info("Starting Gmail MCP Server...")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream, server.create_initialization_options()
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
