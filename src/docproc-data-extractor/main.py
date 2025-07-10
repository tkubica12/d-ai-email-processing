"""
Document Data Extractor Service - Cosmos DB Change Feed Processor

This service processes document data extraction by listening to Cosmos DB Change Feed for
DocumentContentExtractedEvent events. It extracts structured data from documents using OpenAI API and 
updates document records with extracted data.
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
            self.shutdown_event.set()
        
        # Handle SIGTERM and SIGINT for graceful shutdown
        signal.signal(signal.SIGTERM, lambda s, f: signal_handler())
        signal.signal(signal.SIGINT, lambda s, f: signal_handler())
    
    async def start(self) -> NoReturn:
        """
        Start the Document Data Extractor service.
        
        Initializes configuration, sets up logging, and starts the Change Feed processor.
        """
        # Load configuration
        try:
            config = AppConfig.from_env()
        except ValueError as e:
            print(f"Configuration error: {e}")
            exit(1)
        
        # Setup logging
        setup_logging(config.logging)
        logger = logging.getLogger(__name__)
        
        logger.info("Starting Document Data Extractor service")
        logger.info(f"Cosmos DB Endpoint: {config.cosmos_db.endpoint}")
        logger.info(f"Events Container: {config.cosmos_db.events_container_name}")
        
        # Setup signal handlers
        self.setup_signal_handlers()
        
        # Initialize and start the processor
        try:
            self.processor = ChangeFeedProcessor(config)
            await self.processor.initialize()
            
            # Start processing in background
            processing_task = asyncio.create_task(self.processor.start_processing())
            
            # Wait for shutdown signal
            await self.shutdown_event.wait()
            
            logger.info("Shutdown signal received, stopping service...")
            
            # Cancel processing task
            processing_task.cancel()
            
            try:
                await processing_task
            except asyncio.CancelledError:
                pass
            
            # Close processor
            await self.processor.close()
            
            logger.info("Document Data Extractor service stopped")
            
        except Exception as e:
            logger.error(f"Error starting service: {e}")
            exit(1)


async def main() -> NoReturn:
    """
    Main entry point for the Document Data Extractor service.
    """
    runner = ServiceRunner()
    await runner.start()


if __name__ == "__main__":
    asyncio.run(main())
