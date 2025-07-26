"""
Configuration management for the durable functions submission processing.

This module provides centralized configuration loading and validation
for the durable functions orchestration workflow.
"""

import os
from pydantic import BaseModel, Field


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
        example="email-processing-durable-functions"
    )
    
    documents_container_name: str = Field(
        ...,
        description="Cosmos DB documents container name",
        example="documents"
    )
    
    submissions_container_name: str = Field(
        ...,
        description="Cosmos DB submissions container name",
        example="submissions"
    )


class DocumentIntelligenceConfig(BaseModel):
    """Configuration for Azure Document Intelligence service."""
    
    endpoint: str = Field(
        ...,
        description="Document Intelligence service endpoint URL",
        example="https://email-dev-vwyh-docintel.cognitiveservices.azure.com/"
    )


class AzureOpenAIConfig(BaseModel):
    """Configuration for Azure OpenAI service."""
    
    endpoint: str = Field(
        ...,
        description="Azure OpenAI service endpoint URL",
        example="https://ai-foundry-dev-vwyh.openai.azure.com/"
    )
    
    model: str = Field(
        default="gpt-4o-mini",
        description="Azure OpenAI model deployment name",
        example="gpt-4o-mini"
    )


class StorageConfig(BaseModel):
    """Configuration for Azure Storage."""
    
    account_name: str = Field(
        ...,
        description="Azure Storage account name",
        example="stemaildevvwyhemail"
    )


class AppConfig(BaseModel):
    """Main application configuration."""
    
    cosmos_db: CosmosDBConfig
    document_intelligence: DocumentIntelligenceConfig
    azure_openai: AzureOpenAIConfig
    storage: StorageConfig
    
    @classmethod
    def from_env(cls) -> 'AppConfig':
        """
        Load configuration from environment variables.
        
        Returns:
            AppConfig: Configured application settings
            
        Raises:
            ValueError: If required environment variables are missing
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # Extract Cosmos DB configuration
        cosmos_db_endpoint = os.getenv('AZURE_COSMOS_DB_ENDPOINT')
        database_name = os.getenv('AZURE_COSMOS_DB_DATABASE_NAME', 'email-processing-durable-functions')
        documents_container_name = os.getenv('AZURE_COSMOS_DB_DOCUMENTS_CONTAINER_NAME', 'documents')
        submissions_container_name = os.getenv('AZURE_COSMOS_DB_SUBMISSIONS_CONTAINER_NAME', 'submissions')
        
        logger.info(f'Loading configuration: COSMOS_ENDPOINT={cosmos_db_endpoint}, DB_NAME={database_name}')
        
        if not cosmos_db_endpoint:
            logger.error('AZURE_COSMOS_DB_ENDPOINT environment variable is missing!')
            raise ValueError('AZURE_COSMOS_DB_ENDPOINT environment variable is required')
        
        # Extract Document Intelligence configuration
        document_intelligence_endpoint = os.getenv('AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT')
        
        logger.info(f'Loading configuration: DOC_INTEL_ENDPOINT={document_intelligence_endpoint}')
        
        if not document_intelligence_endpoint:
            logger.error('AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT environment variable is missing!')
            raise ValueError('AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT environment variable is required')
        
        # Extract Storage configuration
        storage_account_name = os.getenv('AZURE_STORAGE_ACCOUNT_NAME')
        
        logger.info(f'Loading configuration: STORAGE_ACCOUNT={storage_account_name}')
        
        if not storage_account_name:
            logger.error('AZURE_STORAGE_ACCOUNT_NAME environment variable is missing!')
            raise ValueError('AZURE_STORAGE_ACCOUNT_NAME environment variable is required')
        
        # Extract Azure OpenAI configuration
        azure_openai_endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
        azure_openai_model = os.getenv('AZURE_OPENAI_MODEL', 'gpt-4o-mini')
        
        logger.info(f'Loading configuration: OPENAI_ENDPOINT={azure_openai_endpoint}, MODEL={azure_openai_model}')
        
        if not azure_openai_endpoint:
            logger.error('AZURE_OPENAI_ENDPOINT environment variable is missing!')
            raise ValueError('AZURE_OPENAI_ENDPOINT environment variable is required')
        
        logger.info('Configuration loaded successfully')
        
        return cls(
            cosmos_db=CosmosDBConfig(
                endpoint=cosmos_db_endpoint,
                database_name=database_name,
                documents_container_name=documents_container_name,
                submissions_container_name=submissions_container_name
            ),
            document_intelligence=DocumentIntelligenceConfig(
                endpoint=document_intelligence_endpoint
            ),
            azure_openai=AzureOpenAIConfig(
                endpoint=azure_openai_endpoint,
                model=azure_openai_model
            ),
            storage=StorageConfig(
                account_name=storage_account_name
            )
        )
