"""
Main entry point for the docproc-search-indexer service.

This service listens to DocumentContentExtractedEvent events from the Cosmos DB
Change Feed and processes them for Azure AI Search indexing.
"""

import asyncio
import logging
import signal
import sys
from typing import Optional

from config import AppConfig, setup_logging
from change_feed_processor import ChangeFeedProcessor


class SearchIndexerService:
    """
    Main service class for the document search indexer.
    
    This service processes DocumentContentExtractedEvent events and
    indexes document content into Azure AI Search.
    """
    
    def __init__(self):
        """Initialize the search indexer service."""
        self.config: Optional[AppConfig] = None
        self.processor: Optional[ChangeFeedProcessor] = None
        self.logger = logging.getLogger(__name__)
        self.shutdown_event = asyncio.Event()
    
    async def initialize(self) -> None:
        """
        Initialize the service configuration and processor.
        
        Raises:
            Exception: If service initialization fails
        """
        try:
            # Load configuration
            self.config = AppConfig.from_env()
            
            # Set up logging
            setup_logging(self.config.logging)
            
            self.logger.info("Starting docproc-search-indexer service")
            self.logger.info(f"Configuration loaded successfully")
            
            # Initialize the Change Feed processor
            self.processor = ChangeFeedProcessor(self.config)
            await self.processor.initialize()
            
            self.logger.info("Service initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize service: {str(e)}")
            raise
    
    async def run(self) -> None:
        """
        Run the service main loop.
        
        This method starts the Change Feed processor and handles shutdown signals.
        """
        try:
            # Set up signal handlers for graceful shutdown
            def signal_handler(signum, frame):
                self.logger.info(f"Received signal {signum}, initiating shutdown...")
                self.shutdown_event.set()
            
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
            
            # Start the processor
            processor_task = asyncio.create_task(self.processor.start_processing())
            
            # Wait for shutdown signal
            await self.shutdown_event.wait()
            
            self.logger.info("Shutdown signal received, stopping service...")
            
            # Cancel the processor task
            processor_task.cancel()
            
            try:
                await processor_task
            except asyncio.CancelledError:
                self.logger.info("Processor task cancelled")
            
        except Exception as e:
            self.logger.error(f"Error in service main loop: {str(e)}")
            raise
    
    async def shutdown(self) -> None:
        """
        Gracefully shutdown the service.
        """
        self.logger.info("Shutting down service...")
        
        if self.processor:
            await self.processor.close()
        
        self.logger.info("Service shutdown complete")


async def main():
    """
    Main entry point for the service.
    """
    service = SearchIndexerService()
    
    try:
        await service.initialize()
        await service.run()
    except KeyboardInterrupt:
        print("\nService interrupted by user")
    except Exception as e:
        print(f"Service failed: {str(e)}")
        sys.exit(1)
    finally:
        await service.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
