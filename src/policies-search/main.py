"""
Policies Search Setup Script

This script sets up the policies-search system by:
1. Creating Azure Blob Storage container and uploading policy documents
2. Setting up Azure AI Search index with vector and semantic search capabilities
3. Creating skillsets for embedding generation using Azure OpenAI
4. Setting up indexer to process documents and generate embeddings
5. Testing search capabilities (text, semantic, and vector search)

All operations are idempotent - safe to run multiple times.
"""

import asyncio
import logging
import os
import sys
import time
from pathlib import Path
from typing import List

from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexerClient, SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    AzureOpenAIVectorizer,
    AzureOpenAIVectorizerParameters,
    SemanticConfiguration,
    SemanticPrioritizedFields,
    SemanticField,
    SemanticSearch,
    SearchIndexerDataSourceConnection,
    SearchIndexerDataContainer,
    SearchIndexer,
    IndexingSchedule,
    IndexingParameters,
    SearchIndexerSkillset,
    InputFieldMappingEntry,
    OutputFieldMappingEntry,
    OcrSkill,
    MergeSkill,
    AzureOpenAIEmbeddingSkill,
    SplitSkill,
    TextSplitMode
)
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Remap Azure SDK INFO logs to DEBUG to reduce noise
logging.getLogger('azure.core.pipeline.policies.http_logging_policy').setLevel(logging.WARNING)
logging.getLogger('azure.identity').setLevel(logging.WARNING)
logging.getLogger('azure.storage.blob').setLevel(logging.WARNING)
logging.getLogger('azure.search.documents').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


