"""
Google Cloud Storage sync manager for embeddings folder
Handles upload/download of embeddings_db folder to/from GCS
"""

import os
import tarfile
import tempfile
import logging
import shutil
from typing import Optional, Dict, Any
from datetime import datetime
from google.cloud import storage
from google.oauth2 import service_account
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class GCSSyncManager:
    """Manager for syncing embeddings folder with Google Cloud Storage"""

    def __init__(self):
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        self.bucket_name = os.getenv(
            "EMBEDDINGS_BUCKET", "orchestrator-agent-embeddings"
        )
        self.local_folder = "embeddings_db"
        self.gcs_folder = "embeddings_db"
        self.client = None
        self.gcs_available = False

        # Check if GCS is available (credentials and project)
        if not self.project_id:
            logger.warning("GOOGLE_CLOUD_PROJECT not set - GCS sync disabled")
            return

        try:
            # Initialize GCS client with explicit credentials
            credentials_path = os.getenv(
                "GOOGLE_APPLICATION_CREDENTIALS", "./google-cred.json"
            )

            if os.path.exists(credentials_path):
                credentials = service_account.Credentials.from_service_account_file(
                    credentials_path,
                    scopes=["https://www.googleapis.com/auth/cloud-platform"],
                )
                self.client = storage.Client(
                    project=self.project_id, credentials=credentials
                )
                self.gcs_available = True
                logger.info(
                    f"GCS sync manager initialized with explicit credentials for project: {self.project_id}"
                )
            else:
                # Fall back to default credentials
                self.client = storage.Client(project=self.project_id)
                self.gcs_available = True
                logger.info(
                    f"GCS sync manager initialized with default credentials for project: {self.project_id}"
                )

        except Exception as e:
            logger.warning(
                f"Failed to initialize GCS client: {str(e)} - GCS sync disabled"
            )
            self.client = None
            self.gcs_available = False

    def ensure_bucket_exists(self) -> bool:
        """Ensure the embeddings bucket exists, create if it doesn't"""
        if not self.gcs_available:
            logger.warning("GCS not available - skipping bucket check")
            return False

        try:
            bucket = self.client.bucket(self.bucket_name)

            if bucket.exists():
                logger.info(f"Bucket {self.bucket_name} already exists")
                return True

            # Create the bucket
            bucket = self.client.create_bucket(self.bucket_name)
            logger.info(f"Created bucket: {self.bucket_name}")
            return True

        except Exception as e:
            logger.error(f"Error ensuring bucket exists: {str(e)}")
            return False

    def compress_folder(self, folder_path: str) -> str:
        """Compress folder to tar.gz file"""
        try:
            # Create temporary file for compression
            temp_file = tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False)
            temp_path = temp_file.name
            temp_file.close()

            # Compress the folder
            with tarfile.open(temp_path, "w:gz") as tar:
                tar.add(folder_path, arcname=os.path.basename(folder_path))

            logger.info(f"Compressed folder {folder_path} to {temp_path}")
            return temp_path

        except Exception as e:
            logger.error(f"Error compressing folder: {str(e)}")
            raise

    def decompress_folder(self, tar_path: str, extract_to: str) -> bool:
        """Decompress tar.gz file to folder"""
        try:
            # Create directory if it doesn't exist
            os.makedirs(extract_to, exist_ok=True)

            # Extract the tar file
            with tarfile.open(tar_path, "r:gz") as tar:
                tar.extractall(extract_to)

            logger.info(f"Decompressed {tar_path} to {extract_to}")
            return True

        except Exception as e:
            logger.error(f"Error decompressing folder: {str(e)}")
            return False

    def upload_folder(self, folder_path: str) -> bool:
        """Upload local folder to GCS"""
        if not self.gcs_available:
            logger.warning("GCS not available - skipping upload")
            return False

        try:
            # Ensure bucket exists
            if not self.ensure_bucket_exists():
                return False

            # Check if folder exists locally
            if not os.path.exists(folder_path):
                logger.warning(f"Local folder {folder_path} does not exist")
                return False

            # Compress the folder
            compressed_path = self.compress_folder(folder_path)

            try:
                # Upload compressed file to GCS
                bucket = self.client.bucket(self.bucket_name)
                blob_name = f"{self.gcs_folder}/embeddings_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.tar.gz"
                blob = bucket.blob(blob_name)

                # Upload with metadata
                blob.metadata = {
                    "uploaded_at": datetime.now().isoformat(),
                    "folder_name": folder_path,
                    "compressed": "true",
                }

                blob.upload_from_filename(compressed_path)

                logger.info(
                    f"Successfully uploaded folder to gs://{self.bucket_name}/{blob_name}"
                )

                # Also upload as latest backup
                latest_blob_name = f"{self.gcs_folder}/latest_backup.tar.gz"
                latest_blob = bucket.blob(latest_blob_name)
                latest_blob.upload_from_filename(compressed_path)

                logger.info(
                    f"Updated latest backup: gs://{self.bucket_name}/{latest_blob_name}"
                )

                return True

            finally:
                # Clean up temporary file
                if os.path.exists(compressed_path):
                    os.unlink(compressed_path)

        except Exception as e:
            logger.error(f"Error uploading folder: {str(e)}")
            return False

    def download_folder(self, folder_path: str) -> bool:
        """Download folder from GCS"""
        if not self.gcs_available:
            logger.warning("GCS not available - skipping download")
            return True  # Return True to allow local operation to continue

        try:
            # Ensure bucket exists
            if not self.ensure_bucket_exists():
                return False

            bucket = self.client.bucket(self.bucket_name)

            # Try to download latest backup first
            latest_blob_name = f"{self.gcs_folder}/latest_backup.tar.gz"
            latest_blob = bucket.blob(latest_blob_name)

            if latest_blob.exists():
                # Download latest backup
                temp_file = tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False)
                temp_path = temp_file.name
                temp_file.close()

                try:
                    latest_blob.download_to_filename(temp_path)
                    logger.info(f"Downloaded latest backup from GCS")

                    # Decompress to target folder
                    # Use current directory if folder_path doesn't have a parent directory
                    extract_to = (
                        os.path.dirname(folder_path)
                        if os.path.dirname(folder_path)
                        else "."
                    )
                    success = self.decompress_folder(temp_path, extract_to)

                    if success:
                        logger.info(
                            f"Successfully downloaded and extracted folder to {folder_path}"
                        )
                        return True
                    else:
                        logger.error("Failed to decompress downloaded folder")
                        return False

                finally:
                    # Clean up temporary file
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
            else:
                logger.info("No backup found in GCS, will start with empty folder")
                return True

        except Exception as e:
            logger.error(f"Error downloading folder: {str(e)}")
            return False

    def get_backup_info(self) -> Dict[str, Any]:
        """Get information about available backups"""
        if not self.gcs_available:
            return {
                "bucket_name": self.bucket_name,
                "folder_path": f"gs://{self.bucket_name}/{self.gcs_folder}",
                "backup_count": 0,
                "backups": [],
                "gcs_available": False,
                "message": "GCS not available - running in local mode only",
            }

        try:
            bucket = self.client.bucket(self.bucket_name)
            blobs = list(bucket.list_blobs(prefix=f"{self.gcs_folder}/"))

            backups = []
            for blob in blobs:
                if blob.name.endswith(".tar.gz"):
                    backups.append(
                        {
                            "name": blob.name,
                            "size": blob.size,
                            "created": (
                                blob.time_created.isoformat()
                                if blob.time_created
                                else None
                            ),
                            "updated": (
                                blob.updated.isoformat() if blob.updated else None
                            ),
                            "is_latest": blob.name.endswith("latest_backup.tar.gz"),
                        }
                    )

            return {
                "bucket_name": self.bucket_name,
                "folder_path": f"gs://{self.bucket_name}/{self.gcs_folder}",
                "backup_count": len(backups),
                "backups": backups,
                "gcs_available": True,
            }

        except Exception as e:
            logger.error(f"Error getting backup info: {str(e)}")
            return {"error": str(e), "gcs_available": False}

    def cleanup_old_backups(self, keep_count: int = 5) -> bool:
        """Clean up old backups, keeping only the most recent ones"""
        if not self.gcs_available:
            logger.warning("GCS not available - skipping cleanup")
            return False

        try:
            bucket = self.client.bucket(self.bucket_name)
            blobs = list(bucket.list_blobs(prefix=f"{self.gcs_folder}/"))

            # Filter out latest_backup.tar.gz and sort by creation time
            backup_blobs = [
                blob
                for blob in blobs
                if blob.name.endswith(".tar.gz")
                and not blob.name.endswith("latest_backup.tar.gz")
            ]
            backup_blobs.sort(
                key=lambda x: x.time_created or datetime.min, reverse=True
            )

            # Delete old backups
            deleted_count = 0
            for blob in backup_blobs[keep_count:]:
                blob.delete()
                deleted_count += 1
                logger.info(f"Deleted old backup: {blob.name}")

            logger.info(f"Cleaned up {deleted_count} old backups")
            return True

        except Exception as e:
            logger.error(f"Error cleaning up old backups: {str(e)}")
            return False


