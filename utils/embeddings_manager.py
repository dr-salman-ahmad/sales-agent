"""
Utility functions for managing embeddings and ChromaDB operations
"""

import os
import chromadb
from chromadb.config import Settings
from openai import AsyncOpenAI
from typing import List, Dict, Any
import json
import logging

logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize ChromaDB with new client format
chroma_client = chromadb.PersistentClient(path="embeddings_db")


def get_or_create_collection(
    user_id: str, reset: bool = False
) -> Any:  # Return type Any since Collection type is not available
    """
    Get or create a ChromaDB collection for a user

    Args:
        user_id: The user's ID
        reset: If True, delete existing collection and create new one
    """
    collection_name = f"drive_docs_{user_id}"

    try:
        if reset:
            try:
                # Delete existing collection if it exists
                chroma_client.delete_collection(name=collection_name)
                logger.info(f"Deleted existing collection: {collection_name}")
            except Exception as e:
                # Ignore error if collection doesn't exist
                logger.info(f"No existing collection to delete: {collection_name}")

            # Create new collection
            collection = chroma_client.create_collection(
                name=collection_name, metadata={"user_id": user_id}
            )
            logger.info(f"Created new collection: {collection_name}")
            return collection

        # Try to get existing collection
        collection = chroma_client.get_collection(name=collection_name)
        logger.info(f"Retrieved existing collection: {collection_name}")
        return collection

    except Exception as e:
        logger.info(f"Collection {collection_name} not found, creating new one")
        try:
            # Create new collection
            collection = chroma_client.create_collection(
                name=collection_name, metadata={"user_id": user_id}
            )
            logger.info(f"Successfully created collection: {collection_name}")
            return collection
        except Exception as create_error:
            logger.error(
                f"Error creating collection {collection_name}: {str(create_error)}"
            )
            raise


async def get_embedding(text: str) -> List[float]:
    """Get embeddings using OpenAI's API"""
    try:
        # Generate embeddings using OpenAI
        response = await client.embeddings.create(
            input=text,
            model="text-embedding-3-small",  # Most efficient model, 1536 dimensions
        )

        embedding = response.data[0].embedding
        logger.info(f"Generated embedding of size: {len(embedding)}")

        return embedding

    except Exception as e:
        logger.error(f"Error getting embeddings: {str(e)}")
        raise


def chunk_text(text: str, chunk_size: int = 1000) -> List[str]:
    """Split text into chunks for embedding"""
    words = text.split()
    chunks = []
    current_chunk = []
    current_size = 0

    for word in words:
        word_size = len(word) + 1  # +1 for space
        if current_size + word_size > chunk_size:
            chunks.append(" ".join(current_chunk))
            current_chunk = [word]
            current_size = word_size
        else:
            current_chunk.append(word)
            current_size += word_size

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks


def delete_file_embeddings(collection: Any, file_id: str) -> bool:
    """Delete all embeddings for a specific file"""
    try:
        # Get all chunks for this file
        results = collection.get(
            where={"file_id": file_id}, include=["metadatas", "documents"]
        )

        if not results["ids"]:
            logger.info(f"No existing embeddings found for file {file_id}")
            return True

        # Delete the chunks
        collection.delete(ids=results["ids"])
        logger.info(f"Deleted {len(results['ids'])} chunks for file {file_id}")
        return True

    except Exception as e:
        logger.error(f"Error deleting embeddings for file {file_id}: {str(e)}")
        return False


async def process_and_store_document(
    user_id: str,
    file_id: str,
    content: str,
    metadata: Dict[str, Any],
    reset_collection: bool = False,
) -> None:
    """
    Process document content and store embeddings in ChromaDB

    Args:
        user_id: The user's ID
        file_id: The file's ID
        content: The file's content
        metadata: File metadata
        reset_collection: If True, delete entire collection before processing
    """
    try:
        # Get user's collection (optionally reset it)
        collection = get_or_create_collection(user_id, reset=reset_collection)
        logger.info(f"Processing document {metadata.get('name', file_id)}")

        # Delete existing embeddings for this file
        if not reset_collection:  # No need to delete if we reset the whole collection
            delete_file_embeddings(collection, file_id)

        # Chunk the content
        chunks = chunk_text(content)
        logger.info(f"Split document into {len(chunks)} chunks")

        # Get embeddings for each chunk
        embeddings = []
        ids = []
        metadatas = []

        for i, chunk in enumerate(chunks):
            # Get embedding for chunk
            logger.info(f"Getting embedding for chunk {i+1}/{len(chunks)}")
            embedding = await get_embedding(chunk)
            embeddings.append(embedding)

            # Create unique ID for chunk
            chunk_id = f"{file_id}_chunk_{i}"
            ids.append(chunk_id)

            # Add chunk metadata
            chunk_metadata = {
                **metadata,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "file_id": file_id,
                "user_id": user_id,
            }
            metadatas.append(chunk_metadata)

        # Store in ChromaDB
        logger.info(f"Storing {len(chunks)} chunks in ChromaDB")
        collection.add(
            embeddings=embeddings, documents=chunks, ids=ids, metadatas=metadatas
        )

        logger.info(
            f"Successfully stored embeddings for file {metadata.get('name', file_id)}"
        )

    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        raise


def get_stored_embeddings(user_id: str) -> Dict[str, Any]:
    """Get all stored embeddings for a user"""
    try:
        collection = get_or_create_collection(user_id)
        logger.info(f"Retrieving embeddings for user {user_id}")

        # Get all documents
        results = collection.get(include=["embeddings", "documents", "metadatas"])
        logger.info(f"Found {len(results['metadatas'])} chunks")

        # Group by file_id
        files = {}
        for i, metadata in enumerate(results["metadatas"]):
            file_id = metadata["file_id"]
            if file_id not in files:
                files[file_id] = {
                    "name": metadata["name"],
                    "mime_type": metadata["mime_type"],
                    "modified_time": metadata["modified_time"],
                    "size": metadata["size"],
                    "chunks": [],
                }

            files[file_id]["chunks"].append(
                {
                    "chunk_index": metadata["chunk_index"],
                    "content": results["documents"][i],
                    "embedding_size": len(results["embeddings"][i]),
                }
            )

        logger.info(f"Successfully retrieved embeddings for {len(files)} files")
        return {"total_files": len(files), "files": files}

    except Exception as e:
        logger.error(f"Error getting embeddings for user {user_id}: {str(e)}")
        return {"error": str(e), "total_files": 0, "files": {}}
