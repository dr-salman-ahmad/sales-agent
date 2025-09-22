"""
Utility functions for Google Drive operations
"""

import os
import io
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import fitz  # PyMuPDF for PDF reading
import pandas as pd
from docx import Document
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def get_drive_service(oauth_data: Dict[str, Any]):
    """
    Get authenticated Google Drive service

    Args:
        oauth_data: Dictionary containing OAuth credentials from Supabase
    """
    try:
        # Create credentials with all necessary OAuth2 fields
        creds = Credentials(
            token=oauth_data["access_token"],
            refresh_token=oauth_data["refresh_token"],
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.getenv("GOOGLE_CLIENT_ID"),
            client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
            scopes=["https://www.googleapis.com/auth/drive.readonly"],
        )

        return build("drive", "v3", credentials=creds)

    except Exception as e:
        logger.error(f"Error creating Drive service: {str(e)}")
        raise


async def list_files(
    oauth_data: Dict[str, Any], folder_id: str
) -> List[Dict[str, Any]]:
    """List all files in a Google Drive folder recursively"""
    try:
        service = get_drive_service(oauth_data)
        all_files = []

        # Use a queue to process folders recursively
        folders_to_process = [folder_id]

        while folders_to_process:
            current_folder = folders_to_process.pop(0)

            # Construct the search query for current folder
            query = f"'{current_folder}' in parents and trashed = false"

            # Execute the search
            results = (
                service.files()
                .list(
                    q=query,
                    spaces="drive",
                    fields="files(id, name, mimeType, modifiedTime, size, parents)",
                    orderBy="modifiedTime desc",
                )
                .execute()
            )

            files = results.get("files", [])

            for file in files:
                # Add folder path information
                file["folder_path"] = current_folder

                if "folder" in file["mimeType"]:
                    # This is a folder, add it to the queue for processing
                    folders_to_process.append(file["id"])
                    logger.info(
                        f"Found nested folder: {file['name']} (ID: {file['id']})"
                    )
                else:
                    # This is a file, add it to our results
                    all_files.append(file)
                    logger.info(
                        f"Found file: {file['name']} (Type: {file['mimeType']})"
                    )

        logger.info(f"Total files found across all folders: {len(all_files)}")
        return all_files

    except Exception as e:
        logger.error(f"Error listing files: {str(e)}")
        raise


async def read_file_content(oauth_data: Dict[str, Any], file_id: str) -> Dict[str, Any]:
    """Read content from a Google Drive file"""
    try:
        service = get_drive_service(oauth_data)

        # Get file metadata
        file = (
            service.files()
            .get(fileId=file_id, fields="name,mimeType,modifiedTime,size")
            .execute()
        )

        mime_type = file.get("mimeType", "")
        content = ""

        # Handle Google Workspace files with export
        if mime_type in [
            "application/vnd.google-apps.document",  # Google Docs
            "application/vnd.google-apps.spreadsheet",  # Google Sheets
            "application/vnd.google-apps.presentation",  # Google Slides
            "application/vnd.google-apps.drawing",  # Google Drawings
        ]:
            # Export Google Workspace files to a readable format
            export_mime_type = "text/plain"  # Default export format

            if mime_type == "application/vnd.google-apps.spreadsheet":
                export_mime_type = "text/csv"  # Export Sheets as CSV
            elif mime_type == "application/vnd.google-apps.document":
                export_mime_type = "text/plain"  # Export Docs as plain text
            elif mime_type == "application/vnd.google-apps.presentation":
                export_mime_type = "text/plain"  # Export Slides as plain text
            elif mime_type == "application/vnd.google-apps.drawing":
                export_mime_type = "text/plain"  # Export Drawings as plain text

            logger.info(
                f"Exporting Google Workspace file {file.get('name')} as {export_mime_type}"
            )

            # Export the file
            request = service.files().export_media(
                fileId=file_id, mimeType=export_mime_type
            )
            file_content = io.BytesIO()
            downloader = MediaIoBaseDownload(file_content, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()

            # Process exported content
            if export_mime_type == "text/csv":
                # Handle CSV export from Google Sheets
                try:
                    df = pd.read_csv(
                        io.StringIO(file_content.getvalue().decode("utf-8"))
                    )
                    content = df.to_string()
                except Exception as e:
                    logger.warning(f"Failed to parse CSV, using raw text: {e}")
                    content = file_content.getvalue().decode("utf-8")
            else:
                # Handle plain text export
                content = file_content.getvalue().decode("utf-8")

        else:
            # Handle regular files (PDF, Excel, Word, etc.)
            request = service.files().get_media(fileId=file_id)
            file_content = io.BytesIO()
            downloader = MediaIoBaseDownload(file_content, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()

            # Process different file types
            if "application/pdf" in mime_type:
                # PDF files
                pdf_document = fitz.open(stream=file_content.getvalue(), filetype="pdf")
                for page_num in range(pdf_document.page_count):
                    content += pdf_document[page_num].get_text()
                pdf_document.close()

            elif "spreadsheet" in mime_type or "excel" in mime_type:
                # Excel files
                df = pd.read_excel(file_content)
                content = df.to_string()

            elif "document" in mime_type and "officedocument" in mime_type:
                # Word documents
                doc = Document(file_content)
                content = "\n".join([paragraph.text for paragraph in doc.paragraphs])

            elif "text/" in mime_type:
                # Text files
                content = file_content.getvalue().decode("utf-8")

            else:
                # Try to read as text as fallback
                try:
                    content = file_content.getvalue().decode("utf-8")
                    logger.info(
                        f"Read file {file.get('name')} as plain text (MIME: {mime_type})"
                    )
                except:
                    raise ValueError(f"Unsupported file type: {mime_type}")

        return {
            "file_id": file_id,
            "name": file.get("name"),
            "mime_type": mime_type,
            "modified_time": file.get("modifiedTime"),
            "size": file.get("size"),
            "content": content,
        }

    except Exception as e:
        logger.error(f"Error reading file content: {str(e)}")
        raise
