"""
Airtable CRM MCP Server for user-specific CRM operations
"""

import os
import logging
import asyncio
from typing import Any, Sequence, Dict, List
import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from utils.helpers import setup_api_logger, log_api_interaction

# Setup API logger
setup_api_logger()

logger = logging.getLogger(__name__)

# Create MCP server
server = Server("airtable-crm-server")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="get_base_id",
            description="Get the base ID for user's Sales Agent CRM",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User ID to get base ID for",
                    }
                },
                "required": ["user_id"],
            },
        ),
        Tool(
            name="create_leads",
            description="Create new leads in user's Airtable CRM",
            inputSchema={
                "type": "object",
                "properties": {
                    "access_token": {
                        "type": "string",
                        "description": "User's Airtable access token",
                    },
                    "base_id": {"type": "string", "description": "Airtable base ID"},
                    "leads": {
                        "type": "array",
                        "description": "Array of lead records to create",
                        "items": {
                            "type": "object",
                            "properties": {
                                "fields": {
                                    "type": "object",
                                    "description": "Lead fields",
                                    "properties": {
                                        "UUID": {
                                            "type": "string",
                                            "description": "Unique identifier for the lead",
                                        },
                                        "Name": {
                                            "type": "string",
                                            "description": "Lead's name",
                                        },
                                        "Address": {
                                            "type": "string",
                                            "description": "Lead's address",
                                        },
                                        "Website": {
                                            "type": "string",
                                            "description": "Lead's website URL",
                                        },
                                        "Email": {
                                            "type": "string",
                                            "description": "Lead's email address",
                                        },
                                        "Phone": {
                                            "type": "string",
                                            "description": "Lead's phone number",
                                        },
                                        "Title": {
                                            "type": "string",
                                            "description": "Lead's job title",
                                        },
                                        "Company": {
                                            "type": "string",
                                            "description": "Lead's company name",
                                        },
                                        "Background": {
                                            "type": "string",
                                            "description": "Description of the lead",
                                        },
                                    },
                                    "required": ["Name", "Company"],
                                }
                            },
                        },
                    },
                },
                "required": ["access_token", "base_id", "leads"],
            },
        ),
        Tool(
            name="update_lead",
            description="Update a lead in user's Airtable CRM",
            inputSchema={
                "type": "object",
                "properties": {
                    "access_token": {
                        "type": "string",
                        "description": "User's Airtable access token",
                    },
                    "base_id": {"type": "string", "description": "Airtable base ID"},
                    "record_id": {
                        "type": "string",
                        "description": "Record ID to update",
                    },
                    "fields": {
                        "type": "object",
                        "description": "Fields to update",
                        "properties": {
                            "Industry": {
                                "type": "string",
                                "description": "Company's industry from Hunter.io",
                            },
                            "Employees": {
                                "type": "string",
                                "description": "Company's employee count from Hunter.io",
                            },
                            "LinkedIn": {
                                "type": "string",
                                "description": "Company's LinkedIn profile URL",
                            },
                            "Product Launch": {
                                "type": "string",
                                "description": "Product launch information from company description",
                            },
                            "Email": {
                                "type": "string",
                                "description": "Lead's email address from Hunter.io",
                            },
                            "Address": {
                                "type": "string",
                                "description": "Lead's address",
                            },
                            "Enriched": {
                                "type": "boolean",
                                "description": "Whether the lead has been enriched with Hunter.io data",
                                "default": True,
                            },
                        },
                    },
                },
                "required": ["access_token", "base_id", "record_id", "fields"],
            },
        ),
        Tool(
            name="search_leads",
            description="Search leads in user's Airtable CRM",
            inputSchema={
                "type": "object",
                "properties": {
                    "access_token": {
                        "type": "string",
                        "description": "User's Airtable access token",
                    },
                    "base_id": {"type": "string", "description": "Airtable base ID"},
                    "filter_formula": {
                        "type": "string",
                        "description": "Airtable filter formula",
                    },
                    "max_records": {
                        "type": "integer",
                        "description": "Maximum number of records to return",
                        "default": 100,
                    },
                },
                "required": ["access_token", "base_id"],
            },
        ),
        Tool(
            name="get_personas",
            description="Get user's ICP personas from Airtable",
            inputSchema={
                "type": "object",
                "properties": {
                    "access_token": {
                        "type": "string",
                        "description": "User's Airtable access token",
                    },
                    "base_id": {"type": "string", "description": "Airtable base ID"},
                    "user_id": {
                        "type": "string",
                        "description": "User ID to filter personas",
                    },
                },
                "required": ["access_token", "base_id", "user_id"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> Sequence[TextContent]:
    """Handle tool calls."""
    if name == "get_base_id":
        return await get_base_id(arguments)
    elif name == "create_leads":
        return await create_leads(arguments)
    elif name == "update_lead":
        return await update_lead(arguments)
    elif name == "search_leads":
        return await search_leads(arguments)
    elif name == "get_personas":
        return await get_personas(arguments)

    raise ValueError(f"Unknown tool: {name}")


async def get_base_id(arguments: Dict[str, Any]) -> Sequence[TextContent]:
    """Get the base ID for user's Sales Agent CRM"""
    try:
        from supabase import create_client
        import json
        from dotenv import load_dotenv

        load_dotenv()

        # Get Supabase credentials
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")

        if not supabase_url or not supabase_key:
            return [
                TextContent(
                    type="text", text="Error: Supabase credentials not configured"
                )
            ]

        # Get user_id from access token or arguments
        user_id = arguments.get("user_id")
        if not user_id:
            return [TextContent(type="text", text="Error: User ID is required")]

        # Get Airtable token from Supabase
        client = create_client(supabase_url, supabase_key)
        response = (
            client.table("oauth_connections")
            .select("*")
            .eq("user_id", user_id)
            .eq("provider", "airtable")
            .eq("is_active", True)
            .execute()
        )

        if not response.data:
            return [
                TextContent(
                    type="text",
                    text=f"No active Airtable connection found for user {user_id}",
                )
            ]

        access_token = response.data[0]["access_token"]
        logger.info("Getting user's Airtable bases")

        headers = {"Authorization": f"Bearer {access_token}"}
        url = "https://api.airtable.com/v0/meta/bases"

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(url, headers=headers)

                # Log the API interaction
                log_api_interaction(
                    method="GET", url=url, headers=headers, response=response
                )
            except Exception as e:
                # Log the failed API interaction
                log_api_interaction(method="GET", url=url, headers=headers, error=e)
                raise

            if response.status_code == 200:
                data = response.json()
                bases = data.get("bases", [])

                # Find Sales Agent CRM base
                for base in bases:
                    if base.get("name") == "Sales Agent CRM":
                        return [
                            TextContent(
                                type="text",
                                text=f"Found Sales Agent CRM base ID: {base['id']}",
                            )
                        ]

                return [
                    TextContent(
                        type="text",
                        text="Error: Sales Agent CRM base not found. Please create a base named 'Sales Agent CRM' in your Airtable workspace.",
                    )
                ]
            else:
                error_msg = (
                    f"Failed to get bases: {response.status_code} - {response.text}"
                )
                logger.error(error_msg)
                return [TextContent(type="text", text=f"Error: {error_msg}")]

    except Exception as e:
        error_msg = f"Error getting base ID: {str(e)}"
        logger.error(error_msg)
        return [TextContent(type="text", text=f"Error: {error_msg}")]


async def create_leads(arguments: Dict[str, Any]) -> Sequence[TextContent]:
    """Create new leads in user's Airtable CRM"""
    try:
        from utils.helpers import generate_uuid

        access_token = arguments.get("access_token")
        base_id = arguments.get("base_id")
        leads = arguments.get("leads", [])

        if not access_token or not base_id:
            return [
                TextContent(
                    type="text", text="Error: Access token and base ID are required"
                )
            ]

        if not leads:
            return [TextContent(type="text", text="Error: No leads provided")]

        logger.info(f"Creating {len(leads)} leads in Airtable")

        # Process leads to ensure each has a UUID
        processed_leads = []
        for lead in leads:
            fields = lead.get("fields", {})
            # Generate UUID if not provided
            fields["UUID"] = generate_uuid()
            processed_leads.append({"fields": fields})

        url = f"https://api.airtable.com/v0/{base_id}/Demo%20Table"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        body = {"records": processed_leads}

        # Log the request
        log_api_interaction(method="POST", url=url, headers=headers, body=body)

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, json=body)

            # Log the response
            log_api_interaction(
                method="POST", url=url, headers=headers, response=response
            )

            if response.status_code == 200:
                data = response.json()
                created_records = data.get("records", [])

                return [
                    TextContent(
                        type="text",
                        text=f"Successfully created {len(created_records)} leads in Airtable CRM",
                    )
                ]
            else:
                error_msg = (
                    f"Failed to create leads: {response.status_code} - {response.text}"
                )
                logger.error(error_msg)
                return [TextContent(type="text", text=f"Error: {error_msg}")]

    except Exception as e:
        error_msg = f"Error creating leads: {str(e)}"
        logger.error(error_msg)
        return [TextContent(type="text", text=f"Error: {error_msg}")]


async def update_lead(arguments: Dict[str, Any]) -> Sequence[TextContent]:
    """Update a lead in user's Airtable CRM"""
    try:
        access_token = arguments.get("access_token")
        base_id = arguments.get("base_id")
        record_id = arguments.get("record_id")
        fields = arguments.get("fields", {})

        if not access_token or not base_id or not record_id:
            return [
                TextContent(
                    type="text",
                    text="Error: Access token, base ID, and record ID are required",
                )
            ]

        logger.info(f"Updating lead {record_id} in Airtable")

        url = f"https://api.airtable.com/v0/{base_id}/Demo%20Table/{record_id}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        body = {"fields": fields}

        # Log the request
        log_api_interaction(method="PATCH", url=url, headers=headers, body=body)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.patch(url, headers=headers, json=body)

            # Log the response
            log_api_interaction(
                method="PATCH", url=url, headers=headers, response=response
            )

            if response.status_code == 200:
                return [
                    TextContent(
                        type="text", text=f"Successfully updated lead {record_id}"
                    )
                ]
            else:
                error_msg = (
                    f"Failed to update lead: {response.status_code} - {response.text}"
                )
                logger.error(error_msg)
                return [TextContent(type="text", text=f"Error: {error_msg}")]

    except Exception as e:
        error_msg = f"Error updating lead: {str(e)}"
        logger.error(error_msg)
        return [TextContent(type="text", text=f"Error: {error_msg}")]


async def search_leads(arguments: Dict[str, Any]) -> Sequence[TextContent]:
    """Search leads in user's Airtable CRM"""
    try:
        access_token = arguments.get("access_token")
        base_id = arguments.get("base_id")
        filter_formula = arguments.get("filter_formula")
        max_records = arguments.get("max_records", 100)

        if not access_token or not base_id:
            return [
                TextContent(
                    type="text", text="Error: Access token and base ID are required"
                )
            ]

        logger.info(f"Searching leads in Airtable with filter: {filter_formula}")

        params = {"maxRecords": max_records}
        if filter_formula:
            params["filterByFormula"] = filter_formula

        url = f"https://api.airtable.com/v0/{base_id}/Demo%20Table"
        headers = {"Authorization": f"Bearer {access_token}"}

        # Log the request
        log_api_interaction(
            method="GET", url=url, headers=headers, body={"params": params}
        )

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers, params=params)

            # Log the response
            log_api_interaction(
                method="GET", url=url, headers=headers, response=response
            )

            if response.status_code == 200:
                data = response.json()
                records = data.get("records", [])

                if records:
                    result_text = f"Found {len(records)} leads:\n\n"
                    for i, record in enumerate(records, 1):
                        fields = record.get("fields", {})
                        result_text += f"{i}. {fields.get('Name', 'Unknown')}\n"
                        result_text += f"   ID: {record.get('id')}\n"
                        if fields.get("Email"):
                            result_text += f"   Email: {fields['Email']}\n"
                        if fields.get("Industry"):
                            result_text += f"   Industry: {fields['Industry']}\n"
                        if fields.get("Score"):
                            result_text += f"   Score: {fields['Score']}\n"
                        result_text += "\n"

                    return [TextContent(type="text", text=result_text)]
                else:
                    return [
                        TextContent(
                            type="text", text="No leads found matching the criteria"
                        )
                    ]
            else:
                error_msg = (
                    f"Failed to search leads: {response.status_code} - {response.text}"
                )
                logger.error(error_msg)
                return [TextContent(type="text", text=f"Error: {error_msg}")]

    except Exception as e:
        error_msg = f"Error searching leads: {str(e)}"
        logger.error(error_msg)
        return [TextContent(type="text", text=f"Error: {error_msg}")]


async def get_personas(arguments: Dict[str, Any]) -> Sequence[TextContent]:
    """Get user's ICP personas from Airtable"""
    try:
        access_token = arguments.get("access_token")
        base_id = arguments.get("base_id")
        user_id = arguments.get("user_id")

        if not access_token or not base_id or not user_id:
            return [
                TextContent(
                    type="text",
                    text="Error: Access token, base ID, and user ID are required",
                )
            ]

        logger.info(f"Getting personas for user {user_id}")

        url = f"https://api.airtable.com/v0/{base_id}/Personas"
        headers = {"Authorization": f"Bearer {access_token}"}
        params = {
            "filterByFormula": f'{{User ID}} = "{user_id}"',
            "maxRecords": 1,
        }

        # Log the request
        log_api_interaction(
            method="GET", url=url, headers=headers, body={"params": params}
        )

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers, params=params)

            # Log the response
            log_api_interaction(
                method="GET", url=url, headers=headers, response=response
            )

            if response.status_code == 200:
                data = response.json()
                records = data.get("records", [])

                if records:
                    persona = records[0].get("fields", {})

                    result_text = f"User's ICP Persona:\n\n"
                    result_text += f"Name: {persona.get('Name', 'Default Persona')}\n"
                    result_text += f"Target Industries: {persona.get('Target Industries', 'Not specified')}\n"
                    result_text += f"Company Size: {persona.get('Company Size Range', 'Not specified')}\n"
                    result_text += (
                        f"Job Titles: {persona.get('Job Titles', 'Not specified')}\n"
                    )
                    result_text += (
                        f"Pain Points: {persona.get('Pain Points', 'Not specified')}\n"
                    )
                    result_text += (
                        f"Use Cases: {persona.get('Use Cases', 'Not specified')}\n"
                    )

                    return [TextContent(type="text", text=result_text)]
                else:
                    return [
                        TextContent(
                            type="text",
                            text=f"No persona found for user {user_id}. Please create an ICP persona in your Airtable CRM.",
                        )
                    ]
            else:
                error_msg = (
                    f"Failed to get personas: {response.status_code} - {response.text}"
                )
                logger.error(error_msg)
                return [TextContent(type="text", text=f"Error: {error_msg}")]

    except Exception as e:
        error_msg = f"Error getting personas: {str(e)}"
        logger.error(error_msg)
        return [TextContent(type="text", text=f"Error: {error_msg}")]


async def main():
    """Run the Airtable CRM MCP server."""
    logger.info("Starting Airtable CRM MCP Server...")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream, server.create_initialization_options()
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
