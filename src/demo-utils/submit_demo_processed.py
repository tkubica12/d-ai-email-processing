#!/usr/bin/env python3
"""
Demo script to send a processed submission message to Service Bus.

This script sends a sample processed submission message to the configured
Service Bus topic for testing purposes.
"""

import os
import sys
import json
import logging

from azure.servicebus import ServiceBusClient, ServiceBusMessage
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Remap Azure SDK INFO logs to DEBUG
logging.getLogger('azure').setLevel(logging.WARNING)
logging.getLogger('azure.core').setLevel(logging.WARNING)
logging.getLogger('azure.servicebus').setLevel(logging.WARNING)


class ProcessedSubmissionSender:
    """
    Sends a demo processed submission message to Service Bus.
    """
    
    def __init__(self):
        """Initialize the sender with Azure clients and configuration."""
        self.service_bus_fqdn = os.getenv("AZURE_SERVICE_BUS_FQDN")
        self.processed_topic = os.getenv("AZURE_SERVICE_BUS_PROCESSED_TOPIC_NAME", "processed-submissions")
        
        self._validate_configuration()
        self._initialize_azure_clients()
    
    def _validate_configuration(self) -> None:
        """Validate that all required environment variables are set."""
        required_vars = {
            "AZURE_SERVICE_BUS_FQDN": self.service_bus_fqdn,
            "AZURE_SERVICE_BUS_PROCESSED_TOPIC_NAME": self.processed_topic,
        }
        
        missing_vars = [var for var, value in required_vars.items() if not value]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    def _initialize_azure_clients(self) -> None:
        """Initialize Azure service clients using DefaultAzureCredential."""
        try:
            credential = DefaultAzureCredential()
            
            # Initialize Service Bus Client
            self.service_bus_client = ServiceBusClient(
                fully_qualified_namespace=self.service_bus_fqdn,
                credential=credential
            )
            
            logger.info("Azure Service Bus client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Azure clients: {e}")
            raise
    
    def send_processed_message(self) -> None:
        """
        Send a demo processed submission message to Service Bus.
        
        Raises:
            Exception: If message sending fails
        """
        # Create the demo message payload
        message_payload = {
            "submissionId": "123e4567-e89b-12d3-a456-426614174000",
            "userId": "admin@tkubica.net",
            "submittedAt": "2025-07-07T14:30:00.123456Z",
            "processedAt": "2025-07-07T14:35:00.123456Z",
            "results": "Dear user, we have successfully processed your submission. The attached documents have been analyzed and classified. Here are the key findings:"
        }
        
        try:
            # Convert to JSON string
            message_body = json.dumps(message_payload, indent=2)
            
            # Create Service Bus message
            message = ServiceBusMessage(message_body)
            
            # Send message
            with self.service_bus_client.get_topic_sender(topic_name=self.processed_topic) as sender:
                sender.send_messages(message)
            
            logger.info(f"Successfully sent processed submission message to topic '{self.processed_topic}'")
            logger.debug(f"Message content: {message_body}")
            
        except Exception as e:
            logger.error(f"Failed to send processed submission message: {e}")
            raise


def main():
    """Main entry point for the demo script."""
    try:
        sender = ProcessedSubmissionSender()
        sender.send_processed_message()
        
        print("\n" + "="*60)
        print("PROCESSED SUBMISSION MESSAGE SENT")
        print("="*60)
        print("Successfully sent demo processed submission message to Service Bus")
        print(f"Topic: {sender.processed_topic}")
        print(f"Service Bus: {sender.service_bus_fqdn}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Fatal error in demo script: {e}", exc_info=True)
        print(f"\nFatal error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
