"""
Storage operations for Cosmos DB.

This module provides async operations for storing and retrieving
submission documents from Azure Cosmos DB.
"""

import logging
from datetime import datetime
from typing import Optional

from azure.cosmos.aio import CosmosClient, DatabaseProxy, ContainerProxy
from azure.cosmos.exceptions import CosmosResourceNotFoundError, CosmosHttpResponseError
from azure.identity.aio import DefaultAzureCredential

from config import CosmosDBConfig
from models import SubmissionDocument, DocumentInfo, SubmissionMessage

logger = logging.getLogger(__name__)


class CosmosDBStorage:
    """
    Async storage operations for Cosmos DB.
    
    This class provides methods to store and retrieve submission documents
    from Azure Cosmos DB using the async SDK.
    """
    
    def __init__(self, config: CosmosDBConfig):
        """
        Initialize the Cosmos DB storage client.
        
        Args:
            config: Cosmos DB configuration settings
        """
        self.config = config
        self._client: Optional[CosmosClient] = None
        self._database: Optional[DatabaseProxy] = None
        self._submissions_container: Optional[ContainerProxy] = None
        self._credential = DefaultAzureCredential()
        
    async def initialize(self) -> None:
        """
        Initialize the Cosmos DB client and containers.
        
        This method should be called once before using the storage operations.
        It establishes the connection to Cosmos DB and gets references to
        the required containers.
        
        Raises:
            CosmosHttpResponseError: If connection to Cosmos DB fails
        """
        try:
            self._client = CosmosClient(
                url=self.config.endpoint,
                credential=self._credential
            )
            
            self._database = self._client.get_database_client(
                database=self.config.database_name
            )
            
            self._submissions_container = self._database.get_container_client(
                container=self.config.submissions_container_name
            )
            
            logger.info(
                f"Initialized Cosmos DB client for database '{self.config.database_name}'"
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize Cosmos DB client: {e}")
            raise
    
    async def store_submission(self, submission_message: SubmissionMessage) -> SubmissionDocument:
        """
        Store a new submission document in Cosmos DB.
        
        This method creates a new submission document based on the Service Bus
        message and stores it in the submissions container.
        
        Args:
            submission_message: The submission message from Service Bus
            
        Returns:
            SubmissionDocument: The stored submission document
            
        Raises:
            CosmosHttpResponseError: If the storage operation fails
        """
        if not self._submissions_container:
            raise RuntimeError("Storage not initialized. Call initialize() first.")
        
        # Create document info list from URLs
        documents = [
            DocumentInfo(
                documentUrl=url,
                processed=None,
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
            documents=documents
        )
        
        try:
            # Store in Cosmos DB
            await self._submissions_container.create_item(
                body=submission_doc.model_dump(mode='json')
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
    
    async def close(self) -> None:
        """
        Close the Cosmos DB client connection.
        
        This method should be called when shutting down the application
        to properly close the connection.
        """
        if self._client:
            await self._client.close()
            logger.info("Closed Cosmos DB client connection")
