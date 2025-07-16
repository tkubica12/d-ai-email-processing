"""
Main entry point for the submission-trigger service.

This service monitors document processing events and maintains a projection
of submission status, emitting completion events when all documents are processed.
"""
import asyncio
import logging
import signal
from typing import Optional

from config import AppConfig, setup_logging
from change_feed_processor import SubmissionTriggerProcessor


class SubmissionTriggerService:
    """
    Main service class for the submission-trigger service.
    
    This service initializes and manages the change feed processor
    that tracks document processing status.
    """
    
    def __init__(self):
        """Initialize the submission trigger service."""
        self.config: Optional[AppConfig] = None
        self.processor: Optional[SubmissionTriggerProcessor] = None
        self.logger = logging.getLogger(__name__)
        self.shutdown_event = asyncio.Event()
        
    async def initialize(self) -> None:
        """
        Initialize the service components.
        
        Raises:
            Exception: If initialization fails
        """
        try:
            # Load configuration
            self.config = AppConfig.from_env()
            
            # Setup logging
            setup_logging(self.config.logging)
            
            # Initialize processor
            self.processor = SubmissionTriggerProcessor(self.config)
            await self.processor.initialize()
            
            self.logger.info("Submission trigger service initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize submission trigger service: {e}")
            raise
    
    async def start(self) -> None:
        """
        Start the submission trigger service.
        
        This method starts the change feed processor and handles
        graceful shutdown on SIGINT and SIGTERM.
        """
        try:
            self.logger.info("Starting submission trigger service...")
            
            # Setup signal handlers for graceful shutdown
            def signal_handler(signum, frame):
                self.logger.info(f"Received signal {signum}, initiating shutdown...")
                self.shutdown_event.set()
            
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
            
            # Start processing in a task
            process_task = asyncio.create_task(self.processor.start_processing())
            
            # Wait for shutdown signal
            await self.shutdown_event.wait()
            
            # Cancel processing task
            process_task.cancel()
            
            try:
                await process_task
            except asyncio.CancelledError:
                self.logger.info("Processing task cancelled")
            
            self.logger.info("Submission trigger service stopped")
            
        except Exception as e:
            self.logger.error(f"Error in submission trigger service: {e}")
            raise
    
    async def close(self) -> None:
        """
        Close the service and clean up resources.
        """
        if self.processor:
            await self.processor.close()
        
        self.logger.info("Submission trigger service closed")


async def main():
    """
    Main entry point for the submission-trigger service.
    """
    service = SubmissionTriggerService()
    
    try:
        await service.initialize()
        await service.start()
    except KeyboardInterrupt:
        logging.info("Received keyboard interrupt")
    except Exception as e:
        logging.error(f"Service error: {e}")
        raise
    finally:
        await service.close()


if __name__ == "__main__":
    asyncio.run(main())
