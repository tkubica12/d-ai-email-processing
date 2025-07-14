"""
Cosmos DB Change Feed processor for the docproc-parser-foundry service.

This module handles listening to the Cosmos DB Change Feed for DocumentUploadedEvent
events and processes them for document intelligence analysis.
"""

import asyncio
import base64
import logging
import uuid
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

from azure.cosmos.aio import CosmosClient
from azure.identity.aio import DefaultAzureCredential
from azure.storage.blob.aio import BlobServiceClient
from azure.ai.documentintelligence.aio import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest, DocumentContentFormat
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
from models import DocumentUploadedEvent, DocumentRecord, DocumentContentExtractedEvent, DocumentContentExtractedEventData
from continuation_token_storage import ContinuationTokenStorage


class ChangeFeedProcessor:
    """
    Processes Cosmos DB Change Feed for DocumentUploadedEvent events.
    
    This class monitors the events container Change Feed, filters for
    DocumentUploadedEvent types, and processes them for document analysis.
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
        self.blob_service_client: Optional[BlobServiceClient] = None
        self.document_intelligence_client: Optional[DocumentIntelligenceClient] = None
        self.continuation_token: Optional[str] = None
        self.token_storage: Optional[ContinuationTokenStorage] = None
        self.processor_id = "docproc-parser-foundry"  # Consistent processor ID for single-instance service
        
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
            
            # Initialize Azure Storage Blob client
            storage_account_url = f"https://{self.config.table_storage.account_name}.blob.core.windows.net"
            self.blob_service_client = BlobServiceClient(
                account_url=storage_account_url,
                credential=credential
            )
            
            # Initialize Azure Document Intelligence client
            self.document_intelligence_client = DocumentIntelligenceClient(
                endpoint=self.config.document_intelligence.endpoint,
                credential=credential
            )
            
            # Initialize continuation token storage
            self.token_storage = ContinuationTokenStorage(self.config.table_storage)
            await self.token_storage.initialize()
            
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
            
            self.logger.info("All Azure clients initialized successfully (Cosmos DB, Storage Blob, Document Intelligence)")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Cosmos DB client: {e}")
            raise
    
    async def start_processing(self) -> None:
        """
        Start the main processing loop for Change Feed events.
        
        This method runs indefinitely, polling the Change Feed for new events
        and processing DocumentUploadedEvent types.
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
            # Check if this is a DocumentUploadedEvent
            event_type = event_data.get('eventType')
            
            if event_type == 'DocumentUploadedEvent':
                self.logger.info(f"Found DocumentUploadedEvent: {event_data.get('id', 'unknown')}")
                
                # Parse and validate the event
                try:
                    event = DocumentUploadedEvent(**event_data)
                    await self._handle_document_uploaded_event(event)
                except Exception as validation_error:
                    self.logger.error(f"Failed to parse DocumentUploadedEvent {event_data.get('id')}: {validation_error}")
            else:
                self.logger.debug(f"Skipping event type: {event_type}")
                
        except Exception as e:
            self.logger.error(f"Error processing event {event_data.get('id', 'unknown')}: {e}")
    
    async def _handle_document_uploaded_event(self, event: DocumentUploadedEvent) -> None:
        """
        Handle a DocumentUploadedEvent by downloading the document, processing it with Document Intelligence,
        storing the extracted content in Cosmos DB, and emitting a DocumentContentExtractedEvent.
        
        Args:
            event: Validated DocumentUploadedEvent to process
        """
        self.logger.info(
            f"Processing document: {event.data.documentUrl} "
            f"for submission: {event.submissionId} "
            f"uploaded at: {event.timestamp}"
        )
        
        try:
            # Download document from blob storage
            document_content = await self._download_document_from_storage(event.data.documentUrl)
            
            # Check if document format is supported by Document Intelligence
            if self._is_supported_document_format(event.data.documentUrl):
                # Process document with Document Intelligence
                markdown_content = await self._process_document_with_intelligence(document_content)
                self.logger.debug(f"Extracted markdown content from document {event.data.documentUrl}:\n{markdown_content}")
            else:
                # For unsupported formats (like .txt), read content directly
                markdown_content = await self._process_text_document(document_content, event.data.documentUrl)
                self.logger.debug(f"Read text content from document {event.data.documentUrl}:\n{markdown_content}")
            
            # Store the extracted content in Cosmos DB documents container
            await self._store_document_content(event, markdown_content)
            
            # Emit DocumentContentExtractedEvent
            await self._emit_document_content_extracted_event(event, markdown_content, success=True)
            
            self.logger.info(f"Successfully processed document {event.data.documentUrl}")
            
        except Exception as e:
            self.logger.error(f"Failed to process document {event.data.documentUrl}: {e}")
            # Emit failure event
            try:
                await self._emit_document_content_extracted_event(event, "", success=False)
            except Exception as emit_error:
                self.logger.error(f"Failed to emit failure event for document {event.data.documentUrl}: {emit_error}")
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((ClientAuthenticationError, TimeoutError, ConnectionError)),
        before_sleep=before_sleep_log(logging.getLogger(__name__), logging.WARNING),
        after=after_log(logging.getLogger(__name__), logging.INFO)
    )
    async def _download_document_from_storage(self, document_url: str) -> bytes:
        """
        Download a document from Azure Blob Storage.
        
        Args:
            document_url: Full URL to the document in blob storage
            
        Returns:
            Document content as bytes
            
        Raises:
            Exception: If document download fails
        """
        try:
            # Parse the blob URL to extract container and blob name
            parsed_url = urlparse(document_url)
            path_parts = parsed_url.path.lstrip('/').split('/', 1)
            
            if len(path_parts) < 2:
                raise ValueError(f"Invalid blob URL format: {document_url}")
            
            container_name = path_parts[0]
            blob_name = path_parts[1]
            
            self.logger.debug(f"Downloading blob: {blob_name} from container: {container_name}")
            
            # Get blob client and download content
            blob_client = self.blob_service_client.get_blob_client(
                container=container_name,
                blob=blob_name
            )
            
            download_stream = await blob_client.download_blob()
            document_content = await download_stream.readall()
            
            self.logger.debug(f"Successfully downloaded document, size: {len(document_content)} bytes")
            return document_content
            
        except ClientAuthenticationError as e:
            self.logger.warning(f"Authentication error while downloading blob. Will retry after backoff. Error: {e}")
            raise
        except Exception as e:
            if "Timed out waiting for Azure CLI" in str(e):
                self.logger.warning(f"Azure CLI timeout during authentication. Will retry after backoff. Error: {e}")
                raise ClientAuthenticationError(f"Azure CLI authentication timeout: {e}") from e
            else:
                self.logger.error(f"Failed to download document from {document_url}: {e}")
                raise
    
    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=8, max=60),
        retry=retry_if_exception_type((HttpResponseError, ClientAuthenticationError, TimeoutError, ConnectionError)),
        before_sleep=before_sleep_log(logging.getLogger(__name__), logging.WARNING),
        after=after_log(logging.getLogger(__name__), logging.INFO)
    )
    async def _process_document_with_intelligence(self, document_content: bytes) -> str:
        """
        Process document content with Azure Document Intelligence to extract markdown.
        
        Args:
            document_content: Document content as bytes
            
        Returns:
            Extracted content in markdown format
            
        Raises:
            Exception: If document processing fails
        """
        try:
            self.logger.debug("Starting document analysis with Document Intelligence")
            
            # Create analyze request with document bytes
            analyze_request = AnalyzeDocumentRequest()
            analyze_request.bytes_source = document_content
            
            # Start analysis with prebuilt-layout model and markdown output format
            poller = await self.document_intelligence_client.begin_analyze_document(
                model_id="prebuilt-layout",
                body=analyze_request,
                output_content_format=DocumentContentFormat.MARKDOWN
            )
            
            # Wait for completion
            result = await poller.result()
            
            # Extract markdown content from result
            markdown_content = result.content or ""
            
            self.logger.debug(f"Document analysis completed, extracted {len(markdown_content)} characters")
            return markdown_content
            
        except HttpResponseError as e:
            if e.status_code == 429:
                self.logger.warning(f"Rate limit exceeded (429). Will retry after backoff. Error: {e}")
                raise  # Let tenacity handle the retry
            elif e.status_code in [401, 403]:
                self.logger.warning(f"Authentication error ({e.status_code}). Will retry after backoff. Error: {e}")
                raise ClientAuthenticationError(f"Authentication failed: {e}") from e
            else:
                self.logger.error(f"HTTP error {e.status_code} from Document Intelligence: {e}")
                raise
        except Exception as e:
            self.logger.error(f"Failed to process document with Document Intelligence: {e}")
            raise
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((ClientAuthenticationError, HttpResponseError, TimeoutError, ConnectionError)),
        before_sleep=before_sleep_log(logging.getLogger(__name__), logging.WARNING),
        after=after_log(logging.getLogger(__name__), logging.INFO)
    )
    async def _store_document_content(self, event: DocumentUploadedEvent, markdown_content: str) -> None:
        """
        Update the existing document record with extracted content in Cosmos DB documents container.
        
        Args:
            event: Original DocumentUploadedEvent
            markdown_content: Extracted markdown content from Document Intelligence
            
        Raises:
            Exception: If updating document content fails
        """
        try:
            # Get documents container
            database = self.cosmos_client.get_database_client(self.config.cosmos_db.database_name)
            documents_container = database.get_container_client(self.config.cosmos_db.documents_container_name)
            
            # Read the existing document record
            try:
                existing_doc = await documents_container.read_item(
                    item=event.data.documentId,
                    partition_key=event.submissionId
                )
            except Exception as e:
                self.logger.error(f"Failed to read existing document {event.data.documentId}: {e}")
                raise
            
            # Update the document with extracted content
            existing_doc['content'] = markdown_content
            existing_doc['lastProcessedAt'] = datetime.utcnow().isoformat()
            
            # Update the document in Cosmos DB
            await documents_container.replace_item(
                item=event.data.documentId,
                body=existing_doc
            )
            
            self.logger.info(
                f"Successfully updated document content for {event.data.documentUrl} "
                f"with ID {event.data.documentId} ({len(markdown_content)} characters)"
            )
            
        except HttpResponseError as e:
            if e.status_code in [401, 403]:
                self.logger.warning(f"Authentication error while updating document content. Will retry after backoff. Error: {e}")
                raise ClientAuthenticationError(f"Authentication failed: {e}") from e
            else:
                self.logger.error(f"HTTP error {e.status_code} while updating document content: {e}")
                raise
        except Exception as e:
            self.logger.error(f"Failed to update document content for {event.data.documentUrl}: {e}")
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((ClientAuthenticationError, HttpResponseError, TimeoutError, ConnectionError)),
        before_sleep=before_sleep_log(logging.getLogger(__name__), logging.WARNING),
        after=after_log(logging.getLogger(__name__), logging.INFO)
    )
    async def _emit_document_content_extracted_event(self, event: DocumentUploadedEvent, markdown_content: str, success: bool) -> None:
        """
        Emit a DocumentContentExtractedEvent to the events container.
        
        Args:
            event: Original DocumentUploadedEvent
            markdown_content: Extracted markdown content (empty string if failed)
            success: Whether content extraction was successful
            
        Raises:
            Exception: If emitting event fails
        """
        try:
            # Create event data
            event_data = DocumentContentExtractedEventData(
                documentUrl=event.data.documentUrl,
                documentId=event.data.documentId,
                contentLength=len(markdown_content) if success else 0,
                success=success
            )
            
            # Create event
            content_extracted_event = DocumentContentExtractedEvent(
                id=str(uuid.uuid4()),
                eventType="DocumentContentExtractedEvent",
                submissionId=event.submissionId,
                userId=event.userId,
                timestamp=datetime.utcnow(),
                data=event_data
            )
            
            # Get events container
            database = self.cosmos_client.get_database_client(self.config.cosmos_db.database_name)
            events_container = database.get_container_client(self.config.cosmos_db.events_container_name)
            
            # Emit event (using submissionId as partition key)
            await events_container.create_item(
                body=content_extracted_event.model_dump(mode='json')
            )
            
            self.logger.info(
                f"Successfully emitted DocumentContentExtractedEvent for {event.data.documentUrl} "
                f"(success={success}, contentLength={len(markdown_content) if success else 0})"
            )
            
        except HttpResponseError as e:
            if e.status_code in [401, 403]:
                self.logger.warning(f"Authentication error while emitting event. Will retry after backoff. Error: {e}")
                raise ClientAuthenticationError(f"Authentication failed: {e}") from e
            else:
                self.logger.error(f"HTTP error {e.status_code} while emitting event: {e}")
                raise
        except Exception as e:
            self.logger.error(f"Failed to emit DocumentContentExtractedEvent for {event.data.documentUrl}: {e}")
            raise
        
    async def close(self) -> None:
        """
        Clean up resources and close connections.
        """
        if self.cosmos_client:
            await self.cosmos_client.close()
            self.logger.info("Cosmos DB client closed")
            
        if self.blob_service_client:
            await self.blob_service_client.close()
            self.logger.info("Blob service client closed")
            
        if self.document_intelligence_client:
            await self.document_intelligence_client.close()
            self.logger.info("Document Intelligence client closed")
            
        if self.token_storage:
            await self.token_storage.close()
            self.logger.info("Table storage client closed")
    
    def _is_supported_document_format(self, document_url: str) -> bool:
        """
        Check if a document format is supported by Azure Document Intelligence.
        
        Args:
            document_url: URL of the document
            
        Returns:
            True if the document format is supported, False otherwise
        """
        # Extract file extension from URL
        parsed_url = urlparse(document_url)
        file_path = parsed_url.path.lower()
        
        # Document Intelligence supported formats
        supported_extensions = {
            '.pdf',      # PDF documents
            '.jpg',      # JPEG images
            '.jpeg',     # JPEG images
            '.png',      # PNG images
            '.bmp',      # BMP images
            '.tiff',     # TIFF images
            '.tif',      # TIFF images
            '.heif',     # HEIF images
            '.docx',     # Word documents
            '.xlsx',     # Excel spreadsheets
            '.pptx',     # PowerPoint presentations
            '.html',     # HTML documents
        }
        
        # Check if file extension is supported
        for ext in supported_extensions:
            if file_path.endswith(ext):
                return True
        
        self.logger.debug(f"Unsupported document format for Document Intelligence: {file_path}")
        return False
    
    async def _process_text_document(self, document_content: bytes, document_url: str) -> str:
        """
        Process text document content by reading it directly without Document Intelligence.
        
        Args:
            document_content: Document content as bytes
            document_url: URL of the document for logging
            
        Returns:
            Text content of the document
            
        Raises:
            Exception: If text decoding fails
        """
        try:
            # Try to decode as UTF-8 first
            try:
                text_content = document_content.decode('utf-8')
            except UnicodeDecodeError:
                # Fall back to other common encodings
                try:
                    text_content = document_content.decode('utf-8-sig')  # UTF-8 with BOM
                except UnicodeDecodeError:
                    try:
                        text_content = document_content.decode('iso-8859-1')  # Latin-1
                    except UnicodeDecodeError:
                        text_content = document_content.decode('cp1252')  # Windows-1252
            
            self.logger.debug(f"Successfully decoded text document, length: {len(text_content)} characters")
            return text_content
            
        except Exception as e:
            self.logger.error(f"Failed to decode text document {document_url}: {e}")
            raise
