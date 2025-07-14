"""
Document chunking and embedding service for search indexing.

This module provides functionality to chunk document content and generate
embeddings using OpenAI's text-embedding-3-large model.
"""

import logging
from typing import List, Optional
from datetime import datetime
import asyncio

from openai import AsyncAzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    after_log
)

from config import OpenAIConfig


logger = logging.getLogger(__name__)


class DocumentChunk:
    """
    Represents a chunk of document content with metadata.
    """
    
    def __init__(
        self,
        content: str,
        chunk_index: int,
        document_id: str,
        document_url: str,
        submission_id: str,
        user_id: str,
        embedding: Optional[List[float]] = None
    ):
        """
        Initialize a document chunk.
        
        Args:
            content: The text content of the chunk
            chunk_index: Sequential index of this chunk within the document
            document_id: ID of the source document
            document_url: URL of the source document
            submission_id: ID of the submission
            user_id: ID of the user who submitted the document
            embedding: Optional embedding vector for the content
        """
        self.id = f"{document_id}_{chunk_index}"
        self.content = content
        self.chunk_index = chunk_index
        self.document_id = document_id
        self.document_url = document_url
        self.submission_id = submission_id
        self.user_id = user_id
        self.embedding = embedding
        self.timestamp = datetime.utcnow()
    
    def to_search_document(self) -> dict:
        """
        Convert the chunk to a search document for indexing.
        
        Returns:
            dict: Search document ready for Azure AI Search indexing
        """
        doc = {
            "id": self.id,
            "content": self.content,
            "documentId": self.document_id,
            "documentUrl": self.document_url,
            "submissionId": self.submission_id,
            "userId": self.user_id,
            "chunkIndex": self.chunk_index,
            "timestamp": self.timestamp.isoformat() + "Z"  # Add Z to indicate UTC timezone
        }
        
        if self.embedding:
            doc["contentVector"] = self.embedding
        
        return doc


class DocumentChunkingService:
    """
    Service for chunking documents and generating embeddings.
    
    This service handles document chunking with overlap and generates
    embeddings using OpenAI's text-embedding-3-large model.
    """
    
    def __init__(self, config: OpenAIConfig):
        """
        Initialize the document chunking service.
        
        Args:
            config: Azure OpenAI configuration settings
        """
        self.config = config
        
        # Create token provider for Azure OpenAI authentication
        credential = DefaultAzureCredential()
        token_provider = get_bearer_token_provider(
            credential,
            "https://cognitiveservices.azure.com/.default"
        )
        
        self.client = AsyncAzureOpenAI(
            azure_endpoint=config.endpoint,
            api_version=config.api_version,
            azure_ad_token_provider=token_provider
        )
        self.logger = logging.getLogger(__name__)
    
    def chunk_document(
        self,
        content: str,
        document_id: str,
        document_url: str,
        submission_id: str,
        user_id: str
    ) -> List[DocumentChunk]:
        """
        Chunk a document into overlapping segments.
        
        Args:
            content: Document content to chunk
            document_id: ID of the source document
            document_url: URL of the source document
            submission_id: ID of the submission
            user_id: ID of the user who submitted the document
            
        Returns:
            List[DocumentChunk]: List of document chunks
        """
        if not content or not content.strip():
            self.logger.warning(f"Empty content for document {document_id}")
            return []
        
        chunks = []
        chunk_index = 0
        start = 0
        
        while start < len(content):
            # Calculate end position for this chunk
            end = start + self.config.chunk_size
            
            # If this is not the last chunk, try to break at a word boundary
            if end < len(content):
                # Find the last space within the chunk to avoid breaking words
                last_space = content.rfind(' ', start, end)
                if last_space > start:
                    end = last_space
            
            # Extract the chunk content
            chunk_content = content[start:end].strip()
            
            if chunk_content:
                chunk = DocumentChunk(
                    content=chunk_content,
                    chunk_index=chunk_index,
                    document_id=document_id,
                    document_url=document_url,
                    submission_id=submission_id,
                    user_id=user_id
                )
                chunks.append(chunk)
                chunk_index += 1
            
            # Move to the next chunk with overlap
            start = end - self.config.chunk_overlap
            
            # Ensure we don't go backwards
            if start <= 0:
                start = end
        
        self.logger.info(f"Created {len(chunks)} chunks for document {document_id}")
        return chunks
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(Exception),
        before_sleep=before_sleep_log(logging.getLogger(__name__), logging.WARNING),
        after=after_log(logging.getLogger(__name__), logging.INFO)
    )
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a text using Azure OpenAI's embedding model.
        
        Args:
            text: Text to generate embedding for
            
        Returns:
            List[float]: Embedding vector
            
        Raises:
            Exception: If embedding generation fails
        """
        try:
            response = await self.client.embeddings.create(
                input=text,
                model=self.config.deployment_name,
                dimensions=self.config.embedding_dimensions
            )
            
            embedding = response.data[0].embedding
            self.logger.debug(f"Generated embedding with {len(embedding)} dimensions")
            return embedding
            
        except Exception as e:
            self.logger.error(f"Failed to generate embedding: {e}")
            raise
    
    async def process_chunks_with_embeddings(self, chunks: List[DocumentChunk]) -> List[DocumentChunk]:
        """
        Process chunks by generating embeddings for each chunk.
        
        Args:
            chunks: List of document chunks to process
            
        Returns:
            List[DocumentChunk]: Chunks with embeddings generated
        """
        if not chunks:
            return []
        
        self.logger.info(f"Generating embeddings for {len(chunks)} chunks")
        
        # Generate embeddings for all chunks concurrently
        embedding_tasks = [
            self.generate_embedding(chunk.content) for chunk in chunks
        ]
        
        try:
            embeddings = await asyncio.gather(*embedding_tasks)
            
            # Assign embeddings to chunks
            for chunk, embedding in zip(chunks, embeddings):
                chunk.embedding = embedding
            
            self.logger.info(f"Successfully generated embeddings for {len(chunks)} chunks")
            return chunks
            
        except Exception as e:
            self.logger.error(f"Failed to generate embeddings for chunks: {e}")
            raise
    
    async def chunk_and_embed_document(
        self,
        content: str,
        document_id: str,
        document_url: str,
        submission_id: str,
        user_id: str
    ) -> List[DocumentChunk]:
        """
        Complete processing pipeline: chunk document and generate embeddings.
        
        Args:
            content: Document content to process
            document_id: ID of the source document
            document_url: URL of the source document
            submission_id: ID of the submission
            user_id: ID of the user who submitted the document
            
        Returns:
            List[DocumentChunk]: Processed chunks with embeddings
        """
        # Step 1: Chunk the document
        chunks = self.chunk_document(
            content=content,
            document_id=document_id,
            document_url=document_url,
            submission_id=submission_id,
            user_id=user_id
        )
        
        if not chunks:
            self.logger.warning(f"No chunks created for document {document_id}")
            return []
        
        # Step 2: Generate embeddings for all chunks
        chunks_with_embeddings = await self.process_chunks_with_embeddings(chunks)
        
        return chunks_with_embeddings
