"""
Data models for the Sales Automation Agent
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class LeadScore(str, Enum):
    HOT = "Hot"
    WARM = "Warm"
    COLD = "Cold"


class TaskType(str, Enum):
    PROSPECTING = "prospecting"
    ENRICHMENT = "enrichment"
    QUALIFY = "qualify"
    PERSONALIZE = "personalize"


class Lead(BaseModel):
    """Lead data model"""

    uuid: str = Field(..., description="Unique identifier for the lead")
    name: str = Field(..., description="Company or person name")
    website: Optional[str] = Field(None, description="Company website URL")
    email: Optional[str] = Field(None, description="Contact email address")
    phone: Optional[str] = Field(None, description="Contact phone number")
    industry: Optional[str] = Field(None, description="Company industry")
    company_size: Optional[str] = Field(None, description="Number of employees")
    address: Optional[str] = Field(None, description="Company address")
    linkedin: Optional[str] = Field(None, description="LinkedIn profile URL")
    background: Optional[str] = Field(
        None, description="Company background/description"
    )
    score: Optional[LeadScore] = Field(None, description="Lead qualification score")
    numerical_score: Optional[int] = Field(
        None, ge=0, le=10, description="Numerical score 0-10"
    )
    score_reasoning: Optional[str] = Field(None, description="Reasoning for the score")
    personalized_opener: Optional[str] = Field(
        None, description="Personalized email opener"
    )
    subject_line: Optional[str] = Field(None, description="Email subject line")
    enriched: bool = Field(False, description="Whether lead has been enriched")
    email_sent: bool = Field(False, description="Whether email has been sent")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Additional enrichment fields
    funding_round: Optional[str] = Field(None, description="Recent funding information")
    new_hires: Optional[str] = Field(None, description="Recent hiring activity")
    product_launch: Optional[str] = Field(None, description="Recent product launches")


class ICP(BaseModel):
    """Ideal Customer Persona model"""

    user_id: str = Field(..., description="User who owns this ICP")
    name: Optional[str] = Field(None, description="ICP name/title")
    target_industries: List[str] = Field(
        default_factory=list, description="Target industries"
    )
    company_size_range: str = Field(..., description="Target company size range")
    job_titles: List[str] = Field(default_factory=list, description="Target job titles")
    pain_points: List[str] = Field(default_factory=list, description="Key pain points")
    use_cases: List[str] = Field(default_factory=list, description="Primary use cases")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class OAuthConnection(BaseModel):
    """OAuth connection model for Supabase storage"""

    user_id: str = Field(..., description="User ID")
    provider: str = Field(..., description="OAuth provider (gmail, airtable)")
    provider_email: str = Field(..., description="Email associated with the provider")
    access_token: str = Field(..., description="OAuth access token")
    refresh_token: str = Field(..., description="OAuth refresh token")
    token_expires_at: datetime = Field(..., description="Token expiration time")
    is_active: bool = Field(True, description="Whether connection is active")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class User(BaseModel):
    """User model"""

    user_id: str = Field(..., description="Unique user identifier")
    email: str = Field(..., description="User email address")
    gmail_credentials: Optional[Dict[str, Any]] = Field(
        None, description="Gmail OAuth credentials"
    )
    airtable_credentials: Optional[Dict[str, Any]] = Field(
        None, description="Airtable OAuth credentials"
    )
    preferences: Optional[Dict[str, Any]] = Field(None, description="User preferences")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ProspectingRequest(BaseModel):
    """Request model for prospecting"""

    user_id: str = Field(..., description="User making the request")
    query: str = Field(..., description="Natural language prospecting query")
    industry: Optional[str] = Field(None, description="Target industry")
    location: Optional[str] = Field(None, description="Target location")
    min_employees: Optional[int] = Field(
        None, description="Minimum number of employees"
    )
    num_companies: Optional[int] = Field(5, description="Number of companies to find")


class EnrichmentRequest(BaseModel):
    """Request model for lead enrichment"""

    user_id: str = Field(..., description="User making the request")
    lead_ids: Optional[List[str]] = Field(
        None, description="Specific lead IDs to enrich"
    )
    enrich_all_unenriched: bool = Field(
        False, description="Enrich all unenriched leads"
    )


class ScoringRequest(BaseModel):
    """Request model for lead scoring"""

    user_id: str = Field(..., description="User making the request")
    lead_ids: Optional[List[str]] = Field(
        None, description="Specific lead IDs to score"
    )
    score_all_enriched: bool = Field(False, description="Score all enriched leads")


class PersonalizationRequest(BaseModel):
    """Request model for email personalization"""

    user_id: str = Field(..., description="User making the request")
    lead_ids: Optional[List[str]] = Field(
        None, description="Specific lead IDs to personalize"
    )
    personalize_hot_warm: bool = Field(
        False, description="Personalize all hot/warm leads"
    )
    send_emails: bool = Field(
        False, description="Whether to send emails after personalization"
    )


class AgentResponse(BaseModel):
    """Standard agent response model"""

    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Response message")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")
    leads_processed: Optional[int] = Field(
        None, description="Number of leads processed"
    )
    errors: Optional[List[str]] = Field(None, description="Any errors encountered")


class EmailData(BaseModel):
    """Email data model"""

    to_email: str = Field(..., description="Recipient email")
    from_email: str = Field(..., description="Sender email")
    subject: str = Field(..., description="Email subject")
    body: str = Field(..., description="Email body")
    is_html: bool = Field(False, description="Whether body is HTML")


class AirtableRecord(BaseModel):
    """Airtable record model"""

    record_id: Optional[str] = Field(None, description="Airtable record ID")
    fields: Dict[str, Any] = Field(..., description="Record fields")


class HunterEmailResult(BaseModel):
    """Hunter.io email search result"""

    email: str = Field(..., description="Email address")
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")
    position: Optional[str] = Field(None, description="Job position")
    verification_status: Optional[str] = Field(
        None, description="Email verification status"
    )
    confidence: Optional[int] = Field(None, description="Confidence score")


class WebScrapingResult(BaseModel):
    """Web scraping result model"""

    url: str = Field(..., description="Scraped URL")
    title: Optional[str] = Field(None, description="Page title")
    content: str = Field(..., description="Extracted content")
    links: Optional[List[str]] = Field(None, description="Extracted links")
    insights: Optional[List[str]] = Field(None, description="Generated insights")


class TaskRequest(BaseModel):
    """Generic task request model"""

    user_id: str = Field(..., description="User making the request")
    task_type: TaskType = Field(..., description="Type of task to perform")
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Task parameters"
    )
    message: str = Field(..., description="User message/query")
