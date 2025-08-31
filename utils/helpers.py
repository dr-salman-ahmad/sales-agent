"""
Helper utilities for the Sales Automation Agent
"""

import uuid
import re
import base64
import logging
import json
import os
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse, urljoin
from datetime import datetime


def setup_api_logger():
    """Setup logger for API interactions"""
    # Create logs directory if it doesn't exist
    if not os.path.exists("logs"):
        os.makedirs("logs")

    # Create a logger for API interactions
    api_logger = logging.getLogger("api_interactions")
    api_logger.setLevel(logging.DEBUG)

    # Create file handler
    file_handler = logging.FileHandler("logs/api_interactions.log")
    file_handler.setLevel(logging.DEBUG)

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)

    # Add handler to logger if it doesn't already have it
    if not api_logger.handlers:
        api_logger.addHandler(file_handler)

    return api_logger


def log_api_interaction(
    method: str,
    url: str,
    headers: Dict,
    body: Any = None,
    response: Any = None,
    error: Any = None,
):
    """Log API request and response details"""
    api_logger = logging.getLogger("api_interactions")

    # Log full headers including auth tokens
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "method": method,
        "url": url,
        "headers": headers,  # Log original headers
    }

    if body:
        # Log full body including tokens
        log_entry["request_body"] = body

    if response:
        try:
            if hasattr(response, "status_code"):
                log_entry["response_status"] = response.status_code
            if hasattr(response, "headers"):
                log_entry["response_headers"] = dict(response.headers)
            if hasattr(response, "text"):
                try:
                    # Try to parse as JSON
                    response_body = json.loads(response.text)
                    # Log full response including tokens
                    log_entry["response_body"] = response_body
                except json.JSONDecodeError:
                    # If not JSON, store as text
                    log_entry["response_body"] = response.text
        except Exception as e:
            log_entry["response_logging_error"] = str(e)

    if error:
        log_entry["error"] = str(error)

    api_logger.debug(json.dumps(log_entry, indent=2))


logger = logging.getLogger(__name__)


def generate_uuid() -> str:
    """Generate a UUID for leads"""
    return str(uuid.uuid4())


def clean_url(url: str) -> str:
    """Clean and validate URL"""
    if not url:
        return ""

    # Add protocol if missing
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    # Parse and clean
    parsed = urlparse(url)
    if parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

    return ""


def extract_domain(url: str) -> str:
    """Extract domain from URL"""
    try:
        parsed = urlparse(url)
        return parsed.netloc.replace("www.", "")
    except:
        return ""


def clean_email(email: str) -> str:
    """Clean and validate email address"""
    if not email:
        return ""

    email = email.strip().lower()

    # Basic email validation
    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if re.match(email_pattern, email):
        return email

    return ""


def clean_phone(phone: str) -> str:
    """Clean phone number"""
    if not phone:
        return ""

    # Remove all non-digit characters except + at the beginning
    cleaned = re.sub(r"[^\d+]", "", phone)

    # Ensure + is only at the beginning
    if cleaned.startswith("+"):
        cleaned = "+" + re.sub(r"[^0-9]", "", cleaned[1:])
    else:
        cleaned = re.sub(r"[^0-9]", "", cleaned)

    return cleaned if len(cleaned) >= 10 else ""


def clean_company_name(name: str) -> str:
    """Clean company name"""
    if not name:
        return ""

    # Remove common suffixes and clean
    suffixes = ["Inc.", "Inc", "LLC", "Ltd.", "Ltd", "Corp.", "Corp", "Co.", "Co"]
    cleaned = name.strip()

    for suffix in suffixes:
        if cleaned.endswith(f" {suffix}"):
            cleaned = cleaned[: -len(suffix) - 1].strip()

    return cleaned


def parse_company_size(size_str: str) -> str:
    """Parse and standardize company size"""
    if not size_str:
        return "Unknown"

    size_str = size_str.strip().lower()

    # Extract numbers
    numbers = re.findall(r"\d+", size_str)
    if not numbers:
        return size_str.title()

    # Convert to standard ranges
    num = int(numbers[0])
    if num < 10:
        return "1-10 employees"
    elif num < 50:
        return "11-50 employees"
    elif num < 200:
        return "51-200 employees"
    elif num < 1000:
        return "201-1000 employees"
    elif num < 5000:
        return "1001-5000 employees"
    else:
        return "5000+ employees"


def create_email_mime(
    from_email: str, to_email: str, subject: str, body: str, is_html: bool = False
) -> str:
    """Create MIME email format for Gmail API"""
    content_type = "text/html" if is_html else "text/plain"

    mime_message = (
        f"From: {from_email}\r\n"
        f"To: {to_email}\r\n"
        f"Subject: {subject}\r\n"
        f'Content-Type: {content_type}; charset="UTF-8"\r\n'
        f"\r\n"
        f"{body}"
    )

    # Encode to base64
    return base64.urlsafe_b64encode(mime_message.encode()).decode()


