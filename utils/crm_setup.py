"""
CRM Setup Utility for creating Agentflow CRM base and Contact table
"""

import os
import logging
import httpx
from typing import Dict, Any, Optional
from fastapi import HTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


async def setup_agentflow_crm(
    user_id: str, workspace_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Setup Agentflow CRM base and Contact table for a user

    Args:
        user_id (str): The user's ID
        workspace_id (Optional[str]): The workspace ID to create the base in. If None, Airtable will use default workspace.

    Returns:
        Dict[str, Any]: Response with base information

    Raises:
        HTTPException: If setup fails
    """
    try:
        from mcp_tools.supabase_client import get_oauth_connection
        from mcp.types import TextContent

        logger.info(f"Setting up CRM for user {user_id}")

        # Get OAuth connection with automatic token refresh
        oauth_response = await get_oauth_connection(
            {"user_id": user_id, "provider": "airtable"}
        )

        if not oauth_response or not isinstance(oauth_response[0], TextContent):
            raise HTTPException(
                status_code=404,
                detail=f"No active Airtable connection found for user {user_id}",
            )

        # Parse the OAuth connection data
        import json

        oauth_data = json.loads(oauth_response[0].text)
        access_token = oauth_data.get("access_token")

        if not access_token:
            raise HTTPException(
                status_code=500,
                detail="Failed to get access token from OAuth connection",
            )

        # Check if Agentflow CRM base already exists
        headers = {"Authorization": f"Bearer {access_token}"}
        url = "https://api.airtable.com/v0/meta/bases"

        async with httpx.AsyncClient(timeout=30.0) as http_client:
            response = await http_client.get(url, headers=headers)

            if response.status_code == 200:
                data = response.json()
                bases = data.get("bases", [])

                # Check if Agentflow CRM base exists
                for base in bases:
                    if base.get("name") == "Agentflow CRM":
                        logger.info(
                            f"Agentflow CRM base already exists for user {user_id}"
                        )
                        return {
                            "message": "Agentflow CRM base already exists",
                            "base_id": base["id"],
                            "base_name": base["name"],
                        }

                # Create Agentflow CRM base with Contact table
                create_base_data = {
                    "name": "Agentflow CRM",
                    "tables": [
                        {
                            "name": "Contact Table",
                            "description": "Contact table for storing leads and prospects",
                            "fields": [
                                {
                                    "name": "Name",
                                    "type": "singleLineText",
                                    "description": "Contact or company name",
                                },
                                {
                                    "name": "Company",
                                    "type": "singleLineText",
                                    "description": "Company name",
                                },
                                {
                                    "name": "UUID",
                                    "type": "singleLineText",
                                    "description": "Unique identifier for the contact",
                                },
                                {
                                    "name": "Title",
                                    "type": "singleLineText",
                                    "description": "Job title or position",
                                },
                                {
                                    "name": "Address",
                                    "type": "singleLineText",
                                    "description": "Physical address",
                                },
                                {
                                    "name": "Website",
                                    "type": "singleLineText",
                                    "description": "Company website URL",
                                },
                                {
                                    "name": "Phone",
                                    "type": "phoneNumber",
                                    "description": "Phone number",
                                },
                                {
                                    "name": "Email",
                                    "type": "email",
                                    "description": "Email address",
                                },
                                {
                                    "name": "Background",
                                    "type": "multilineText",
                                    "description": "Company background and description",
                                },
                                {
                                    "name": "Enriched",
                                    "type": "checkbox",
                                    "description": "Whether the lead has been enriched with additional data",
                                    "options": {
                                        "color": "greenBright",
                                        "icon": "check",
                                    },
                                },
                                {
                                    "name": "Score",
                                    "type": "singleLineText",
                                    "description": "Lead qualification score (Hot, Warm, Cold)",
                                },
                                {
                                    "name": "Industry",
                                    "type": "singleLineText",
                                    "description": "Company industry",
                                },
                                {
                                    "name": "Employees",
                                    "type": "singleLineText",
                                    "description": "Number of employees",
                                },
                                {
                                    "name": "LinkedIn",
                                    "type": "singleLineText",
                                    "description": "LinkedIn company profile URL",
                                },
                                {
                                    "name": "Product Launch",
                                    "type": "multilineText",
                                    "description": "Product launch information",
                                },
                                {
                                    "name": "Personalized Opener",
                                    "type": "multilineText",
                                    "description": "Personalized email opener",
                                },
                                {
                                    "name": "Campaign",
                                    "type": "singleLineText",
                                    "description": "Campaign name or identifier",
                                },
                            ],
                        }
                    ],
                }

                # Add workspace_id if provided
                if workspace_id:
                    create_base_data["workspaceId"] = workspace_id
                    logger.info(f"Creating base in workspace: {workspace_id}")
                else:
                    logger.info("Creating base in default workspace")

                # Create the base
                create_response = await http_client.post(
                    "https://api.airtable.com/v0/meta/bases",
                    headers=headers,
                    json=create_base_data,
                )

                if create_response.status_code == 200:
                    base_data = create_response.json()
                    logger.info(
                        f"Successfully created Agentflow CRM base for user {user_id}"
                    )

                    return {
                        "message": "Agentflow CRM base created successfully",
                        "base_id": base_data["id"],
                        "base_name": base_data["name"],
                        "table_name": "Contact Table",
                        "workspace_id": workspace_id,
                    }
                else:
                    error_msg = f"Failed to create base: {create_response.status_code} - {create_response.text}"
                    logger.error(error_msg)
                    raise HTTPException(status_code=500, detail=error_msg)
            else:
                error_msg = (
                    f"Failed to get bases: {response.status_code} - {response.text}"
                )
                logger.error(error_msg)
                raise HTTPException(status_code=500, detail=error_msg)

    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Error setting up CRM: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)
