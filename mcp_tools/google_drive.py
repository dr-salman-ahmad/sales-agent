"""
Google Drive MCP Server for document search and reading
"""

import os
import logging
import asyncio
from typing import Dict, Any, List, Optional, Sequence
import mimetypes
from datetime import datetime, timezone
import io
import fitz  # PyMuPDF for PDF reading
import pandas as pd
from docx import Document
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from utils.helpers import log_api_interaction
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# Setup loggers
logger = logging.getLogger(__name__)

# Create MCP server
server = Server("google-drive-server")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="search_drive_files",
            description="Search for files in a specific Google Drive folder",
            inputSchema={
                "type": "object",
                "properties": {
                    "access_token": {
                        "type": "string",
                        "description": "Google Drive access token",
                    },
                    "folder_id": {
                        "type": "string",
                        "description": "Google Drive folder ID to search in",
                    },
                    "query": {
                        "type": "string",
                        "description": "Optional search query (filename, content). If not provided, lists all files in the folder",
                    },
                },
                "required": ["access_token", "folder_id"],
            },
        ),
        Tool(
            name="read_file_content",
            description="Read content from a specific Google Drive file",
            inputSchema={
                "type": "object",
                "properties": {
                    "access_token": {
                        "type": "string",
                        "description": "Google Drive access token",
                    },
                    "file_id": {
                        "type": "string",
                        "description": "Google Drive file ID to read",
                    },
                },
                "required": ["access_token", "file_id"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> Sequence[TextContent]:
    """Handle tool calls."""
    if name == "search_drive_files":
        return await search_drive_files(arguments)
    elif name == "read_file_content":
        return await read_file_content(arguments)

    raise ValueError(f"Unknown tool: {name}")


def get_drive_service(access_token: str):
    """Get authenticated Google Drive service"""
    creds = Credentials(token=access_token)
    return build("drive", "v3", credentials=creds)


async def search_drive_files(arguments: Dict[str, Any]) -> Sequence[TextContent]:
    """Search for files in a specific Google Drive folder"""
    try:
        access_token = arguments.get("access_token")
        folder_id = arguments.get("folder_id")
        query = arguments.get("query")

        if not all([access_token, folder_id]):
            return [TextContent(type="text", text="Error: Missing required parameters")]

        service = get_drive_service(access_token)

        # Construct the search query
        folder_query = f"'{folder_id}' in parents"
        if query and query.strip():
            folder_query += (
                f" and (name contains '{query}' or fullText contains '{query}')"
            )

        # Log the API request
        log_api_interaction(
            method="GET",
            url="https://www.googleapis.com/drive/v3/files",
            headers={"Authorization": "Bearer <token>"},
            body={"q": folder_query},
        )

        # Execute the search
        results = (
            service.files()
            .list(
                q=folder_query,
                spaces="drive",
                fields="files(id, name, mimeType, modifiedTime)",
                orderBy="modifiedTime desc",
            )
            .execute()
        )

        # Log the response
        log_api_interaction(
            method="GET",
            url="https://www.googleapis.com/drive/v3/files",
            headers={"Authorization": "Bearer <token>"},
            response=results,
        )

        files = results.get("files", [])
        if not files:
            return [TextContent(type="text", text="No files found.")]

        # Format results
        file_list = []
        for file in files:
            modified_time = datetime.fromisoformat(
                file["modifiedTime"].replace("Z", "+00:00")
            )
            # Get friendly file type
            file_type = "Document"
            if "spreadsheet" in file["mimeType"]:
                file_type = "Spreadsheet"
            elif "presentation" in file["mimeType"]:
                file_type = "Presentation"
            elif "pdf" in file["mimeType"]:
                file_type = "PDF"
            elif "folder" in file["mimeType"]:
                file_type = "Folder"

            file_info = (
                f"{file['name']} ({file_type})\n"
                f"ID: {file['id']}\n"
                f"Last modified: {modified_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            )
            file_list.append(file_info)

        return [TextContent(type="text", text="\n".join(file_list))]

    except Exception as e:
        error_msg = f"Error searching Drive files: {str(e)}"
        log_api_interaction(
            method="GET",
            url="https://www.googleapis.com/drive/v3/files",
            headers={"Authorization": "Bearer <token>"},
            error=error_msg,
        )
        return [TextContent(type="text", text=error_msg)]


async def read_file_content(arguments: Dict[str, Any]) -> Sequence[TextContent]:
    """Read content from a specific Google Drive file"""
    try:
        access_token = arguments.get("access_token")
        file_id = arguments.get("file_id")

        if not all([access_token, file_id]):
            return [TextContent(type="text", text="Error: Missing required parameters")]

        service = get_drive_service(access_token)

        # Get file metadata
        file = service.files().get(fileId=file_id, fields="name,mimeType").execute()
        mime_type = file.get("mimeType", "")

        # Download file content
        request = service.files().get_media(fileId=file_id)
        file_content = io.BytesIO()
        downloader = MediaIoBaseDownload(file_content, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()

        # Process different file types
        content = ""
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
            return [
                TextContent(type="text", text=f"Unsupported file type: {mime_type}")
            ]

        # Log the interaction
        log_api_interaction(
            method="GET",
            url=f"https://www.googleapis.com/drive/v3/files/{file_id}/content",
            headers={"Authorization": "Bearer <token>"},
            response={"filename": file["name"], "content_length": len(content)},
        )

        return [TextContent(type="text", text=content)]

    except Exception as e:
        error_msg = f"Error reading file content: {str(e)}"
        log_api_interaction(
            method="GET",
            url=f"https://www.googleapis.com/drive/v3/files/{file_id}/content",
            headers={"Authorization": "Bearer <token>"},
            error=error_msg,
        )
        return [TextContent(type="text", text=error_msg)]


async def main():
    """Run the Google Drive MCP server."""
    logger.info("Starting Google Drive MCP Server...")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream, server.create_initialization_options()
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
