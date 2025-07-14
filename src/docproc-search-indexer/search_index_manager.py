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
    SearchableField
)

from config import AISearchConfig


logger = logging.getLogger(__name__)


class SearchIndexManager:
    """
    Manages Azure AI Search index creation and configuration.
    
    This class handles the creation of search indexes with proper field
    definitions for document chunking, vector search, and security trimming.
    """
    
    def __init__(self, config: AISearchConfig, credential: Optional[TokenCredential] = None):
        """
        Initialize the search index manager.
        
        Args:
            config: AI Search configuration settings
            credential: Azure credential for authentication (defaults to DefaultAzureCredential)
        """
        self.config = config
        self.credential = credential or DefaultAzureCredential()
        self.client = SearchIndexClient(
            endpoint=config.endpoint,
            credential=self.credential
        )
    
    def ensure_index_exists(self) -> bool:
        """
        Ensure the search index exists, creating it if necessary.
        
        Returns:
            bool: True if index was created or already exists, False on error
            
        Raises:
            Exception: If index creation fails
        """
        try:
            # Check if index already exists
            existing_indexes = [index.name for index in self.client.list_indexes()]
            
            if self.config.index_name in existing_indexes:
                logger.info(f"Search index '{self.config.index_name}' already exists")
                return True
            
            # Create the index
            logger.info(f"Creating search index '{self.config.index_name}'")
            index = self._create_index_definition()
            
            result = self.client.create_index(index)
            logger.info(f"Successfully created search index '{result.name}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to ensure search index exists: {e}")
            raise
    
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
            
            # Searchable content field
            SearchableField(
                name="content",
                type=SearchFieldDataType.String,
                retrievable=True,
                analyzer_name="en.microsoft"  # English language analyzer
            ),
            
            # Vector field for semantic search (placeholder for now)
            # Note: Vector search configuration would be added here
            # when implementing semantic search capabilities
            
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
        
        # Create the index definition
        index = SearchIndex(
            name=self.config.index_name,
            fields=fields
        )
        
        return index
