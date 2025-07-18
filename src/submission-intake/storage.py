"""
Storage operations for Cosmos DB.

This module provides async operations for storing and retrieving
submission documents from Azure Cosmos DB.
"""

import logging
import uuid
from datetime import datetime
from typing import Optional, List, TypeVar
from urllib.parse import urlparse

from azure.cosmos.aio import CosmosClient, DatabaseProxy, ContainerProxy
from azure.cosmos.exceptions import CosmosResourceNotFoundError, CosmosHttpResponseError
from azure.identity.aio import DefaultAzureCredential
from azure.storage.blob.aio import BlobServiceClient
from azure.core.exceptions import ResourceNotFoundError as BlobResourceNotFoundError
from pydantic import BaseModel

from config import CosmosDBConfig, AzureStorageConfig
from models import (
    SubmissionDocument, 
    DocumentInfo, 
    DocumentRecord,
    SubmissionMessage,
    SubmissionCreatedEvent,
    SubmissionCreatedData,
    DocumentUploadedEvent,
    DocumentUploadedEventData
)

EventType = TypeVar('EventType', bound=BaseModel)

logger = logging.getLogger(__name__)


class CosmosDBStorage:
    """
    Async storage operations for Cosmos DB and Azure Storage.
    
    This class provides methods to store and retrieve submission documents
    from Azure Cosmos DB and read user messages from Azure Storage.
    """
    
    def __init__(self, cosmos_config: CosmosDBConfig, storage_config: AzureStorageConfig):
        """
        Initialize the Cosmos DB and Azure Storage clients.
        
        Args:
            cosmos_config: Cosmos DB configuration settings
            storage_config: Azure Storage configuration settings
        """
        self.cosmos_config = cosmos_config
        self.storage_config = storage_config
        self._client: Optional[CosmosClient] = None
        self._database: Optional[DatabaseProxy] = None
        self._submissions_container: Optional[ContainerProxy] = None
        self._events_container: Optional[ContainerProxy] = None
        self._documents_container: Optional[ContainerProxy] = None
        self._blob_service_client: Optional[BlobServiceClient] = None
        self._credential = DefaultAzureCredential()
        
    async def initialize(self) -> None:
        """
        Initialize the Cosmos DB and Azure Storage clients.
        
        This method should be called once before using the storage operations.
        It establishes the connection to Cosmos DB and Azure Storage and gets references to
        the required containers.
        
        Raises:
            CosmosHttpResponseError: If connection to Cosmos DB fails
        """
        try:
            # Initialize Cosmos DB client
            self._client = CosmosClient(
                url=self.cosmos_config.endpoint,
                credential=self._credential
            )
            
            self._database = self._client.get_database_client(
                database=self.cosmos_config.database_name
            )
            
            self._submissions_container = self._database.get_container_client(
                container=self.cosmos_config.submissions_container_name
            )
            
            self._events_container = self._database.get_container_client(
                container=self.cosmos_config.events_container_name
            )
            
            self._documents_container = self._database.get_container_client(
                container=self.cosmos_config.documents_container_name
            )
            
            # Initialize Azure Storage client
            storage_account_url = f"https://{self.storage_config.account_name}.blob.core.windows.net"
            self._blob_service_client = BlobServiceClient(
                account_url=storage_account_url,
                credential=self._credential
            )
            
            logger.info(
                f"Initialized Cosmos DB client for database '{self.cosmos_config.database_name}'"
            )
            logger.info(
                f"Initialized Azure Storage client for account '{self.storage_config.account_name}'"
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize Cosmos DB client: {e}")
            raise
    
    async def store_submission(self, submission_message: SubmissionMessage) -> SubmissionDocument:
        """
        Store a new submission document in Cosmos DB.
        
        This method creates a new submission document based on the Service Bus
        message and stores it in the submissions container. It reads the user message
        from the body.txt file in the blob storage container.
        
        Args:
            submission_message: The submission message from Service Bus
            
        Returns:
            SubmissionDocument: The stored submission document
            
        Raises:
            CosmosHttpResponseError: If the storage operation fails
        """
        if not self._submissions_container:
            raise RuntimeError("Storage not initialized. Call initialize() first.")
        
        # Read user message from blob storage
        user_message = await self._read_user_message_from_blob(submission_message.submissionId)
        
        # Create document info list from URLs
        documents = [
            DocumentInfo(
                documentUrl=url,
                type=None
            )
            for url in submission_message.documentUrls
        ]
        
        # Create submission document following Design.md schema
        submission_doc = SubmissionDocument(
            id=submission_message.submissionId,
            submissionId=submission_message.submissionId,
            userId=submission_message.userId,
            submittedAt=submission_message.submittedAt,
            userMessage=user_message,
            documents=documents,
            evaluationResults=None
        )
        
        try:
            # Store submission in Cosmos DB
            submission_json = submission_doc.model_dump(mode='json')
            logger.debug(f"COSMOS_DB_DOCUMENT: {submission_json}")
            await self._submissions_container.create_item(
                body=submission_json
            )
            
            logger.info(
                f"Stored submission document: {submission_doc.submissionId} "
                f"for user: {submission_doc.userId} "
                f"with {len(submission_doc.documents)} documents"
            )
            
            return submission_doc
            
        except CosmosHttpResponseError as e:
            logger.error(
                f"Failed to store submission {submission_message.submissionId}: {e}"
            )
            raise
    
    async def _create_and_store_event(self, event: EventType, event_description: str) -> EventType:
        """
        Generic method to create and store an event in the events container.
        
        This method provides common functionality for storing any type of event
        to reduce code duplication across different event creation methods.
        
        Args:
            event: The event object to store
            event_description: Description for logging purposes
            
        Returns:
            EventType: The stored event object
            
        Raises:
            CosmosHttpResponseError: If the storage operation fails
        """
        if not self._events_container:
            raise RuntimeError("Storage not initialized. Call initialize() first.")
        
        try:
            # Store event in Cosmos DB events container
            event_json = event.model_dump(mode='json')
            logger.debug(f"COSMOS_DB_DOCUMENT: {event_json}")
            await self._events_container.create_item(
                body=event_json
            )
            
            logger.info(f"Created {event_description}: {event.id} for submission: {event.submissionId}")
            
            return event
            
        except CosmosHttpResponseError as e:
            logger.error(f"Failed to store {event_description} for submission {event.submissionId}: {e}")
            raise

    async def create_submission_created_event(self, submission_message: SubmissionMessage) -> SubmissionCreatedEvent:
        """
        Create and store a SubmissionCreatedEvent in the events container.
        
        This method creates a SubmissionCreatedEvent based on the Service Bus
        message and stores it in the events container for event sourcing.
        
        Args:
            submission_message: The submission message from Service Bus
            
        Returns:
            SubmissionCreatedEvent: The created and stored event
            
        Raises:
            CosmosHttpResponseError: If the storage operation fails
        """
        # Create event data
        event_data = SubmissionCreatedData(
            documentUrls=submission_message.documentUrls,
            containerName=submission_message.submissionId
        )
        
        # Create the event
        event = SubmissionCreatedEvent(
            id=str(uuid.uuid4()),
            eventType="SubmissionCreated",
            submissionId=submission_message.submissionId,
            userId=submission_message.userId,
            timestamp=datetime.utcnow(),
            data=event_data
        )
        
        return await self._create_and_store_event(
            event, 
            f"SubmissionCreatedEvent with {len(event.data.documentUrls)} documents"
        )

    async def create_document_uploaded_events(self, submission_message: SubmissionMessage) -> List[DocumentUploadedEvent]:
        """
        Create and store DocumentUploadedEvent for each document in the submission.
        
        This method creates a separate DocumentUploadedEvent for each document URL
        in the submission message and stores them in the events container.
        
        Args:
            submission_message: The submission message from Service Bus
            
        Returns:
            List[DocumentUploadedEvent]: List of created and stored events
            
        Raises:
            CosmosHttpResponseError: If any storage operation fails
        """
        # First, create document records to get the document IDs
        document_records = await self.create_document_records(submission_message)
        
        # Create a mapping from document URL to document ID
        url_to_id = {doc.documentUrl: doc.id for doc in document_records}
        
        events = []
        
        for document_url in submission_message.documentUrls:
            # Get the document ID for this URL
            document_id = url_to_id.get(document_url)
            if not document_id:
                raise RuntimeError(f"Document ID not found for URL: {document_url}")
            
            # Create event data for this document
            event_data = DocumentUploadedEventData(
                documentUrl=document_url,
                documentId=document_id
            )
            
            # Create the event
            event = DocumentUploadedEvent(
                id=str(uuid.uuid4()),
                eventType="DocumentUploadedEvent",
                submissionId=submission_message.submissionId,
                userId=submission_message.userId,
                timestamp=datetime.utcnow(),
                data=event_data
            )
            
            # Store the event using the generic method
            stored_event = await self._create_and_store_event(
                event, 
                f"DocumentUploadedEvent for document: {document_url}"
            )
            
            events.append(stored_event)
        
        logger.info(
            f"Created {len(events)} DocumentUploadedEvent(s) for submission: {submission_message.submissionId}"
        )
        
        return events
    
    async def create_document_records(self, submission_message: SubmissionMessage) -> List[DocumentRecord]:
        """
        Create document records for each document in the submission.
        
        This method creates initial document records in the documents container
        with only the basic information available at intake time. Processing
        fields (content, type, summary, extractedData) are set to null.
        
        Args:
            submission_message: The submission message containing document URLs
            
        Returns:
            List[DocumentRecord]: List of created document records
            
        Raises:
            CosmosHttpResponseError: If any storage operation fails
        """
        if not self._documents_container:
            raise RuntimeError("Storage not initialized. Call initialize() first.")
        
        document_records = []
        current_time = datetime.now()
        
        for document_url in submission_message.documentUrls:
            # Create document record with minimal initial data
            # Generate a GUID for the document ID
            document_id = str(uuid.uuid4())
            
            doc_record = DocumentRecord(
                id=document_id,
                documentUrl=document_url,
                submissionId=submission_message.submissionId,
                userId=submission_message.userId,
                content=None,
                type=None,
                summary=None,
                extractedData=None,
                firstProcessedAt=current_time,
                lastProcessedAt=current_time
            )
            
            try:
                # Store document record in Cosmos DB
                doc_record_json = doc_record.model_dump(mode='json')
                logger.debug(f"COSMOS_DB_DOCUMENT: {doc_record_json}")
                await self._documents_container.create_item(
                    body=doc_record_json
                )
                
                document_records.append(doc_record)
                
                logger.info(
                    f"Created document record for URL: {document_url} "
                    f"in submission: {submission_message.submissionId}"
                )
                
            except CosmosHttpResponseError as e:
                logger.error(
                    f"Failed to create document record for URL {document_url} "
                    f"in submission {submission_message.submissionId}: {e}"
                )
                raise
        
        logger.info(
            f"Created {len(document_records)} document records "
            f"for submission: {submission_message.submissionId}"
        )
        
        return document_records
    
    async def get_submission(self, submission_id: str) -> Optional[SubmissionDocument]:
        """
        Retrieve a submission document from Cosmos DB.
        
        Args:
            submission_id: The unique identifier of the submission
            
        Returns:
            SubmissionDocument: The retrieved submission document, or None if not found
            
        Raises:
            CosmosHttpResponseError: If the retrieval operation fails
        """
        if not self._submissions_container:
            raise RuntimeError("Storage not initialized. Call initialize() first.")
        
        try:
            response = await self._submissions_container.read_item(
                item=submission_id,
                partition_key=submission_id
            )
            
            return SubmissionDocument(**response)
            
        except CosmosResourceNotFoundError:
            logger.warning(f"Submission not found: {submission_id}")
            return None
        except CosmosHttpResponseError as e:
            logger.error(f"Failed to retrieve submission {submission_id}: {e}")
            raise
    
    async def get_document_record(self, document_url: str) -> Optional[DocumentRecord]:
        """
        Retrieve a document record from Cosmos DB by document URL.
        
        Args:
            document_url: The Azure Blob Storage URL of the document
            
        Returns:
            DocumentRecord: The retrieved document record, or None if not found
            
        Raises:
            CosmosHttpResponseError: If the retrieval operation fails
        """
        if not self._documents_container:
            raise RuntimeError("Storage not initialized. Call initialize() first.")
        
        try:
            # Query for document by documentUrl (partition key)
            query = "SELECT * FROM c WHERE c.documentUrl = @documentUrl"
            parameters = [{"name": "@documentUrl", "value": document_url}]
            
            items = self._documents_container.query_items(
                query=query,
                parameters=parameters,
                partition_key=document_url
            )
            
            # Get the first (and should be only) result
            async for item in items:
                return DocumentRecord(**item)
            
            logger.warning(f"Document record not found: {document_url}")
            return None
            
        except CosmosHttpResponseError as e:
            logger.error(f"Failed to retrieve document record {document_url}: {e}")
            raise
    
    async def close(self) -> None:
        """
        Close the Cosmos DB and Azure Storage client connections.
        
        This method should be called when shutting down the application
        to properly close the connections.
        """
        if self._client:
            await self._client.close()
            logger.info("Closed Cosmos DB client connection")
        
        if self._blob_service_client:
            await self._blob_service_client.close()
            logger.info("Closed Azure Storage client connection")
    
    async def _read_user_message_from_blob(self, submission_id: str) -> str:
        """
        Read the user message from the body.txt file in the submission's blob container.
        
        Args:
            submission_id: The submission ID which is also the container name
            
        Returns:
            str: The user message content from body.txt
            
        Raises:
            Exception: If the body.txt file cannot be read
        """
        if not self._blob_service_client:
            raise RuntimeError("Storage not initialized. Call initialize() first.")
        
        try:
            # Get the blob client for body.txt in the submission container
            blob_client = self._blob_service_client.get_blob_client(
                container=submission_id,
                blob="body.txt"
            )
            
            # Download the blob content
            blob_data = await blob_client.download_blob()
            user_message = await blob_data.readall()
            
            # Decode the content to string
            user_message_text = user_message.decode('utf-8')
            
            logger.info(f"Successfully read user message from blob: {submission_id}/body.txt")
            return user_message_text
            
        except BlobResourceNotFoundError:
            logger.warning(f"body.txt not found in container {submission_id}, using empty message")
            return ""
        except Exception as e:
            logger.error(f"Failed to read user message from blob {submission_id}/body.txt: {e}")
            raise
