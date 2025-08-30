"""
OpenAI MCP Server for AI-powered text generation and analysis
"""

import os
import logging
import asyncio
from typing import Any, Sequence, Dict
import httpx
from dotenv import load_dotenv

load_dotenv()
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

logger = logging.getLogger(__name__)

# Create MCP server
server = Server("openai-client-server")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="generate_text",
            description="Generate text using OpenAI GPT models",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Text prompt for generation",
                    },
                    "model": {
                        "type": "string",
                        "description": "OpenAI model to use",
                        "default": "gpt-4o-mini",
                    },
                    "max_tokens": {
                        "type": "integer",
                        "description": "Maximum tokens to generate",
                        "default": 1000,
                    },
                    "temperature": {
                        "type": "number",
                        "description": "Temperature for generation (0-2)",
                        "default": 0.7,
                    },
                },
                "required": ["prompt"],
            },
        ),
        Tool(
            name="analyze_company_data",
            description="Analyze company data and extract insights",
            inputSchema={
                "type": "object",
                "properties": {
                    "company_data": {
                        "type": "string",
                        "description": "Company data to analyze",
                    },
                    "analysis_type": {
                        "type": "string",
                        "description": "Type of analysis (insights, summary, pain_points)",
                        "default": "insights",
                    },
                },
                "required": ["company_data"],
            },
        ),
        Tool(
            name="score_lead",
            description="Score a lead against ICP criteria",
            inputSchema={
                "type": "object",
                "properties": {
                    "lead_data": {
                        "type": "object",
                        "description": "Lead data to score",
                    },
                    "icp_data": {
                        "type": "object",
                        "description": "ICP criteria for scoring",
                    },
                },
                "required": ["lead_data", "icp_data"],
            },
        ),
        Tool(
            name="generate_email_opener",
            description="Generate personalized email opener",
            inputSchema={
                "type": "object",
                "properties": {
                    "company_insights": {
                        "type": "string",
                        "description": "Company insights and background",
                    },
                    "recipient_name": {
                        "type": "string",
                        "description": "Recipient name (optional)",
                    },
                    "company_name": {"type": "string", "description": "Company name"},
                },
                "required": ["company_insights", "company_name"],
            },
        ),
        Tool(
            name="generate_subject_line",
            description="Generate email subject line",
            inputSchema={
                "type": "object",
                "properties": {
                    "email_opener": {
                        "type": "string",
                        "description": "Email opener content",
                    },
                    "company_name": {"type": "string", "description": "Company name"},
                },
                "required": ["email_opener", "company_name"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> Sequence[TextContent]:
    """Handle tool calls."""
    if name == "generate_text":
        return await generate_text(arguments)
    elif name == "analyze_company_data":
        return await analyze_company_data(arguments)
    elif name == "score_lead":
        return await score_lead(arguments)
    elif name == "generate_email_opener":
        return await generate_email_opener(arguments)
    elif name == "generate_subject_line":
        return await generate_subject_line(arguments)

    raise ValueError(f"Unknown tool: {name}")


async def generate_text(arguments: Dict[str, Any]) -> Sequence[TextContent]:
    """Generate text using OpenAI"""
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return [
                TextContent(type="text", text="Error: OPENAI_API_KEY not configured")
            ]

        prompt = arguments.get("prompt")
        model = arguments.get("model", "gpt-4o-mini")
        max_tokens = arguments.get("max_tokens", 1000)
        temperature = arguments.get("temperature", 0.7)

        if not prompt:
            return [TextContent(type="text", text="Error: Prompt is required")]

        logger.info(f"Generating text with model: {model}")

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
            )

            if response.status_code == 200:
                data = response.json()
                generated_text = data["choices"][0]["message"]["content"]

                return [TextContent(type="text", text=generated_text)]
            else:
                error_msg = f"OpenAI API request failed: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return [TextContent(type="text", text=f"Error: {error_msg}")]

    except Exception as e:
        error_msg = f"Error generating text: {str(e)}"
        logger.error(error_msg)
        return [TextContent(type="text", text=f"Error: {error_msg}")]


async def analyze_company_data(arguments: Dict[str, Any]) -> Sequence[TextContent]:
    """Analyze company data and extract insights"""
    try:
        company_data = arguments.get("company_data")
        analysis_type = arguments.get("analysis_type", "insights")

        if not company_data:
            return [TextContent(type="text", text="Error: Company data is required")]

        # Create analysis prompt based on type
        if analysis_type == "insights":
            prompt = f"""
            Analyze the following company data and extract 3-5 key insights that would be useful for sales outreach:
            
            {company_data}
            
            Focus on:
            - Business model and value proposition
            - Growth indicators or recent developments
            - Technology stack or industry focus
            - Pain points or challenges they might face
            - Competitive advantages
            
            Return only the insights, one per line, starting with a dash (-).
            """
        elif analysis_type == "summary":
            prompt = f"""
            Create a concise 2-3 sentence summary of this company based on the following data:
            
            {company_data}
            
            Focus on what they do, their target market, and any notable characteristics.
            """
        elif analysis_type == "pain_points":
            prompt = f"""
            Based on the following company data, identify potential pain points or challenges this company might face:
            
            {company_data}
            
            Consider industry-specific challenges, growth-related issues, technology needs, or operational challenges.
            Return 2-3 potential pain points, one per line.
            """
        else:
            prompt = f"Analyze this company data: {company_data}"

        # Use the generate_text function
        result = await generate_text(
            {
                "prompt": prompt,
                "model": "gpt-4o-mini",
                "max_tokens": 500,
                "temperature": 0.3,
            }
        )

        return result

    except Exception as e:
        error_msg = f"Error analyzing company data: {str(e)}"
        logger.error(error_msg)
        return [TextContent(type="text", text=f"Error: {error_msg}")]


async def score_lead(arguments: Dict[str, Any]) -> Sequence[TextContent]:
    """Score a lead against ICP criteria"""
    try:
        lead_data = arguments.get("lead_data", {})
        icp_data = arguments.get("icp_data", {})

        if not lead_data or not icp_data:
            return [
                TextContent(
                    type="text", text="Error: Both lead data and ICP data are required"
                )
            ]

        prompt = f"""
        You are a Lead Qualification AI Agent. Score this lead against the provided ICP criteria.
        
        Lead Data:
        {lead_data}
        
        ICP Criteria:
        {icp_data}
        
        Scoring Criteria (Total: 10 points):
        - Industry Match (Max 3 points): Exact match or highly relevant → 3, Similar → 2, Unrelated → 0-1
        - Company Size Match (Max 3 points): Within target range → 3, Slightly off → 1-2, Significantly off → 0
        - Use Case Fit (Max 2 points): Clear match → 2, Some alignment → 1, No fit → 0
        - Pain Point Fit (Max 2 points): Clear alignment → 2, Some alignment → 1, No alignment → 0
        
        Rating Rules:
        - Hot: Score 8-10 (Strong alignment)
        - Warm: Score 5-7 (Moderate fit)
        - Cold: Score below 5 (Weak match)
        
        Return your response in this exact JSON format:
        {{
            "Score": "Hot|Warm|Cold",
            "NumericalScore": <0-10>,
            "Reasoning": "<Explain the score based on key similarities/differences>"
        }}
        """

        result = await generate_text(
            {
                "prompt": prompt,
                "model": "gpt-4o-mini",
                "max_tokens": 300,
                "temperature": 0.1,
            }
        )

        return result

    except Exception as e:
        error_msg = f"Error scoring lead: {str(e)}"
        logger.error(error_msg)
        return [TextContent(type="text", text=f"Error: {error_msg}")]


async def generate_email_opener(arguments: Dict[str, Any]) -> Sequence[TextContent]:
    """Generate personalized email opener"""
    try:
        company_insights = arguments.get("company_insights")
        recipient_name = arguments.get("recipient_name", "")
        company_name = arguments.get("company_name")

        if not company_insights or not company_name:
            return [
                TextContent(
                    type="text",
                    text="Error: Company insights and company name are required",
                )
            ]

        name_part = f" {recipient_name}" if recipient_name else ""

        prompt = f"""
        Generate a personalized 2-line email opener for a cold outreach email.
        
        Company: {company_name}
        Recipient:{name_part}
        Company Insights: {company_insights}
        
        Requirements:
        - Keep it concise (max 2 sentences)
        - Feel natural and personalized (avoid generic sales pitches)
        - Use first-person (e.g., "I came across...")
        - Include a curiosity-driven hook or relevant observation
        - Reference something specific about the company
        - Tone should be friendly, professional, and engaging
        
        Examples of good openers:
        - "I came across {company_name} and saw you're focused on [specific area]. Many teams I speak with find [relevant challenge] to be a major bottleneck—curious how you're tackling it?"
        - "Noticed that {company_name} is growing fast in [industry]—exciting times! With [relevant trend], companies like yours are rethinking [relevant process]—curious if that's on your radar?"
        
        Generate only the opener, no additional text.
        """

        result = await generate_text(
            {
                "prompt": prompt,
                "model": "gpt-4o-mini",
                "max_tokens": 150,
                "temperature": 0.7,
            }
        )

        return result

    except Exception as e:
        error_msg = f"Error generating email opener: {str(e)}"
        logger.error(error_msg)
        return [TextContent(type="text", text=f"Error: {error_msg}")]


async def generate_subject_line(arguments: Dict[str, Any]) -> Sequence[TextContent]:
    """Generate email subject line"""
    try:
        email_opener = arguments.get("email_opener")
        company_name = arguments.get("company_name")

        if not email_opener or not company_name:
            return [
                TextContent(
                    type="text",
                    text="Error: Email opener and company name are required",
                )
            ]

        prompt = f"""
        Generate a professional and catchy subject line based on this email opener:
        
        "{email_opener}"
        
        Company: {company_name}
        
        Requirements:
        - Be between 5 to 10 words
        - Avoid using quotation marks, apostrophes, or colons
        - Allow exclamation marks or question marks
        - Be concise, clear, and engaging
        - Reference the company or key topic from the opener
        
        Generate only the subject line, no additional text.
        """

        result = await generate_text(
            {
                "prompt": prompt,
                "model": "gpt-4o-mini",
                "max_tokens": 50,
                "temperature": 0.5,
            }
        )

        return result

    except Exception as e:
        error_msg = f"Error generating subject line: {str(e)}"
        logger.error(error_msg)
        return [TextContent(type="text", text=f"Error: {error_msg}")]


async def main():
    """Run the OpenAI MCP server."""
    logger.info("Starting OpenAI MCP Server...")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream, server.create_initialization_options()
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
