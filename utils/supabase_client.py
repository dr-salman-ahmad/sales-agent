"""
Supabase client for managing user credentials and data
"""

import os
import logging
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

        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")

        self.client: Client = create_client(self.url, self.key)

    async def get_user_oauth_connections(self, user_id: str) -> List[OAuthConnection]:
        """Get all OAuth connections for a user"""
        try:
            response = (
                self.client.table("oauth_connections")
                .select("*")
                .eq("user_id", user_id)
                .eq("is_active", True)
                .execute()
            )

            connections = []
            for row in response.data:
                connections.append(
                    OAuthConnection(
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
                )

            return connections
        except Exception as e:
            logger.error(f"Error getting OAuth connections for user {user_id}: {e}")
            return []

    async def get_oauth_connection(
        self, user_id: str, provider: str
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

    async def update_oauth_tokens(
        self,
        user_id: str,
        provider: str,
        access_token: str,
        refresh_token: Optional[str] = None,
        expires_in: int = 3600,
    ) -> bool:
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
                .execute()
            )

            return len(response.data) > 0
        except Exception as e:
            logger.error(f"Error updating {provider} tokens for user {user_id}: {e}")
            return False

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

    async def is_token_expired(self, user_id: str, provider: str) -> bool:
        """Check if a token is expired"""
        connection = await self.get_oauth_connection(user_id, provider)
        if not connection:
            return True

        return datetime.now(timezone.utc) >= connection.token_expires_at

    async def get_user_credentials(self, user_id: str) -> Dict[str, Any]:
        """Get all user credentials organized by provider"""
        connections = await self.get_user_oauth_connections(user_id)

        credentials = {}
        for conn in connections:
            credentials[conn.provider] = {
                "access_token": conn.access_token,
                "refresh_token": conn.refresh_token,
                "expires_at": conn.token_expires_at,
                "provider_email": conn.provider_email,
                "is_expired": datetime.now(timezone.utc) >= conn.token_expires_at,
            }

        return credentials


# Global instance
supabase_client = SupabaseClient()
