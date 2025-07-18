"""
Azure AI Search indexing service for document content.

This module handles retrieval of document content from Cosmos DB and indexing
into Azure AI Search with proper metadata and security trimming.
"""

import logging
import uuid
from typing import Optional, Dict, Any
from datetime import datetime

from azure.cosmos.aio import CosmosClient
from azure.core.exceptions import ResourceNotFoundError, HttpResponseError
from azure.identity.aio import DefaultAzureCredential
from azure.identity import DefaultAzureCredential as SyncDefaultAzureCredential
from azure.search.documents.aio import SearchClient
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    after_log
)

from config import AppConfig
from models import DocumentContentExtractedEvent, DocumentRecord, DocumentIndexedEvent, DocumentIndexedEventData
from search_index_manager import SearchIndexManager
from document_chunking_service import DocumentChunkingService


class SearchIndexer:
    """
    Azure AI Search indexing service for document content.
    
    This class handles document retrieval from Cosmos DB and indexing into
    Azure AI Search with proper metadata and security trimming.
    """
    
    def __init__(self, config: AppConfig):
        """
        Initialize the search indexer.
        
        Args:
            config: Application configuration containing Cosmos DB and AI Search settings
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.cosmos_client: Optional[CosmosClient] = None
        self.documents_container = None
        self.search_index_manager: Optional[SearchIndexManager] = None
        self.search_client: Optional[SearchClient] = None
        self.chunking_service: Optional[DocumentChunkingService] = None
        
    async def initialize(self) -> None:
        """
        Initialize the search indexer and required Azure clients.
        
        Raises:
            Exception: If initialization fails
        """
        try:
            # Initialize credentials
            credential = DefaultAzureCredential()
            
            # Initialize Cosmos DB client
            self.cosmos_client = CosmosClient(
                url=self.config.cosmos_db.endpoint,
                credential=credential
            )
            
            # Get database and container references
            database = self.cosmos_client.get_database_client(self.config.cosmos_db.database_name)
            self.documents_container = database.get_container_client(self.config.cosmos_db.documents_container_name)
            
            # Initialize search index manager (using sync credential)
            sync_credential = SyncDefaultAzureCredential()
            self.search_index_manager = SearchIndexManager(
                config=self.config.ai_search,
                openai_config=self.config.openai,
                credential=sync_credential
            )
            
            # Ensure the search index exists (sync call)
            self.search_index_manager.ensure_index_exists()
            
            # Initialize search client for indexing documents
            self.search_client = SearchClient(
                endpoint=self.config.ai_search.endpoint,
                index_name=self.config.ai_search.index_name,
                credential=credential
            )
            
            # Initialize document chunking service
            self.chunking_service = DocumentChunkingService(config=self.config.openai)
            
            self.logger.info("Search indexer initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize search indexer: {e}")
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((HttpResponseError, ResourceNotFoundError)),
        before_sleep=before_sleep_log(logging.getLogger(__name__), logging.WARNING),
        after=after_log(logging.getLogger(__name__), logging.INFO)
    )
    async def retrieve_document(self, document_id: str, submission_id: str) -> Optional[DocumentRecord]:
        """
        Retrieve document content from Cosmos DB documents container.
        
        Args:
            document_id: ID of the document to retrieve
            submission_id: Submission ID (partition key)
            
        Returns:
            Optional[DocumentRecord]: The document record if found, None otherwise
        """
        try:
            # Retrieve document from Cosmos DB
            document_data = await self.documents_container.read_item(
                item=document_id,
                partition_key=submission_id
            )
            
            # Parse into DocumentRecord model
            document = DocumentRecord(**document_data)
            
            self.logger.info(f"Retrieved document: {document.id}")
            self.logger.debug(f"Document details: submissionId={document.submissionId}, "
                            f"userId={document.userId}, contentLength={len(document.content)}, "
                            f"documentUrl={document.documentUrl}")
            
            return document
            
        except ResourceNotFoundError:
            self.logger.warning(f"Document not found: {document_id} in submission {submission_id}")
            return None
        except Exception as e:
            self.logger.error(f"Failed to retrieve document {document_id}: {e}")
            raise
    
    async def index_document(self, event: DocumentContentExtractedEvent) -> DocumentIndexedEvent:
        """
        Index a document into Azure AI Search.
        
        Args:
            event: DocumentContentExtractedEvent to process
            
        Returns:
            DocumentIndexedEvent: Event indicating indexing completion
        """
        try:
            # Step 1: Retrieve document content from Cosmos DB
            document = await self.retrieve_document(
                document_id=event.data.documentId,
                submission_id=event.submissionId
            )
            
            if not document:
                # Document not found, create failed event
                return await self._create_failed_event(event, "Document not found in documents container")
            
            # TODO: Step 2: Create Azure AI Search index if it doesn't exist
            # Index already ensured to exist during initialization
            
            # Step 3: Process document content (chunking and embeddings)
            chunks = await self.chunking_service.chunk_and_embed_document(
                content=document.content,
                document_id=document.id,
                document_url=document.documentUrl,
                submission_id=document.submissionId,
                user_id=document.userId
            )
            
            if not chunks:
                self.logger.warning(f"No chunks generated for document {document.id}")
                return await self._create_failed_event(event, "No chunks generated from document content")
            
            # Step 4: Index document chunks with metadata and security trimming
            search_documents = [chunk.to_search_document() for chunk in chunks]
            
            try:
                result = await self.search_client.upload_documents(search_documents)
                
                # Check if all documents were indexed successfully
                failed_count = len([r for r in result if not r.succeeded])
                if failed_count > 0:
                    self.logger.warning(f"Failed to index {failed_count} out of {len(search_documents)} chunks")
                
                self.logger.info(f"Successfully indexed {len(search_documents) - failed_count} chunks for document {document.id}")
                
            except Exception as e:
                self.logger.error(f"Failed to upload documents to search index: {e}")
                return await self._create_failed_event(event, f"Failed to upload to search index: {str(e)}")
            
            # Return success event
            return await self._create_success_event(event, self.config.ai_search.index_name)
            
        except Exception as e:
            self.logger.error(f"Failed to index document {event.data.documentId}: {e}")
            return await self._create_failed_event(event, str(e))
    
    async def _create_success_event(self, event: DocumentContentExtractedEvent, index_name: str) -> DocumentIndexedEvent:
        """
        Create a successful DocumentIndexedEvent.
        
        Args:
            event: The original DocumentContentExtractedEvent
            index_name: Name of the search index
            
        Returns:
            DocumentIndexedEvent: Success event
        """
        event_data = DocumentIndexedEventData(
            documentUrl=event.data.documentUrl,
            documentId=event.data.documentId,
            searchIndexName=index_name,
            success=True
        )
        
        return DocumentIndexedEvent(
            id=str(uuid.uuid4()),
            eventType="DocumentIndexedEvent",
            submissionId=event.submissionId,
            userId=event.userId,
            timestamp=datetime.utcnow(),
            data=event_data
        )
    
    async def _create_failed_event(self, event: DocumentContentExtractedEvent, error_message: str) -> DocumentIndexedEvent:
        """
        Create a failed DocumentIndexedEvent.
        
        Args:
            event: The original DocumentContentExtractedEvent
            error_message: Error message describing the failure
            
        Returns:
            DocumentIndexedEvent: Failed event
        """
        event_data = DocumentIndexedEventData(
            documentUrl=event.data.documentUrl,
            documentId=event.data.documentId,
            searchIndexName=self.config.ai_search.index_name,
            success=False
        )
        
        return DocumentIndexedEvent(
            id=str(uuid.uuid4()),
            eventType="DocumentIndexedEvent",
            submissionId=event.submissionId,
            userId=event.userId,
            timestamp=datetime.utcnow(),
            data=event_data
        )
    
    async def close(self) -> None:
        """
        Close all client connections and clean up resources.
        """
        if self.search_client:
            await self.search_client.close()
        if self.cosmos_client:
            await self.cosmos_client.close()
            self.logger.info("Search indexer closed")