def extract_insights_from_text(text: str, max_insights: int = 5) -> List[str]:
    """Extract key insights from company text"""
    if not text:
        return []

    insights = []
    text_lower = text.lower()

    # Look for funding information
    funding_keywords = [
        "funding",
        "raised",
        "series",
        "investment",
        "venture",
        "capital",
    ]
    if any(keyword in text_lower for keyword in funding_keywords):
        funding_match = re.search(
            r"(raised|funding|investment).*?(\$[\d.]+[kmb]?)", text_lower
        )
        if funding_match:
            insights.append(f"Recent funding: {funding_match.group(0)}")

    # Look for growth indicators
    growth_keywords = ["growing", "expansion", "expanding", "launched", "new product"]
    for keyword in growth_keywords:
        if keyword in text_lower:
            # Extract sentence containing the keyword
            sentences = text.split(".")
            for sentence in sentences:
                if keyword in sentence.lower():
                    insights.append(f"Growth indicator: {sentence.strip()}")
                    break

    # Look for technology mentions
    tech_keywords = [
        "ai",
        "artificial intelligence",
        "machine learning",
        "cloud",
        "saas",
        "api",
    ]
    for keyword in tech_keywords:
        if keyword in text_lower:
            insights.append(f"Technology focus: {keyword.upper()}")
            break

    # Look for industry-specific terms
    industry_keywords = {
        "fintech": ["payment", "banking", "financial", "fintech"],
        "healthtech": ["health", "medical", "healthcare", "patient"],
        "edtech": ["education", "learning", "student", "course"],
        "retail": ["retail", "ecommerce", "shopping", "consumer"],
    }

    for industry, keywords in industry_keywords.items():
        if any(keyword in text_lower for keyword in keywords):
            insights.append(f"Industry focus: {industry.title()}")
            break

    return insights[:max_insights]


def score_lead_against_icp(lead: Dict[str, Any], icp: Dict[str, Any]) -> Dict[str, Any]:
    """Score a lead against ICP criteria"""
    score = 0
    max_score = 10
    reasoning = []

    # Industry match (3 points)
    if lead.get("industry") and icp.get("target_industries"):
        lead_industry = lead["industry"].lower()
        target_industries = [ind.lower() for ind in icp["target_industries"]]

        if any(target in lead_industry for target in target_industries):
            score += 3
            reasoning.append(f"Industry match: {lead['industry']}")
        else:
            reasoning.append(f"Industry mismatch: {lead['industry']} not in targets")

    # Company size match (3 points)
    if lead.get("company_size") and icp.get("company_size_range"):
        # This is simplified - you'd want more sophisticated matching
        if icp["company_size_range"].lower() in lead["company_size"].lower():
            score += 3
            reasoning.append(f"Company size match: {lead['company_size']}")
        else:
            score += 1
            reasoning.append(f"Partial company size match: {lead['company_size']}")

    # Background/use case fit (2 points)
    if lead.get("background") and icp.get("use_cases"):
        background_lower = lead["background"].lower()
        use_cases = [uc.lower() for uc in icp["use_cases"]]

        if any(use_case in background_lower for use_case in use_cases):
            score += 2
            reasoning.append("Use case alignment found in company background")

    # Pain point fit (2 points)
    if lead.get("background") and icp.get("pain_points"):
        background_lower = lead["background"].lower()
        pain_points = [pp.lower() for pp in icp["pain_points"]]

        if any(pain_point in background_lower for pain_point in pain_points):
            score += 2
            reasoning.append("Pain point alignment found in company background")

    # Determine rating
    if score >= 8:
        rating = "Hot"
    elif score >= 5:
        rating = "Warm"
    else:
        rating = "Cold"

    return {
        "score": rating,
        "numerical_score": score,
        "reasoning": "; ".join(reasoning) if reasoning else "Limited data for scoring",
    }


def validate_lead_data(lead_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and clean lead data"""
    cleaned = {}

    # Required fields with your Airtable structure
    cleaned["UUID"] = generate_uuid()
    cleaned["Name"] = lead_data.get("Name", "N/A")
    cleaned["Address"] = lead_data.get("Address", "N/A")
    cleaned["Website"] = clean_url(lead_data.get("Website", "N/A"))
    cleaned["Email"] = clean_email(lead_data.get("Email", "Not available"))
    cleaned["Phone"] = clean_phone(lead_data.get("Phone", "Not available"))
    cleaned["Title"] = lead_data.get("Title", "N/A")
    cleaned["Company"] = clean_company_name(lead_data.get("Company", "N/A"))
    cleaned["Background"] = lead_data.get("Description", "N/A")

    return cleaned


def format_response_message(
    operation: str, leads_processed: int, errors: List[str] = None
) -> str:
    """Format a response message for the user"""
    if errors:
        error_msg = f" with {len(errors)} errors" if errors else ""
        return f"Completed {operation} for {leads_processed} leads{error_msg}."
    else:
        return f"Successfully completed {operation} for {leads_processed} leads."


def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """Extract JSON from text that might contain markdown or other formatting"""
    import json

    # Try direct JSON parsing first
    try:
        return json.loads(text)
    except:
        pass

    # Try to extract JSON from code blocks
    json_pattern = r"```json\s*(\{.*?\})\s*```"
    match = re.search(json_pattern, text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except:
            pass

    # Try to extract JSON objects
    json_pattern = r"\{[^{}]*\}"
    matches = re.findall(json_pattern, text)
    for match in matches:
        try:
            return json.loads(match)
        except:
            continue

    return None
