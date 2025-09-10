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
    """List all files in a Google Drive folder"""
    try:
        service = get_drive_service(oauth_data)

        # Construct the search query
        query = f"'{folder_id}' in parents and trashed = false"

        # Execute the search
        results = (
            service.files()
            .list(
                q=query,
                spaces="drive",
                fields="files(id, name, mimeType, modifiedTime, size)",
                orderBy="modifiedTime desc",
            )
            .execute()
        )

        return results.get("files", [])

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

        # Download file content
        request = service.files().get_media(fileId=file_id)
        file_content = io.BytesIO()
        downloader = MediaIoBaseDownload(file_content, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()

        # Process different file types
        content = ""
        mime_type = file.get("mimeType", "")

        if "application/pdf" in mime_type:
            # PDF files
            pdf_document = fitz.open(stream=file_content.getvalue(), filetype="pdf")
            for page_num in range(pdf_document.page_count):
                content += pdf_document[page_num].get_text()
            pdf_document.close()

        elif "spreadsheet" in mime_type:
            # Excel/Google Sheets
            df = pd.read_excel(file_content)
            content = df.to_string()

        elif "document" in mime_type:
            # Word/Google Docs
            doc = Document(file_content)
            content = "\n".join([paragraph.text for paragraph in doc.paragraphs])

        elif "text/" in mime_type:
            # Text files
            content = file_content.getvalue().decode("utf-8")

        else:
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
