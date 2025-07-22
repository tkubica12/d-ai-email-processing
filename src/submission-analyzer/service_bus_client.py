"""
Azure Service Bus client for sending processed submission messages.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from azure.servicebus import ServiceBusClient, ServiceBusMessage
from azure.identity import DefaultAzureCredential

from config import ServiceBusConfig


class SubmissionServiceBusClient:
    """
    Azure Service Bus client for sending processed submission messages.
    
    This client sends analysis results to the processed-submissions topic
    for further processing by downstream services.
    """
    
    def __init__(self, config: ServiceBusConfig):
        """
        Initialize the Service Bus client.
        
        Args:
            config: Service Bus configuration
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Create Service Bus client with managed identity
        credential = DefaultAzureCredential()
        self.client = ServiceBusClient(
            fully_qualified_namespace=config.fqdn,
            credential=credential
        )
        
        self.logger.info(f"Service Bus client initialized for namespace: {config.fqdn}")
    
    def send_analysis_complete_message(
        self,
        submission_id: str,
        user_id: str,
        submitted_at: datetime,
        results: str
    ) -> None:
        """
        Send a submission analysis complete message to the Service Bus topic.
        
        Args:
            submission_id: Unique identifier for the submission
            user_id: User who submitted the request
            submitted_at: When the submission was originally created
            results: Analysis results from the AI agent
            
        Raises:
            Exception: If message sending fails
        """
        try:
            processed_at = datetime.now(timezone.utc)
            
            # Create message payload
            message_data = {
                "submissionId": submission_id,
                "userId": user_id,
                "submittedAt": submitted_at.isoformat(),
                "processedAt": processed_at.isoformat(),
                "results": results
            }
            
            # Convert to JSON
            message_json = json.dumps(message_data)
            
            # Create Service Bus message
            message = ServiceBusMessage(
                body=message_json,
                content_type="application/json",
                subject="SubmissionAnalysisComplete"
            )
            
            # Send message
            with self.client.get_topic_sender(topic_name=self.config.topic_name) as sender:
                sender.send_messages(message)
            
            self.logger.info(f"Sent analysis complete message for submission {submission_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to send Service Bus message for submission {submission_id}: {e}")
            raise
    
    def close(self):
        """Close the Service Bus client."""
        try:
            self.client.close()
            self.logger.info("Service Bus client closed")
        except Exception as e:
            self.logger.error(f"Error closing Service Bus client: {e}")
