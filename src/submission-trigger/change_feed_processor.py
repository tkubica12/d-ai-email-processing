"""
Change Feed processor for the submission-trigger service.

This module implements the change feed processor that listens to events
from the Cosmos DB events container and filters for events of interest:
- SubmissionCreated
- DocumentClassifiedEvent
- DocumentIndexedEvent
- DocumentDataExtractedEvent

The processor maintains a projection in the submissionstrigger container
to track document processing status and emits SubmissionPreparationCompletedEvent
when all documents in a submission are fully processed.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from uuid import uuid4

from azure.cosmos.aio import CosmosClient, ContainerProxy
from azure.cosmos.exceptions import CosmosResourceNotFoundError, CosmosResourceExistsError
from azure.identity.aio import DefaultAzureCredential
from pydantic import ValidationError

from config import AppConfig
from models import (
    SubmissionCreatedEvent,
    DocumentClassifiedEvent,
    DocumentIndexedEvent,
    DocumentDataExtractedEvent,
    SubmissionPreparationCompletedEvent,
    SubmissionPreparationCompletedEventData,
    SubmissionTriggerProjection
)
from continuation_token_storage import ContinuationTokenStorage


class SubmissionTriggerProcessor:
    """
    Change Feed processor for tracking document processing status.
    
    This processor listens to events from the Cosmos DB events container
    and maintains a projection of document processing status in the
    submissionstrigger container.
    """
    
    def __init__(self, config: AppConfig):
        """
        Initialize the submission trigger processor.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.cosmos_client: Optional[CosmosClient] = None
        self.events_container: Optional[ContainerProxy] = None
        self.trigger_container: Optional[ContainerProxy] = None
        self.continuation_token_storage: Optional[ContinuationTokenStorage] = None
        self.continuation_token: Optional[str] = None
        self.processor_id = "submission-trigger-processor"
        
        # Events we are interested in
        self.target_event_types = {
            "SubmissionCreated",
            "DocumentClassifiedEvent",
            "DocumentIndexedEvent",
            "DocumentDataExtractedEvent"
        }
        
    async def initialize(self) -> None:
        """
        Initialize the processor components.
        
        Raises:
            Exception: If initialization fails
        """
        try:
            # Initialize Azure credentials and Cosmos client
            credential = DefaultAzureCredential()
            self.cosmos_client = CosmosClient(
                url=self.config.cosmos_db.endpoint,
                credential=credential
            )
            
            # Get database reference
            database = self.cosmos_client.get_database_client(
                self.config.cosmos_db.database_name
            )
            
            # Get container references
            self.events_container = database.get_container_client(
                self.config.cosmos_db.events_container_name
            )
            
            self.trigger_container = database.get_container_client(
                self.config.cosmos_db.submissions_trigger_container_name
            )
            
            # Initialize continuation token storage
            self.continuation_token_storage = ContinuationTokenStorage(
                self.config.table_storage
            )
            await self.continuation_token_storage.initialize()
            
            # Load continuation token if available
            self.continuation_token = await self.continuation_token_storage.load_continuation_token(
                self.processor_id
            )
            
            self.logger.info("Submission trigger processor initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize submission trigger processor: {e}")
            raise
    
    async def start_processing(self) -> None:
        """
        Start processing the change feed.
        
        This method runs continuously, processing events from the change feed
        and maintaining the submission trigger projection.
        """
        self.logger.info("Starting change feed processing...")
        
        try:
            # Create change feed iterator
            if self.continuation_token:
                self.logger.info("Resuming from continuation token")
                feed_iterator = self.events_container.query_items_change_feed(
                    continuation=self.continuation_token
                )
            else:
                self.logger.info("Starting from beginning of change feed")
                feed_iterator = self.events_container.query_items_change_feed(
                    start_time="Beginning"
                )
            
            # Process events from change feed
            async for event_data in feed_iterator:
                try:
                    await self._process_event(event_data)
                except Exception as e:
                    self.logger.error(f"Error processing event {event_data.get('id', 'unknown')}: {e}")
                    # Continue processing other events
                    continue
                
                # Update continuation token after each successful event
                if hasattr(feed_iterator, 'continuation_token'):
                    self.continuation_token = feed_iterator.continuation_token
                    await self.continuation_token_storage.save_continuation_token(
                        self.processor_id,
                        self.continuation_token
                    )
                
                # Small delay to prevent overwhelming the system
                await asyncio.sleep(0.1)
                
        except Exception as e:
            self.logger.error(f"Error in change feed processing: {e}")
            raise
    
    async def _process_event(self, event_data: Dict[str, Any]) -> None:
        """
        Process a single event from the change feed.
        
        Args:
            event_data: Raw event data from Cosmos DB
        """
        event_type = event_data.get("eventType")
        
        # Filter for events we're interested in
        if event_type not in self.target_event_types:
            self.logger.debug(f"Ignoring event type: {event_type}")
            return
        
        self.logger.info(f"Processing event: {event_type} for submission {event_data.get('submissionId')}")
        
        try:
            # Parse event based on type
            if event_type == "SubmissionCreated":
                event = SubmissionCreatedEvent(**event_data)
                await self._handle_submission_created(event)
            elif event_type == "DocumentClassifiedEvent":
                event = DocumentClassifiedEvent(**event_data)
                await self._handle_document_classified(event)
            elif event_type == "DocumentIndexedEvent":
                event = DocumentIndexedEvent(**event_data)
                await self._handle_document_indexed(event)
            elif event_type == "DocumentDataExtractedEvent":
                event = DocumentDataExtractedEvent(**event_data)
                await self._handle_document_data_extracted(event)
            else:
                self.logger.warning(f"Unhandled event type: {event_type}")
                
        except ValidationError as e:
            self.logger.error(f"Failed to parse event {event_data.get('id')}: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Failed to handle event {event_data.get('id')}: {e}")
            raise
    
    async def _handle_submission_created(self, event: SubmissionCreatedEvent) -> None:
        """
        Handle SubmissionCreated event by creating initial projection.
        
        Args:
            event: SubmissionCreated event data
        """
        self.logger.info(f"Creating projection for submission {event.submissionId}")
        
        # Create initial projection with all documents unprocessed
        documents_status = {}
        for document_url in event.data.documentUrls:
            documents_status[document_url] = {
                "classified": False,
                "indexed": False,
                "dataExtracted": False
            }
        
        projection = SubmissionTriggerProjection(
            id=event.submissionId,
            submissionId=event.submissionId,
            userId=event.userId,
            totalDocuments=len(event.data.documentUrls),
            documents=documents_status,
            createdAt=event.timestamp,
            updatedAt=datetime.now(timezone.utc)
        )
        
        try:
            await self.trigger_container.create_item(
                body=projection.model_dump(mode='json')
            )
            self.logger.info(f"Created projection for submission {event.submissionId}")
        except CosmosResourceExistsError:
            self.logger.warning(f"Projection already exists for submission {event.submissionId}")
        except Exception as e:
            self.logger.error(f"Failed to create projection for submission {event.submissionId}: {e}")
            raise
    
    async def _handle_document_classified(self, event: DocumentClassifiedEvent) -> None:
        """
        Handle DocumentClassifiedEvent by updating projection.
        
        Args:
            event: DocumentClassifiedEvent data
        """
        if event.data.success:
            await self._update_document_status(
                event.submissionId,
                event.data.documentUrl,
                "classified",
                True
            )
    
    async def _handle_document_indexed(self, event: DocumentIndexedEvent) -> None:
        """
        Handle DocumentIndexedEvent by updating projection.
        
        Args:
            event: DocumentIndexedEvent data
        """
        if event.data.success:
            await self._update_document_status(
                event.submissionId,
                event.data.documentUrl,
                "indexed",
                True
            )
    
    async def _handle_document_data_extracted(self, event: DocumentDataExtractedEvent) -> None:
        """
        Handle DocumentDataExtractedEvent by updating projection.
        
        Args:
            event: DocumentDataExtractedEvent data
        """
        if event.data.success:
            await self._update_document_status(
                event.submissionId,
                event.data.documentUrl,
                "dataExtracted",
                True
            )
    
    async def _update_document_status(
        self,
        submission_id: str,
        document_url: str,
        status_field: str,
        value: bool
    ) -> None:
        """
        Update document processing status in projection.
        
        Args:
            submission_id: Submission identifier
            document_url: Document URL
            status_field: Status field to update (classified, indexed, dataExtracted)
            value: Status value
        """
        try:
            # Get current projection
            projection_data = await self.trigger_container.read_item(
                item=submission_id,
                partition_key=submission_id
            )
            
            # Update document status
            if document_url in projection_data["documents"]:
                projection_data["documents"][document_url][status_field] = value
                projection_data["updatedAt"] = datetime.now(timezone.utc).isoformat()
                
                # Save updated projection
                await self.trigger_container.replace_item(
                    item=submission_id,
                    body=projection_data
                )
                
                self.logger.info(f"Updated {status_field} status for document {document_url} in submission {submission_id}")
                
                # Check if all documents are fully processed
                await self._check_submission_completion(submission_id, projection_data)
            else:
                self.logger.warning(f"Document {document_url} not found in projection for submission {submission_id}")
                
        except CosmosResourceNotFoundError:
            self.logger.warning(f"Projection not found for submission {submission_id}")
        except Exception as e:
            self.logger.error(f"Failed to update document status for submission {submission_id}: {e}")
            raise
    
    async def _check_submission_completion(self, submission_id: str, projection_data: Dict[str, Any]) -> None:
        """
        Check if all documents in submission are fully processed.
        
        Args:
            submission_id: Submission identifier
            projection_data: Current projection data
        """
        documents = projection_data.get("documents", {})
        
        # Check if all documents have all three statuses set to True
        all_complete = True
        for document_url, status in documents.items():
            if not (status.get("classified", False) and
                    status.get("indexed", False) and
                    status.get("dataExtracted", False)):
                all_complete = False
                break
        
        if all_complete:
            self.logger.info(f"All documents processed for submission {submission_id}, emitting completion event")
            await self._emit_submission_preparation_completed(submission_id, projection_data)
    
    async def _emit_submission_preparation_completed(
        self,
        submission_id: str,
        projection_data: Dict[str, Any]
    ) -> None:
        """
        Emit SubmissionPreparationCompletedEvent.
        
        Args:
            submission_id: Submission identifier
            projection_data: Current projection data
        """
        try:
            # Create completion event
            completion_event = SubmissionPreparationCompletedEvent(
                id=str(uuid4()),
                submissionId=submission_id,
                userId=projection_data["userId"],
                timestamp=datetime.now(timezone.utc),
                data=SubmissionPreparationCompletedEventData(
                    documentsProcessed=projection_data["totalDocuments"]
                )
            )
            
            # Store event in events container
            await self.events_container.create_item(
                body=completion_event.model_dump(mode='json')
            )
            
            self.logger.info(f"Emitted SubmissionPreparationCompletedEvent for submission {submission_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to emit completion event for submission {submission_id}: {e}")
            raise
    
    async def close(self) -> None:
        """
        Close the processor and clean up resources.
        """
        if self.continuation_token_storage:
            await self.continuation_token_storage.close()
        
        if self.cosmos_client:
            await self.cosmos_client.close()
            
        self.logger.info("Submission trigger processor closed")
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
