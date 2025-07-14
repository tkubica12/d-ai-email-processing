"""
Azure AI Search index management for the search indexer service.

This module provides functionality to create and manage Azure AI Search
indexes for document indexing with proper field definitions and
security trimming capabilities.
"""

import logging
from typing import List, Optional

from azure.core.credentials import TokenCredential
from azure.identity import DefaultAzureCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
    VectorSearch,
    VectorSearchProfile,
    HnswAlgorithmConfiguration,
    VectorSearchAlgorithmKind,
    VectorSearchAlgorithmMetric,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
    AzureOpenAIVectorizer,
    AzureOpenAIVectorizerParameters
)

from config import AISearchConfig, OpenAIConfig


logger = logging.getLogger(__name__)


class SearchIndexManager:
    """
    Manages Azure AI Search index creation and configuration.
    
    This class handles the creation of search indexes with proper field
    definitions for document chunking, vector search, and security trimming.
    """
    
    def __init__(self, config: AISearchConfig, openai_config: OpenAIConfig, credential: Optional[TokenCredential] = None):
        """
        Initialize the search index manager.
        
        Args:
            config: AI Search configuration settings
            openai_config: Azure OpenAI configuration for vectorizers
            credential: Azure credential for authentication (defaults to DefaultAzureCredential)
        """
        self.config = config
        self.openai_config = openai_config
        self.credential = credential or DefaultAzureCredential()
        self.client = SearchIndexClient(
            endpoint=config.endpoint,
            credential=self.credential
        )
    
    def ensure_index_exists(self) -> bool:
        """
        Ensure the search index exists with the correct schema, updating it if necessary.
        
        Returns:
            bool: True if index was created or updated successfully, False on error
            
        Raises:
            Exception: If index creation/update fails
        """
        try:
            # Check if index already exists
            existing_indexes = [index.name for index in self.client.list_indexes()]
            
            if self.config.index_name in existing_indexes:
                logger.info(f"Search index '{self.config.index_name}' already exists")
                # Check if the existing index has the correct schema
                if self._validate_index_schema():
                    logger.info("Index schema is up to date")
                    return True
                else:
                    logger.info("Index schema needs update, recreating index")
                    return self._recreate_index()
            
            # Create the index
            logger.info(f"Creating search index '{self.config.index_name}'")
            index = self._create_index_definition()
            
            result = self.client.create_index(index)
            logger.info(f"Successfully created search index '{result.name}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to ensure search index exists: {e}")
            raise
    
    def _validate_index_schema(self) -> bool:
        """
        Validate that the existing index has the required vector field.
        
        Returns:
            bool: True if schema is valid, False if update needed
        """
        try:
            existing_index = self.client.get_index(self.config.index_name)
            
            # Check if contentVector field exists
            vector_field_exists = any(
                field.name == "contentVector" 
                for field in existing_index.fields
            )
            
            # Check if vector search configuration exists
            vector_search_exists = existing_index.vector_search is not None
            
            return vector_field_exists and vector_search_exists
            
        except Exception as e:
            logger.warning(f"Failed to validate index schema: {e}")
            return False
    
    def _recreate_index(self) -> bool:
        """
        Delete and recreate the index with the correct schema.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"Deleting existing index '{self.config.index_name}'")
            self.client.delete_index(self.config.index_name)
            
            logger.info("Creating new index with updated schema")
            index = self._create_index_definition()
            result = self.client.create_index(index)
            
            logger.info(f"Successfully recreated search index '{result.name}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to recreate index: {e}")
            return False
    
    def _create_index_definition(self) -> SearchIndex:
        """
        Create the search index definition with proper fields and configuration.
        
        Returns:
            SearchIndex: Complete index definition ready for creation
        """
        # Define the search fields based on the design document
        fields = [
            # Primary key field for chunks
            SimpleField(
                name="id",
                type=SearchFieldDataType.String,
                key=True,
                retrievable=True
            ),
            
            # Searchable content field with semantic search capabilities
            SearchableField(
                name="content",
                type=SearchFieldDataType.String,
                retrievable=True,
                analyzer_name="en.microsoft"  # English language analyzer
            ),
            
            # Vector field for semantic search
            SearchField(
                name="contentVector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                stored=True,  # Use 'stored' instead of 'retrievable'
                vector_search_dimensions=3072,  # text-embedding-3-large dimensions
                vector_search_profile_name="default"
            ),
            
            # Document metadata fields
            SimpleField(
                name="documentId",
                type=SearchFieldDataType.String,
                filterable=True,
                retrievable=True
            ),
            
            SimpleField(
                name="documentUrl",
                type=SearchFieldDataType.String,
                filterable=True,
                retrievable=True
            ),
            
            SimpleField(
                name="submissionId",
                type=SearchFieldDataType.String,
                filterable=True,
                retrievable=True
            ),
            
            # Security trimming field - critical for user isolation
            SimpleField(
                name="userId",
                type=SearchFieldDataType.String,
                filterable=True,
                retrievable=True
            ),
            
            # Chunk metadata fields
            SimpleField(
                name="chunkIndex",
                type=SearchFieldDataType.Int32,
                filterable=True,
                retrievable=True
            ),
            
            SimpleField(
                name="timestamp",
                type=SearchFieldDataType.DateTimeOffset,
                filterable=True,
                retrievable=True,
                sortable=True
            )
        ]
        
        # Create vector search configuration with Azure OpenAI vectorizer
        vector_search = VectorSearch(
            profiles=[
                VectorSearchProfile(
                    name="default",
                    algorithm_configuration_name="default-algorithm",
                    vectorizer_name="openai-vectorizer"
                )
            ],
            algorithms=[
                HnswAlgorithmConfiguration(
                    name="default-algorithm",
                    kind=VectorSearchAlgorithmKind.HNSW
                )
            ],
            vectorizers=[
                AzureOpenAIVectorizer(
                    vectorizer_name="openai-vectorizer",
                    parameters=AzureOpenAIVectorizerParameters(
                        resource_url=self.openai_config.resource_uri or self.openai_config.endpoint,
                        deployment_name="text-embedding-3-large",
                        model_name="text-embedding-3-large",
                        api_key=None,  # Use managed identity
                        auth_identity=None  # Use service's system-assigned identity
                    )
                )
            ]
        )
        
        # Create semantic search configuration
        semantic_search = SemanticSearch(
            configurations=[
                SemanticConfiguration(
                    name="default-semantic-config",
                    prioritized_fields=SemanticPrioritizedFields(
                        content_fields=[
                            SemanticField(field_name="content")
                        ]
                    )
                )
            ]
        )
        
        # Create the index definition
        index = SearchIndex(
            name=self.config.index_name,
            fields=fields,
            vector_search=vector_search,
            semantic_search=semantic_search
        )
        
        return index
