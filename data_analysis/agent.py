"""
Data Analysis Agent for querying and analyzing document embeddings
"""

import os
import logging
from typing import Dict, Any, List
from dotenv import load_dotenv
from google.genai import types
from google.adk.agents.llm_agent import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from utils.embeddings_manager import get_or_create_collection, get_embedding

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Constants
APP_NAME = "data_analysis"
RELEVANCE_THRESHOLD = -100  # Lowered from 50% to 30% to catch more results

# Initialize session service
session_service = InMemorySessionService()


async def search_documents(user_id: str, agent_id: str, query: str) -> Dict[str, Any]:
    """
    Search through user's documents using semantic search

    Args:
        user_id (str): The user's ID
        agent_id (str): The agent's ID
        query (str): The search query

    Returns:
        dict: Search results with status and findings
    """
    try:
        # Get the user's document collection for this agent
        collection = get_or_create_collection(user_id, agent_id)
        logger.info(
            f"Searching documents for user {user_id}, agent {agent_id} with query: {query}"
        )

        # Get embedding for the query
        query_embedding = await get_embedding(query)
        logger.info("Generated query embedding")

        # Search for relevant documents
        logger.info("Querying ChromaDB collection...")
        query_results = collection.query(
            query_embeddings=[query_embedding],
            n_results=10,  # Increased from 5 to 10 to get more potential matches
            include=["documents", "metadatas", "distances"],
        )

        # Debug log the raw results
        logger.info(f"Raw query results: {len(query_results['ids'][0])} chunks found")
        for i, (doc_id, distance) in enumerate(
            zip(query_results["ids"][0], query_results["distances"][0])
        ):
            relevance = 1 - distance
            relevance_percent = int(relevance * 100)
            logger.info(
                f"Chunk {i+1}: ID={doc_id}, Distance={distance:.4f}, Relevance={relevance_percent}%"
            )

        if not query_results["ids"][0]:
            logger.info("No documents found in collection")
            return {
                "status": "no_results",
                "message": "No documents found. Please make sure you have indexed some documents first.",
            }

        # Group results by file
        file_results = {}
        total_relevant_chunks = 0

        for i, metadata in enumerate(query_results["metadatas"][0]):
            file_id = metadata["file_id"]
            if file_id not in file_results:
                file_results[file_id] = {
                    "name": metadata.get("name", "Unknown"),
                    "chunks": [],
                }

            # Calculate relevance score
            relevance = 1 - query_results["distances"][0][i]
            relevance_percent = int(relevance * 100)

            # Include if relevance > threshold
            if relevance_percent > RELEVANCE_THRESHOLD:
                total_relevant_chunks += 1
                file_results[file_id]["chunks"].append(
                    {
                        "content": query_results["documents"][0][i],
                        "relevance": relevance_percent,
                    }
                )
                logger.info(
                    f"Found relevant chunk in {metadata.get('name', 'Unknown')}: {relevance_percent}% relevant"
                )

        # Format results, only including files with relevant chunks
        findings = []
        for file_id, file_data in file_results.items():
            if file_data["chunks"]:  # Only include if there are relevant chunks
                # Sort chunks by relevance
                sorted_chunks = sorted(
                    file_data["chunks"], key=lambda x: x["relevance"], reverse=True
                )

                findings.append(
                    {"file_name": file_data["name"], "chunks": sorted_chunks}
                )
                logger.info(
                    f"Including {len(sorted_chunks)} relevant chunks from {file_data['name']}"
                )

        if findings:
            logger.info(
                f"Returning {len(findings)} files with {total_relevant_chunks} relevant chunks"
            )
            return {"status": "success", "findings": findings}
        else:
            logger.info(
                f"No chunks met the relevance threshold of {RELEVANCE_THRESHOLD}%"
            )
            return {
                "status": "no_results",
                "message": f"""I found some potential matches in your documents, but none were relevant enough (threshold: {RELEVANCE_THRESHOLD}%).
Would you like me to:
1. Lower the relevance threshold
2. Try a different search approach
3. Look for related topics instead""",
            }

    except Exception as e:
        logger.error(f"Error searching documents: {str(e)}")
        return {"status": "error", "message": f"Error searching documents: {str(e)}"}


async def get_or_create_session(user_id: str):
    """Get existing session for user or create a new one if none exists"""
    try:
        # First, try to get existing sessions for this user
        list_response = await session_service.list_sessions(
            app_name=APP_NAME,
            user_id=user_id,
        )

        # If sessions exist, use the most recent one
        if list_response.sessions:
            logger.info(
                f"Found {len(list_response.sessions)} existing sessions for user {user_id}"
            )
            # Return the most recent session
            return list_response.sessions[-1]

        # No existing sessions, create a new one
        logger.info(f"Creating new session for user {user_id}")
        return await session_service.create_session(
            app_name=APP_NAME,
            user_id=user_id,
        )

    except Exception as e:
        logger.error(f"Error getting or creating session: {e}")
        # Fallback to creating a new session
        return await session_service.create_session(
            app_name=APP_NAME,
            user_id=user_id,
        )


# Create the agent
agent = LlmAgent(
    model="gemini-2.5-flash",
    name="document_analysis_agent",
    instruction="""You are a dynamic document analysis assistant that adapts based on the user's specific goal.

Your core capabilities:
1. Search through document embeddings to find relevant information
2. Answer questions based on document content
3. Provide summaries and insights from documents
4. Quote relevant passages when answering questions
5. ADAPT your analysis style based on the user's goal

GOAL-BASED BEHAVIOR:
- Extract the "goal" from the user's message context
- Adjust your analysis focus and terminology based on this goal
- Provide insights most relevant to achieving that goal
- Use appropriate domain expertise and language

Core Guidelines:
1. Always search through documents first before answering
2. When answering questions, cite specific documents and quote relevant passages
3. If you can't find relevant information, be honest and say so
4. Maintain context between questions about the same documents
5. Format responses in a clear, readable way
6. Don't return the user id, access and refresh tokens in the response
7. Don't return the user's document collection id in the response
8. User will provide user id in the chat message but don't return it in the response

IMPORTANT: You need both user_id and agent_id to search documents. Extract these from the user's message context.

When using the search_documents tool:
1. The tool returns findings grouped by file
2. Each finding includes the file name and relevant chunks
3. Chunks are sorted by relevance (percentage)
4. Use the relevance scores to prioritize information

GOAL ADAPTATION EXAMPLES:

For Finance Goal:
- Focus on financial metrics, revenue, costs, ROI
- Use financial terminology and context
- Highlight budget implications and financial health

For Marketing Goal:
- Focus on campaign performance, customer metrics, market insights
- Use marketing terminology and frameworks
- Highlight conversion rates, brand performance, market opportunities

For Sales Goal:
- Focus on pipeline, deals, customer relationships, performance
- Use sales terminology and metrics
- Highlight opportunities, challenges, and actionable insights

Response Format (adapt based on goal):
Question: What is the revenue growth?
Finance-focused Response: Based on the financial documents, revenue grew 25% year-over-year, indicating strong financial performance and market expansion.

If no relevant information is found:
"I've searched through your documents but couldn't find any information directly relevant to your query about [goal-specific context]."

Remember: Your analysis style and focus should dynamically adjust based on the user's goal while maintaining your core document search and analysis capabilities.
""",
    tools=[search_documents],
)

# Create the runner
runner = Runner(agent=agent, app_name=APP_NAME, session_service=session_service)
