"""
Document data extractor action for Azure Durable Functions.

This module provides document data extraction functionality using Azure OpenAI
for the durable functions orchestration workflow. Updates documents container with
extracted data results and handles concurrency using Cosmos DB Patch API with ETag.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

from azure.identity.aio import DefaultAzureCredential
from azure.cosmos.aio import CosmosClient
from azure.core.exceptions import HttpResponseError, ClientAuthenticationError
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from openai import AsyncAzureOpenAI
from jinja2 import Environment, FileSystemLoader
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    after_log
)

from config import AppConfig
from models import LLMDataExtractionResponse


class DocumentDataExtractor:
    """
    Document data extractor using Azure OpenAI API.
    
    This class handles document data extraction using Azure OpenAI with structured outputs
    and updates Cosmos DB documents container using Patch API for concurrency safety.
    """
    
    def __init__(self):
        """Initialize the document data extractor with Azure clients."""
        self.logger = logging.getLogger(__name__)
        self.config = AppConfig.from_env()
        self.credential = DefaultAzureCredential()
        
        # Initialize clients (will be created async when needed)
        self.cosmos_client: Optional[CosmosClient] = None
        self.openai_client: Optional[AsyncAzureOpenAI] = None
        self.system_prompt_template = None
    
    async def _ensure_client_initialized(self):
        """Ensure Cosmos DB and OpenAI clients are initialized."""
        if not self.cosmos_client:
            self.cosmos_client = CosmosClient(
                url=self.config.cosmos_db.endpoint,
                credential=self.credential
            )
        
        if not self.openai_client:
            self.openai_client = AsyncAzureOpenAI(
                azure_endpoint=self.config.azure_openai.endpoint,
                azure_ad_token_provider=self._get_azure_ad_token,
                api_version="2024-08-01-preview"
            )
        
        if not self.system_prompt_template:
            # Load system prompt template from prompts folder
            template_dir = Path(__file__).parent / "prompts"
            env = Environment(loader=FileSystemLoader(template_dir))
            self.system_prompt_template = env.get_template("extractor_system_prompt.jinja2")

    async def _get_azure_ad_token(self) -> str:
        """
        Get Azure AD token for OpenAI API authentication.
        
        Returns:
            Azure AD access token for Cognitive Services
        """
        token = await self.credential.get_token("https://cognitiveservices.azure.com/.default")
        return token.token
    
    async def extract_document_data_async(self, document_id: str, submission_id: str) -> Dict[str, Any]:
        """
        Extract structured data from document using Azure OpenAI API.
        
        This method processes ALL documents regardless of type and lets the LLM
        determine what data can be extracted. For non-invoice documents, fields
        will be null but the extraction still runs.
        
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
            print(f'DEBUG: Document details - fileName: {document_record.get("fileName")}, contentLength: {len(document_record.get("content", ""))}')
            
            # OpenAI data extraction using structured outputs
            extraction_result = await self._extract_document_data_with_openai(document_record)
            
            # Convert to dict format expected by update method, or None if no extraction
            extraction_dict = None
            if extraction_result:
                extraction_dict = extraction_result.model_dump(exclude_none=True)
                print(f'DEBUG: Extraction result: {extraction_dict}')
            else:
                print('DEBUG: No data extraction performed (failed)')
            
            # Update document with extraction results using Patch API
            await self._update_document_extraction_with_retry(
                document_id, 
                submission_id, 
                extraction_dict,
                document_record.get('_etag')
            )
            
            print(f'DEBUG: Document data extraction updated for {document_id}')
            self.logger.info(f'Document data extraction completed for {document_id}')
            
            return {
                "documentId": document_id,
                "extractedData": extraction_dict,
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
    
    async def _extract_document_data_with_openai(self, document_record: Dict[str, Any]) -> Optional[LLMDataExtractionResponse]:
        """
        Extract document data using Azure OpenAI API.
        
        This method processes ALL documents and lets the LLM determine what data
        can be extracted. For non-invoice documents, fields will be null.
        
        Args:
            document_record: Document record from Cosmos DB
            
        Returns:
            Extracted structured data or None if API call fails
            
        Raises:
            Exception: If OpenAI API call fails
        """
        content = document_record.get('content', '')
        filename = document_record.get('fileName', 'unknown')
        
        print(f'DEBUG: Extracting data from document {filename} with {len(content)} characters')
        
        if not content.strip():
            print(f'DEBUG: Empty content for document {filename}, skipping extraction')
            return None
        
        # Render system prompt from template
        system_prompt = self.system_prompt_template.render()
        print(f'DEBUG: System prompt rendered for data extraction, length: {len(system_prompt)}')
        
        try:
            print('DEBUG: Making OpenAI API call for data extraction')
            response = await self.openai_client.beta.chat.completions.parse(
                model=self.config.azure_openai.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": content}
                ],
                response_format=LLMDataExtractionResponse,
                temperature=0,
                max_tokens=1000
            )
            
            extraction_result = response.choices[0].message.parsed
            print(f'DEBUG: OpenAI extraction result: {extraction_result}')
            
            return extraction_result
            
        except Exception as e:
            print(f'DEBUG ERROR: OpenAI API call failed: {str(e)}')
            self.logger.error(f'OpenAI API call failed for {filename}: {str(e)}')
            raise
    
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
