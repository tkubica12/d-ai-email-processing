"""
Cosmos DB Change Feed processor for the docproc-search-indexer service.

This module handles listening to the Cosmos DB Change Feed for DocumentContentExtractedEvent
events and processes them for Azure AI Search indexing.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Optional

from azure.cosmos.aio import CosmosClient
from azure.identity.aio import DefaultAzureCredential
from azure.core.exceptions import HttpResponseError, ClientAuthenticationError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    after_log
)

from config import AppConfig
from models import DocumentContentExtractedEvent, DocumentIndexedEvent, DocumentIndexedEventData
from continuation_token_storage import ContinuationTokenStorage
from search_indexer import SearchIndexer


class ChangeFeedProcessor:
    """
    Processes Cosmos DB Change Feed for DocumentContentExtractedEvent events.
    
    This class monitors the events container Change Feed, filters for
    DocumentContentExtractedEvent types, and processes them for Azure AI Search indexing.
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
        self.search_indexer: Optional[SearchIndexer] = None
        self.processor_id = "docproc-search-indexer"
        
    async def initialize(self) -> None:
        """
        Initialize the Change Feed processor and required Azure clients.
        
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
            
            # Initialize continuation token storage
            self.token_storage = ContinuationTokenStorage(self.config.table_storage)
            await self.token_storage.initialize()
            
            # Initialize search indexer
            self.search_indexer = SearchIndexer(self.config)
            await self.search_indexer.initialize()
            
            # Load continuation token if available
            if self.token_storage.config.enabled:
                self.continuation_token = await self.token_storage.load_continuation_token(self.processor_id)
                if self.continuation_token:
                    self.logger.info(f"Loaded continuation token from storage: {self.continuation_token[:20]}...")
                else:
                    self.logger.info("No continuation token found in storage - starting from beginning")
            
            self.logger.info(f"Change Feed processor initialized successfully")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize Change Feed processor: {str(e)}")
            raise
    
    async def start_processing(self) -> None:
        """
        Start processing the Change Feed for DocumentContentExtractedEvent events.
        
        This method runs continuously, processing change feed batches and
        handling any errors that occur.
        """
        self.logger.info("Starting Change Feed processing...")
        
        try:
            database = self.cosmos_client.get_database_client(self.config.cosmos_db.database_name)
            container = database.get_container_client(self.config.cosmos_db.events_container_name)
            
            self.logger.info(f"Connected to database: {self.config.cosmos_db.database_name}")
            self.logger.info(f"Connected to container: {self.config.cosmos_db.events_container_name}")
            
            # Check if there are any DocumentContentExtractedEvent events in the container
            try:
                # Use a simpler query that doesn't require cross-partition query
                query = "SELECT TOP 1 c.eventType FROM c WHERE c.eventType = 'DocumentContentExtractedEvent'"
                items = container.query_items(query=query)
                found_events = []
                async for item in items:
                    found_events.append(item)
                
                if found_events:
                    self.logger.info("Found DocumentContentExtractedEvent events in container")
                else:
                    self.logger.info("No DocumentContentExtractedEvent events found in container")
                    
            except Exception as e:
                self.logger.warning(f"Could not query event count: {str(e)}")
            
            # Also check for any events at all
            try:
                query = "SELECT TOP 5 c.eventType FROM c"
                items = container.query_items(query=query)
                event_types = []
                async for item in items:
                    event_types.append(item.get('eventType'))
                
                if event_types:
                    self.logger.info(f"Found event types in container: {event_types}")
                else:
                    self.logger.info("No events found in container at all")
                    
            except Exception as e:
                self.logger.warning(f"Could not query event types: {str(e)}")
            
            # Check container properties for change feed
            try:
                container_properties = await container.read()
                self.logger.debug(f"Container properties: {container_properties}")
            except Exception as e:
                self.logger.warning(f"Could not read container properties: {str(e)}")
            
            while True:
                try:
                    await self._process_change_feed_batch(container)
                    await asyncio.sleep(5)  # Wait 5 seconds between batches
                    
                except Exception as e:
                    self.logger.error(f"Error processing change feed batch: {str(e)}")
                    await asyncio.sleep(10)  # Wait longer on error
                    
        except Exception as e:
            self.logger.error(f"Critical error in Change Feed processing: {str(e)}")
            raise
    
    async def _process_change_feed_batch(self, container) -> None:
        """
        Process a single batch of changes from the Change Feed.
        
        Args:
            container: Cosmos DB container client for events
        """
        try:
            # Query the change feed
            self.logger.debug(f"Querying change feed with continuation token: {self.continuation_token}")
            
            # If no continuation token, start from beginning
            if self.continuation_token:
                feed_iterator = container.query_items_change_feed(
                    continuation=self.continuation_token,
                    max_item_count=100
                )
            else:
                feed_iterator = container.query_items_change_feed(
                    start_time="Beginning",
                    max_item_count=100
                )
            
            events_processed = 0
            
            # Process all items from the change feed iterator
            async for event_data in feed_iterator:
                self.logger.debug(f"Found event in change feed: {event_data.get('eventType', 'unknown')}")
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
            self.logger.error(f"Error processing change feed batch: {str(e)}")
            raise
    
    async def _process_event(self, event_data: dict) -> None:
        """
        Process a single event from the Change Feed.
        
        Args:
            event_data: Raw event data from Cosmos DB
        """
        try:
            event_type = event_data.get('eventType')
            
            if event_type == 'DocumentContentExtractedEvent':
                self.logger.info(f"Processing DocumentContentExtractedEvent: {event_data.get('id')}")
                
                # Parse the event
                event = DocumentContentExtractedEvent(**event_data)
                
                # Handle the event
                await self._handle_document_content_extracted_event(event)
                
            else:
                self.logger.debug(f"Ignoring event type: {event_type}")
                
        except Exception as e:
            self.logger.error(f"Error processing event {event_data.get('id', 'unknown')}: {str(e)}")
            # Continue processing other events even if one fails
    
    async def _handle_document_content_extracted_event(self, event: DocumentContentExtractedEvent) -> None:
        """
        Handle a DocumentContentExtractedEvent by indexing the document.
        
        Args:
            event: The DocumentContentExtractedEvent to process
        """
        self.logger.info(f"Received DocumentContentExtractedEvent:")
        self.logger.info(f"  Event ID: {event.id}")
        self.logger.info(f"  Submission ID: {event.submissionId}")
        self.logger.info(f"  User ID: {event.userId}")
        self.logger.info(f"  Document ID: {event.data.documentId}")
        self.logger.info(f"  Document URL: {event.data.documentUrl}")
        self.logger.info(f"  Content Length: {event.data.contentLength}")
        self.logger.info(f"  Success: {event.data.success}")
        self.logger.info(f"  Timestamp: {event.timestamp}")
        
        # Use search indexer to process the document
        try:
            indexed_event = await self.search_indexer.index_document(event)
            self.logger.info(f"Document indexing completed: {indexed_event.data.success}")
            
            # Emit the DocumentIndexedEvent to Cosmos DB
            await self._emit_document_indexed_event(indexed_event)
            
        except Exception as e:
            self.logger.error(f"Failed to index document {event.data.documentId}: {e}")
            # Continue processing other events even if one fails
    
    async def _emit_document_indexed_event(self, event: DocumentIndexedEvent) -> None:
        """
        Emit a DocumentIndexedEvent to the Cosmos DB events container.
        
        Args:
            event: The DocumentIndexedEvent to emit
        """
        try:
            database = self.cosmos_client.get_database_client(self.config.cosmos_db.database_name)
            container = database.get_container_client(self.config.cosmos_db.events_container_name)
            
            # Convert event to JSON-serializable format
            event_json = event.model_dump(mode='json')
            
            # Emit the event
            await container.create_item(body=event_json)
            
            self.logger.info(f"Emitted DocumentIndexedEvent: {event.id}")
            
        except Exception as e:
            self.logger.error(f"Failed to emit DocumentIndexedEvent {event.id}: {str(e)}")
            raise
    
    async def close(self) -> None:
        """
        Close all client connections and clean up resources.
        """
        if self.cosmos_client:
            await self.cosmos_client.close()
            
        if self.token_storage:
            await self.token_storage.close()
            
        if self.search_indexer:
            await self.search_indexer.close()
            
        self.logger.info("Change Feed processor closed")
