"""
Configuration management for the submission-analyzer service.

This module provides centralized configuration loading and validation
for the submission analysis service using Azure AI Foundry,
including environment variables and logging setup.
"""

import logging
import os
from typing import Optional

from pydantic import BaseModel, Field, validator
from dotenv import load_dotenv


class CompanyAPIConfig(BaseModel):
    """Configuration for Company APIs integration with autonomous authentication."""
    
    base_url: str = Field(
        default="http://localhost:8003",
        description="Base URL for Company APIs",
        example="http://localhost:8003"
    )


class AISearchConfig(BaseModel):
    """Configuration for Azure AI Search service."""
    
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
    
    connection_id: str = Field(
        ...,
        description="Azure AI Search connection ID in AI Foundry",
        example="/subscriptions/xxx/resourceGroups/xxx/providers/Microsoft.MachineLearningServices/workspaces/xxx/connections/xxx"
    )
    
    @property
    def endpoint(self) -> str:
        """Generate the full Azure AI Search endpoint URL."""
        return f"https://{self.service_name}.search.windows.net"


class AzureAIProjectsConfig(BaseModel):
    """Configuration for Azure AI Projects connection."""
    
    project_endpoint: str = Field(
        ...,
        description="Azure AI Foundry project endpoint URL",
        example="https://my-instance.services.ai.azure.com/api/projects/my-project"
    )
    
    model_deployment_name: str = Field(
        ...,
        description="Model deployment name for the AI agent",
        example="gpt-4.1"
    )
    
    bing_connection_id: str = Field(
        ...,
        description="Bing connection ID for grounding tool",
        example="/subscriptions/xxx/resourceGroups/xxx/providers/Microsoft.CognitiveServices/accounts/xxx"
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
    
    submissions_container_name: str = Field(
        default="submissions",
        description="Cosmos DB submissions container name",
        example="submissions"
    )


class AzureOpenAIConfig(BaseModel):
    """Configuration for Azure OpenAI service."""
    
    endpoint: str = Field(
        ...,
        description="Azure AI Foundry project endpoint URL",
        example="https://my-instance.services.ai.azure.com/api/projects/my-project"
    )
    
    model: str = Field(
        default="gpt-4.1",
        description="Azure OpenAI model to use for analysis",
        example="gpt-4.1"
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


class ServiceBusConfig(BaseModel):
    """Configuration for Azure Service Bus."""
    
    fqdn: str = Field(
        ...,
        description="Azure Service Bus fully qualified domain name",
        example="sb-email-dev-vwyh.servicebus.windows.net"
    )
    
    topic_name: str = Field(
        ...,
        description="Service Bus topic name for processed submissions",
        example="processed-submissions"
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
    
    ai_projects: AzureAIProjectsConfig
    cosmos_db: CosmosDBConfig
    openai: AzureOpenAIConfig
    table_storage: TableStorageConfig
    company_api: CompanyAPIConfig
    logging: LoggingConfig
    search: AISearchConfig
    service_bus: ServiceBusConfig
    pretty_print: bool = Field(
        default=True,
        description="Enable pretty console output for debugging",
        example=True
    )
    
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
        
        # Extract Azure AI Projects configuration
        project_endpoint = os.getenv('AZURE_FOUNDRY_PROJECT_ENDPOINT')
        model_deployment_name = os.getenv('AZURE_OPENAI_MODEL')
        bing_connection_id = os.getenv('BING_CONNECTION_ID')
        
        if not all([project_endpoint, model_deployment_name, bing_connection_id]):
            raise ValueError(
                "Missing required Azure AI Projects configuration. "
                "Check AZURE_FOUNDRY_PROJECT_ENDPOINT, AZURE_OPENAI_MODEL, and BING_CONNECTION_ID environment variables."
            )
        
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
        
        # Extract Azure OpenAI configuration
        azure_openai_endpoint = os.getenv('AZURE_FOUNDRY_PROJECT_ENDPOINT')
        
        if not azure_openai_endpoint:
            raise ValueError(
                "Missing required Azure OpenAI configuration. "
                "Check AZURE_FOUNDRY_PROJECT_ENDPOINT environment variable."
            )
        
        # Extract Table Storage configuration
        storage_account_name = os.getenv('AZURE_STORAGE_ACCOUNT_NAME')
        table_storage_enabled = os.getenv('AZURE_TABLE_STORAGE_ENABLED', 'false').lower() == 'true'
        
        if table_storage_enabled and not storage_account_name:
            raise ValueError(
                "Missing required Table Storage configuration. "
                "Check AZURE_STORAGE_ACCOUNT_NAME environment variable when table storage is enabled."
            )
        
        # Extract logging configuration
        log_level = os.getenv('LOG_LEVEL', 'INFO')
        pretty_print = os.getenv('PRETTY_PRINT', 'true').lower() == 'true'
        
        # Extract AI Search configuration
        search_service_name = os.getenv('AZURE_SEARCH_SERVICE_NAME')
        index_name = os.getenv('AZURE_SEARCH_INDEX_NAME')
        connection_id = os.getenv('AZURE_SEARCH_CONNECTION_ID')
        
        if not all([search_service_name, index_name, connection_id]):
            raise ValueError(
                "Missing required AI Search configuration. "
                "Check AZURE_SEARCH_SERVICE_NAME, AZURE_SEARCH_INDEX_NAME, and AZURE_SEARCH_CONNECTION_ID environment variables."
            )
        
        # Extract Service Bus configuration
        service_bus_fqdn = os.getenv('AZURE_SERVICE_BUS_FQDN')
        service_bus_topic = os.getenv('AZURE_SERVICE_BUS_TOPIC_NAME')
        
        if not all([service_bus_fqdn, service_bus_topic]):
            raise ValueError(
                "Missing required Service Bus configuration. "
                "Check AZURE_SERVICE_BUS_FQDN and AZURE_SERVICE_BUS_TOPIC_NAME environment variables."
            )
        
        return cls(
            ai_projects=AzureAIProjectsConfig(
                project_endpoint=project_endpoint,
                model_deployment_name=model_deployment_name,
                bing_connection_id=bing_connection_id
            ),
            cosmos_db=CosmosDBConfig(
                endpoint=cosmos_db_endpoint,
                database_name=database_name,
                events_container_name=events_container_name,
                documents_container_name=documents_container_name,
                submissions_container_name=os.getenv('AZURE_COSMOS_DB_SUBMISSIONS_CONTAINER_NAME', 'submissions')
            ),
            openai=AzureOpenAIConfig(
                endpoint=azure_openai_endpoint,
                model=os.getenv('AZURE_OPENAI_MODEL', 'gpt-4.1')
            ),
            table_storage=TableStorageConfig(
                account_name=storage_account_name or "",
                table_name=os.getenv('AZURE_TABLE_STORAGE_TABLE_NAME', 'continuationtokens'),
                enabled=table_storage_enabled
            ),
            company_api=CompanyAPIConfig(
                base_url=os.getenv('COMPANY_API_BASE_URL', 'http://localhost:8003')
            ),
            logging=LoggingConfig(
                level=log_level
            ),
            search=AISearchConfig(
                service_name=search_service_name,
                index_name=index_name,
                connection_id=connection_id
            ),
            service_bus=ServiceBusConfig(
                fqdn=service_bus_fqdn,
                topic_name=service_bus_topic
            ),
            pretty_print=pretty_print
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
        'azure.identity',
        'azure.core',
        'azure.ai.projects'
    ]
    
    for logger_name in azure_loggers:
        azure_logger = logging.getLogger(logger_name)
        azure_logger.setLevel(logging.WARNING)
    
    # Log configuration loaded successfully
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured with level: {config.level}")