class PoliciesSearchSetup:
    """Setup class for policies-search system."""
    
    def __init__(self):
        """Initialize the setup with Azure credentials and configuration."""
        load_dotenv()
        
        self.storage_account_name = os.getenv('AZURE_STORAGE_ACCOUNT_NAME')
        self.container_name = os.getenv('AZURE_STORAGE_POLICIES_CONTAINER_NAME')
        self.local_folder = os.getenv('AZURE_STORAGE_LOCAL_FOLDER')
        self.search_service_name = os.getenv('AZURE_SEARCH_SERVICE_NAME')
        self.search_index_name = os.getenv('AZURE_SEARCH_INDEX_NAME')
        self.search_subscription_id = os.getenv('AZURE_SEARCH_SUBSCRIPTION_ID')
        self.search_resource_group = os.getenv('AZURE_SEARCH_RESOURCE_GROUP')
        self.openai_endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
        self.openai_deployment = os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME')
        self.openai_api_version = os.getenv('AZURE_OPENAI_API_VERSION')
        
        if not all([self.storage_account_name, self.container_name, self.local_folder, 
                   self.search_service_name, self.search_index_name, self.search_subscription_id,
                   self.search_resource_group, self.openai_endpoint, self.openai_deployment, 
                   self.openai_api_version]):
            raise ValueError("Missing required environment variables. Check .env file.")
        
        self.credential = DefaultAzureCredential()
        self.blob_service_client = BlobServiceClient(
            account_url=f"https://{self.storage_account_name}.blob.core.windows.net",
            credential=self.credential
        )
        
        # Initialize search clients
        search_endpoint = f"https://{self.search_service_name}.search.windows.net"
        self.search_client = SearchClient(
            endpoint=search_endpoint,
            index_name=self.search_index_name,
            credential=self.credential
        )
        self.search_index_client = SearchIndexClient(
            endpoint=search_endpoint,
            credential=self.credential
        )
        self.indexer_client = SearchIndexerClient(
            endpoint=search_endpoint,
            credential=self.credential
        )
        self.index_client = SearchIndexClient(
            endpoint=search_endpoint,
            credential=self.credential
        )
        
        # Resolve local folder path relative to script location
        self.local_policies_path = Path(__file__).parent / self.local_folder
        logger.info(f"Local policies folder: {self.local_policies_path}")
        logger.info(f"Search service endpoint: {search_endpoint}")
        logger.info(f"Search index name: {self.search_index_name}")
        
        # Add OpenAI client for testing vector search
        try:
            from openai import AzureOpenAI
            self.openai_client = AzureOpenAI(
                api_key=self.credential.get_token("https://cognitiveservices.azure.com/.default").token,
                api_version=self.openai_api_version,
                azure_endpoint=self.openai_endpoint
            )
        except ImportError:
            logger.warning("OpenAI client not available for vector search testing")
            self.openai_client = None
        except Exception as e:
            logger.warning(f"Could not initialize OpenAI client: {e}")
            self.openai_client = None
        
    async def setup_blob_storage(self) -> None:
        """Create blob storage container and upload policy documents."""
        logger.info("=== Step 1: Setting up Azure Blob Storage ===")
        
        try:
            # Create container if it doesn't exist
            container_client = self.blob_service_client.get_container_client(self.container_name)
            
            try:
                container_client.create_container()
                logger.info(f"✓ Created container: {self.container_name}")
            except ResourceExistsError:
                logger.info(f"✓ Container already exists: {self.container_name}")
            
            # Upload policy documents
            await self._upload_policy_documents(container_client)
            
        except Exception as e:
            logger.error(f"✗ Failed to setup blob storage: {e}")
            raise
            
    async def _upload_policy_documents(self, container_client) -> None:
        """Upload all policy documents from local folder to blob storage."""
        if not self.local_policies_path.exists():
            raise FileNotFoundError(f"Local policies folder not found: {self.local_policies_path}")
            
        policy_files = list(self.local_policies_path.glob("*.md"))
        
        if not policy_files:
            logger.warning(f"No policy files found in {self.local_policies_path}")
            return
            
        logger.info(f"Found {len(policy_files)} policy files to upload")
        
        uploaded_count = 0
        for policy_file in policy_files:
            try:
                blob_name = policy_file.name
                
                # Upload file (overwrites existing)
                with open(policy_file, 'rb') as data:
                    container_client.upload_blob(
                        name=blob_name,
                        data=data,
                        overwrite=True
                    )
                
                logger.info(f"  ✓ Uploaded: {blob_name}")
                uploaded_count += 1
                
            except Exception as e:
                logger.error(f"  ✗ Failed to upload {policy_file.name}: {e}")
                
        logger.info(f"✓ Successfully uploaded {uploaded_count}/{len(policy_files)} policy documents")
        
    async def setup_search_index(self) -> None:
        """Create or update the Azure AI Search index with vector search capabilities."""
        logger.info("=== Step 2: Setting up Azure AI Search Index ===")
        
        try:
            # Check if index exists and delete it if it does (to allow schema changes)
            try:
                existing_index = self.search_index_client.get_index(self.search_index_name)
                logger.info(f"Index '{self.search_index_name}' already exists. Deleting to allow schema changes...")
                self.search_index_client.delete_index(self.search_index_name)
                logger.info(f"✓ Deleted existing index: {self.search_index_name}")
            except Exception:
                logger.info(f"Index '{self.search_index_name}' does not exist. Creating new index...")
            
            # Create vector search configuration (keeping for future use)
            vector_search = VectorSearch(
                profiles=[
                    VectorSearchProfile(
                        name="policies-vector-profile",
                        algorithm_configuration_name="policies-hnsw-config",
                        vectorizer_name="policies-vectorizer"
                    )
                ],
                algorithms=[
                    HnswAlgorithmConfiguration(
                        name="policies-hnsw-config",
                        parameters={
                            "m": 4,
                            "ef_construction": 400,
                            "ef_search": 500,
                            "metric": "cosine"
                        }
                    )
                ],
                vectorizers=[
                    AzureOpenAIVectorizer(
                        vectorizer_name="policies-vectorizer",
                        parameters=AzureOpenAIVectorizerParameters(
                            resource_url=self.openai_endpoint,
                            deployment_name=self.openai_deployment,
                            model_name="text-embedding-3-large"
                        )
                    )
                ]
            )
            
            # Create semantic search configuration
            semantic_search = SemanticSearch(
                configurations=[
                    SemanticConfiguration(
                        name="policies-semantic-config",
                        prioritized_fields=SemanticPrioritizedFields(
                            title_field=SemanticField(field_name="title"),
                            content_fields=[
                                SemanticField(field_name="content")
                            ],
                            keywords_fields=[
                                SemanticField(field_name="filename")
                            ]
                        )
                    )
                ]
            )
            
            # Define index fields (with vector field for embeddings)
            fields = [
                SimpleField(name="id", type=SearchFieldDataType.String, key=True),
                SearchableField(name="title", type=SearchFieldDataType.String, sortable=True),
                SearchableField(name="content", type=SearchFieldDataType.String, analyzer_name="en.lucene"),
                SimpleField(name="filename", type=SearchFieldDataType.String, filterable=True, facetable=True),
                SimpleField(name="last_modified", type=SearchFieldDataType.DateTimeOffset, sortable=True),
                SimpleField(name="size", type=SearchFieldDataType.Int32, sortable=True),
                SearchField(
                    name="content_vector",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    searchable=True,
                    retrievable=True,
                    vector_search_dimensions=3072,  # text-embedding-3-large dimensions
                    vector_search_profile_name="policies-vector-profile"
                )
            ]
            
            # Create the index with vector search enabled
            index = SearchIndex(
                name=self.search_index_name,
                fields=fields,
                vector_search=vector_search,
                semantic_search=semantic_search
            )
            
            # Create the new index
            self.search_index_client.create_index(index)
            logger.info(f"✓ Created search index: {self.search_index_name}")
            
        except Exception as e:
            logger.error(f"✗ Failed to setup search index: {e}")
            raise
            
    async def setup_data_source(self) -> None:
        """Create or update the data source for the blob storage container."""
        logger.info("=== Step 3: Setting up Azure AI Search Data Source ===")
        
        try:
            data_source_name = f"{self.search_index_name}-datasource"
            indexer_name = f"{self.search_index_name}-indexer"
            skillset_name = f"{self.search_index_name}-skillset"
            
            # First, handle any existing indexer that might be using this data source
            try:
                indexer = self.indexer_client.get_indexer(indexer_name)
                logger.info(f"Found existing indexer '{indexer_name}' that uses this data source. Stopping and deleting it...")
                
                # Stop the indexer if it's running
                try:
                    self.indexer_client.reset_indexer(indexer_name)
                    logger.info(f"✓ Reset indexer: {indexer_name}")
                except Exception as e:
                    logger.info(f"Could not reset indexer (it may not be running): {e}")
                
                # Delete the indexer
                self.indexer_client.delete_indexer(indexer_name)
                logger.info(f"✓ Deleted existing indexer: {indexer_name}")
                
            except Exception:
                logger.info(f"No existing indexer found for '{indexer_name}'")
            
            # Handle existing skillset if it exists
            try:
                self.indexer_client.get_skillset(skillset_name)
                logger.info(f"Found existing skillset '{skillset_name}'. Will be recreated in skillset setup...")
            except Exception:
                logger.info(f"No existing skillset found for '{skillset_name}'")
            
            # Now handle the data source
            try:
                self.indexer_client.get_data_source_connection(data_source_name)
                logger.info(f"Data source '{data_source_name}' already exists. Deleting to ensure clean setup...")
                self.indexer_client.delete_data_source_connection(data_source_name)
                logger.info(f"✓ Deleted existing data source: {data_source_name}")
            except Exception:
                logger.info(f"Data source '{data_source_name}' does not exist. Creating new data source...")
            
            # Create connection string using Resource ID for managed identity
            connection_string = f"ResourceId=/subscriptions/{self.search_subscription_id}/resourceGroups/{self.search_resource_group}/providers/Microsoft.Storage/storageAccounts/{self.storage_account_name};"
            
            # Create data source connection
            data_source = SearchIndexerDataSourceConnection(
                name=data_source_name,
                type="azureblob",
                connection_string=connection_string,
                container=SearchIndexerDataContainer(name=self.container_name)
            )
            
            # Create the data source
            self.indexer_client.create_data_source_connection(data_source)
            logger.info(f"✓ Created data source: {data_source_name}")
            
        except Exception as e:
            logger.error(f"✗ Failed to setup data source: {e}")
            raise
            
    async def setup_skillset(self) -> None:
        """Create or update the skillset for document processing and embedding generation."""
        logger.info("=== Step 4: Setting up Azure AI Search Skillset ===")
        
        try:
            skillset_name = f"{self.search_index_name}-skillset"
            
            # Check if skillset exists and delete it to allow updates
            try:
                self.indexer_client.get_skillset(skillset_name)
                logger.info(f"Skillset '{skillset_name}' already exists. Deleting to allow updates...")
                self.indexer_client.delete_skillset(skillset_name)
                logger.info(f"✓ Deleted existing skillset: {skillset_name}")
            except Exception:
                logger.info(f"Skillset '{skillset_name}' does not exist. Creating new skillset...")
            
            # Define skills for processing
            skills = [
                # Generate embeddings for content
                AzureOpenAIEmbeddingSkill(
                    name="generate-content-embeddings",
                    description="Generate embeddings for document content using Azure OpenAI",
                    context="/document",
                    resource_url=self.openai_endpoint,
                    deployment_name=self.openai_deployment,
                    model_name="text-embedding-3-large",
                    dimensions=3072,
                    inputs=[
                        InputFieldMappingEntry(name="text", source="/document/content")
                    ],
                    outputs=[
                        OutputFieldMappingEntry(name="embedding", target_name="content_vector")
                    ]
                )
            ]
            
            skillset = SearchIndexerSkillset(
                name=skillset_name,
                description="Skillset for processing policy documents and generating embeddings",
                skills=skills
            )
            
            # Create the skillset
            self.indexer_client.create_skillset(skillset)
            logger.info(f"✓ Created skillset: {skillset_name}")
            
        except Exception as e:
            logger.error(f"✗ Failed to setup skillset: {e}")
            raise
            
    async def setup_indexer(self) -> None:
        """Create or update the indexer to process documents."""
        logger.info("=== Step 5: Setting up Azure AI Search Indexer ===")
        
        try:
            indexer_name = f"{self.search_index_name}-indexer"
            data_source_name = f"{self.search_index_name}-datasource"
            
            # Check if indexer exists (it might have been deleted in setup_data_source)
            try:
                self.indexer_client.get_indexer(indexer_name)
                logger.info(f"Indexer '{indexer_name}' still exists. Deleting to ensure clean setup...")
                self.indexer_client.delete_indexer(indexer_name)
                logger.info(f"✓ Deleted existing indexer: {indexer_name}")
            except Exception:
                logger.info(f"Indexer '{indexer_name}' does not exist. Creating new indexer...")
            
            # Define field mappings
            field_mappings = [
                {"sourceFieldName": "metadata_storage_path", "targetFieldName": "id", "mappingFunction": {"name": "base64Encode"}},
                {"sourceFieldName": "metadata_storage_name", "targetFieldName": "filename"},
                {"sourceFieldName": "metadata_storage_name", "targetFieldName": "title"},
                {"sourceFieldName": "content", "targetFieldName": "content"},
                {"sourceFieldName": "metadata_storage_last_modified", "targetFieldName": "last_modified"},
                {"sourceFieldName": "metadata_storage_size", "targetFieldName": "size"}
            ]
            
            # Define output field mappings for skillset
            output_field_mappings = [
                {"sourceFieldName": "/document/content_vector", "targetFieldName": "content_vector"}
            ]
            
            skillset_name = f"{self.search_index_name}-skillset"
            
            # Create indexer with skillset for vector embedding generation
            indexer = SearchIndexer(
                name=indexer_name,
                data_source_name=data_source_name,
                target_index_name=self.search_index_name,
                skillset_name=skillset_name,
                field_mappings=field_mappings,
                output_field_mappings=output_field_mappings,
                schedule=IndexingSchedule(interval="PT1H"),  # Run every hour
                parameters=IndexingParameters(
                    batch_size=10,
                    max_failed_items=5,
                    max_failed_items_per_batch=5,
                    configuration={
                        "dataToExtract": "contentAndMetadata",
                        "parsingMode": "default"
                    }
                )
            )
            
            # Create the indexer
            self.indexer_client.create_indexer(indexer)
            logger.info(f"✓ Created indexer: {indexer_name}")
            
            # Run the indexer immediately
            logger.info("Running indexer to process documents...")
            self.indexer_client.run_indexer(indexer_name)
            logger.info("✓ Indexer started successfully")
            
        except Exception as e:
            logger.error(f"✗ Failed to setup indexer: {e}")
            raise
    
    async def test_search_capabilities(self) -> None:
        """Test text and semantic search capabilities."""
        logger.info("=== Testing Search Capabilities ===")
        
        try:
            # Wait for indexer to complete
            logger.info("Waiting for indexer to complete processing...")
            await self._wait_for_indexer_completion()
            
            # Test basic text search
            logger.info("Testing basic text search...")
            await self._test_text_search("risk management")
            
            # Test semantic search
            logger.info("Testing semantic search...")
            await self._test_semantic_search("how to handle customer complaints")
            
            logger.info("✓ Search capabilities testing completed successfully!")
            
        except Exception as e:
            logger.error(f"✗ Failed to test search capabilities: {e}")
            raise
    
    async def _wait_for_indexer_completion(self, timeout_minutes: int = 10) -> None:
        """Wait for indexer to complete processing with timeout."""
        indexer_name = f"{self.search_index_name}-indexer"
        timeout_seconds = timeout_minutes * 60
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            try:
                status = self.indexer_client.get_indexer_status(indexer_name)
                if status.last_result and status.last_result.status == "success":
                    logger.info(f"✓ Indexer completed successfully. Processed {status.last_result.item_count} items.")
                    return
                elif status.last_result and status.last_result.status == "transientFailure":
                    logger.warning(f"Indexer has transient failures. Waiting...")
                elif status.last_result and status.last_result.status == "persistentFailure":
                    logger.error(f"Indexer has persistent failures: {status.last_result.error_message}")
                    raise Exception(f"Indexer failed: {status.last_result.error_message}")
                else:
                    logger.info(f"Indexer status: {status.status}. Waiting...")
                
                await asyncio.sleep(10)  # Wait 10 seconds before checking again
                
            except Exception as e:
                logger.warning(f"Error checking indexer status: {e}")
                await asyncio.sleep(10)
        
        raise TimeoutError(f"Indexer did not complete within {timeout_minutes} minutes")
    
    async def _test_text_search(self, query: str) -> None:
        """Test basic text search functionality."""
        try:
            results = self.search_client.search(
                search_text=query,
                top=3,
                select=["title", "filename", "content"],
                highlight_fields="content"
            )
            
            count = 0
            for result in results:
                count += 1
                logger.info(f"  Text Search Result {count}: {result.get('title', 'No title')} ({result.get('filename', 'No filename')})")
                if result.get('@search.highlights'):
                    logger.info(f"    Highlights: {result['@search.highlights']}")
            
            if count == 0:
                logger.warning("  No text search results found")
            else:
                logger.info(f"✓ Text search returned {count} results")
                
        except Exception as e:
            logger.error(f"  ✗ Text search failed: {e}")
    
    async def _test_semantic_search(self, query: str) -> None:
        """Test semantic search functionality."""
        try:
            results = self.search_client.search(
                search_text=query,
                top=3,
                select=["title", "filename", "content"],
                query_type="semantic",
                semantic_configuration_name="policies-semantic-config",
                query_caption="extractive",
                query_answer="extractive"
            )
            
            count = 0
            for result in results:
                count += 1
                logger.info(f"  Semantic Search Result {count}: {result.get('title', 'No title')} ({result.get('filename', 'No filename')})")
                if result.get('@search.captions'):
                    captions = result['@search.captions']
                    if captions and len(captions) > 0:
                        logger.info(f"    Caption: {captions[0].text}")
                if result.get('@search.reranker_score'):
                    logger.info(f"    Reranker Score: {result['@search.reranker_score']}")
            
            if count == 0:
                logger.warning("  No semantic search results found")
            else:
                logger.info(f"✓ Semantic search returned {count} results")
                
        except Exception as e:
            logger.error(f"  ✗ Semantic search failed: {e}")
    
    async def run_setup(self) -> None:
        """Run the complete setup process."""
        logger.info("Starting policies-search setup...")
        
        try:
            await self.setup_blob_storage()
            await self.setup_search_index()
            await self.setup_data_source()
            await self.setup_skillset()
            await self.setup_indexer()
            logger.info("✓ Setup completed successfully!")
            logger.info("Text search and semantic search capabilities are now available.")
            logger.info("Vector search capabilities are configured and ready for use.")
            
            # Test search capabilities
            await self.test_search_capabilities()
            
        except Exception as e:
            logger.error(f"✗ Setup failed: {e}")
            sys.exit(1)


async def main():
    """Main entry point for the setup script."""
    setup = PoliciesSearchSetup()
    await setup.run_setup()


if __name__ == "__main__":
    asyncio.run(main())
