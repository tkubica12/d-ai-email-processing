"""
Azure Table Storage client for persisting Cosmos DB Change Feed continuation tokens.

This module provides a storage abstraction for Change Feed continuation tokens,
enabling stateful processing across service restarts and supporting distributed
deployment scenarios.
"""
import logging
from typing import Optional
from datetime import datetime, timezone

from azure.data.tables import TableServiceClient, TableClient
from azure.data.tables.aio import TableServiceClient as AsyncTableServiceClient, TableClient as AsyncTableClient
from azure.identity.aio import DefaultAzureCredential
from azure.core.exceptions import ResourceNotFoundError, ResourceExistsError

from config import TableStorageConfig


class ContinuationTokenStorage:
    """
    Azure Table Storage client for persisting Change Feed continuation tokens.
    
    This class provides methods to store and retrieve continuation tokens for
    Cosmos DB Change Feed processing, enabling stateful processing across
    service restarts and distributed deployments.
    """
    
    def __init__(self, config: TableStorageConfig):
        """
        Initialize the continuation token storage client.
        
        Args:
            config: Table storage configuration
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.table_service_client: Optional[AsyncTableServiceClient] = None
        self.table_client: Optional[AsyncTableClient] = None
        
    async def initialize(self) -> None:
        """
        Initialize the Table Storage client and ensure the table exists.
        
        Raises:
            Exception: If client initialization fails
        """
        if not self.config.enabled:
            self.logger.info("Table storage is disabled - continuation tokens will not be persisted")
            return
            
        try:
            # Initialize credentials and client
            credential = DefaultAzureCredential()
            endpoint = f"https://{self.config.account_name}.table.core.windows.net"
            
            self.table_service_client = AsyncTableServiceClient(
                endpoint=endpoint,
                credential=credential
            )
            
            self.table_client = self.table_service_client.get_table_client(
                table_name=self.config.table_name
            )
            
            # Ensure the table exists
            await self._ensure_table_exists()
            
            self.logger.info(f"Table storage initialized successfully - table: {self.config.table_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize table storage: {e}")
            raise
    
    async def _ensure_table_exists(self) -> None:
        """
        Ensure the continuation tokens table exists, create if it doesn't.
        """
        try:
            await self.table_client.create_table()
            self.logger.info(f"Created table: {self.config.table_name}")
        except ResourceExistsError:
            self.logger.debug(f"Table already exists: {self.config.table_name}")
        except Exception as e:
            self.logger.error(f"Failed to create table {self.config.table_name}: {e}")
            raise
    
    async def save_continuation_token(self, processor_id: str, continuation_token: str) -> None:
        """
        Save a continuation token to Table Storage.
        
        Args:
            processor_id: Unique identifier for the processor instance
            continuation_token: The continuation token to save
        """
        if not self.config.enabled or not self.table_client:
            self.logger.debug("Table storage disabled - skipping token save")
            return
            
        try:
            entity = {
                "PartitionKey": "changefeed",
                "RowKey": processor_id,
                "ContinuationToken": continuation_token,
                "LastUpdated": datetime.now(timezone.utc).isoformat()
            }
            
            await self.table_client.upsert_entity(entity)
            self.logger.debug(f"Saved continuation token for processor {processor_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to save continuation token for processor {processor_id}: {e}")
            # Don't raise exception to avoid breaking the processing loop
    
    async def load_continuation_token(self, processor_id: str) -> Optional[str]:
        """
        Load a continuation token from Table Storage.
        
        Args:
            processor_id: Unique identifier for the processor instance
            
        Returns:
            Optional[str]: The continuation token if found, None otherwise
        """
        if not self.config.enabled or not self.table_client:
            self.logger.debug("Table storage disabled - no token to load")
            return None
            
        try:
            entity = await self.table_client.get_entity(
                partition_key="changefeed",
                row_key=processor_id
            )
            
            continuation_token = entity.get("ContinuationToken")
            last_updated = entity.get("LastUpdated")
            
            if continuation_token:
                self.logger.info(f"Loaded continuation token for processor {processor_id} (last updated: {last_updated})")
                return continuation_token
            else:
                self.logger.debug(f"No continuation token found for processor {processor_id}")
                return None
                
        except ResourceNotFoundError:
            self.logger.debug(f"No continuation token found for processor {processor_id}")
            return None
        except Exception as e:
            self.logger.error(f"Failed to load continuation token for processor {processor_id}: {e}")
            return None
    
    async def delete_continuation_token(self, processor_id: str) -> None:
        """
        Delete a continuation token from Table Storage.
        
        Args:
            processor_id: Unique identifier for the processor instance
        """
        if not self.config.enabled or not self.table_client:
            self.logger.debug("Table storage disabled - no token to delete")
            return
            
        try:
            await self.table_client.delete_entity(
                partition_key="changefeed",
                row_key=processor_id
            )
            self.logger.info(f"Deleted continuation token for processor {processor_id}")
            
        except ResourceNotFoundError:
            self.logger.debug(f"No continuation token found to delete for processor {processor_id}")
        except Exception as e:
            self.logger.error(f"Failed to delete continuation token for processor {processor_id}: {e}")
    
    async def close(self) -> None:
        """
        Close the Table Storage client connections.
        """
        if self.table_service_client:
            await self.table_service_client.close()
            self.logger.debug("Table storage client closed")
