"""
Sales Automation Agent - FastAPI Main Application
"""

import os
import logging
from typing import Dict, Any, Optional, List, Literal
import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from google.adk.cli.fast_api import get_fast_api_app
from google.genai import types

# Import our components
from sales_automation.agent import sales_orchestrator
from data_analysis.agent import runner as analysis_runner, get_or_create_session
from utils.data_models import AgentResponse, TaskRequest
from utils.supabase_client import supabase_client
from utils.drive_manager import list_files, read_file_content
from utils.embeddings_manager import process_and_store_document

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Get the directory where main.py is located
AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
ALLOWED_ORIGINS = ["*"]
SERVE_WEB_INTERFACE = True

# Call the function to get the FastAPI app instance
app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    allow_origins=ALLOWED_ORIGINS,
    web=SERVE_WEB_INTERFACE,
)


# Request/Response models
class ChatRequest(BaseModel):
    message: str
    user_id: str
    user_email: str = None
    agent_type: Literal[
        "prospecting", "write_message", "qualifying", "data_analysis"
    ] = "prospecting"  # Default to prospecting agent
    agent_id: str = None
    goal: str = None  # Goal for data_analysis agent


class Agent(BaseModel):
    id: str


class Folder(BaseModel):
    folderId: str


class IndexFolderRequest(BaseModel):
    agent: Agent
    folder: Folder
    userId: str
    reset_collection: bool = False  # Optional parameter to control collection reset


class IndexingResponse(BaseModel):
    success: bool
    message: str
    files_processed: int
    errors: Optional[List[str]] = None


@app.post("/chat")
async def chat(request: ChatRequest, background_tasks: BackgroundTasks):
    """Main chat endpoint for interacting with agents"""
    try:
        logger.info(
            f"Received chat request from user {request.user_id} for {request.agent_type} agent: {request.message}"
        )

        # Validate request
        if not request.user_id:
            raise HTTPException(status_code=400, detail="User ID is required")

        if not request.message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")

        text_with_context = request.message + f" user_id: {request.user_id}"
        if request.agent_id:
            text_with_context += f" agent_id: {request.agent_id}"

        # Select the appropriate agent and get/create session
        if request.agent_type in ["prospecting", "write_message", "qualifying"]:
            text_with_context += f" agent_type: {request.agent_type}"
            session = await sales_orchestrator._get_or_create_session(request.user_id)
            runner = sales_orchestrator.runner
        else:  # data_analysis
            if request.goal:
                text_with_context += f" goal: {request.goal}"
            session = await get_or_create_session(user_id=request.user_id)
            runner = analysis_runner

        # Create content object for the runner
        content = types.Content(
            role="user",
            parts=[types.Part(text=text_with_context)],
        )

        # Run the agent with the session
        events = []
        async for event in runner.run_async(
            user_id=request.user_id,
            session_id=session.id,
            new_message=content,
        ):
            events.append(event)

        # Extract response from events
        response_message = "Response from agent"
        for event in events:
            if hasattr(event, "content") and event.content and event.content.parts:
                text_parts = []
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        text_parts.append(part.text)
                if text_parts:
                    response_message = " ".join(text_parts)

        response = AgentResponse(
            success=True,
            message=response_message,
            data={"session_id": session.id, "agent_type": request.agent_type},
            leads_processed=0,
            errors=[],
        )
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404, content={"error": "Endpoint not found", "status_code": 404}
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500, content={"error": "Internal server error", "status_code": 500}
    )


@app.post("/index-folder", response_model=IndexingResponse)
async def index_folder(request: IndexFolderRequest):
    """Index all files in a Google Drive folder and create embeddings"""
    try:
        user_id = request.userId
        agent_id = request.agent.id
        folder_id = request.folder.folderId

        logger.info(
            f"Indexing folder {folder_id} for user {user_id} and agent {agent_id}"
        )

        # Get user's Google Drive OAuth credentials
        oauth_data = await supabase_client.get_user_oauth_connections(user_id)
        if not oauth_data or "google-drive" not in oauth_data:
            raise HTTPException(
                status_code=400,
                detail="Google Drive credentials not found. Please connect your Google Drive account.",
            )

        # Get the Google Drive credentials
        drive_creds = oauth_data["google-drive"]

        # Check if token is expired
        if drive_creds["is_expired"]:
            # Try to refresh the token
            try:
                updated_creds = await supabase_client.refresh_oauth_token(
                    user_id, "google-drive"
                )
                if not updated_creds:
                    raise HTTPException(
                        status_code=401,
                        detail="Failed to refresh Google Drive token. Please reconnect your account.",
                    )
                drive_creds = updated_creds
            except Exception as e:
                logger.error(f"Error refreshing token: {str(e)}")
                raise HTTPException(
                    status_code=401,
                    detail="Failed to refresh Google Drive token. Please reconnect your account.",
                )

        # List all files in the folder
        files = await list_files(drive_creds, folder_id)
        if not files:
            return IndexingResponse(
                success=True, message="No files found in the folder", files_processed=0
            )

        errors = []
        processed_count = 0

        # Process each file
        for file in files:
            try:
                # Skip unsupported file types
                if "folder" in file["mimeType"]:
                    continue

                # Read file content
                file_data = await read_file_content(drive_creds, file["id"])

                # Process and store embeddings with agent_id and user_id
                await process_and_store_document(
                    user_id=user_id,
                    agent_id=agent_id,
                    file_id=file["id"],
                    content=file_data["content"],
                    metadata={
                        "name": file["name"],
                        "mime_type": file["mimeType"],
                        "modified_time": file["modifiedTime"],
                        "size": file.get("size", 0),
                        "folder_id": folder_id,
                    },
                    reset_collection=request.reset_collection,
                )

                processed_count += 1
                logger.info(f"Successfully processed file: {file['name']}")

            except Exception as e:
                error_msg = (
                    f"Error processing file {file.get('name', 'unknown')}: {str(e)}"
                )
                logger.error(error_msg)
                errors.append(error_msg)

        # Prepare response
        message = f"Successfully processed {processed_count} files"
        if request.reset_collection:
            message = f"Reset collection and {message.lower()}"
        if errors:
            message += f" with {len(errors)} errors"

        return IndexingResponse(
            success=True,
            message=message,
            files_processed=processed_count,
            errors=errors if errors else None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error indexing folder: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error indexing folder: {str(e)}")


if __name__ == "__main__":
    # Get configuration from environment
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 8080))

    logger.info(f"Starting Sales Automation Agent on {host}:{port}")

    uvicorn.run(app, host=host, port=port, reload=True)
