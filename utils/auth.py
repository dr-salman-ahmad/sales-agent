"""
OAuth authentication utilities for Gmail and Airtable
"""

import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import httpx
from dotenv import load_dotenv

load_dotenv()
from .supabase_client import supabase_client

logger = logging.getLogger(__name__)


class OAuthManager:
    """Manages OAuth token refresh for Gmail and Airtable"""

    def __init__(self):
        self.gmail_client_id = os.getenv("GMAIL_CLIENT_ID")
        self.gmail_client_secret = os.getenv("GMAIL_CLIENT_SECRET")
        self.airtable_client_id = os.getenv("AIRTABLE_CLIENT_ID")
        self.airtable_client_secret = os.getenv("AIRTABLE_CLIENT_SECRET")

    async def refresh_gmail_token(
        self, user_id: str, refresh_token: str
    ) -> Optional[Dict[str, Any]]:
        """Refresh Gmail OAuth token"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": refresh_token,
                        "client_id": self.gmail_client_id,
                        "client_secret": self.gmail_client_secret,
                    },
                )

                if response.status_code == 200:
                    token_data = response.json()

                    # Update tokens in Supabase
                    success = await supabase_client.update_oauth_tokens(
                        user_id=user_id,
                        provider="gmail",
                        access_token=token_data["access_token"],
                        refresh_token=token_data.get("refresh_token", refresh_token),
                        expires_in=token_data.get("expires_in", 3600),
                    )

                    if success:
                        return {
                            "access_token": token_data["access_token"],
                            "refresh_token": token_data.get(
                                "refresh_token", refresh_token
                            ),
                            "expires_in": token_data.get("expires_in", 3600),
                        }

                logger.error(
                    f"Failed to refresh Gmail token for user {user_id}: {response.text}"
                )
                return None

        except Exception as e:
            logger.error(f"Error refreshing Gmail token for user {user_id}: {e}")
            return None

    async def refresh_airtable_token(
        self, user_id: str, refresh_token: str
    ) -> Optional[Dict[str, Any]]:
        """Refresh Airtable OAuth token"""
        try:
            # Airtable uses Basic Auth with base64 encoded client_id:client_secret
            import base64

            auth_string = f"{self.airtable_client_id}:{self.airtable_client_secret}"
            auth_bytes = auth_string.encode("ascii")
            auth_b64 = base64.b64encode(auth_bytes).decode("ascii")

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://airtable.com/oauth2/v1/token",
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Authorization": f"Basic {auth_b64}",
                    },
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": refresh_token,
                    },
                )

                if response.status_code == 200:
                    token_data = response.json()

                    # Update tokens in Supabase
                    success = await supabase_client.update_oauth_tokens(
                        user_id=user_id,
                        provider="airtable",
                        access_token=token_data["access_token"],
                        refresh_token=token_data.get("refresh_token", refresh_token),
                        expires_in=token_data.get("expires_in", 3600),
                    )

                    if success:
                        return {
                            "access_token": token_data["access_token"],
                            "refresh_token": token_data.get(
                                "refresh_token", refresh_token
                            ),
                            "expires_in": token_data.get("expires_in", 3600),
                        }

                logger.error(
                    f"Failed to refresh Airtable token for user {user_id}: {response.text}"
                )
                return None

        except Exception as e:
            logger.error(f"Error refreshing Airtable token for user {user_id}: {e}")
            return None

    async def get_valid_token(self, user_id: str, provider: str) -> Optional[str]:
        """Get a valid access token, refreshing if necessary"""
        connection = await supabase_client.get_oauth_connection(user_id, provider)

        if not connection:
            logger.warning(f"No {provider} connection found for user {user_id}")
            return None

        # Check if token is expired
        if datetime.now(timezone.utc) >= connection.token_expires_at:
            logger.info(
                f"Token expired for user {user_id}, provider {provider}. Refreshing..."
            )

            if provider == "gmail":
                token_data = await self.refresh_gmail_token(
                    user_id, connection.refresh_token
                )
            elif provider == "airtable":
                token_data = await self.refresh_airtable_token(
                    user_id, connection.refresh_token
                )
            else:
                logger.error(f"Unknown provider: {provider}")
                return None

            if token_data:
                return token_data["access_token"]
            else:
                logger.error(
                    f"Failed to refresh token for user {user_id}, provider {provider}"
                )
                return None

        return connection.access_token

    async def get_user_credentials(self, user_id: str) -> Dict[str, Any]:
        """Get all valid user credentials, refreshing tokens as needed"""
        credentials = {}

        # Get Gmail credentials
        gmail_token = await self.get_valid_token(user_id, "gmail")

        if gmail_token:
            gmail_connection = await supabase_client.get_oauth_connection(
                user_id, "gmail"
            )
            credentials["gmail"] = {
                "access_token": gmail_token,
                "refresh_token": gmail_connection.refresh_token,
                "provider_email": gmail_connection.provider_email,
            }

        # Get Airtable credentials
        airtable_token = await self.get_valid_token(user_id, "airtable")
        if airtable_token:
            airtable_connection = await supabase_client.get_oauth_connection(
                user_id, "airtable"
            )
            credentials["airtable"] = {
                "access_token": airtable_token,
                "refresh_token": airtable_connection.refresh_token,
                "provider_email": airtable_connection.provider_email,
            }

        return credentials


# Global instance
oauth_manager = OAuthManager()
