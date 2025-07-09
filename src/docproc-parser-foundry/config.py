"""
Configuration management for the docproc-parser-foundry service.

This module provides centralized configuration loading and validation
for the document processing service using Azure Document Intelligence,
including environment variables and logging setup.
"""

import logging
import os
from typing import Optional

from pydantic import BaseModel, Field, validator
from dotenv import load_dotenv


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
    
    events_container_name: str = Field(
        ...,
        description="Cosmos DB events container name",
        example="events"
    )
    
    documents_container_name: str = Field(
        ...,
        description="Cosmos DB documents container name",
        example="documents"
    )


class DocumentIntelligenceConfig(BaseModel):
    """Configuration for Azure Document Intelligence service."""
    
    endpoint: str = Field(
        ...,
        description="Document Intelligence service endpoint URL",
        example="https://email-dev-vwyh-docintel.cognitiveservices.azure.com/"
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
    
    cosmos_db: CosmosDBConfig
    document_intelligence: DocumentIntelligenceConfig
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
        
        # Extract Cosmos DB configuration
        cosmos_db_endpoint = os.getenv('AZURE_COSMOS_DB_ENDPOINT')
        database_name = os.getenv('AZURE_COSMOS_DB_DATABASE_NAME')
        events_container_name = os.getenv('AZURE_COSMOS_DB_EVENTS_CONTAINER_NAME')
        documents_container_name = os.getenv('AZURE_COSMOS_DB_DOCUMENTS_CONTAINER_NAME')
        
        if not all([cosmos_db_endpoint, database_name, events_container_name, documents_container_name]):
            raise ValueError(
                "Missing required Cosmos DB configuration. "
                "Check AZURE_COSMOS_DB_ENDPOINT, AZURE_COSMOS_DB_DATABASE_NAME, "
                "AZURE_COSMOS_DB_EVENTS_CONTAINER_NAME, "
                "and AZURE_COSMOS_DB_DOCUMENTS_CONTAINER_NAME environment variables."
            )
        
        # Extract Document Intelligence configuration
        document_intelligence_endpoint = os.getenv('AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT')
        
        if not document_intelligence_endpoint:
            raise ValueError(
                "Missing required Document Intelligence configuration. "
                "Check AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT environment variable."
            )
        
        # Extract logging configuration
        log_level = os.getenv('LOG_LEVEL', 'INFO')
        
        return cls(
            cosmos_db=CosmosDBConfig(
                endpoint=cosmos_db_endpoint,
                database_name=database_name,
                events_container_name=events_container_name,
                documents_container_name=documents_container_name
            ),
            document_intelligence=DocumentIntelligenceConfig(
                endpoint=document_intelligence_endpoint
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
        'azure.cosmos',
        'azure.ai.formrecognizer',
        'azure.ai.documentintelligence',
        'azure.identity',
        'azure.core'
    ]
    
    for logger_name in azure_loggers:
        azure_logger = logging.getLogger(logger_name)
        azure_logger.setLevel(logging.WARNING)
    
    # Log configuration loaded successfully
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured with level: {config.level}")
