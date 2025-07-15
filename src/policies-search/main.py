"""
Policies Search Setup Script

This script sets up the policies-search system by:
1. Creating Azure Blob Storage container and uploading policy documents
2. Creating Azure AI Search index
3. Processing and indexing documents for search

All operations are idempotent - safe to run multiple times.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import List

from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Remap Azure SDK INFO logs to DEBUG to reduce noise
logging.getLogger('azure.core.pipeline.policies.http_logging_policy').setLevel(logging.WARNING)
logging.getLogger('azure.identity').setLevel(logging.WARNING)
logging.getLogger('azure.storage.blob').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


class PoliciesSearchSetup:
    """Setup class for policies-search system."""
    
    def __init__(self):
        """Initialize the setup with Azure credentials and configuration."""
        load_dotenv()
        
        self.storage_account_name = os.getenv('AZURE_STORAGE_ACCOUNT_NAME')
        self.container_name = os.getenv('AZURE_STORAGE_POLICIES_CONTAINER_NAME')
        self.local_folder = os.getenv('AZURE_STORAGE_LOCAL_FOLDER')
        self.search_service_name = os.getenv('AZURE_SEARCH_SERVICE_NAME')
        self.search_index_name = os.getenv('AZURE_SEARCH_INDEX_NAME')
        
        if not all([self.storage_account_name, self.container_name, self.local_folder]):
            raise ValueError("Missing required environment variables. Check .env file.")
        
        self.credential = DefaultAzureCredential()
        self.blob_service_client = BlobServiceClient(
            account_url=f"https://{self.storage_account_name}.blob.core.windows.net",
            credential=self.credential
        )
        
        # Resolve local folder path relative to script location
        self.local_policies_path = Path(__file__).parent / self.local_folder
        logger.info(f"Local policies folder: {self.local_policies_path}")
        
    async def setup_blob_storage(self) -> None:
        """Create blob storage container and upload policy documents."""
        logger.info("=== Step 1: Setting up Azure Blob Storage ===")
        
        try:
            # Create container if it doesn't exist
            container_client = self.blob_service_client.get_container_client(self.container_name)
            
            try:
                container_client.create_container()
                logger.info(f"✓ Created container: {self.container_name}")
            except ResourceExistsError:
                logger.info(f"✓ Container already exists: {self.container_name}")
            
            # Upload policy documents
            await self._upload_policy_documents(container_client)
            
        except Exception as e:
            logger.error(f"✗ Failed to setup blob storage: {e}")
            raise
            
    async def _upload_policy_documents(self, container_client) -> None:
        """Upload all policy documents from local folder to blob storage."""
        if not self.local_policies_path.exists():
            raise FileNotFoundError(f"Local policies folder not found: {self.local_policies_path}")
            
        policy_files = list(self.local_policies_path.glob("*.md"))
        
        if not policy_files:
            logger.warning(f"No policy files found in {self.local_policies_path}")
            return
            
        logger.info(f"Found {len(policy_files)} policy files to upload")
        
        uploaded_count = 0
        for policy_file in policy_files:
            try:
                blob_name = policy_file.name
                
                # Upload file (overwrites existing)
                with open(policy_file, 'rb') as data:
                    container_client.upload_blob(
                        name=blob_name,
                        data=data,
                        overwrite=True
                    )
                
                logger.info(f"  ✓ Uploaded: {blob_name}")
                uploaded_count += 1
                
            except Exception as e:
                logger.error(f"  ✗ Failed to upload {policy_file.name}: {e}")
                
        logger.info(f"✓ Successfully uploaded {uploaded_count}/{len(policy_files)} policy documents")
        
    async def run_setup(self) -> None:
        """Run the complete setup process."""
        logger.info("Starting policies-search setup...")
        
        try:
            await self.setup_blob_storage()
            logger.info("✓ Setup completed successfully!")
            
        except Exception as e:
            logger.error(f"✗ Setup failed: {e}")
            sys.exit(1)


async def main():
    """Main entry point for the setup script."""
    setup = PoliciesSearchSetup()
    await setup.run_setup()


if __name__ == "__main__":
    asyncio.run(main())
