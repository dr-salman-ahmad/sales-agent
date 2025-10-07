"""
Supabase CRM MCP Server for user-specific CRM operations
"""

import os
import logging
import asyncio
from typing import Any, Sequence, Dict, List
from datetime import datetime, timezone
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from utils.helpers import setup_api_logger
from dotenv import load_dotenv

load_dotenv()

# Setup API logger
setup_api_logger()

logger = logging.getLogger(__name__)

# Create MCP server
server = Server("supabase-crm-server")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="create_leads",
            description="Create new leads in Supabase CRM",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User ID to create leads for",
                    },
                    "leads": {
                        "type": "array",
                        "description": "Array of lead records to create",
                        "items": {
                            "type": "object",
                            "properties": {
                                "company": {
                                    "type": "string",
                                    "description": "Company name",
                                },
                                "name": {
                                    "type": "string",
                                    "description": "Contact or company name",
                                },
                                "title": {
                                    "type": "string",
                                    "description": "Job title or position",
                                },
                                "address": {
                                    "type": "string",
                                    "description": "Physical address",
                                },
                                "website": {
                                    "type": "string",
                                    "description": "Company website URL",
                                },
                                "rating": {
                                    "type": "string",
                                    "description": "Company rating",
                                },
                                "opening_hours": {
                                    "type": "string",
                                    "description": "Business opening hours",
                                },
                                "phone": {
                                    "type": "string",
                                    "description": "Phone number",
                                },
                                "email": {
                                    "type": "string",
                                    "description": "Email address",
                                },
                                "background": {
                                    "type": "string",
                                    "description": "Company background and description",
                                },
                                "enriched": {
                                    "type": "boolean",
                                    "description": "Whether the lead has been enriched",
                                    "default": False,
                                },
                                "score": {
                                    "type": "string",
                                    "description": "Lead qualification score (Hot, Warm, Cold)",
                                },
                                "industry": {
                                    "type": "string",
                                    "description": "Company industry",
                                },
                                "employees": {
                                    "type": "string",
                                    "description": "Number of employees",
                                },
                                "linkedin": {
                                    "type": "string",
                                    "description": "LinkedIn profile URL",
                                },
                                "funding_round": {
                                    "type": "string",
                                    "description": "Recent funding information",
                                },
                                "new_hires": {
                                    "type": "string",
                                    "description": "Recent hiring activity",
                                },
                                "product_launch": {
                                    "type": "string",
                                    "description": "Product launch information",
                                },
                                "personalized_opener": {
                                    "type": "string",
                                    "description": "Personalized email opener",
                                },
                                "campaign": {
                                    "type": "string",
                                    "description": "Campaign name or identifier",
                                },
                            },
                        },
                    },
                },
                "required": ["user_id", "leads"],
            },
        ),
        Tool(
            name="update_lead",
            description="Update a lead in Supabase CRM",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User ID",
                    },
                    "lead_id": {
                        "type": "string",
                        "description": "Lead ID to update",
                    },
                    "fields": {
                        "type": "object",
                        "description": "Fields to update",
                        "properties": {
                            "company": {
                                "type": "string",
                                "description": "Company name",
                            },
                            "name": {
                                "type": "string",
                                "description": "Contact or company name",
                            },
                            "title": {
                                "type": "string",
                                "description": "Job title",
                            },
                            "address": {
                                "type": "string",
                                "description": "Physical address",
                            },
                            "website": {
                                "type": "string",
                                "description": "Company website URL",
                            },
                            "phone": {
                                "type": "string",
                                "description": "Phone number",
                            },
                            "email": {
                                "type": "string",
                                "description": "Email address",
                            },
                            "background": {
                                "type": "string",
                                "description": "Company background",
                            },
                            "enriched": {
                                "type": "boolean",
                                "description": "Whether lead has been enriched",
                            },
                            "score": {
                                "type": "string",
                                "description": "Lead qualification score",
                            },
                            "industry": {
                                "type": "string",
                                "description": "Company industry",
                            },
                            "employees": {
                                "type": "string",
                                "description": "Number of employees",
                            },
                            "linkedin": {
                                "type": "string",
                                "description": "LinkedIn profile URL",
                            },
                            "funding_round": {
                                "type": "string",
                                "description": "Recent funding information",
                            },
                            "new_hires": {
                                "type": "string",
                                "description": "Recent hiring activity",
                            },
                            "product_launch": {
                                "type": "string",
                                "description": "Product launch information",
                            },
                            "personalized_opener": {
                                "type": "string",
                                "description": "Personalized email opener",
                            },
                            "campaign": {
                                "type": "string",
                                "description": "Campaign identifier",
                            },
                        },
                    },
                },
                "required": ["user_id", "lead_id", "fields"],
            },
        ),
        Tool(
            name="search_leads",
            description="Search leads in Supabase CRM",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User ID to search leads for",
                    },
                    "agent_id": {
                        "type": "string",
                        "description": "Agent ID to filter by (optional)",
                    },
                    "filters": {
                        "type": "object",
                        "description": "Search filters",
                        "properties": {
                            "score": {
                                "type": "string",
                                "description": "Filter by score (Hot, Warm, Cold)",
                            },
                            "enriched": {
                                "type": "boolean",
                                "description": "Filter by enrichment status",
                            },
                            "industry": {
                                "type": "string",
                                "description": "Filter by industry",
                            },
                            "campaign": {
                                "type": "string",
                                "description": "Filter by campaign",
                            },
                            "personalized_opener": {
                                "type": "string",
                                "description": "Filter by personalized opener status (empty, not_empty)",
                            },
                            "email": {
                                "type": "string",
                                "description": "Filter by email status (empty, not_empty)",
                            },
                            "website": {
                                "type": "string",
                                "description": "Filter by website status (empty, not_empty)",
                            },
                        },
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of records to return",
                        "default": 100,
                    },
                },
                "required": ["user_id"],
            },
        ),
        Tool(
            name="get_lead_stats",
            description="Get lead statistics for user",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User ID to get stats for",
                    },
                    "agent_id": {
                        "type": "string",
                        "description": "Agent ID to filter by (optional)",
                    },
                },
                "required": ["user_id"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> Sequence[TextContent]:
    """Handle tool calls."""
    if name == "create_leads":
        return await create_leads(arguments)
    elif name == "update_lead":
        return await update_lead(arguments)
    elif name == "search_leads":
        return await search_leads(arguments)
    elif name == "get_lead_stats":
        return await get_lead_stats(arguments)

    raise ValueError(f"Unknown tool: {name}")


async def create_leads(arguments: Dict[str, Any]) -> Sequence[TextContent]:
    """Create new leads in Supabase CRM"""
    try:
        from supabase import create_client
        import json

        # Get Supabase credentials
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")

        if not supabase_url or not supabase_key:
            return [
                TextContent(
                    type="text", text="Error: Supabase credentials not configured"
                )
            ]

        user_id = arguments.get("user_id")
        leads = arguments.get("leads", [])

        if not user_id:
            return [TextContent(type="text", text="Error: User ID is required")]

        if not leads:
            return [TextContent(type="text", text="Error: No leads provided")]

        logger.info(f"Creating {len(leads)} leads in Supabase CRM for user {user_id}")

        # Process leads to ensure each has required fields
        processed_leads = []
        for lead in leads:
            # Add user_id to each lead
            lead_data = {
                "user_id": user_id,
                "company": lead.get("company"),
                "name": lead.get("name", "Unknown"),
                "title": lead.get("title"),
                "address": lead.get("address"),
                "website": lead.get("website"),
                "rating": lead.get("rating"),
                "opening_hours": lead.get("opening_hours"),
                "phone": lead.get("phone"),
                "email": lead.get("email"),
                "background": lead.get("background"),
                "enriched": lead.get("enriched", False),
                "score": lead.get("score"),
                "industry": lead.get("industry"),
                "employees": lead.get("employees"),
                "linkedin": lead.get("linkedin"),
                "funding_round": lead.get("funding_round"),
                "new_hires": lead.get("new_hires"),
                "product_launch": lead.get("product_launch"),
                "personalized_opener": lead.get("personalized_opener"),
                "campaign": lead.get("campaign"),
            }

            processed_leads.append(lead_data)

        # Create Supabase client
        client = create_client(supabase_url, supabase_key)

        # Insert leads
        response = client.table("user_crm").insert(processed_leads).execute()

        if response.data:
            logger.info(
                f"Successfully created {len(response.data)} leads in Supabase CRM"
            )
            return [
                TextContent(
                    type="text",
                    text=f"Successfully created {len(response.data)} leads in Supabase CRM",
                )
            ]
        else:
            error_msg = "Failed to create leads: No data returned"
            logger.error(error_msg)
            return [TextContent(type="text", text=f"Error: {error_msg}")]

    except Exception as e:
        error_msg = f"Error creating leads: {str(e)}"
        logger.error(error_msg)
        return [TextContent(type="text", text=f"Error: {error_msg}")]


async def update_lead(arguments: Dict[str, Any]) -> Sequence[TextContent]:
    """Update a lead in Supabase CRM"""
    try:
        from supabase import create_client

        # Get Supabase credentials
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")

        if not supabase_url or not supabase_key:
            return [
                TextContent(
                    type="text", text="Error: Supabase credentials not configured"
                )
            ]

        user_id = arguments.get("user_id")
        lead_id = arguments.get("lead_id")
        fields = arguments.get("fields", {})

        if not user_id or not lead_id:
            return [
                TextContent(
                    type="text",
                    text="Error: User ID and lead ID are required",
                )
            ]

        logger.info(f"Updating lead {lead_id} in Supabase CRM for user {user_id}")

        # Add updated_at timestamp
        fields["updated_at"] = datetime.now(timezone.utc).isoformat()

        # Create Supabase client
        client = create_client(supabase_url, supabase_key)

        # Update lead
        response = (
            client.table("user_crm")
            .update(fields)
            .eq("id", lead_id)
            .eq("user_id", user_id)
            .execute()
        )

        if response.data:
            logger.info(f"Successfully updated lead {lead_id}")
            return [
                TextContent(type="text", text=f"Successfully updated lead {lead_id}")
            ]
        else:
            error_msg = f"Failed to update lead {lead_id}: No data returned"
            logger.error(error_msg)
            return [TextContent(type="text", text=f"Error: {error_msg}")]

    except Exception as e:
        error_msg = f"Error updating lead: {str(e)}"
        logger.error(error_msg)
        return [TextContent(type="text", text=f"Error: {error_msg}")]


async def search_leads(arguments: Dict[str, Any]) -> Sequence[TextContent]:
    """Search leads in Supabase CRM"""
    try:
        from supabase import create_client

        # Get Supabase credentials
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")

        if not supabase_url or not supabase_key:
            return [
                TextContent(
                    type="text", text="Error: Supabase credentials not configured"
                )
            ]

        user_id = arguments.get("user_id")
        filters = arguments.get("filters", {})
        limit = arguments.get("limit", 100)

        if not user_id:
            return [TextContent(type="text", text="Error: User ID is required")]

        logger.info(
            f"Searching leads in Supabase CRM for user {user_id} with filters: {filters}"
        )

        # Create Supabase client
        client = create_client(supabase_url, supabase_key)

        # Build query
        query = client.table("user_crm").select("*").eq("user_id", user_id)

        # Apply filters
        if filters.get("enriched") is not None:
            query = query.eq("enriched", filters["enriched"])

        if filters.get("industry"):
            query = query.eq("industry", filters["industry"])

        if filters.get("campaign"):
            query = query.eq("campaign", filters["campaign"])

        # Handle personalized_opener filter
        if filters.get("personalized_opener") == "empty":
            query = query.is_("personalized_opener", "null")
        elif filters.get("personalized_opener") == "not_empty":
            query = query.not_.is_("personalized_opener", "null").not_.eq(
                "personalized_opener", ""
            )

        # Handle email filter
        if filters.get("email") == "empty":
            query = query.is_("email", "null")
        elif filters.get("email") == "not_empty":
            query = query.not_.is_("email", "null").not_.eq("email", "")

        # Handle website filter
        if filters.get("website") == "empty":
            query = query.is_("website", "null")
        elif filters.get("website") == "not_empty":
            query = query.not_.is_("website", "null").not_.eq("website", "")

        if filters.get("score") == "empty":
            query = query.is_("score", "null")
        elif filters.get("score"):
            query = query.eq("score", filters["score"])

        # Apply limit
        query = query.limit(limit)

        # Execute query
        response = query.execute()

        if response.data:
            records = response.data
            result_text = f"Found {len(records)} leads:\n\n"

            for i, record in enumerate(records, 1):
                result_text += f"{i}. {record.get('name', 'Unknown')}\n"
                result_text += f"   ID: {record.get('id')}\n"

                if record.get("company"):
                    result_text += f"   Company: {record['company']}\n"
                if record.get("name"):
                    result_text += f"   Name: {record['name']}\n"
                if record.get("title"):
                    result_text += f"   Title: {record['title']}\n"
                if record.get("email"):
                    result_text += f"   Email: {record['email']}\n"
                if record.get("website"):
                    result_text += f"   Website: {record['website']}\n"
                if record.get("phone"):
                    result_text += f"   Phone: {record['phone']}\n"
                if record.get("industry"):
                    result_text += f"   Industry: {record['industry']}\n"
                if record.get("employees"):
                    result_text += f"   Employees: {record['employees']}\n"
                if record.get("linkedin"):
                    result_text += f"   LinkedIn: {record['linkedin']}\n"
                if record.get("score"):
                    result_text += f"   Score: {record['score']}\n"
                if record.get("enriched"):
                    result_text += f"   Enriched: {record['enriched']}\n"
                if record.get("personalized_opener"):
                    result_text += (
                        f"   Personalized Opener: {record['personalized_opener']}\n"
                    )
                if record.get("campaign"):
                    result_text += f"   Campaign: {record['campaign']}\n"

                result_text += "\n"

            return [TextContent(type="text", text=result_text)]
        else:
            return [
                TextContent(type="text", text="No leads found matching the criteria")
            ]

    except Exception as e:
        error_msg = f"Error searching leads: {str(e)}"
        logger.error(error_msg)
        return [TextContent(type="text", text=f"Error: {error_msg}")]


async def get_lead_stats(arguments: Dict[str, Any]) -> Sequence[TextContent]:
    """Get lead statistics for user"""
    try:
        from supabase import create_client

        # Get Supabase credentials
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

        logger.info(f"Getting lead statistics for user {user_id}")

        # Create Supabase client
        client = create_client(supabase_url, supabase_key)

        # Build base query
        base_query = client.table("user_crm").select("*").eq("user_id", user_id)

        # Get total leads
        total_response = base_query.execute()
        total_leads = len(total_response.data) if total_response.data else 0

        # Get enriched leads
        enriched_response = base_query.eq("enriched", True).execute()
        enriched_count = len(enriched_response.data) if enriched_response.data else 0

        # Get leads by score
        hot_response = base_query.eq("score", "Hot").execute()
        hot_count = len(hot_response.data) if hot_response.data else 0

        warm_response = base_query.eq("score", "Warm").execute()
        warm_count = len(warm_response.data) if warm_response.data else 0

        cold_response = base_query.eq("score", "Cold").execute()
        cold_count = len(cold_response.data) if cold_response.data else 0

        # Get leads with personalized openers
        personalized_response = (
            base_query.not_.is_("personalized_opener", "null")
            .not_.eq("personalized_opener", "")
            .execute()
        )
        personalized_count = (
            len(personalized_response.data) if personalized_response.data else 0
        )

        # Calculate percentages
        enriched_percentage = (
            (enriched_count / total_leads * 100) if total_leads > 0 else 0
        )
        personalized_percentage = (
            (personalized_count / total_leads * 100) if total_leads > 0 else 0
        )

        # Build stats text
        stats_text = f"Lead Statistics for User {user_id}:\n\n"
        stats_text += f"📊 Total Leads: {total_leads}\n"
        stats_text += (
            f"🔍 Enriched Leads: {enriched_count} ({enriched_percentage:.1f}%)\n"
        )
        stats_text += f"✍️ Personalized Leads: {personalized_count} ({personalized_percentage:.1f}%)\n\n"
        stats_text += f"🎯 Score Distribution:\n"
        stats_text += f"   🔥 Hot: {hot_count}\n"
        stats_text += f"   🔶 Warm: {warm_count}\n"
        stats_text += f"   ❄️ Cold: {cold_count}\n"
        stats_text += (
            f"   📝 Unscored: {total_leads - hot_count - warm_count - cold_count}\n"
        )

        return [TextContent(type="text", text=stats_text)]

    except Exception as e:
        error_msg = f"Error getting lead stats: {str(e)}"
        logger.error(error_msg)
        return [TextContent(type="text", text=f"Error: {error_msg}")]


async def main():
    """Run the Supabase CRM MCP server."""
    logger.info("Starting Supabase CRM MCP Server...")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream, server.create_initialization_options()
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
