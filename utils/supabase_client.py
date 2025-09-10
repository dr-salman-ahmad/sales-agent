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

    async def get_user_oauth_connections(
        self, user_id: str
    ) -> Dict[str, Dict[str, Any]]:
        """Get all OAuth connections for a user with automatic token refresh"""
        try:
            response = (
                self.client.table("oauth_connections")
                .select("*")
                .eq("user_id", user_id)
                .eq("is_active", True)
                .eq("provider", "google-drive")
                .execute()
            )

            if not response.data:
                return {}

            credentials = {}

            for row in response.data:
                provider = row["provider"]
                token_expires_at = datetime.fromisoformat(
                    row["token_expires_at"].replace("Z", "+00:00")
                )
                is_expired = datetime.now(timezone.utc) >= token_expires_at

                # If token is expired, try to refresh it
                if is_expired:
                    try:
                        # Refresh token based on provider
                        if provider in ["google-drive", "gmail"]:
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

                                if refresh_response.status_code == 200:
                                    token_data = refresh_response.json()
                                    # Update tokens in database
                                    updated_data = await self.update_oauth_tokens(
                                        user_id=user_id,
                                        provider=provider,
                                        access_token=token_data["access_token"],
                                        refresh_token=token_data.get(
                                            "refresh_token", row["refresh_token"]
                                        ),
                                        expires_in=token_data.get("expires_in", 3600),
                                    )
                                    if updated_data:
                                        row = response.data[
                                            0
                                        ]  # Get fresh data after update
                                        token_expires_at = datetime.fromisoformat(
                                            row["token_expires_at"].replace(
                                                "Z", "+00:00"
                                            )
                                        )
                                        is_expired = False

                    except Exception as e:
                        logger.error(f"Failed to refresh {provider} token: {e}")
                        continue

                # Add credentials to response
                credentials[provider] = {
                    "access_token": row["access_token"],
                    "refresh_token": row["refresh_token"],
                    "provider_email": row["provider_email"],
                    "expires_at": token_expires_at.isoformat(),
                    "is_expired": is_expired,
                }

            return credentials

        except Exception as e:
            logger.error(f"Error getting OAuth connections for user {user_id}: {e}")
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

            if response.data:
                return response.data[0]
            return None

        except Exception as e:
            logger.error(f"Error updating {provider} tokens for user {user_id}: {e}")
            return None

    async def get_oauth_connection(
        self,
        user_id: str,
        provider: str = "google-drive",
    ) -> Optional[OAuthConnection]:
        """Get specific OAuth connection for a user and provider"""
        try:
            response = (
                self.client.table("oauth_connections")
                .select("*")
                .eq("user_id", user_id)
                .eq("provider", provider)
                .eq("is_active", True)
                .execute()
            )

            if response.data:
                row = response.data[0]
                return OAuthConnection(
                    user_id=row["user_id"],
                    provider=row["provider"],
                    provider_email=row["provider_email"],
                    access_token=row["access_token"],
                    refresh_token=row["refresh_token"],
                    token_expires_at=datetime.fromisoformat(
                        row["token_expires_at"].replace("Z", "+00:00")
                    ),
                    is_active=row["is_active"],
                    created_at=datetime.fromisoformat(
                        row["created_at"].replace("Z", "+00:00")
                    ),
                    updated_at=datetime.fromisoformat(
                        row["updated_at"].replace("Z", "+00:00")
                    ),
                )
            return None
        except Exception as e:
            logger.error(f"Error getting {provider} connection for user {user_id}: {e}")
            return None

    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile data"""
        try:
            response = (
                self.client.table("profiles").select("*").eq("id", user_id).execute()
            )

            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error getting user profile for {user_id}: {e}")
            return None

    async def create_oauth_connection(self, connection: OAuthConnection) -> bool:
        """Create a new OAuth connection"""
        try:
            data = {
                "user_id": connection.user_id,
                "provider": connection.provider,
                "provider_email": connection.provider_email,
                "access_token": connection.access_token,
                "refresh_token": connection.refresh_token,
                "token_expires_at": connection.token_expires_at.isoformat(),
                "is_active": connection.is_active,
                "created_at": connection.created_at.isoformat(),
                "updated_at": connection.updated_at.isoformat(),
            }

            response = self.client.table("oauth_connections").insert(data).execute()
            return len(response.data) > 0
        except Exception as e:
            logger.error(f"Error creating OAuth connection: {e}")
            return False

    async def deactivate_oauth_connection(self, user_id: str, provider: str) -> bool:
        """Deactivate an OAuth connection"""
        try:
            response = (
                self.client.table("oauth_connections")
                .update(
                    {
                        "is_active": False,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
                .eq("user_id", user_id)
                .eq("provider", provider)
                .execute()
            )

            return len(response.data) > 0
        except Exception as e:
            logger.error(
                f"Error deactivating {provider} connection for user {user_id}: {e}"
            )
            return False


# Global instance
supabase_client = SupabaseClient()
