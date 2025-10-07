"""
Data models for the Sales Automation Agent
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class AgentResponse(BaseModel):
    """Standard agent response model"""

    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Response message")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")
    leads_processed: Optional[int] = Field(
        None, description="Number of leads processed"
    )
    errors: Optional[List[str]] = Field(None, description="Any errors encountered")