# Global instance
sync_manager = None


def get_sync_manager() -> Optional[GCSSyncManager]:
    """Get or create the global sync manager instance"""
    global sync_manager

    if sync_manager is None:
        try:
            sync_manager = GCSSyncManager()
        except Exception as e:
            logger.error(f"Failed to create sync manager: {str(e)}")
            return None

    return sync_manager


def ensure_embeddings_folder_exists() -> bool:
    """Ensure the embeddings folder exists locally"""
    manager = get_sync_manager()
    if not manager:
        # If no manager available, just create local folder
        os.makedirs("embeddings_db", exist_ok=True)
        logger.info("Created local embeddings folder (no sync manager available)")
        return True

    # Try to download from GCS if local folder doesn't exist
    if not os.path.exists(manager.local_folder):
        logger.info(
            "Local embeddings folder not found, attempting to download from GCS..."
        )
        success = manager.download_folder(manager.local_folder)
        if not success and manager.gcs_available:
            # If download failed but GCS is available, create empty folder
            os.makedirs(manager.local_folder, exist_ok=True)
            logger.info("Created empty local embeddings folder after failed download")
        elif not manager.gcs_available:
            # If GCS not available, just create local folder
            os.makedirs(manager.local_folder, exist_ok=True)
            logger.info("Created local embeddings folder (GCS not available)")
        return True

    return True


def backup_embeddings_folder() -> bool:
    """Backup the embeddings folder to GCS"""
    manager = get_sync_manager()
    if not manager:
        logger.warning("No sync manager available - skipping backup")
        return False

    if not os.path.exists(manager.local_folder):
        logger.warning("Local embeddings folder does not exist, nothing to backup")
        return False

    if not manager.gcs_available:
        logger.warning("GCS not available - skipping backup")
        return False

    return manager.upload_folder(manager.local_folder)
