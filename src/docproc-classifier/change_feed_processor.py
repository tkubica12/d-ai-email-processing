"""
Cosmos DB Change Feed processor for the docproc-classifier service.

This module handles listening to the Cosmos DB Change Feed for DocumentContentExtractedEvent
events and processes them for document classification.
"""

import asyncio
import logging
from typing import Optional

from azure.cosmos.aio import CosmosClient
from azure.identity.aio import DefaultAzureCredential
from azure.core.exceptions import HttpResponseError, ClientAuthenticationError

from config import AppConfig
from models import DocumentContentExtractedEvent, DocumentRecord
from continuation_token_storage import ContinuationTokenStorage
from document_classifier import DocumentClassifier


class ChangeFeedProcessor:
    """
    Processes Cosmos DB Change Feed for DocumentContentExtractedEvent events.
    
    This class monitors the events container Change Feed, filters for
    DocumentContentExtractedEvent types, and processes them for classification.
    """
    
    def __init__(self, config: AppConfig):
        """
        Initialize the Change Feed processor.
        
        Args:
            config: Application configuration containing Cosmos DB settings
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.cosmos_client: Optional[CosmosClient] = None
        self.continuation_token: Optional[str] = None
        self.token_storage: Optional[ContinuationTokenStorage] = None
        self.processor_id = "docproc-classifier"  # Consistent processor ID for single-instance service
        self.document_classifier: Optional[DocumentClassifier] = None
        
    async def initialize(self) -> None:
        """
        Initialize Azure clients and connections.
        
        Raises:
            Exception: If client initialization fails
        """
        try:
            credential = DefaultAzureCredential()
            self.cosmos_client = CosmosClient(
                url=self.config.cosmos_db.endpoint,
                credential=credential
            )
            
            # Initialize continuation token storage
            self.token_storage = ContinuationTokenStorage(self.config.table_storage)
            await self.token_storage.initialize()
            
            # Initialize document classifier
            self.document_classifier = DocumentClassifier(
                openai_config=self.config.openai,
                cosmos_config=self.config.cosmos_db
            )
            
            # Load persisted continuation token if available
            if self.token_storage.config.enabled:
                self.continuation_token = await self.token_storage.load_continuation_token(self.processor_id)
                if self.continuation_token:
                    self.logger.info(f"Loaded continuation token from storage: {self.continuation_token[:20]}...")
                else:
                    self.logger.info("No continuation token found in storage - starting from beginning")
            
            # Test connection
            database = self.cosmos_client.get_database_client(self.config.cosmos_db.database_name)
            container = database.get_container_client(self.config.cosmos_db.events_container_name)
            
            self.logger.info("All Azure clients initialized successfully (Cosmos DB)")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Cosmos DB client: {e}")
            raise
    
    async def start_processing(self) -> None:
        """
        Start the main processing loop for Change Feed events.
        
        This method runs indefinitely, polling the Change Feed for new events
        and processing DocumentContentExtractedEvent types.
        """
        if not self.cosmos_client:
            await self.initialize()
        
        database = self.cosmos_client.get_database_client(self.config.cosmos_db.database_name)
        container = database.get_container_client(self.config.cosmos_db.events_container_name)
        
        self.logger.info("Starting Change Feed processing loop")
        
        while True:
            try:
                await self._process_change_feed_batch(container)
                await asyncio.sleep(5)  # Poll every 5 seconds
                
            except Exception as e:
                self.logger.error(f"Error in Change Feed processing loop: {e}")
                await asyncio.sleep(10)  # Wait longer on errors
    
    async def _process_change_feed_batch(self, container) -> None:
        """
        Process a single batch of Change Feed events.
        
        Args:
            container: Cosmos DB container client for events
        """
        try:
            # Query change feed with continuation token if available
            if self.continuation_token:
                response_iterator = container.query_items_change_feed(
                    continuation=self.continuation_token
                )
            else:
                response_iterator = container.query_items_change_feed(
                    start_time="Beginning"
                )
            
            events_processed = 0
            
            # Use async for to iterate over AsyncItemPaged
            async for event_data in response_iterator:
                await self._process_event(event_data)
                events_processed += 1
            
            # Update continuation token after processing batch
            headers = container.client_connection.last_response_headers
            if 'etag' in headers:
                old_token = self.continuation_token
                self.continuation_token = headers['etag']
                self.logger.debug(f"Updated continuation token: {self.continuation_token[:20]}...")
                
                # Save continuation token to storage if enabled and token changed
                if (self.token_storage and 
                    self.token_storage.config.enabled and 
                    old_token != self.continuation_token):
                    await self.token_storage.save_continuation_token(
                        self.processor_id, 
                        self.continuation_token
                    )
            
            if events_processed > 0:
                self.logger.info(f"Processed {events_processed} events from Change Feed")
            else:
                self.logger.debug("No new events in Change Feed")
                
        except Exception as e:
            self.logger.error(f"Error processing Change Feed batch: {e}")
            raise
    
    async def _process_event(self, event_data: dict) -> None:
        """
        Process a single event from the Change Feed.
        
        Args:
            event_data: Raw event data from Cosmos DB Change Feed
        """
        self.logger.debug(f"Processing event: {event_data}")
        try:
            # Check if this is a DocumentContentExtractedEvent
            event_type = event_data.get('eventType')
            
            if event_type == 'DocumentContentExtractedEvent':
                self.logger.info(f"Found DocumentContentExtractedEvent: {event_data.get('id', 'unknown')}")
                
                # Parse and validate the event
                try:
                    event = DocumentContentExtractedEvent(**event_data)
                    await self._handle_document_content_extracted_event(event)
                except Exception as validation_error:
                    self.logger.error(f"Failed to parse DocumentContentExtractedEvent {event_data.get('id')}: {validation_error}")
            else:
                self.logger.debug(f"Skipping event type: {event_type}")
                
        except Exception as e:
            self.logger.error(f"Error processing event {event_data.get('id', 'unknown')}: {e}")
    
    async def _handle_document_content_extracted_event(self, event: DocumentContentExtractedEvent) -> None:
        """
        Handle a DocumentContentExtractedEvent by fetching the document and classifying it.
        
        Args:
            event: Validated DocumentContentExtractedEvent to process
        """
        self.logger.debug(
            f"Processing DocumentContentExtractedEvent: {event.id} "
            f"for document: {event.data.documentUrl} "
            f"submission: {event.submissionId} "
            f"content length: {event.data.contentLength} "
            f"success: {event.data.success} "
            f"timestamp: {event.timestamp}"
        )
        
        try:
            # Fetch the document record from the documents container
            document_record = await self._fetch_document_record(event.data.documentId, event.submissionId)
            
            if not document_record:
                self.logger.warning(f"Document record not found for ID: {event.data.documentId}")
                return
            
            # Classify the document and update Cosmos DB record
            self.logger.info(f"Classifying document {event.data.documentId}")
            classification_result = await self.document_classifier.classify_and_update_document(document_record)
            
            # Log the classification result
            self.logger.debug(f"Classification result for document {event.data.documentId}: {classification_result}")
            
            self.logger.info(f"Document {event.data.documentId} classified and updated successfully: type={classification_result.type}, summary_length={len(classification_result.summary)}")
            
            self.logger.info(f"DocumentContentExtractedEvent processed successfully: {event.id}")
            
        except Exception as e:
            self.logger.error(f"Failed to process DocumentContentExtractedEvent {event.id}: {e}")
            raise
    
    async def _fetch_document_record(self, document_id: str, submission_id: str) -> Optional[DocumentRecord]:
        """
        Fetch document record from the documents container.
        
        Args:
            document_id: ID of the document record
            submission_id: Submission ID (partition key)
            
        Returns:
            DocumentRecord if found, None otherwise
        """
        try:
            database = self.cosmos_client.get_database_client(self.config.cosmos_db.database_name)
            container = database.get_container_client(self.config.cosmos_db.documents_container_name)
            
            # Query for the document record
            item = await container.read_item(
                item=document_id,
                partition_key=submission_id
            )
            
            # Parse the document record
            document_record = DocumentRecord(**item)
            self.logger.debug(f"Fetched document record: {document_id} with content length: {len(document_record.content)}")
            
            return document_record
            
        except Exception as e:
            self.logger.error(f"Failed to fetch document record {document_id}: {e}")
            return None
    
    async def close(self) -> None:
        """
        Close all Azure clients and connections.
        """
        if self.document_classifier:
            await self.document_classifier.close()
            
        if self.token_storage:
            await self.token_storage.close()
            
        if self.cosmos_client:
            await self.cosmos_client.close()
            
        self.logger.info("Change Feed processor closed")
