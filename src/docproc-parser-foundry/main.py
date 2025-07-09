"""
Document Parser Foundry Service - Cosmos DB Change Feed Processor

This service processes documents using Azure Document Intelligence by listening to
Cosmos DB Change Feed for DocumentUploadedEvent events. It extracts content from
documents and stores the results in the documents container.
"""

import asyncio
import logging
from typing import NoReturn

from config import AppConfig, setup_logging


async def main() -> NoReturn:
    """
    Main entry point for the Document Parser Foundry service.
    
    Initializes configuration, sets up logging, and starts the Change Feed processor.
    """
    # Load configuration
    try:
        config = AppConfig.from_env()
    except ValueError as e:
        print(f"Configuration error: {e}")
        raise
    
    # Setup logging
    setup_logging(config.logging)
    logger = logging.getLogger(__name__)
    
    logger.info("Starting Document Parser Foundry service")
    logger.info(f"Cosmos DB Endpoint: {config.cosmos_db.endpoint}")
    logger.info(f"Document Intelligence Endpoint: {config.document_intelligence.endpoint}")
    
    # TODO: Initialize Change Feed processor
    # TODO: Start processing DocumentUploadedEvent events
    
    logger.info("Document Parser Foundry service started successfully")
    
    # Keep the service running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Received shutdown signal, stopping service...")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
