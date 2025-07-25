"""
Document parser action for Azure Durable Functions.

This module provides document parsing functionality using Azure Document Intelligence
for the durable functions orchestration workflow.
"""

import logging
import uuid
from datetime import datetime
from urllib.parse import urlparse
from typing import Dict, Any, Optional

from azure.ai.documentintelligence.aio import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest, DocumentContentFormat
from azure.storage.blob.aio import BlobServiceClient
from azure.identity.aio import DefaultAzureCredential
from azure.cosmos.aio import CosmosClient
from azure.core.exceptions import HttpResponseError, ClientAuthenticationError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    retry_if_exception,
    before_sleep_log,
    after_log
)

from config import AppConfig
from models import DocumentRecord


class DocumentParser:
    """
    Document parser using Azure Document Intelligence.
    
    This class handles document parsing and content extraction using Azure Document Intelligence,
    and stores the results in Cosmos DB.
    """
    
    def __init__(self):
        """Initialize the document parser with Azure clients."""
        self.logger = logging.getLogger(__name__)
        self.config = AppConfig.from_env()
        self.credential = DefaultAzureCredential()
        
        # Initialize clients (will be created async when needed)
        self.document_intelligence_client: Optional[DocumentIntelligenceClient] = None
        self.blob_service_client: Optional[BlobServiceClient] = None
        self.cosmos_client: Optional[CosmosClient] = None
    
    async def _ensure_clients_initialized(self):
        """Ensure all Azure clients are initialized."""
        if not self.document_intelligence_client:
            self.document_intelligence_client = DocumentIntelligenceClient(
                endpoint=self.config.document_intelligence.endpoint,
                credential=self.credential
            )
        
        if not self.blob_service_client:
            blob_endpoint = f"https://{self.config.storage.account_name}.blob.core.windows.net"
            self.blob_service_client = BlobServiceClient(
                account_url=blob_endpoint,
                credential=self.credential
            )
        
        if not self.cosmos_client:
            self.cosmos_client = CosmosClient(
                url=self.config.cosmos_db.endpoint,
                credential=self.credential
            )
    
    async def parse_document_async(self, submission_id: str, document_url: str, user_id: str) -> Dict[str, Any]:
        """
        Parse a document using Azure Document Intelligence.
        
        Args:
            submission_id: ID of the submission this document belongs to
            document_url: Azure Blob Storage URL of the document
            user_id: ID of the user who uploaded the document
            
        Returns:
            Dict containing the parsing results
        """
        document_id = str(uuid.uuid4())
        file_name = self._extract_filename_from_url(document_url)
        
        try:
            self.logger.info(f'Starting document parsing for {file_name} (ID: {document_id})')
            
            # Ensure clients are initialized
            await self._ensure_clients_initialized()
            self.logger.info(f'Azure clients initialized successfully for {file_name}')
            
            # Download document content
            document_content = await self._download_document(document_url)
            self.logger.info(f'Downloaded {len(document_content)} bytes for {file_name}')

            # Analyze with Document Intelligence (will throw exception if it fails)
            parsed_markdown_content = await self._analyze_document_with_intelligence(document_content, document_url)
            
            # Log content type and sample for debugging
            self.logger.info(f'Document {file_name} - Parsed content type: {type(parsed_markdown_content)}, Content length: {len(parsed_markdown_content)}')
            if len(parsed_markdown_content) > 100:
                self.logger.info(f'Document {file_name} - Markdown preview: {parsed_markdown_content[:100]}...')
            
            # Verify we're not storing raw bytes
            if isinstance(parsed_markdown_content, bytes):
                self.logger.error('ERROR: parsed_markdown_content is bytes, not string! This should not happen.')
                raise TypeError('Document Intelligence returned bytes instead of string')
            
            # Determine the metadata based on file type
            is_body_txt = file_name.lower() == 'body.txt'
            
            # Create document record
            document_record = DocumentRecord(
                id=document_id,
                submissionId=submission_id,
                documentUrl=document_url,
                fileName=file_name,
                contentType=self._get_content_type(file_name),
                content=parsed_markdown_content,
                metadata={
                    "contentLength": len(parsed_markdown_content),
                    "contentType": "text/plain" if is_body_txt else "text/markdown",
                    "parsedBy": "Direct text extraction" if is_body_txt else "Azure Document Intelligence",
                    "outputFormat": "plain text" if is_body_txt else "markdown",
                    "originalContentType": self._get_content_type(file_name)
                },
                processingStatus="parsed",
                createdAt=datetime.utcnow(),
                updatedAt=datetime.utcnow()
            )
            
            self.logger.info(f'Created document record for {file_name}, attempting to store in Cosmos DB')
            
            # Store in Cosmos DB
            await self._store_document_record(document_record)
            
            self.logger.info(f'Successfully parsed and stored document {file_name}')
            
            return {
                "documentId": document_id,
                "fileName": file_name,
                "contentLength": len(parsed_markdown_content),
                "status": "success"
            }
            
        except Exception as e:
            self.logger.error(f'CRITICAL ERROR: Failed to parse document {file_name}: {str(e)}', exc_info=True)
            # Re-raise to let the activity function handle it
            raise
        finally:
            try:
                await self._close_clients()
                self.logger.info(f'Closed Azure clients for {file_name}')
            except Exception as e:
                self.logger.warning(f'Failed to close Azure clients for {file_name}: {e}')
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((ClientAuthenticationError, TimeoutError, ConnectionError)),
        before_sleep=before_sleep_log(logging.getLogger(__name__), logging.WARNING),
        after=after_log(logging.getLogger(__name__), logging.INFO)
    )
    async def _download_document(self, document_url: str) -> bytes:
        """
        Download document content from Azure Blob Storage.
        
        Args:
            document_url: Azure Blob Storage URL of the document
            
        Returns:
            Document content as bytes
        """
        parsed_url = urlparse(document_url)
        path_parts = parsed_url.path.strip('/').split('/')
        container_name = path_parts[0]
        blob_name = '/'.join(path_parts[1:])
        
        blob_client = self.blob_service_client.get_blob_client(
            container=container_name,
            blob=blob_name
        )
        
        download_stream = await blob_client.download_blob()
        return await download_stream.readall()
    
    @staticmethod
    def _should_retry_document_intelligence(exception):
        """
        Determine if we should retry Document Intelligence requests based on the exception.
        
        Args:
            exception: The exception that occurred
            
        Returns:
            bool: True if we should retry, False otherwise
        """
        if isinstance(exception, HttpResponseError):
            # Retry on rate limiting, service unavailable, or server errors
            return exception.status_code in [429, 503, 500, 502, 504]
        
        if isinstance(exception, (ClientAuthenticationError, TimeoutError, ConnectionError)):
            return True
            
        return False

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=8, max=60),
        retry=retry_if_exception(lambda e: DocumentParser._should_retry_document_intelligence(e)),
        before_sleep=before_sleep_log(logging.getLogger(__name__), logging.WARNING),
        after=after_log(logging.getLogger(__name__), logging.INFO)
    )
    async def _analyze_document_with_intelligence(self, document_content: bytes, document_url: str) -> str:
        """
        Analyze document using Azure Document Intelligence.
        
        Args:
            document_content: Document content as bytes
            document_url: Original document URL for context
            
        Returns:
            Extracted Markdown content from Document Intelligence or raw text for body.txt
        """
        file_name = self._extract_filename_from_url(document_url)
        
        # Special handling for body.txt files - store as-is without processing
        if file_name.lower() == 'body.txt':
            self.logger.info(f'Processing {file_name} as plain text (body.txt exception)')
            try:
                # Decode as UTF-8 text and return as-is
                return document_content.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    # Fallback to latin-1
                    return document_content.decode('latin-1')
                except UnicodeDecodeError:
                    # Last resort - ignore errors
                    return document_content.decode('utf-8', errors='ignore')
        
        # Check if the document format is supported by Document Intelligence
        if not self._is_supported_document_format(document_url):
            raise ValueError(f'Document format not supported by Document Intelligence: {file_name}')
        
        self.logger.info(f'Starting Document Intelligence analysis for {file_name}')
        
        try:
            # Create analyze request
            analyze_request = AnalyzeDocumentRequest(bytes_source=document_content)
            
            # Start analysis - use 'body' parameter, not 'analyze_request'
            poller = await self.document_intelligence_client.begin_analyze_document(
                model_id="prebuilt-layout",
                body=analyze_request,
                output_content_format=DocumentContentFormat.MARKDOWN
            )
            
            # Wait for completion
            result = await poller.result()
            
            # Extract content
            if result.content:
                self.logger.info(f'Document Intelligence SUCCESS: extracted {len(result.content)} characters of Markdown from {file_name}')
                # Debug: Log first 200 chars to verify it's Markdown, not binary
                content_preview = result.content[:200] if len(result.content) > 200 else result.content
                self.logger.info(f'Document Intelligence Markdown preview for {file_name}: {content_preview}')
                return result.content
            else:
                self.logger.error(f'Document Intelligence returned empty content for {file_name}')
                raise ValueError(f'No content extracted from document {file_name}')
                
        except Exception as e:
            self.logger.error(f'Document Intelligence analysis FAILED for {file_name}: {str(e)}')
            # DO NOT fallback to text processing - raise the error instead
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((ClientAuthenticationError, HttpResponseError, TimeoutError, ConnectionError)),
        before_sleep=before_sleep_log(logging.getLogger(__name__), logging.WARNING),
        after=after_log(logging.getLogger(__name__), logging.INFO)
    )
    async def _store_document_record(self, document_record: DocumentRecord) -> None:
        """
        Store document record in Cosmos DB.
        
        Args:
            document_record: Document record to store
        """
        try:
            self.logger.info(f'Attempting to store document record {document_record.id} to Cosmos DB')
            
            database = self.cosmos_client.get_database_client(self.config.cosmos_db.database_name)
            container = database.get_container_client(self.config.cosmos_db.documents_container_name)
            
            # Convert to dict for Cosmos DB
            document_dict = document_record.dict()
            document_dict['createdAt'] = document_record.createdAt.isoformat()
            document_dict['updatedAt'] = document_record.updatedAt.isoformat()
            
            self.logger.info(f'Calling Cosmos DB create_item for document {document_record.id}')
            
            await container.create_item(body=document_dict)
            
            self.logger.info(f'SUCCESS: Stored document record {document_record.id} in Cosmos DB')
        except Exception as e:
            self.logger.error(f'ERROR storing document record {document_record.id} in Cosmos DB: {str(e)}', exc_info=True)
            raise
    
    def _extract_filename_from_url(self, document_url: str) -> str:
        """Extract filename from blob URL."""
        parsed_url = urlparse(document_url)
        return parsed_url.path.split('/')[-1]
    
    def _get_content_type(self, filename: str) -> str:
        """Get content type based on file extension."""
        extension = filename.lower().split('.')[-1] if '.' in filename else ''
        
        content_types = {
            'pdf': 'application/pdf',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'doc': 'application/msword',
            'txt': 'text/plain',
            'rtf': 'application/rtf',
            'html': 'text/html',
            'htm': 'text/html'
        }
        
        return content_types.get(extension, 'application/octet-stream')
    
    def _is_supported_document_format(self, document_url: str) -> bool:
        """Check if document format is supported by Document Intelligence."""
        filename = self._extract_filename_from_url(document_url)
        extension = filename.lower().split('.')[-1] if '.' in filename else ''
        
        # Document Intelligence supported formats
        supported_formats = {'pdf', 'jpeg', 'jpg', 'png', 'bmp', 'tiff', 'tif', 'docx', 'xlsx', 'pptx', 'html'}
        
        return extension in supported_formats
    
    async def _close_clients(self):
        """Close all Azure clients."""
        if self.document_intelligence_client:
            await self.document_intelligence_client.close()
        if self.blob_service_client:
            await self.blob_service_client.close()
        if self.cosmos_client:
            await self.cosmos_client.close()
