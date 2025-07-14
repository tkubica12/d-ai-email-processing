"""
Configuration management for the docproc-search-indexer service.

This module provides centralized configuration loading and validation
for the search indexing service using Azure AI Search,
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


class TableStorageConfig(BaseModel):
    """Configuration for Azure Table Storage."""
    
    account_name: str = Field(
        ...,
        description="Azure Storage account name",
        example="mystorageaccount"
    )
    
    table_name: str = Field(
        default="continuationtokens",
        description="Table name for storing continuation tokens",
        example="continuationtokens"
    )
    
    enabled: bool = Field(
        default=False,
        description="Enable persistent continuation token storage",
        example=True
    )


class AISearchConfig(BaseModel):
    """Configuration for Azure AI Search."""
    
    service_name: str = Field(
        ...,
        description="Azure AI Search service name",
        example="search-email-dev-vwyh"
    )
    
    index_name: str = Field(
        ...,
        description="Azure AI Search index name for documents",
        example="documents-index"
    )
    
    @property
    def endpoint(self) -> str:
        """Generate the full Azure AI Search endpoint URL."""
        return f"https://{self.service_name}.search.windows.net"


class OpenAIConfig(BaseModel):
    """Configuration for Azure OpenAI embeddings."""
    
    endpoint: str = Field(
        ...,
        description="Azure OpenAI endpoint URL",
        example="https://your-openai-instance.openai.azure.com"
    )
    
    deployment_name: str = Field(
        ...,
        description="Azure OpenAI embedding deployment name",
        example="text-embedding-3-large"
    )
    
    resource_uri: Optional[str] = Field(
        default=None,
        description="Azure OpenAI resource URI for vectorizers",
        example="https://your-openai-instance.openai.azure.com"
    )
    
    api_version: str = Field(
        default="2024-06-01",
        description="Azure OpenAI API version",
        example="2024-06-01"
    )
    
    embedding_dimensions: int = Field(
        default=3072,
        description="Embedding dimensions for text-embedding-3-large",
        example=3072
    )
    
    chunk_size: int = Field(
        default=2000,
        description="Character chunk size for document splitting",
        example=2000
    )
    
    chunk_overlap: int = Field(
        default=200,
        description="Character overlap between chunks",
        example=200
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
    table_storage: TableStorageConfig
    ai_search: AISearchConfig
    openai: OpenAIConfig
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
        
        # Extract Document Intelligence configuration - not needed for search indexer
        
        # Extract Table Storage configuration
        storage_account_name = os.getenv('AZURE_STORAGE_ACCOUNT_NAME')
        table_storage_enabled = os.getenv('AZURE_TABLE_STORAGE_ENABLED', 'false').lower() == 'true'
        
        if table_storage_enabled and not storage_account_name:
            raise ValueError(
                "Missing required Table Storage configuration. "
                "Check AZURE_STORAGE_ACCOUNT_NAME environment variable when table storage is enabled."
            )
        
        # Extract AI Search configuration
        search_service_name = os.getenv('AZURE_SEARCH_SERVICE_NAME')
        search_index_name = os.getenv('AZURE_SEARCH_INDEX_NAME')
        
        if not all([search_service_name, search_index_name]):
            raise ValueError(
                "Missing required AI Search configuration. "
                "Check AZURE_SEARCH_SERVICE_NAME and AZURE_SEARCH_INDEX_NAME environment variables."
            )
        
        # Extract Azure OpenAI configuration
        azure_openai_endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
        azure_openai_resource_uri = os.getenv('AZURE_OPENAI_RESOURCE_URI')
        azure_openai_deployment = os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME')
        
        if not all([azure_openai_endpoint, azure_openai_deployment]):
            raise ValueError(
                "Missing required Azure OpenAI configuration. "
                "Check AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_DEPLOYMENT_NAME environment variables."
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
            table_storage=TableStorageConfig(
                account_name=storage_account_name or "",
                table_name=os.getenv('AZURE_TABLE_STORAGE_TABLE_NAME', 'continuationtokens'),
                enabled=table_storage_enabled
            ),
            ai_search=AISearchConfig(
                service_name=search_service_name,
                index_name=search_index_name
            ),
            openai=OpenAIConfig(
                endpoint=azure_openai_endpoint,
                resource_uri=azure_openai_resource_uri,
                deployment_name=azure_openai_deployment,
                api_version=os.getenv('AZURE_OPENAI_API_VERSION', '2024-06-01'),
                embedding_dimensions=int(os.getenv('AZURE_OPENAI_EMBEDDING_DIMENSIONS', '3072')),
                chunk_size=int(os.getenv('AZURE_OPENAI_CHUNK_SIZE', '2000')),
                chunk_overlap=int(os.getenv('AZURE_OPENAI_CHUNK_OVERLAP', '200'))
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
        'azure.ai.inference',
        'azure.search.documents',
        'azure.identity',
        'azure.core'
    ]
    
    for logger_name in azure_loggers:
        azure_logger = logging.getLogger(logger_name)
        azure_logger.setLevel(logging.WARNING)
    
    # Log configuration loaded successfully
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured with level: {config.level}")
