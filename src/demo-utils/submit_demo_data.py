#!/usr/bin/env python3
"""
Demo script to submit data from demo-submissions folders.

This script mimics the client-web functionality by:
1. Reading all subfolders in DEMO_SUBMISSIONS_BASE_FOLDER
2. For each subfolder, uploading all files including body.txt to Azure Blob Storage
3. Emitting a Service Bus message with the document URLs

The script uses the same Azure services and data structures as the client-web application.
"""

import os
import uuid
import asyncio
import logging
from pathlib import Path
from datetime import datetime, UTC
from typing import List, Dict, Optional

from azure.storage.blob import BlobServiceClient
from azure.servicebus import ServiceBusClient, ServiceBusMessage
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

from models import SubmissionMessage

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Remap Azure SDK INFO logs to WARNING
logging.getLogger('azure').setLevel(logging.WARNING)
logging.getLogger('azure.core').setLevel(logging.WARNING)
logging.getLogger('azure.storage').setLevel(logging.WARNING)
logging.getLogger('azure.servicebus').setLevel(logging.WARNING)


class DemoSubmissionProcessor:
    """
    Processes demo submissions by uploading files to Azure Blob Storage
    and sending messages to Service Bus.
    """
    
    def __init__(self):
        """Initialize the processor with Azure clients and configuration."""
        self.storage_account_name = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
        self.service_bus_fqdn = os.getenv("AZURE_SERVICE_BUS_FQDN")
        self.service_bus_topic = os.getenv("AZURE_SERVICE_BUS_TOPIC_NAME", "new-submissions")
        self.demo_email = os.getenv("DEMO_SUBMISSIONS_EMAIL")
        self.demo_base_folder = os.getenv("DEMO_SUBMISSIONS_BASE_FOLDER", "../../demo-submissions")
        
        self._validate_configuration()
        self._initialize_azure_clients()
    
    def _validate_configuration(self) -> None:
        """Validate that all required environment variables are set."""
        required_vars = {
            "AZURE_STORAGE_ACCOUNT_NAME": self.storage_account_name,
            "AZURE_SERVICE_BUS_FQDN": self.service_bus_fqdn,
            "DEMO_SUBMISSIONS_EMAIL": self.demo_email,
        }
        
        missing_vars = [var for var, value in required_vars.items() if not value]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        # Validate demo base folder exists
        demo_path = Path(self.demo_base_folder)
        if not demo_path.exists():
            raise ValueError(f"Demo submissions folder not found: {demo_path.absolute()}")
    
    def _initialize_azure_clients(self) -> None:
        """Initialize Azure service clients using DefaultAzureCredential."""
        try:
            credential = DefaultAzureCredential()
            
            # Initialize Blob Service Client
            self.blob_client = BlobServiceClient(
                account_url=f"https://{self.storage_account_name}.blob.core.windows.net",
                credential=credential
            )
            
            # Initialize Service Bus Client
            self.service_bus_client = ServiceBusClient(
                fully_qualified_namespace=self.service_bus_fqdn,
                credential=credential
            )
            
            logger.info("Azure clients initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Azure clients: {e}")
            raise
    
    def get_demo_subfolders(self) -> List[Path]:
        """
        Get all subfolders in the demo submissions directory.
        
        Returns:
            List of Path objects representing demo submission folders
        """
        demo_path = Path(self.demo_base_folder)
        subfolders = [folder for folder in demo_path.iterdir() if folder.is_dir()]
        
        logger.info(f"Found {len(subfolders)} demo submission folders")
        return subfolders
    
    def read_message_body(self, folder_path: Path) -> str:
        """
        Read the message body from body.txt file in the folder.
        
        Args:
            folder_path: Path to the demo submission folder
            
        Returns:
            Content of the body.txt file
            
        Raises:
            FileNotFoundError: If body.txt is not found
        """
        body_file = folder_path / "body.txt"
        if not body_file.exists():
            raise FileNotFoundError(f"body.txt not found in {folder_path}")
        
        with open(body_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        logger.debug(f"Read message body from {body_file} ({len(content)} characters)")
        return content
    
    def get_attachment_files(self, folder_path: Path) -> List[Path]:
        """
        Get all files in the folder except body.txt (these are attachments).
        
        Args:
            folder_path: Path to the demo submission folder
            
        Returns:
            List of Path objects representing attachment files
        """
        all_files = [f for f in folder_path.iterdir() if f.is_file()]
        attachments = [f for f in all_files if f.name != "body.txt"]
        
        logger.debug(f"Found {len(attachments)} attachment files in {folder_path}")
        return attachments
    
    async def upload_files_to_blob(self, submission_id: str, folder_path: Path) -> List[str]:
        """
        Upload all files from the folder to Azure Blob Storage.
        
        Args:
            submission_id: Unique identifier for the submission
            folder_path: Path to the demo submission folder
            
        Returns:
            List of blob URLs for uploaded files
            
        Raises:
            Exception: If upload fails
        """
        try:
            # Create container for this submission
            container_name = submission_id.lower()
            container_client = self.blob_client.get_container_client(container_name)
            
            # Create container if it doesn't exist
            try:
                container_client.create_container()
                logger.info(f"Created blob container: {container_name}")
            except Exception as e:
                if "ContainerAlreadyExists" not in str(e):
                    logger.error(f"Failed to create container {container_name}: {e}")
                    raise
                logger.info(f"Container {container_name} already exists")
            
            # Get all files to upload
            all_files = [f for f in folder_path.iterdir() if f.is_file()]
            document_urls = []
            
            # Upload each file
            for file_path in all_files:
                filename = file_path.name
                
                # Read file content
                with open(file_path, 'rb') as f:
                    file_content = f.read()
                
                # Upload to blob storage
                blob_client = container_client.get_blob_client(filename)
                blob_client.upload_blob(file_content, overwrite=True)
                
                # Generate blob URL
                blob_url = f"https://{self.storage_account_name}.blob.core.windows.net/{container_name}/{filename}"
                document_urls.append(blob_url)
                
                logger.info(f"Uploaded {filename} to blob storage ({len(file_content)} bytes)")
            
            logger.info(f"Successfully uploaded {len(document_urls)} files for submission {submission_id}")
            return document_urls
            
        except Exception as e:
            logger.error(f"Failed to upload files for submission {submission_id}: {e}")
            raise
    
    async def send_service_bus_message(self, submission_id: str, document_urls: List[str]) -> None:
        """
        Send a Service Bus message for the submission.
        
        Args:
            submission_id: Unique identifier for the submission
            document_urls: List of blob URLs for uploaded documents
            
        Raises:
            Exception: If message sending fails
        """
        try:
            # Create Service Bus message using Pydantic model
            submission_message = SubmissionMessage(
                submissionId=submission_id,
                userId=self.demo_email,
                documentUrls=document_urls,
                submittedAt=datetime.now(UTC)
            )
            
            # Send message to Service Bus
            with self.service_bus_client:
                sender = self.service_bus_client.get_topic_sender(topic_name=self.service_bus_topic)
                
                service_bus_message = ServiceBusMessage(
                    body=submission_message.model_dump_json(),
                    content_type="application/json"
                )
                
                sender.send_messages(service_bus_message)
                sender.close()
                
                logger.info(f"Sent Service Bus message for submission {submission_id}")
                
        except Exception as e:
            logger.error(f"Failed to send Service Bus message for submission {submission_id}: {e}")
            raise
    
    async def process_submission(self, folder_path: Path) -> Dict:
        """
        Process a single demo submission folder.
        
        Args:
            folder_path: Path to the demo submission folder
            
        Returns:
            Dictionary with submission processing results
        """
        submission_id = str(uuid.uuid4())
        folder_name = folder_path.name
        
        logger.info(f"Processing demo submission: {folder_name} (ID: {submission_id})")
        
        try:
            # Read message body
            message_body = self.read_message_body(folder_path)
            
            # Get attachment files
            attachment_files = self.get_attachment_files(folder_path)
            
            # Upload files to blob storage
            document_urls = await self.upload_files_to_blob(submission_id, folder_path)
            
            # Send Service Bus message
            await self.send_service_bus_message(submission_id, document_urls)
            
            result = {
                'submission_id': submission_id,
                'folder_name': folder_name,
                'status': 'success',
                'message_length': len(message_body),
                'attachment_count': len(attachment_files),
                'document_urls': document_urls
            }
            
            logger.info(f"Successfully processed submission {submission_id} from {folder_name}")
            return result
            
        except Exception as e:
            logger.error(f"Error processing submission from {folder_name}: {e}")
            return {
                'submission_id': submission_id,
                'folder_name': folder_name,
                'status': 'error',
                'error_message': str(e)
            }
    
    async def process_all_submissions(self) -> List[Dict]:
        """
        Process all demo submissions from the configured base folder.
        
        Returns:
            List of processing results for each submission
        """
        logger.info("Starting demo submission processing")
        
        # Get all demo subfolders
        demo_folders = self.get_demo_subfolders()
        
        if not demo_folders:
            logger.warning("No demo submission folders found")
            return []
        
        # Process each folder
        results = []
        for folder_path in demo_folders:
            result = await self.process_submission(folder_path)
            results.append(result)
        
        # Summary
        successful = len([r for r in results if r['status'] == 'success'])
        failed = len([r for r in results if r['status'] == 'error'])
        
        logger.info(f"Demo submission processing complete: {successful} successful, {failed} failed")
        
        return results


async def main():
    """Main entry point for the demo script."""
    try:
        processor = DemoSubmissionProcessor()
        results = await processor.process_all_submissions()
        
        # Print summary
        print("\n" + "="*60)
        print("DEMO SUBMISSION PROCESSING SUMMARY")
        print("="*60)
        
        for result in results:
            status_symbol = "✓" if result['status'] == 'success' else "✗"
            print(f"{status_symbol} {result['folder_name']} ({result['submission_id']})")
            
            if result['status'] == 'success':
                print(f"  • Message length: {result['message_length']} characters")
                print(f"  • Attachments: {result['attachment_count']} files")
                print(f"  • Documents uploaded: {len(result['document_urls'])} URLs")
            else:
                print(f"  • Error: {result['error_message']}")
            print()
        
        successful = len([r for r in results if r['status'] == 'success'])
        failed = len([r for r in results if r['status'] == 'error'])
        
        print(f"Total: {len(results)} submissions processed")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        
        if failed > 0:
            print(f"\nCheck logs for details on failed submissions")
            return 1
        
        return 0
        
    except Exception as e:
        logger.error(f"Fatal error in demo script: {e}", exc_info=True)
        print(f"\nFatal error: {e}")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))
