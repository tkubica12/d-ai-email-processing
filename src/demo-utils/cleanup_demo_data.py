"""
Demo utility to clean up all demo data from Azure resources.

This script performs the following cleanup operations:
1. Deletes all records from Cosmos DB containers (events, documents, submissions)
2. Deletes all storage containers in GUID format, preserving the policies-docs container

Usage:
    python cleanup_demo_data.py
"""

import logging
import os
import re
from typing import List

from azure.cosmos import CosmosClient
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Suppress Azure SDK INFO logs to DEBUG level
logging.getLogger('azure.core.pipeline.policies.http_logging_policy').setLevel(logging.WARNING)
logging.getLogger('azure.identity').setLevel(logging.WARNING)
logging.getLogger('azure.storage').setLevel(logging.WARNING)
logging.getLogger('azure.cosmos').setLevel(logging.WARNING)


class DemoDataCleanup:
    """Utility class for cleaning up demo data from Azure resources."""
    
    def __init__(self):
        """Initialize the cleanup utility with Azure clients."""
        load_dotenv()
        
        # Initialize Azure credential
        self.credential = DefaultAzureCredential()
        
        # Cosmos DB configuration
        self.cosmos_endpoint = os.getenv('AZURE_COSMOS_DB_ENDPOINT')
        self.cosmos_database_name = os.getenv('AZURE_COSMOS_DB_DATABASE_NAME')
        self.cosmos_events_container = os.getenv('AZURE_COSMOS_DB_EVENTS_CONTAINER_NAME')
        self.cosmos_documents_container = os.getenv('AZURE_COSMOS_DB_DOCUMENTS_CONTAINER_NAME')
        self.cosmos_submissions_container = os.getenv('AZURE_COSMOS_DB_SUBMISSIONS_CONTAINER_NAME')
        self.cosmos_submissions_trigger_container = os.getenv('AZURE_COSMOS_DB_SUBMISSIONS_TRIGGER_CONTAINER_NAME')
        
        # Durable Functions Cosmos DB configuration
        self.cosmos_durable_functions_database_name = os.getenv('AZURE_COSMOS_DB_DURABLE_FUNCTIONS_DATABASE_NAME')
        self.cosmos_durable_functions_documents_container = os.getenv('AZURE_COSMOS_DB_DURABLE_FUNCTIONS_DOCUMENTS_CONTAINER_NAME')
        self.cosmos_durable_functions_submissions_container = os.getenv('AZURE_COSMOS_DB_DURABLE_FUNCTIONS_SUBMISSIONS_CONTAINER_NAME')
        
        # Storage configuration
        self.storage_account_name = os.getenv('AZURE_STORAGE_ACCOUNT_NAME')
        
        # Initialize clients
        self.cosmos_client = CosmosClient(self.cosmos_endpoint, self.credential)
        self.blob_service_client = BlobServiceClient(
            account_url=f"https://{self.storage_account_name}.blob.core.windows.net",
            credential=self.credential
        )
        
        # GUID pattern for container names
        self.guid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
        
        # Validate configuration
        self._validate_configuration()
        
    def _validate_configuration(self) -> None:
        """Validate that all required environment variables are set."""
        required_vars = [
            ('AZURE_COSMOS_DB_ENDPOINT', self.cosmos_endpoint),
            ('AZURE_STORAGE_ACCOUNT_NAME', self.storage_account_name),
        ]
        
        missing_vars = []
        for var_name, var_value in required_vars:
            if not var_value:
                missing_vars.append(var_name)
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        # Log configuration status
        event_sourcing_vars = [
            self.cosmos_database_name,
            self.cosmos_events_container,
            self.cosmos_documents_container,
            self.cosmos_submissions_container,
            self.cosmos_submissions_trigger_container
        ]
        
        durable_functions_vars = [
            self.cosmos_durable_functions_database_name,
            self.cosmos_durable_functions_documents_container,
            self.cosmos_durable_functions_submissions_container
        ]
        
        event_sourcing_configured = all(var for var in event_sourcing_vars)
        durable_functions_configured = all(var for var in durable_functions_vars)
        
        logger.info("Configuration status:")
        logger.info(f"  Event-Sourcing containers: {'✓' if event_sourcing_configured else '✗'}")
        logger.info(f"  Durable Functions containers: {'✓' if durable_functions_configured else '✗'}")
        
    def cleanup_cosmos_container(self, container_name: str) -> None:
        """
        Delete all documents from a Cosmos DB container.
        
        Args:
            container_name: Name of the container to clean up
            
        Raises:
            CosmosResourceNotFoundError: If the container doesn't exist
        """
        try:
            database = self.cosmos_client.get_database_client(self.cosmos_database_name)
            container = database.get_container_client(container_name)
            
            logger.info(f"Cleaning up container: {container_name}")
            
            # Query all documents
            query = "SELECT * FROM c"
            items = list(container.query_items(query=query, enable_cross_partition_query=True))
            
            if not items:
                logger.info(f"Container {container_name} is already empty")
                return
                
            logger.info(f"Found {len(items)} documents to delete in {container_name}")
            
            # Delete each document
            deleted_count = 0
            for item in items:
                try:
                    # Get the partition key property from the container
                    container_properties = container.read()
                    partition_key_path = container_properties['partitionKey']['paths'][0][1:]  # Remove the leading '/'
                    
                    # Get the partition key value from the document
                    partition_key_value = item.get(partition_key_path, item['id'])
                    
                    container.delete_item(item['id'], partition_key=partition_key_value)
                    deleted_count += 1
                    
                    if deleted_count % 10 == 0:
                        logger.info(f"Deleted {deleted_count}/{len(items)} documents from {container_name}")
                        
                except Exception:
                    # Fallback: try with id as partition key
                    try:
                        container.delete_item(item['id'], partition_key=item['id'])
                        deleted_count += 1
                    except Exception as e2:
                        logger.warning(f"Failed to delete document {item['id']}: {str(e2)}")
                    
            logger.info(f"Successfully deleted {deleted_count} documents from {container_name}")
            
        except CosmosResourceNotFoundError:
            logger.warning(f"Container {container_name} not found")
        except Exception as e:
            logger.error(f"Error cleaning up container {container_name}: {str(e)}")
            
    def cleanup_all_cosmos_containers(self) -> None:
        """Clean up all Cosmos DB containers (both event-sourcing and durable functions)."""
        # Event-sourcing containers
        event_sourcing_containers = [
            (self.cosmos_database_name, self.cosmos_events_container),
            (self.cosmos_database_name, self.cosmos_documents_container),
            (self.cosmos_database_name, self.cosmos_submissions_container),
            (self.cosmos_database_name, self.cosmos_submissions_trigger_container)
        ]
        
        # Durable Functions containers
        durable_functions_containers = [
            (self.cosmos_durable_functions_database_name, self.cosmos_durable_functions_documents_container),
            (self.cosmos_durable_functions_database_name, self.cosmos_durable_functions_submissions_container)
        ]
        
        # Clean up event-sourcing containers
        logger.info("--- Cleaning up Event-Sourcing Cosmos DB containers ---")
        for database_name, container_name in event_sourcing_containers:
            if container_name and database_name:
                self.cleanup_cosmos_container_in_database(database_name, container_name)
            else:
                logger.warning("Container or database name not configured for one of the event-sourcing containers")
        
        # Clean up durable functions containers
        logger.info("--- Cleaning up Durable Functions Cosmos DB containers ---")
        for database_name, container_name in durable_functions_containers:
            if container_name and database_name:
                self.cleanup_cosmos_container_in_database(database_name, container_name)
            else:
                logger.warning("Container or database name not configured for one of the durable functions containers")
                
    def cleanup_cosmos_container_in_database(self, database_name: str, container_name: str) -> None:
        """
        Delete all documents from a Cosmos DB container in a specific database.
        
        Args:
            database_name: Name of the database
            container_name: Name of the container to clean up
            
        Raises:
            CosmosResourceNotFoundError: If the database or container doesn't exist
        """
        try:
            database = self.cosmos_client.get_database_client(database_name)
            container = database.get_container_client(container_name)
            
            logger.info(f"Cleaning up container: {database_name}/{container_name}")
            
            # Query all documents
            query = "SELECT * FROM c"
            items = list(container.query_items(query=query, enable_cross_partition_query=True))
            
            if not items:
                logger.info(f"Container {database_name}/{container_name} is already empty")
                return
                
            logger.info(f"Found {len(items)} documents to delete in {database_name}/{container_name}")
            
            # Delete each document
            deleted_count = 0
            for item in items:
                try:
                    # Get the partition key property from the container
                    container_properties = container.read()
                    partition_key_path = container_properties['partitionKey']['paths'][0][1:]  # Remove the leading '/'
                    
                    # Get the partition key value from the document
                    partition_key_value = item.get(partition_key_path, item['id'])
                    
                    container.delete_item(item['id'], partition_key=partition_key_value)
                    deleted_count += 1
                    
                    if deleted_count % 10 == 0:
                        logger.info(f"Deleted {deleted_count}/{len(items)} documents from {database_name}/{container_name}")
                        
                except Exception:
                    # Fallback: try with id as partition key
                    try:
                        container.delete_item(item['id'], partition_key=item['id'])
                        deleted_count += 1
                    except Exception as e2:
                        logger.warning(f"Failed to delete document {item['id']}: {str(e2)}")
                    
            logger.info(f"Successfully deleted {deleted_count} documents from {database_name}/{container_name}")
            
        except CosmosResourceNotFoundError:
            logger.warning(f"Database {database_name} or container {container_name} not found")
        except Exception as e:
            logger.error(f"Error cleaning up container {database_name}/{container_name}: {str(e)}")
                
    def get_guid_containers(self) -> List[str]:
        """
        Get list of storage containers that match GUID format.
        
        Returns:
            List of container names in GUID format
        """
        try:
            containers = self.blob_service_client.list_containers()
            guid_containers = [
                container.name for container in containers 
                if self.guid_pattern.match(container.name) and container.name != 'policies-docs'
            ]
            
            logger.info(f"Found {len(guid_containers)} GUID-formatted containers")
            return guid_containers
            
        except Exception as e:
            logger.error(f"Error listing storage containers: {str(e)}")
            return []
            
    def delete_storage_container(self, container_name: str) -> None:
        """
        Delete a storage container and all its contents.
        
        Args:
            container_name: Name of the container to delete
        """
        try:
            container_client = self.blob_service_client.get_container_client(container_name)
            
            # Get blob count for logging
            blobs = list(container_client.list_blobs())
            blob_count = len(blobs)
            
            logger.info(f"Deleting container '{container_name}' with {blob_count} blobs")
            
            # Delete the container (this also deletes all blobs)
            container_client.delete_container()
            
            logger.info(f"Successfully deleted container: {container_name}")
            
        except Exception as e:
            logger.error(f"Error deleting container {container_name}: {str(e)}")
            
    def cleanup_guid_storage_containers(self) -> None:
        """Delete all storage containers in GUID format."""
        guid_containers = self.get_guid_containers()
        
        if not guid_containers:
            logger.info("No GUID-formatted containers found to delete")
            return
            
        logger.info(f"Deleting {len(guid_containers)} GUID-formatted containers")
        
        for container_name in guid_containers:
            self.delete_storage_container(container_name)
            
    def run_cleanup(self) -> None:
        """Run the complete cleanup process."""
        logger.info("Starting demo data cleanup process...")
        
        # Clean up Cosmos DB containers
        logger.info("=== Cleaning up Cosmos DB containers ===")
        self.cleanup_all_cosmos_containers()
        
        # Clean up storage containers
        logger.info("=== Cleaning up storage containers ===")
        self.cleanup_guid_storage_containers()
        
        logger.info("Demo data cleanup completed successfully!")


def main():
    """Main entry point for the cleanup utility."""
    try:
        cleanup = DemoDataCleanup()
        cleanup.run_cleanup()
    except Exception as e:
        logger.error(f"Cleanup failed: {str(e)}")
        raise


if __name__ == "__main__":
    main()
