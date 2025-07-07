"""
Configuration management for the submission-intake service.

This module provides centralized configuration loading and validation
for the submission-intake service, including environment variables
and logging setup.
"""

import logging
import os
from typing import Optional

from pydantic import BaseModel, Field, validator
from dotenv import load_dotenv


class ServiceBusConfig(BaseModel):
    """Configuration for Azure Service Bus connection."""
    
    fqdn: str = Field(
        ...,
        description="Service Bus namespace FQDN",
        example="sb-email-dev-vwyh.servicebus.windows.net"
    )
    
    topic_name: str = Field(
        ...,
        description="Service Bus topic name",
        example="new-submissions"
    )
    
    subscription_name: str = Field(
        ...,
        description="Service Bus subscription name",
        example="submission-intake"
    )


class CosmosDBConfig(BaseModel):
    """Configuration for Azure Cosmos DB connection."""
    
    endpoint: str = Field(
        ...,
        description="Cosmos DB account endpoint URL",
        example="https://cosmos-email-dev-vwyh.documents.azure.com:443/"
    )
    
    database_name: str = Field(
        ...,
        description="Cosmos DB database name",
        example="email-processing"
    )
    
    submissions_container_name: str = Field(
        ...,
        description="Cosmos DB submissions container name",
        example="submissions"
    )
    
    events_container_name: str = Field(
        ...,
        description="Cosmos DB events container name",
        example="events"
    )


class LoggingConfig(BaseModel):
    """Configuration for application logging."""
    
    level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
        example="INFO"
    )
    
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log message format string"
    )
    
    date_format: str = Field(
        default="%Y-%m-%d %H:%M:%S",
        description="Date format for log messages"
    )
    
    @validator('level')
    def validate_log_level(cls, v):
        """Validate that log level is valid."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of: {valid_levels}")
        return v.upper()


class AppConfig(BaseModel):
    """Main application configuration."""
    
    service_bus: ServiceBusConfig
    cosmos_db: CosmosDBConfig
    logging: LoggingConfig
    
    @classmethod
    def from_env(cls) -> 'AppConfig':
        """
        Load configuration from environment variables.
        
        Returns:
            AppConfig: Configured application settings
            
        Raises:
            ValueError: If required environment variables are missing
        """
        # Load environment variables from .env file
        load_dotenv()
        
        # Extract Service Bus configuration
        service_bus_fqdn = os.getenv('AZURE_SERVICE_BUS_FQDN')
        topic_name = os.getenv('AZURE_SERVICE_BUS_TOPIC_NAME')
        subscription_name = os.getenv('AZURE_SERVICE_BUS_SUBSCRIPTION_NAME')
        
        if not all([service_bus_fqdn, topic_name, subscription_name]):
            raise ValueError(
                "Missing required Service Bus configuration. "
                "Check AZURE_SERVICE_BUS_FQDN, AZURE_SERVICE_BUS_TOPIC_NAME, "
                "and AZURE_SERVICE_BUS_SUBSCRIPTION_NAME environment variables."
            )
        
        # Extract Cosmos DB configuration
        cosmos_db_endpoint = os.getenv('AZURE_COSMOS_DB_ENDPOINT')
        database_name = os.getenv('AZURE_COSMOS_DB_DATABASE_NAME')
        submissions_container_name = os.getenv('AZURE_COSMOS_DB_SUBMISSIONS_CONTAINER_NAME')
        events_container_name = os.getenv('AZURE_COSMOS_DB_EVENTS_CONTAINER_NAME')
        
        if not all([cosmos_db_endpoint, database_name, submissions_container_name, events_container_name]):
            raise ValueError(
                "Missing required Cosmos DB configuration. "
                "Check AZURE_COSMOS_DB_ENDPOINT, AZURE_COSMOS_DB_DATABASE_NAME, "
                "AZURE_COSMOS_DB_SUBMISSIONS_CONTAINER_NAME, and AZURE_COSMOS_DB_EVENTS_CONTAINER_NAME environment variables."
            )
        
        # Extract logging configuration
        log_level = os.getenv('LOG_LEVEL', 'INFO')
        
        return cls(
            service_bus=ServiceBusConfig(
                fqdn=service_bus_fqdn,
                topic_name=topic_name,
                subscription_name=subscription_name
            ),
            cosmos_db=CosmosDBConfig(
                endpoint=cosmos_db_endpoint,
                database_name=database_name,
                submissions_container_name=submissions_container_name,
                events_container_name=events_container_name
            ),
            logging=LoggingConfig(
                level=log_level
            )
        )


def setup_logging(config: LoggingConfig) -> None:
    """
    Configure logging for the application.
    
    Sets up structured logging with appropriate levels and remaps Azure SDK
    INFO logs to DEBUG level to reduce noise.
    
    Args:
        config: Logging configuration settings
    """
    logging.basicConfig(
        level=getattr(logging, config.level),
        format=config.format,
        datefmt=config.date_format
    )
    
    # Remap Azure SDK INFO logs to WARNING to reduce noise
    azure_loggers = [
        'azure.servicebus',
        'azure.identity',
        'azure.core',
        'azure.servicebus._pyamqp'
    ]
    
    for logger_name in azure_loggers:
        azure_logger = logging.getLogger(logger_name)
        azure_logger.setLevel(logging.WARNING)
    
    # Log configuration loaded successfully
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured with level: {config.level}")
