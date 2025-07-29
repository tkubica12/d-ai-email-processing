"""
Document search indexer action for Azure Durable Functions.

This module provides document search indexing functionality using Azure AI Search
for the durable functions orchestration workflow. It retrieves, processes, and indexes document content with
proper metadata and security trimming for efficient search capabilities.
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

from azure.identity.aio import DefaultAzureCredential, AzureCliCredential
from azure.cosmos.aio import CosmosClient
from azure.core.exceptions import HttpResponseError, ClientAuthenticationError
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    after_log
)
import os

from config import AppConfig


class DocumentChunk:
    """
    Represents a chunk of document content with metadata.
    """
    
    def __init__(
        self,
        content: str,
        chunk_index: int,
        document_id: str,
        document_url: str,
        submission_id: str,
        user_id: str,
        embedding: Optional[List[float]] = None
    ):
        """
        Initialize a document chunk.
        
        Args:
            content: Text content of the chunk
            chunk_index: Index of this chunk within the document
            document_id: Unique identifier for the document
            document_url: Azure Blob Storage URL for the document
            submission_id: Unique identifier for the submission
            user_id: User who uploaded the document
            embedding: Optional vector embedding for the content
        """
        self.content = content
        self.chunk_index = chunk_index
        self.document_id = document_id
        self.document_url = document_url
        self.submission_id = submission_id
        self.user_id = user_id
        self.embedding = embedding
        self.chunk_id = f"{document_id}_{chunk_index}"
    
    def to_search_document(self) -> dict:
        """
        Convert chunk to Azure AI Search document format.
        
        Returns:
            Dict representing the document for indexing
        """
        doc = {
            "id": self.chunk_id,
            "content": self.content,
            "chunkIndex": self.chunk_index,
            "documentId": self.document_id,
            "documentUrl": self.document_url,
            "submissionId": self.submission_id,
            "userId": self.user_id,
            "indexedAt": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        }
        
        if self.embedding:
            doc["contentVector"] = self.embedding
            
        return doc


class DocumentSearchIndexer:
    """
    Document search indexer using Azure AI Search.
    
    This class handles document content indexing into Azure AI Search with proper
    chunking, embeddings generation, and metadata management.
    """
    
    def __init__(self):
        """Initialize the document search indexer with Azure clients."""
        self.logger = logging.getLogger(__name__)
        
        # Immediately test if we can load config to catch early errors
        try:
            self.config = AppConfig.from_env()
            print("DEBUG: DocumentSearchIndexer config loaded successfully")
            print(f"DEBUG: Search service: {self.config.azure_search.service_name}")
            print(f"DEBUG: Search endpoint: {self.config.azure_search.endpoint}")
        except Exception as e:
            print(f"ERROR: Failed to load config in DocumentSearchIndexer.__init__: {str(e)}")
            raise
            
        # Use improved authentication to handle multi-tenant issues
        target_tenant = getattr(self.config, 'tenant_id', None)
        is_local_dev = not bool(os.getenv('FUNCTIONS_WORKER_RUNTIME'))
        
        if is_local_dev:
            # For local development, prefer Azure CLI credential to avoid tenant mismatch
            print("DEBUG: Using AzureCliCredential for local development")
            self.credential = AzureCliCredential()
        elif target_tenant:
            # For cloud deployment or when tenant is specified, use DefaultAzureCredential with additional tenants
            print(f"DEBUG: Using DefaultAzureCredential with additional tenant: {target_tenant}")
            self.credential = DefaultAzureCredential(additionally_allowed_tenants=[target_tenant, "*"])
        else:
            # Fallback: exclude potentially problematic credentials
            print("DEBUG: Using DefaultAzureCredential with shared cache excluded")
            self.credential = DefaultAzureCredential(
                exclude_shared_token_cache_credential=True,
                exclude_visual_studio_credential=True,
                exclude_visual_studio_code_credential=True
            )
        
        # Initialize clients (will be created async when needed)
        self.cosmos_client: Optional[CosmosClient] = None
        self.search_client: Optional[Any] = None  # SearchClient - import moved to avoid module-level issues
        self.search_index_client: Optional[Any] = None  # SearchIndexClient - import moved to avoid module-level issues
        self.openai_client: Optional[Any] = None  # AsyncAzureOpenAI - import moved to avoid module-level issues
        
        # Index configuration
        self.index_name = self.config.azure_search.index_name
        self.chunk_size = 2000
        self.chunk_overlap = 200
        self.embedding_dimensions = 3072
        
        print(f"DEBUG: DocumentSearchIndexer initialized with index: {self.index_name}")
    
    async def _ensure_clients_initialized(self):
        """Ensure all Azure clients are initialized."""
        print("DEBUG: _ensure_clients_initialized called")
        
        if not self.cosmos_client:
            print(f"DEBUG: Initializing Cosmos DB client with endpoint: {self.config.cosmos_db.endpoint}")
            self.cosmos_client = CosmosClient(
                url=self.config.cosmos_db.endpoint,
                credential=self.credential
            )
            print("DEBUG: Cosmos DB client initialized")
            
        if not self.search_client:
            print(f"DEBUG: Initializing Search client with endpoint: {self.config.azure_search.endpoint}")
            # Import here to avoid module-level import issues
            from azure.search.documents.aio import SearchClient
            
            self.search_client = SearchClient(
                endpoint=self.config.azure_search.endpoint,
                index_name=self.index_name,
                credential=self.credential
            )
            print("DEBUG: Search client initialized")
            
        if not self.search_index_client:
            print(f"DEBUG: Initializing Search index client with endpoint: {self.config.azure_search.endpoint}")
            # Import here to avoid module-level import issues
            from azure.search.documents.indexes.aio import SearchIndexClient
            
            self.search_index_client = SearchIndexClient(
                endpoint=self.config.azure_search.endpoint,
                credential=self.credential
            )
            print("DEBUG: Search index client initialized")
            
        if not self.openai_client:
            print(f"DEBUG: Initializing OpenAI client with endpoint: {self.config.azure_openai.embedding_endpoint}")
            # Import here to avoid module-level import issues
            from openai import AsyncAzureOpenAI
            
            # Create a simple async token provider function
            async def get_azure_ad_token():
                token = await self.credential.get_token("https://cognitiveservices.azure.com/.default")
                return token.token
            
            self.openai_client = AsyncAzureOpenAI(
                azure_endpoint=self.config.azure_openai.embedding_endpoint,
                azure_ad_token_provider=get_azure_ad_token,
                api_version="2024-06-01"
            )
            print("DEBUG: OpenAI client initialized")
    
    async def index_document_async(self, document_id: str, submission_id: str) -> Dict[str, Any]:
        """
        Index document content into Azure AI Search.
        
        Args:
            document_id: Unique identifier for the document
            submission_id: Unique identifier for the submission
            
        Returns:
            Dict containing the indexing results
        """
        try:
            print(f"DEBUG: Starting search indexing for document {document_id} in submission {submission_id}")
            self.logger.info(f"Starting search indexing for document {document_id} in submission {submission_id}")
            
            print(f"DEBUG: Initializing Azure clients...")
            await self._ensure_clients_initialized()
            print(f"DEBUG: Azure clients initialized successfully")
            
            # Retrieve document record from Cosmos DB
            print(f"DEBUG: Retrieving document record for {document_id} from Cosmos DB...")
            document_record = await self._get_document_record(document_id, submission_id)
            
            if not document_record:
                error_msg = f"Document record not found for document {document_id}"
                print(f"ERROR: {error_msg}")
                self.logger.error(error_msg)
                return {
                    "documentId": document_id,
                    "status": "error",
                    "error": error_msg,
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            print(f"DEBUG: Document record retrieved successfully - fileName: {document_record.get('fileName', 'unknown')}")
            
            # Check if document has parsed content
            content = document_record.get("content", "")
            if not content:
                error_msg = f"Document {document_id} has no parsed content available for indexing"
                print(f"WARNING: {error_msg}")
                self.logger.warning(error_msg)
                return {
                    "documentId": document_id,
                    "status": "skipped",
                    "reason": "No content available",
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            print(f"DEBUG: Document content found - length: {len(content)} characters")
            
            # Chunk document content
            print(f"DEBUG: Chunking document content...")
            chunks = self._chunk_document_content(
                content=content,
                document_id=document_id,
                document_url=document_record.get("documentUrl", ""),
                submission_id=submission_id,
                user_id=document_record.get("userId", "unknown")
            )
            print(f"DEBUG: Created {len(chunks)} chunks from document content")
            
            # Generate embeddings for chunks
            print(f"DEBUG: Generating embeddings for {len(chunks)} chunks...")
            chunks_with_embeddings = await self._generate_embeddings_for_chunks(chunks)
            print(f"DEBUG: Generated embeddings for {len(chunks_with_embeddings)} chunks")
            
            # Index chunks into Azure AI Search
            print(f"DEBUG: Converting chunks to search documents...")
            search_documents = [chunk.to_search_document() for chunk in chunks_with_embeddings]
            print(f"DEBUG: Created {len(search_documents)} search documents")
            
            print(f"DEBUG: Indexing documents into Azure AI Search index {self.index_name}...")
            await self._index_documents_batch(search_documents)
            print(f"DEBUG: Successfully indexed {len(chunks_with_embeddings)} chunks into Azure AI Search")
            
            self.logger.info(f"Successfully indexed {len(chunks_with_embeddings)} chunks for document {document_id}")
            
            return {
                "documentId": document_id,
                "status": "success",
                "chunksIndexed": len(chunks_with_embeddings),
                "indexName": self.index_name,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            error_msg = f"Failed to index document {document_id}: {str(e)}"
            print(f"ERROR: {error_msg}")
            self.logger.error(error_msg, exc_info=True)
            return {
                "documentId": document_id,
                "status": "error",
                "error": error_msg,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=4, max=60),
        retry=retry_if_exception_type((ClientAuthenticationError, HttpResponseError, TimeoutError, ConnectionError)),
        before_sleep=before_sleep_log(logging.getLogger(__name__), logging.WARNING),
        after=after_log(logging.getLogger(__name__), logging.INFO)
    )
    async def _get_document_record(self, document_id: str, submission_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve document record from Cosmos DB.
        
        Args:
            document_id: Unique identifier for the document
            submission_id: Submission ID (used as partition key)
            
        Returns:
            Document record dict or None if not found
        """
        print(f"DEBUG: Attempting to retrieve document {document_id} from Cosmos DB with partition key {submission_id}...")
        try:
            database = self.cosmos_client.get_database_client(self.config.cosmos_db.database_name)
            container = database.get_container_client(self.config.cosmos_db.documents_container_name)
            
            print(f"DEBUG: Calling read_item for document {document_id} with partition key {submission_id}...")
            response = await container.read_item(
                item=document_id,
                partition_key=submission_id
            )
            
            print(f"DEBUG: Successfully retrieved document {document_id} from Cosmos DB")
            return response
            
        except CosmosResourceNotFoundError:
            print(f"WARNING: Document {document_id} not found in Cosmos DB")
            self.logger.warning(f"Document {document_id} not found in Cosmos DB")
            return None
        except Exception as e:
            print(f"ERROR: Failed to retrieve document {document_id}: {str(e)}")
            self.logger.error(f"Failed to retrieve document {document_id}: {str(e)}", exc_info=True)
            raise
    
    def _chunk_document_content(
        self,
        content: str,
        document_id: str,
        document_url: str,
        submission_id: str,
        user_id: str
    ) -> List[DocumentChunk]:
        """
        Chunk document content into smaller pieces for indexing.
        
        Args:
            content: Document content to chunk
            document_id: Unique identifier for the document
            document_url: Azure Blob Storage URL for the document
            submission_id: Unique identifier for the submission
            user_id: User who uploaded the document
            
        Returns:
            List of DocumentChunk objects
        """
        chunks = []
        
        # Simple chunking strategy with overlap
        start = 0
        chunk_index = 0
        
        while start < len(content):
            end = start + self.chunk_size
            chunk_content = content[start:end]
            
            # Ensure we don't cut words in half (except for the last chunk)
            if end < len(content):
                last_space = chunk_content.rfind(' ')
                if last_space > self.chunk_size * 0.8:  # Only adjust if we find a space reasonably close to the end
                    end = start + last_space
                    chunk_content = content[start:end]
            
            chunks.append(DocumentChunk(
                content=chunk_content.strip(),
                chunk_index=chunk_index,
                document_id=document_id,
                document_url=document_url,
                submission_id=submission_id,
                user_id=user_id
            ))
            
            # Move start position with overlap
            start = end - self.chunk_overlap
            chunk_index += 1
            
            # Prevent infinite loop
            if start >= len(content):
                break
        
        return chunks
    
    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=4, max=60),
        retry=retry_if_exception_type(Exception),
        before_sleep=before_sleep_log(logging.getLogger(__name__), logging.WARNING),
        after=after_log(logging.getLogger(__name__), logging.INFO)
    )
    async def _generate_embeddings_for_chunks(self, chunks: List[DocumentChunk]) -> List[DocumentChunk]:
        """
        Generate embeddings for document chunks using OpenAI.
        
        Args:
            chunks: List of DocumentChunk objects
            
        Returns:
            List of DocumentChunk objects with embeddings
        """
        if not chunks:
            print("DEBUG: No chunks to generate embeddings for")
            return chunks
        
        print(f"DEBUG: Generating embeddings for {len(chunks)} chunks using OpenAI...")
        
        # Prepare texts for embedding
        texts = [chunk.content for chunk in chunks]
        print(f"DEBUG: Prepared {len(texts)} texts for embedding generation")
        
        try:
            # Generate embeddings in batch
            print("DEBUG: Calling OpenAI embeddings API...")
            response = await self.openai_client.embeddings.create(
                input=texts,
                model=self.config.azure_openai.embedding_deployment,
                dimensions=self.embedding_dimensions
            )
            print(f"DEBUG: Received {len(response.data)} embeddings from OpenAI")
            
            # Assign embeddings to chunks
            for i, chunk in enumerate(chunks):
                chunk.embedding = response.data[i].embedding
                
            print(f"DEBUG: Successfully assigned embeddings to {len(chunks)} chunks")
            return chunks
            
        except Exception as e:
            print(f"ERROR: Failed to generate embeddings: {str(e)}")
            self.logger.error(f"Failed to generate embeddings: {str(e)}", exc_info=True)
            raise
    
    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=4, max=30),
        retry=retry_if_exception_type((HttpResponseError, TimeoutError, ConnectionError)),
        before_sleep=before_sleep_log(logging.getLogger(__name__), logging.WARNING),
        after=after_log(logging.getLogger(__name__), logging.INFO)
    )
    async def _index_documents_batch(self, documents: List[dict]) -> None:
        """
        Index documents batch into Azure AI Search.
        Try to upload directly first, create index if it doesn't exist.
        
        Args:
            documents: List of document dictionaries to index
        """
        print(f"DEBUG: Attempting to upload {len(documents)} documents to Azure AI Search...")
        
        try:
            # Try to upload documents directly first
            await self.search_client.upload_documents(documents)
            print(f"DEBUG: Successfully uploaded {len(documents)} documents to Azure AI Search")
            return
        except Exception as upload_error:
            # Check if error is due to index not existing
            error_str = str(upload_error).lower()
            if ("index" in error_str and ("not found" in error_str or "does not exist" in error_str)) or \
               ("resource not found" in error_str):
                print(f"DEBUG: Index {self.index_name} not found, attempting to create it...")
                self.logger.info(f"Index {self.index_name} not found, attempting to create it")
                
                try:
                    # Try to create the index
                    await self._create_search_index()
                    
                    # Retry the upload after successful index creation
                    print("DEBUG: Retrying upload after index creation...")
                    await self.search_client.upload_documents(documents)
                    print(f"DEBUG: Successfully uploaded {len(documents)} documents to Azure AI Search after index creation")
                    return
                    
                except Exception as create_error:
                    create_error_str = str(create_error).lower()
                    if "already exists" in create_error_str or "resourcenamealreadyinuse" in create_error_str:
                        # Index was created by another process, just retry upload
                        print("DEBUG: Index already exists (created by another process), retrying upload...")
                        await self.search_client.upload_documents(documents)
                        print(f"DEBUG: Successfully uploaded {len(documents)} documents to Azure AI Search")
                        return
                    else:
                        print(f"ERROR: Failed to create index: {str(create_error)}")
                        raise create_error
            else:
                print(f"ERROR: Failed to upload documents to search index: {str(upload_error)}")
                self.logger.error(f"Failed to upload documents to search index: {str(upload_error)}", exc_info=True)
                raise upload_error
    
    async def _create_search_index(self) -> None:
        """
        Create the search index with proper field definitions.
        """
        print("DEBUG: Starting index creation...")
        try:
            # Import here to avoid module-level import issues in Azure Functions
            from azure.search.documents.indexes.models import (
                SearchIndex,
                SearchField,
                SearchFieldDataType,
                SimpleField,
                SearchableField,
                VectorSearch,
                VectorSearchProfile,
                HnswAlgorithmConfiguration,
                HnswParameters,
                VectorSearchAlgorithmKind,
                VectorSearchAlgorithmMetric,
                SemanticConfiguration,
                SemanticField,
                SemanticPrioritizedFields,
                SemanticSearch,
                AzureOpenAIVectorizer,
                AzureOpenAIVectorizerParameters
            )
            print("DEBUG: Azure Search models imported successfully")
            
            # Define vector search configuration
            print("DEBUG: Defining vector search configuration...")
            vector_search = VectorSearch(
                profiles=[
                    VectorSearchProfile(
                        name="default-vector-profile",
                        algorithm_configuration_name="default-hnsw-config",
                        vectorizer_name="default-openai-vectorizer"
                    )
                ],
                algorithms=[
                    HnswAlgorithmConfiguration(
                        name="default-hnsw-config",
                        kind=VectorSearchAlgorithmKind.HNSW,
                        parameters=HnswParameters(
                            m=4,
                            ef_construction=400,
                            ef_search=500,
                            metric=VectorSearchAlgorithmMetric.COSINE
                        )
                    )
                ],
                vectorizers=[
                    AzureOpenAIVectorizer(
                        vectorizer_name="default-openai-vectorizer",
                        parameters=AzureOpenAIVectorizerParameters(
                            resource_url=self.config.azure_openai.embedding_endpoint,
                            deployment_name=self.config.azure_openai.embedding_deployment,
                            model_name=self.config.azure_openai.embedding_deployment,
                            api_key=None  # Will use managed identity
                        )
                    )
                ]
            )
            print("DEBUG: Vector search configuration defined")
            
            # Define semantic search configuration
            print("DEBUG: Defining semantic search configuration...")
            semantic_config = SemanticConfiguration(
                name="default-semantic-config",
                prioritized_fields=SemanticPrioritizedFields(
                    content_fields=[SemanticField(field_name="content")]
                )
            )
            
            semantic_search = SemanticSearch(configurations=[semantic_config])
            print("DEBUG: Semantic search configuration defined")
            
            # Define index fields
            print("DEBUG: Defining index fields...")
            fields = [
                SimpleField(name="id", type=SearchFieldDataType.String, key=True),
                SearchableField(name="content", type=SearchFieldDataType.String, analyzer_name="standard.lucene"),
                SimpleField(name="chunkIndex", type=SearchFieldDataType.Int32),
                SimpleField(name="documentId", type=SearchFieldDataType.String, filterable=True),
                SimpleField(name="documentUrl", type=SearchFieldDataType.String),
                SimpleField(name="submissionId", type=SearchFieldDataType.String, filterable=True),
                SimpleField(name="userId", type=SearchFieldDataType.String, filterable=True),
                SimpleField(name="indexedAt", type=SearchFieldDataType.DateTimeOffset),
                SearchField(
                    name="contentVector",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    searchable=True,
                    vector_search_dimensions=self.embedding_dimensions,
                    vector_search_profile_name="default-vector-profile"
                )
            ]
            print(f"DEBUG: Defined {len(fields)} index fields")
            
            # Create index
            print("DEBUG: Creating SearchIndex object...")
            index = SearchIndex(
                name=self.index_name,
                fields=fields,
                vector_search=vector_search,
                semantic_search=semantic_search
            )
            
            print("DEBUG: Calling create_index API...")
            await self.search_index_client.create_index(index)
            print(f"DEBUG: Successfully created search index {self.index_name}")
            self.logger.info(f"Successfully created search index {self.index_name}")
            
        except Exception as e:
            error_msg = f"Failed to create search index {self.index_name}: {str(e)}"
            print(f"ERROR: {error_msg}")
            self.logger.error(error_msg, exc_info=True)
            raise
    
    async def _close_clients(self):
        """Close all Azure clients."""
        if self.cosmos_client:
            await self.cosmos_client.close()
        if self.search_client:
            await self.search_client.close()
        if self.search_index_client:
            await self.search_index_client.close()
        if self.openai_client:
            await self.openai_client.close()
