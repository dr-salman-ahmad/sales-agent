"""
Azure Logic App MCP Server for lead discovery
"""

import os
import logging
import asyncio
from typing import Any, Sequence, Dict, List
import httpx
from dotenv import load_dotenv

load_dotenv()
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

logger = logging.getLogger(__name__)

# Create MCP server
server = Server("azure-logic-app-server")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="search_companies",
            description="Search for companies using Azure Logic App endpoint",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for companies (e.g., 'Find 5 healthtech companies in Toronto')",
                    },
                    "industry": {
                        "type": "string",
                        "description": "Target industry filter",
                    },
                    "location": {
                        "type": "string",
                        "description": "Target location filter",
                    },
                    "min_employees": {
                        "type": "integer",
                        "description": "Minimum number of employees",
                    },
                    "num_companies": {
                        "type": "integer",
                        "description": "Number of companies to find",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> Sequence[TextContent]:
    """Handle tool calls."""
    if name == "search_companies":
        return await search_companies(arguments)

    raise ValueError(f"Unknown tool: {name}")


async def search_companies(arguments: Dict[str, Any]) -> Sequence[TextContent]:
    """Search for companies using Azure Logic App"""
    try:
        azure_url = os.getenv("AZURE_LOGIC_APP_URL")
        if not azure_url:
            return [
                TextContent(
                    type="text", text="Error: AZURE_LOGIC_APP_URL not configured"
                )
            ]

        # Prepare request payload
        payload = {"HTTP_request_content": arguments.get("query", "")}

        # Add optional filters if provided
        if arguments.get("industry"):
            payload["industry"] = arguments["industry"]
        if arguments.get("location"):
            payload["location"] = arguments["location"]
        if arguments.get("min_employees"):
            payload["min_employees"] = arguments["min_employees"]
        if arguments.get("num_companies"):
            payload["num_companies"] = arguments["num_companies"]

        logger.info(f"Calling Azure Logic App with payload: {payload}")

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                azure_url, json=payload, headers={"Content-Type": "application/json"}
            )

            if response.status_code == 200:
                result = response.text
                logger.info(
                    f"Azure Logic App response received: {len(result)} characters"
                )

                return [
                    TextContent(
                        type="text", text=f"Company search results:\n\n{result}"
                    )
                ]
            else:
                error_msg = f"Azure Logic App request failed with status {response.status_code}: {response.text}"
                logger.error(error_msg)
                return [TextContent(type="text", text=f"Error: {error_msg}")]

    except Exception as e:
        error_msg = f"Error calling Azure Logic App: {str(e)}"
        logger.error(error_msg)
        return [TextContent(type="text", text=f"Error: {error_msg}")]


async def main():
    """Run the Azure Logic App MCP server."""
    logger.info("Starting Azure Logic App MCP Server...")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream, server.create_initialization_options()
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
