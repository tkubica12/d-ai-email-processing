"""
Submission storage action for Azure Durable Functions.

This module provides submission record storage functionality using Azure Cosmos DB
for the durable functions orchestration workflow.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

from azure.identity.aio import DefaultAzureCredential
from azure.cosmos.aio import CosmosClient
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
from models import SubmissionRecord


class SubmissionStorage:
    """
    Submission storage using Azure Cosmos DB.
    
    This class handles storing submission records in Cosmos DB.
    """
    
    def __init__(self):
        """Initialize the submission storage with Azure clients."""
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
    
    async def store_submission_async(self, submission_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Store submission record in Cosmos DB.
        
        Args:
            submission_data: Submission data from Service Bus message
            
        Returns:
            Dict containing the storage results
        """
        submission_id = submission_data.get("submissionId", "unknown")
        user_id = submission_data.get("userId", "unknown")
        document_urls = submission_data.get("documentUrls", [])
        
        try:
            self.logger.info(f'Starting submission storage for {submission_id}')
            
            # Ensure client is initialized
            await self._ensure_client_initialized()
            self.logger.info(f'Cosmos DB client initialized successfully for submission {submission_id}')
            
            # Create submission record
            submission_record = SubmissionRecord(
                id=submission_id,
                submissionId=submission_id,
                userId=user_id,
                documentUrls=document_urls,
                status="processing",
                createdAt=datetime.utcnow(),
                updatedAt=datetime.utcnow(),
                metadata={
                    "documentCount": len(document_urls),
                    "submittedAt": submission_data.get("submittedAt"),
                    "source": "durable-functions"
                }
            )
            
            self.logger.info(f'Created submission record for {submission_id}, attempting to store in Cosmos DB')
            
            # Store in Cosmos DB
            await self._store_submission_record(submission_record)
            
            self.logger.info(f'Successfully stored submission record for {submission_id}')
            
            return {
                "submissionId": submission_id,
                "documentCount": len(document_urls),
                "status": "success"
            }
            
        except Exception as e:
            self.logger.error(f'CRITICAL ERROR: Failed to store submission record for {submission_id}: {str(e)}', exc_info=True)
            # Re-raise to let the activity function handle it
            raise
        finally:
            try:
                await self._close_client()
                self.logger.info(f'Closed Cosmos DB client for submission {submission_id}')
            except Exception as e:
                self.logger.warning(f'Failed to close Cosmos DB client for submission {submission_id}: {e}')
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((ClientAuthenticationError, HttpResponseError, TimeoutError, ConnectionError)),
        before_sleep=before_sleep_log(logging.getLogger(__name__), logging.WARNING),
        after=after_log(logging.getLogger(__name__), logging.INFO)
    )
    async def _store_submission_record(self, submission_record: SubmissionRecord) -> None:
        """
        Store submission record in Cosmos DB.
        
        Args:
            submission_record: Submission record to store
        """
        try:
            self.logger.info(f'Attempting to store submission record {submission_record.id} to Cosmos DB')
            
            database = self.cosmos_client.get_database_client(self.config.cosmos_db.database_name)
            container = database.get_container_client(self.config.cosmos_db.submissions_container_name)
            
            # Convert to dict for Cosmos DB
            submission_dict = submission_record.dict()
            submission_dict['createdAt'] = submission_record.createdAt.isoformat()
            submission_dict['updatedAt'] = submission_record.updatedAt.isoformat()
            
            self.logger.info(f'Calling Cosmos DB create_item for submission {submission_record.id}')
            
            await container.create_item(body=submission_dict)
            
            self.logger.info(f'SUCCESS: Stored submission record {submission_record.id} in Cosmos DB')
        except Exception as e:
            self.logger.error(f'ERROR storing submission record {submission_record.id} in Cosmos DB: {str(e)}', exc_info=True)
            raise
    
    async def _close_client(self):
        """Close Cosmos DB client."""
        if self.cosmos_client:
            await self.cosmos_client.close()
