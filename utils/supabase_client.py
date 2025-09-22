"""
Supabase client for managing user credentials and data
"""

import os
import logging
import httpx
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()
from .data_models import OAuthConnection, User

logger = logging.getLogger(__name__)


class SupabaseClient:
    """Client for interacting with Supabase database"""

    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_KEY")
        self.gmail_client_id = os.getenv("GMAIL_CLIENT_ID")
        self.gmail_client_secret = os.getenv("GMAIL_CLIENT_SECRET")

        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")

        self.client: Client = create_client(self.url, self.key)

    async def get_user_oauth_connections(self, user_id: str):
        """Get Google Drive OAuth connection for a user with automatic token refresh"""
        try:
            # Get the Google Drive connection
            response = (
                self.client.table("oauth_connections")
                .select("*")
                .eq("user_id", user_id)
                .eq("provider", "google-drive")
                .eq("is_active", True)
                .limit(1)  # Only get one record
                .execute()
            )

            if not response.data:
                logger.warning(f"No Google Drive connection found for user {user_id}")
                return {}

            # Get the connection data
            row = response.data[0]
            token_expires_at = datetime.fromisoformat(
                row["token_expires_at"].replace("Z", "+00:00")
            )
            is_expired = datetime.now(timezone.utc) >= token_expires_at

            # If token is expired, refresh it
            if is_expired:
                logger.info(f"Refreshing expired token for user {user_id}")
                try:
                    async with httpx.AsyncClient() as http_client:
                        refresh_response = await http_client.post(
                            "https://oauth2.googleapis.com/token",
                            data={
                                "grant_type": "refresh_token",
                                "refresh_token": row["refresh_token"],
                                "client_id": self.gmail_client_id,
                                "client_secret": self.gmail_client_secret,
                            },
                        )

                        if refresh_response.status_code != 200:
                            logger.error(
                                f"Token refresh failed with status {refresh_response.status_code}: {refresh_response.text}"
                            )
                            return {}

                        token_data = refresh_response.json()

                        # Update tokens in database
                        updated_data = await self.update_oauth_tokens(
                            user_id=user_id,
                            provider="google-drive",
                            access_token=token_data["access_token"],
                            refresh_token=token_data.get(
                                "refresh_token", row["refresh_token"]
                            ),
                            expires_in=token_data.get("expires_in", 3600),
                        )

                        if not updated_data:
                            logger.error("Failed to update tokens in database")
                            return {}

                        # Use the updated data
                        row = updated_data
                        token_expires_at = datetime.fromisoformat(
                            row["token_expires_at"].replace("Z", "+00:00")
                        )
                        is_expired = False
                        logger.info("Successfully refreshed and updated token")

                except Exception as e:
                    logger.error(f"Error refreshing token: {str(e)}")
                    return {}

            # Return the credentials
            credentials = {}
            credentials["google-drive"] = {
                "access_token": row["access_token"],
                "refresh_token": row["refresh_token"],
                "provider_email": row["provider_email"],
                "expires_at": token_expires_at.isoformat(),
                "is_expired": is_expired,
            }
            return credentials

        except Exception as e:
            logger.error(f"Error getting OAuth connection for user {user_id}: {str(e)}")
            return {}

    async def update_oauth_tokens(
        self,
        user_id: str,
        provider: str,
        access_token: str,
        refresh_token: Optional[str] = None,
        expires_in: int = 3600,
    ) -> Optional[Dict[str, Any]]:
        """Update OAuth tokens for a user and provider"""
        try:
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

            update_data = {
                "access_token": access_token,
                "token_expires_at": expires_at.isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

            if refresh_token:
                update_data["refresh_token"] = refresh_token

            response = (
                self.client.table("oauth_connections")
                .update(update_data)
                .eq("user_id", user_id)
                .eq("provider", provider)
                .eq("is_active", True)
                .execute()
            )

            if not response.data:
                logger.error("No rows updated when updating OAuth tokens")
                return None

            return response.data[0]

        except Exception as e:
            logger.error(
                f"Error updating {provider} tokens for user {user_id}: {str(e)}"
            )
            return None


# Global instance
supabase_client = SupabaseClient()
