"""
Submission Intake Service - Service Bus Worker

This service listens to Azure Service Bus topic 'new-submissions' and processes
incoming submission messages in an async manner. It receives messages, logs them,
and acknowledges them to prevent redelivery.
"""

import asyncio
import json
import logging
from typing import NoReturn

from azure.identity.aio import DefaultAzureCredential
from azure.servicebus.aio import ServiceBusClient
from azure.servicebus import ServiceBusMessage
from pydantic import ValidationError

from config import AppConfig, setup_logging
from models import SubmissionMessage
from storage import CosmosDBStorage


async def process_message(message: ServiceBusMessage, storage: CosmosDBStorage) -> None:
    """
    Process a Service Bus message containing submission data.
    
    Args:
        message: The Service Bus message to process
        storage: Cosmos DB storage client for persisting submissions
        
    Raises:
        ValidationError: If the message content doesn't match expected schema
        Exception: For any other processing errors
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Parse message body as JSON
        message_body = str(message)
        logger.info(f"Received message: {message.message_id}")
        logger.debug(f"Message body: {message_body}")
        
        # Validate message content against Pydantic model
        message_data = json.loads(message_body)
        submission_message = SubmissionMessage(**message_data)
        
        logger.info(f"Processing submission: {submission_message.submissionId} "
                   f"from user: {submission_message.userId} "
                   f"with {len(submission_message.documentUrls)} documents")
        
        # Store submission in Cosmos DB
        submission_doc = await storage.store_submission(submission_message)
        
        logger.info(f"Successfully stored submission: {submission_doc.submissionId} "
                   f"for user: {submission_doc.userId} "
                   f"with {len(submission_doc.documents)} documents")
        
        # Create and store SubmissionCreatedEvent
        submission_created_event = await storage.create_submission_created_event(submission_message)
        
        logger.info(f"Successfully created SubmissionCreatedEvent: {submission_created_event.id} "
                   f"for submission: {submission_created_event.submissionId}")
        
        # Create and store DocumentUploadedEvent for each document
        document_uploaded_events = await storage.create_document_uploaded_events(submission_message)
        
        logger.info(f"Successfully created {len(document_uploaded_events)} DocumentUploadedEvent(s) "
                   f"for submission: {submission_message.submissionId}")
        
        # Log submission details
        logger.info(f"Submission details: ID={submission_message.submissionId}, "
                   f"User={submission_message.userId}, "
                   f"Submitted={submission_message.submittedAt}, "
                   f"Documents={len(submission_message.documentUrls)}")
        
        for i, doc_url in enumerate(submission_message.documentUrls, 1):
            logger.debug(f"Document {i}: {doc_url}")
            
    except ValidationError as e:
        logger.error(f"Message validation failed for message {message.message_id}: {e}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse message {message.message_id} as JSON: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing message {message.message_id}: {e}")
        raise


async def listen_for_messages(config: AppConfig) -> NoReturn:
    """
    Main message processing loop that listens to Service Bus messages.
    
    This function runs indefinitely, processing messages from the Service Bus
    topic subscription. Messages are acknowledged after successful processing
    to prevent redelivery.
    
    Args:
        config: Application configuration containing Service Bus settings
    
    Raises:
        Exception: If critical errors occur that prevent message processing
    """
    logger = logging.getLogger(__name__)
    
    logger.info(f"Starting Service Bus listener for topic '{config.service_bus.topic_name}' "
               f"subscription '{config.service_bus.subscription_name}' on '{config.service_bus.fqdn}'")
    
    # Initialize Cosmos DB storage
    storage = CosmosDBStorage(config.cosmos_db)
    await storage.initialize()
    
    try:
        # Initialize Azure credentials and Service Bus client
        credential = DefaultAzureCredential()
        
        async with ServiceBusClient(
            fully_qualified_namespace=config.service_bus.fqdn,
            credential=credential
        ) as servicebus_client:
            
            async with servicebus_client.get_subscription_receiver(
                topic_name=config.service_bus.topic_name,
                subscription_name=config.service_bus.subscription_name
            ) as receiver:
                
                logger.info("Service Bus receiver started, waiting for messages...")
                
                async for message in receiver:
                    try:
                        # Process the message with Cosmos DB storage
                        await process_message(message, storage)
                        
                        # Acknowledge the message after successful processing
                        await receiver.complete_message(message)
                        logger.info(f"Message {message.message_id} processed and acknowledged")
                        
                    except Exception as e:
                        logger.error(f"Failed to process message {message.message_id}: {e}")
                        # Let the message be redelivered by not acknowledging it
                        await receiver.abandon_message(message)
                        logger.warning(f"Message {message.message_id} abandoned for redelivery")
    
    finally:
        # Ensure Cosmos DB client is properly closed
        await storage.close()


async def main() -> None:
    """
    Main entry point for the submission-intake service.
    
    Loads configuration, sets up logging, and starts the message
    processing loop.
    """
    try:
        # Load configuration from environment variables
        config = AppConfig.from_env()
        
        # Setup logging with configuration
        setup_logging(config.logging)
        logger = logging.getLogger(__name__)
        
        logger.info("Starting Submission Intake Service")
        logger.info(f"Service Bus: {config.service_bus.fqdn}")
        logger.info(f"Topic: {config.service_bus.topic_name}")
        logger.info(f"Subscription: {config.service_bus.subscription_name}")
        
        await listen_for_messages(config)
        
    except KeyboardInterrupt:
        logger = logging.getLogger(__name__)
        logger.info("Service interrupted by user")
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.critical(f"Critical error in main loop: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
