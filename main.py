"""
Sales Automation Agent - FastAPI Main Application
"""

import os
import logging
from typing import Dict, Any, Optional
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
from utils.data_models import AgentResponse, TaskRequest
from utils.supabase_client import supabase_client

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Get the directory where main.py is located
AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
# Example session service URI (e.g., SQLite)
# SESSION_SERVICE_URI = "sqlite:///./sessions.db"
# Example allowed origins for CORS
ALLOWED_ORIGINS = ["*"]
# Set web=True if you intend to serve a web interface, False otherwise
SERVE_WEB_INTERFACE = True

# Call the function to get the FastAPI app instance
# Ensure the agent directory name ('capital_agent') matches your agent folder
app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    # session_service=session_service,
    allow_origins=ALLOWED_ORIGINS,
    web=SERVE_WEB_INTERFACE,
)


# Request/Response models
class ChatRequest(BaseModel):
    message: str
    user_id: str
    user_email: str = None


@app.post("/chat")
async def chat(request: ChatRequest, background_tasks: BackgroundTasks):
    """Main chat endpoint for interacting with the sales automation agent"""
    try:
        logger.info(
            f"Received chat request from user {request.user_id}: {request.message}"
        )

        # Validate request
        if not request.user_id:
            raise HTTPException(status_code=400, detail="User ID is required")

        if not request.message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")

        # Get or create a session
        session = await sales_orchestrator._get_or_create_session(request.user_id)

        # Create content object for the runner
        content = types.Content(
            role="user",
            parts=[types.Part(text=request.message + f"user_id: {request.user_id}")],
        )

        # Run the agent with the session
        events = []
        async for event in sales_orchestrator.runner.run_async(
            user_id=request.user_id,
            session_id=session.id,  # Use the session ID we just got/created
            new_message=content,
        ):
            events.append(event)
            print(event)  # For debugging

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
            data={"session_id": session.id},  # Include session ID in response
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


if __name__ == "__main__":
    # Get configuration from environment
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 8080))

    logger.info(f"Starting Sales Automation Agent on {host}:{port}")

    uvicorn.run(app, host=host, port=port, reload=True)
