"""
Web Scraper MCP Server for extracting content from websites
"""

import logging
import asyncio
from typing import Any, Sequence, Dict, List
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

logger = logging.getLogger(__name__)

# Create MCP server
server = Server("web-scraper-server")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="scrape_website",
            description="Scrape content from a website",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to scrape"},
                    "extract_links": {
                        "type": "boolean",
                        "description": "Whether to extract links from the page",
                        "default": False,
                    },
                    "max_content_length": {
                        "type": "integer",
                        "description": "Maximum content length to return",
                        "default": 5000,
                    },
                },
                "required": ["url"],
            },
        ),
        Tool(
            name="extract_company_info",
            description="Extract company information from a website",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Company website URL"}
                },
                "required": ["url"],
            },
        ),
        Tool(
            name="find_relevant_pages",
            description="Find relevant pages (About, Products, etc.) from a website",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Website homepage URL"},
                    "max_pages": {
                        "type": "integer",
                        "description": "Maximum number of relevant pages to find",
                        "default": 3,
                    },
                },
                "required": ["url"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> Sequence[TextContent]:
    """Handle tool calls."""
    if name == "scrape_website":
        return await scrape_website(arguments)
    elif name == "extract_company_info":
        return await extract_company_info(arguments)
    elif name == "find_relevant_pages":
        return await find_relevant_pages(arguments)

    raise ValueError(f"Unknown tool: {name}")


async def scrape_website(arguments: Dict[str, Any]) -> Sequence[TextContent]:
    """Scrape content from a website"""
    try:
        url = arguments.get("url")
        extract_links = arguments.get("extract_links", False)
        max_content_length = arguments.get("max_content_length", 5000)

        if not url:
            return [TextContent(type="text", text="Error: URL is required")]

        logger.info(f"Scraping website: {url}")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
            response = await client.get(url)

            if response.status_code == 200:
                soup = BeautifulSoup(response.content, "html.parser")

                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()

                # Extract text content
                text_content = soup.get_text()

                # Clean up text
                lines = (line.strip() for line in text_content.splitlines())
                chunks = (
                    phrase.strip() for line in lines for phrase in line.split("  ")
                )
                clean_text = " ".join(chunk for chunk in chunks if chunk)

                # Truncate if too long
                if len(clean_text) > max_content_length:
                    clean_text = clean_text[:max_content_length] + "..."

                result_text = f"Content from {url}:\n\n{clean_text}"

                # Extract links if requested
                if extract_links:
                    links = []
                    for link in soup.find_all("a", href=True):
                        href = link["href"]
                        text = link.get_text().strip()
                        if href and text:
                            # Convert relative URLs to absolute
                            absolute_url = urljoin(url, href)
                            links.append(f"{text}: {absolute_url}")

                    if links:
                        result_text += f"\n\nLinks found ({len(links)}):\n"
                        for link in links[:20]:  # Limit to first 20 links
                            result_text += f"- {link}\n"

                return [TextContent(type="text", text=result_text)]
            else:
                error_msg = f"Failed to scrape website: {response.status_code} - {response.text[:200]}"
                logger.error(error_msg)
                return [TextContent(type="text", text=f"Error: {error_msg}")]

    except Exception as e:
        error_msg = f"Error scraping website: {str(e)}"
        logger.error(error_msg)
        return [TextContent(type="text", text=f"Error: {error_msg}")]


async def extract_company_info(arguments: Dict[str, Any]) -> Sequence[TextContent]:
    """Extract company information from a website"""
    try:
        url = arguments.get("url")

        if not url:
            return [TextContent(type="text", text="Error: URL is required")]

        logger.info(f"Extracting company info from: {url}")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
            response = await client.get(url)

            if response.status_code == 200:
                soup = BeautifulSoup(response.content, "html.parser")

                # Extract basic info
                title = soup.find("title")
                title_text = title.get_text().strip() if title else "No title found"

                # Look for meta description
                meta_desc = soup.find("meta", attrs={"name": "description"})
                description = meta_desc.get("content", "").strip() if meta_desc else ""

                # Look for company-specific information
                company_info = {
                    "title": title_text,
                    "description": description,
                    "insights": [],
                }

                # Extract text content for analysis
                for script in soup(["script", "style"]):
                    script.decompose()

                text_content = soup.get_text().lower()

                # Look for funding information
                funding_keywords = [
                    "funding",
                    "raised",
                    "series",
                    "investment",
                    "venture capital",
                    "seed round",
                ]
                for keyword in funding_keywords:
                    if keyword in text_content:
                        company_info["insights"].append(f"Mentions {keyword}")
                        break

                # Look for technology stack
                tech_keywords = [
                    "ai",
                    "artificial intelligence",
                    "machine learning",
                    "cloud",
                    "saas",
                    "api",
                    "blockchain",
                ]
                for keyword in tech_keywords:
                    if keyword in text_content:
                        company_info["insights"].append(
                            f"Technology focus: {keyword.upper()}"
                        )
                        break

                # Look for growth indicators
                growth_keywords = [
                    "growing",
                    "expansion",
                    "launched",
                    "new product",
                    "hiring",
                ]
                for keyword in growth_keywords:
                    if keyword in text_content:
                        company_info["insights"].append(f"Growth indicator: {keyword}")
                        break

                # Look for LinkedIn profile
                linkedin_link = soup.find("a", href=lambda x: x and "linkedin.com" in x)
                if linkedin_link:
                    company_info["linkedin"] = linkedin_link.get("href")

                # Format result
                result_text = f"Company Information from {url}:\n\n"
                result_text += f"Title: {company_info['title']}\n"
                if company_info["description"]:
                    result_text += f"Description: {company_info['description']}\n"
                if company_info.get("linkedin"):
                    result_text += f"LinkedIn: {company_info['linkedin']}\n"
                if company_info["insights"]:
                    result_text += f"Insights: {', '.join(company_info['insights'])}\n"

                return [TextContent(type="text", text=result_text)]
            else:
                error_msg = f"Failed to extract company info: {response.status_code}"
                logger.error(error_msg)
                return [TextContent(type="text", text=f"Error: {error_msg}")]

    except Exception as e:
        error_msg = f"Error extracting company info: {str(e)}"
        logger.error(error_msg)
        return [TextContent(type="text", text=f"Error: {error_msg}")]


async def find_relevant_pages(arguments: Dict[str, Any]) -> Sequence[TextContent]:
    """Find relevant pages from a website"""
    try:
        url = arguments.get("url")
        max_pages = arguments.get("max_pages", 3)

        if not url:
            return [TextContent(type="text", text="Error: URL is required")]

        logger.info(f"Finding relevant pages from: {url}")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
            response = await client.get(url)

            if response.status_code == 200:
                soup = BeautifulSoup(response.content, "html.parser")

                # Look for relevant links
                relevant_keywords = [
                    "about",
                    "company",
                    "team",
                    "mission",
                    "vision",
                    "values",
                    "product",
                    "service",
                    "solution",
                    "platform",
                    "case study",
                    "customer",
                    "client",
                    "success",
                    "news",
                    "press",
                    "blog",
                    "resource",
                ]

                relevant_links = []

                for link in soup.find_all("a", href=True):
                    href = link["href"]
                    text = link.get_text().strip().lower()

                    if href and text:
                        # Check if link text contains relevant keywords
                        for keyword in relevant_keywords:
                            if keyword in text or keyword in href.lower():
                                absolute_url = urljoin(url, href)

                                # Avoid duplicates and external links
                                parsed_base = urlparse(url)
                                parsed_link = urlparse(absolute_url)

                                if (
                                    parsed_link.netloc == parsed_base.netloc
                                    and absolute_url
                                    not in [rl["url"] for rl in relevant_links]
                                ):

                                    relevant_links.append(
                                        {
                                            "text": text,
                                            "url": absolute_url,
                                            "type": keyword,
                                        }
                                    )
                                    break

                # Sort by relevance (about pages first, then products, etc.)
                priority_order = [
                    "about",
                    "company",
                    "product",
                    "service",
                    "case study",
                    "news",
                ]
                relevant_links.sort(
                    key=lambda x: (
                        priority_order.index(x["type"])
                        if x["type"] in priority_order
                        else 999
                    )
                )

                # Limit results
                relevant_links = relevant_links[:max_pages]

                if relevant_links:
                    result_text = (
                        f"Found {len(relevant_links)} relevant pages from {url}:\n\n"
                    )
                    for i, link in enumerate(relevant_links, 1):
                        result_text += f"{i}. {link['text'].title()}\n"
                        result_text += f"   Type: {link['type'].title()}\n"
                        result_text += f"   URL: {link['url']}\n\n"

                    return [TextContent(type="text", text=result_text)]
                else:
                    return [
                        TextContent(
                            type="text", text=f"No relevant pages found on {url}"
                        )
                    ]
            else:
                error_msg = f"Failed to find relevant pages: {response.status_code}"
                logger.error(error_msg)
                return [TextContent(type="text", text=f"Error: {error_msg}")]

    except Exception as e:
        error_msg = f"Error finding relevant pages: {str(e)}"
        logger.error(error_msg)
        return [TextContent(type="text", text=f"Error: {error_msg}")]


async def main():
    """Run the Web Scraper MCP server."""
    logger.info("Starting Web Scraper MCP Server...")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream, server.create_initialization_options()
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
