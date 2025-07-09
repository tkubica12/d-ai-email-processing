"""
Document Parser Foundry Service - Cosmos DB Change Feed Processor

This service processes documents using Azure Document Intelligence by listening to
Cosmos DB Change Feed for DocumentUploadedEvent events. It extracts content from
documents and stores the results in the documents container.
"""

import asyncio
import logging
import signal
from typing import NoReturn

from config import AppConfig, setup_logging
from change_feed_processor import ChangeFeedProcessor


class ServiceRunner:
    """
    Main service runner that manages the Change Feed processor lifecycle.
    """
    
    def __init__(self):
        self.processor: ChangeFeedProcessor = None
        self.shutdown_event = asyncio.Event()
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler():
            logging.getLogger(__name__).info("Received shutdown signal")
            self.shutdown_event.set()
        
        # Handle SIGTERM and SIGINT for graceful shutdown
        signal.signal(signal.SIGTERM, lambda s, f: signal_handler())
        signal.signal(signal.SIGINT, lambda s, f: signal_handler())
    
    async def start(self) -> NoReturn:
        """
        Start the Document Parser Foundry service.
        
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
        logger.info(f"Events Container: {config.cosmos_db.events_container_name}")
        logger.info(f"Documents Container: {config.cosmos_db.documents_container_name}")
        logger.info(f"Document Intelligence Endpoint: {config.document_intelligence.endpoint}")
        
        # Setup signal handlers
        self.setup_signal_handlers()
        
        # Initialize Change Feed processor
        self.processor = ChangeFeedProcessor(config)
        
        try:
            await self.processor.initialize()
            logger.info("Document Parser Foundry service started successfully")
            
            # Start processing in background task
            processing_task = asyncio.create_task(self.processor.start_processing())
            
            # Wait for shutdown signal
            await self.shutdown_event.wait()
            
            logger.info("Shutdown signal received, stopping service...")
            processing_task.cancel()
            
            try:
                await processing_task
            except asyncio.CancelledError:
                logger.info("Processing task cancelled")
            
        except Exception as e:
            logger.error(f"Service error: {e}")
            raise
        finally:
            if self.processor:
                await self.processor.close()
            logger.info("Document Parser Foundry service stopped")


async def main() -> NoReturn:
    """
    Main entry point for the Document Parser Foundry service.
    """
    runner = ServiceRunner()
    await runner.start()


if __name__ == "__main__":
    asyncio.run(main())
