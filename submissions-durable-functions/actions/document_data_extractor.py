"""
Document data extractor action for Azure Durable Functions.

This module provides document data extraction functionality using mocked LLM analysis
for the durable functions orchestration workflow. Updates documents container with
extracted data results and handles concurrency using Cosmos DB Patch API with ETag.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

from azure.identity.aio import DefaultAzureCredential
from azure.cosmos.aio import CosmosClient
from azure.core.exceptions import HttpResponseError, ClientAuthenticationError
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    after_log
)

from config import AppConfig


class DocumentDataExtractor:
    """
    Document data extractor using mocked LLM analysis.
    
    This class handles document data extraction with static mock responses
    and updates Cosmos DB documents container using Patch API for concurrency safety.
    """
    
    def __init__(self):
        """Initialize the document data extractor with Azure clients."""
        self.logger = logging.getLogger(__name__)
        self.config = AppConfig.from_env()
        self.credential = DefaultAzureCredential()
        
        # Initialize clients (will be created async when needed)
        self.cosmos_client: Optional[CosmosClient] = None
    
    async def _ensure_client_initialized(self):
        """Ensure Cosmos DB client is initialized."""
        if not self.cosmos_client:
            self.cosmos_client = CosmosClient(
                url=self.config.cosmos_db.endpoint,
                credential=self.credential
            )
    
    async def extract_document_data_async(self, document_id: str, submission_id: str) -> Dict[str, Any]:
        """
        Extract structured data from document using mocked LLM analysis.
        
        Args:
            document_id: Unique document identifier
            submission_id: Reference to the submission this document belongs to
            
        Returns:
            Dict containing the data extraction results
        """
        try:
            self.logger.info(f'Starting document data extraction for document {document_id}')
            print(f'DEBUG: Starting document data extraction for document {document_id}')  # Debug logging
            
            # Ensure client is initialized
            await self._ensure_client_initialized()
            print(f'DEBUG: Client initialized for extraction {document_id}')
            
            # Fetch current document record
            document_record = await self._get_document_with_retry(document_id, submission_id)
            if not document_record:
                raise ValueError(f"Document {document_id} not found")
            
            print(f'DEBUG: Document record fetched for extraction {document_id}')
            
            # Mock LLM data extraction based on document type and content
            extraction_result = self._mock_extract_document_data(document_record)
            print(f'DEBUG: Extraction result: {extraction_result}')
            
            # Update document with extraction results using Patch API
            await self._update_document_extraction_with_retry(
                document_id, 
                submission_id, 
                extraction_result,
                document_record.get('_etag')
            )
            
            print(f'DEBUG: Document data extraction updated for {document_id}')
            self.logger.info(f'Document data extraction completed for {document_id}')
            
            return {
                "documentId": document_id,
                "extractedData": extraction_result,
                "status": "completed"
            }
            
        except Exception as e:
            error_msg = f'Document data extraction failed for {document_id}: {str(e)}'
            print(f'DEBUG EXTRACT ERROR: {error_msg}')  # Debug logging
            print(f'DEBUG EXTRACT ERROR TYPE: {type(e).__name__}')  # Debug logging
            self.logger.error(error_msg)
            
            # Try to update status to failed if we can
            try:
                await self._update_extraction_status_with_retry(document_id, submission_id, "failed")
            except Exception as update_error:
                print(f'DEBUG EXTRACT UPDATE ERROR: Failed to update extraction status: {str(update_error)}')
                self.logger.error(f'Failed to update extraction status: {str(update_error)}')
            
            return {
                "documentId": document_id,
                "extractedData": None,
                "status": f"error: {str(e)}"
            }
        finally:
            await self._close_client()
    
    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ClientAuthenticationError, HttpResponseError, TimeoutError, ConnectionError)),
        before_sleep=before_sleep_log(logging.getLogger(__name__), logging.WARNING),
        after=after_log(logging.getLogger(__name__), logging.INFO)
    )
    async def _get_document_with_retry(self, document_id: str, submission_id: str) -> Optional[Dict[str, Any]]:
        """
        Get document record from Cosmos DB with retry logic.
        
        Args:
            document_id: Document identifier
            submission_id: Submission identifier (partition key)
            
        Returns:
            Document record dict or None if not found
        """
        database = self.cosmos_client.get_database_client(self.config.cosmos_db.database_name)
        container = database.get_container_client(self.config.cosmos_db.documents_container_name)
        
        try:
            response = await container.read_item(
                item=document_id,
                partition_key=submission_id
            )
            return response
        except CosmosResourceNotFoundError:
            self.logger.warning(f'Document {document_id} not found in submission {submission_id}')
            return None
    
    def _mock_extract_document_data(self, document_record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mock document data extraction based on document type and content.
        
        Args:
            document_record: Document record from Cosmos DB
            
        Returns:
            Extracted structured data based on document type
        """
        document_type = document_record.get('documentType', 'other')
        filename = document_record.get('fileName', '').lower()
        content = document_record.get('content', '')
        
        # Mock extraction logic based on document type
        if document_type == "invoice":
            return {
                "invoiceNumber": f"INV-{hash(filename) % 10000:04d}",
                "totalAmount": round(abs(hash(content) % 50000) / 100, 2),
                "currency": "USD",
                "dueDate": "2025-08-15",
                "vendor": f"Vendor-{hash(filename[:10]) % 1000:03d}"
            }
        elif document_type == "contract":
            return {
                "contractNumber": f"CNT-{hash(filename) % 10000:04d}",
                "effectiveDate": "2025-07-01",
                "expirationDate": "2026-06-30",
                "contractValue": round(abs(hash(content) % 1000000) / 100, 2),
                "parties": [f"Party-A-{hash(filename[:5]) % 100:02d}", f"Party-B-{hash(filename[5:10]) % 100:02d}"]
            }
        elif document_type == "bankStatement":
            return {
                "accountNumber": f"****{hash(filename) % 10000:04d}",
                "statementPeriod": "2025-06-01 to 2025-06-30",
                "openingBalance": round(abs(hash(content[:100]) % 100000) / 100, 2),
                "closingBalance": round(abs(hash(content[-100:]) % 100000) / 100, 2),
                "transactionCount": abs(hash(content) % 50) + 10
            }
        elif document_type == "submissionNotes":
            return {
                "noteType": "submission_context",
                "keyPoints": [
                    f"Point 1: {content[:50]}..." if len(content) > 50 else content,
                    f"Document contains {len(content.split())} words",
                    f"Created from file: {document_record.get('fileName')}"
                ],
                "priority": "medium",
                "followUpRequired": len(content) > 1000
            }
        else:
            return {
                "documentFormat": document_record.get('contentType', 'unknown'),
                "wordCount": len(content.split()),
                "characterCount": len(content),
                "requiresManualReview": True,
                "extractionConfidence": 0.5
            }
    
    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ClientAuthenticationError, HttpResponseError, TimeoutError, ConnectionError)),
        before_sleep=before_sleep_log(logging.getLogger(__name__), logging.WARNING),
        after=after_log(logging.getLogger(__name__), logging.INFO)
    )
    async def _update_document_extraction_with_retry(
        self, 
        document_id: str, 
        submission_id: str, 
        extraction_result: Dict[str, Any],
        etag: Optional[str] = None
    ) -> None:
        """
        Update document extraction using Cosmos DB Patch API with ETag concurrency control.
        
        Args:
            document_id: Document identifier
            submission_id: Submission identifier (partition key)
            extraction_result: Extraction results to update
            etag: ETag for concurrency control
        """
        database = self.cosmos_client.get_database_client(self.config.cosmos_db.database_name)
        container = database.get_container_client(self.config.cosmos_db.documents_container_name)
        
        # Prepare patch operations
        patch_operations = [
            {"op": "replace", "path": "/extractedData", "value": extraction_result},
            {"op": "replace", "path": "/dataExtractionStatus", "value": "completed"},
            {"op": "replace", "path": "/updatedAt", "value": datetime.utcnow().isoformat()}
        ]
        
        # Set up request options with ETag if provided
        kwargs = {}
        if etag:
            from azure.core import MatchConditions
            kwargs["etag"] = etag
            kwargs["match_condition"] = MatchConditions.IfNotModified
        
        try:
            await container.patch_item(
                item=document_id,
                partition_key=submission_id,
                patch_operations=patch_operations,
                **kwargs
            )
            self.logger.info(f'Document data extraction updated for {document_id}')
            
        except HttpResponseError as e:
            if e.status_code == 412:  # Precondition Failed - ETag mismatch
                self.logger.warning(f'ETag mismatch for document {document_id}, retrying with fresh document')
                # Get fresh document and retry
                fresh_document = await self._get_document_with_retry(document_id, submission_id)
                if fresh_document:
                    await self._update_document_extraction_with_retry(
                        document_id, 
                        submission_id, 
                        extraction_result, 
                        fresh_document.get('_etag')
                    )
                else:
                    raise ValueError(f"Document {document_id} not found during retry")
            else:
                raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        retry=retry_if_exception_type((ClientAuthenticationError, HttpResponseError, TimeoutError, ConnectionError)),
        before_sleep=before_sleep_log(logging.getLogger(__name__), logging.WARNING),
        after=after_log(logging.getLogger(__name__), logging.INFO)
    )
    async def _update_extraction_status_with_retry(
        self, 
        document_id: str, 
        submission_id: str, 
        status: str
    ) -> None:
        """
        Update only the data extraction status field.
        
        Args:
            document_id: Document identifier
            submission_id: Submission identifier (partition key)
            status: New data extraction status
        """
        database = self.cosmos_client.get_database_client(self.config.cosmos_db.database_name)
        container = database.get_container_client(self.config.cosmos_db.documents_container_name)
        
        patch_operations = [
            {"op": "replace", "path": "/dataExtractionStatus", "value": status},
            {"op": "replace", "path": "/updatedAt", "value": datetime.utcnow().isoformat()}
        ]
        
        await container.patch_item(
            item=document_id,
            partition_key=submission_id,
            patch_operations=patch_operations
        )
    
    async def _close_client(self):
        """Close Cosmos DB client."""
        if self.cosmos_client:
            await self.cosmos_client.close()
            self.cosmos_client = None
