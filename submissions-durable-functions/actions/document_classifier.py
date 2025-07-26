"""
Document classifier action for Azure Durable Functions.

This module provides document classification functionality using mocked LLM analysis
for the durable functions orchestration workflow. Updates documents container with
classification results and handles concurrency using Cosmos DB Patch API with ETag.
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


class DocumentClassifier:
    """
    Document classifier using mocked LLM analysis.
    
    This class handles document classification with static mock responses
    and updates Cosmos DB documents container using Patch API for concurrency safety.
    """
    
    def __init__(self):
        """Initialize the document classifier with Azure clients."""
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
    
    async def classify_document_async(self, document_id: str, submission_id: str) -> Dict[str, Any]:
        """
        Classify document using mocked LLM analysis.
        
        Args:
            document_id: Unique document identifier
            submission_id: Reference to the submission this document belongs to
            
        Returns:
            Dict containing the classification results
        """
        try:
            self.logger.info(f'Starting document classification for document {document_id}')
            print(f'DEBUG: Starting document classification for document {document_id}')  # Debug logging
            
            # Ensure client is initialized
            await self._ensure_client_initialized()
            print(f'DEBUG: Client initialized for document {document_id}')
            
            # Fetch current document record
            document_record = await self._get_document_with_retry(document_id, submission_id)
            if not document_record:
                raise ValueError(f"Document {document_id} not found")
            
            print(f'DEBUG: Document record fetched for {document_id}')
            
            # Mock LLM classification based on filename patterns
            classification_result = self._mock_classify_document(document_record)
            print(f'DEBUG: Classification result: {classification_result}')
            
            # Update document with classification results using Patch API
            await self._update_document_classification_with_retry(
                document_id, 
                submission_id, 
                classification_result,
                document_record.get('_etag')
            )
            
            print(f'DEBUG: Document classification updated for {document_id}')
            self.logger.info(f'Document classification completed for {document_id}: {classification_result["documentType"]}')
            
            return {
                "documentId": document_id,
                "documentType": classification_result["documentType"],
                "summary": classification_result["summary"],
                "status": "completed"
            }
            
        except Exception as e:
            error_msg = f'Document classification failed for {document_id}: {str(e)}'
            print(f'DEBUG ERROR: {error_msg}')  # Debug logging
            print(f'DEBUG ERROR TYPE: {type(e).__name__}')  # Debug logging
            self.logger.error(error_msg)
            
            # Try to update status to failed if we can
            try:
                await self._update_classification_status_with_retry(document_id, submission_id, "failed")
            except Exception as update_error:
                print(f'DEBUG UPDATE ERROR: Failed to update classification status: {str(update_error)}')
                self.logger.error(f'Failed to update classification status: {str(update_error)}')
            
            return {
                "documentId": document_id,
                "documentType": None,
                "summary": None,
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
    
    def _mock_classify_document(self, document_record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mock document classification based on filename patterns.
        
        Args:
            document_record: Document record from Cosmos DB
            
        Returns:
            Classification result with documentType and summary
        """
        filename = document_record.get('fileName', '').lower()
        content = document_record.get('content', '')
        
        # Mock classification logic based on filename patterns
        if 'invoice' in filename or 'bill' in filename:
            document_type = "invoice"
            summary = f"Invoice document with {len(content.split())} words of content. Contains billing information and payment details."
        elif 'contract' in filename or 'agreement' in filename:
            document_type = "contract"
            summary = f"Contract document with {len(content.split())} words of content. Contains legal terms and conditions."
        elif 'statement' in filename or 'bank' in filename:
            document_type = "bankStatement"
            summary = f"Bank statement document with {len(content.split())} words of content. Contains financial transaction details."
        elif 'note' in filename or 'memo' in filename:
            document_type = "submissionNotes"
            summary = f"Submission notes document with {len(content.split())} words of content. Contains additional context and explanations."
        else:
            document_type = "other"
            summary = f"General document with {len(content.split())} words of content. Classification requires manual review."
        
        return {
            "documentType": document_type,
            "summary": summary
        }
    
    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ClientAuthenticationError, HttpResponseError, TimeoutError, ConnectionError)),
        before_sleep=before_sleep_log(logging.getLogger(__name__), logging.WARNING),
        after=after_log(logging.getLogger(__name__), logging.INFO)
    )
    async def _update_document_classification_with_retry(
        self, 
        document_id: str, 
        submission_id: str, 
        classification_result: Dict[str, Any],
        etag: Optional[str] = None
    ) -> None:
        """
        Update document classification using Cosmos DB Patch API with ETag concurrency control.
        
        Args:
            document_id: Document identifier
            submission_id: Submission identifier (partition key)
            classification_result: Classification results to update
            etag: ETag for concurrency control
        """
        database = self.cosmos_client.get_database_client(self.config.cosmos_db.database_name)
        container = database.get_container_client(self.config.cosmos_db.documents_container_name)
        
        # Prepare patch operations
        patch_operations = [
            {"op": "replace", "path": "/documentType", "value": classification_result["documentType"]},
            {"op": "replace", "path": "/summary", "value": classification_result["summary"]},
            {"op": "replace", "path": "/classificationStatus", "value": "completed"},
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
            self.logger.info(f'Document classification updated for {document_id}')
            
        except HttpResponseError as e:
            if e.status_code == 412:  # Precondition Failed - ETag mismatch
                self.logger.warning(f'ETag mismatch for document {document_id}, retrying with fresh document')
                # Get fresh document and retry
                fresh_document = await self._get_document_with_retry(document_id, submission_id)
                if fresh_document:
                    await self._update_document_classification_with_retry(
                        document_id, 
                        submission_id, 
                        classification_result, 
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
    async def _update_classification_status_with_retry(
        self, 
        document_id: str, 
        submission_id: str, 
        status: str
    ) -> None:
        """
        Update only the classification status field.
        
        Args:
            document_id: Document identifier
            submission_id: Submission identifier (partition key)
            status: New classification status
        """
        database = self.cosmos_client.get_database_client(self.config.cosmos_db.database_name)
        container = database.get_container_client(self.config.cosmos_db.documents_container_name)
        
        patch_operations = [
            {"op": "replace", "path": "/classificationStatus", "value": status},
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
