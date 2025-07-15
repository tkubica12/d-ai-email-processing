# Policies Search Setup

This module sets up the Azure AI Search index for policy documents, enabling semantic and vector search capabilities.

## Prerequisites

- Azure CLI installed and authenticated (`az login`)
- Azure subscription with the following resources deployed:
  - Azure Storage Account
  - Azure AI Search service
  - Azure OpenAI service with text-embedding-3-large deployment

## Configuration

Copy `.env.example` to `.env` and configure the following variables:

```bash
# Azure Storage Configuration
AZURE_STORAGE_ACCOUNT_NAME=your-storage-account-name
AZURE_STORAGE_POLICIES_CONTAINER_NAME=policies-docs
AZURE_STORAGE_LOCAL_FOLDER=../../policies-docs

# Azure AI Search Configuration
AZURE_SEARCH_SERVICE_NAME=your-search-service-name
AZURE_SEARCH_INDEX_NAME=policies-index
AZURE_SEARCH_SUBSCRIPTION_ID=your-subscription-id
AZURE_SEARCH_RESOURCE_GROUP=your-resource-group-name

# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT=https://your-openai-service.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=text-embedding-3-large
AZURE_OPENAI_API_VERSION=2024-06-01

# Application Configuration
LOG_LEVEL=INFO
```

## Usage

Run the setup script to create the complete search infrastructure:

```bash
uv run main.py
```

This script will:

1. **Setup Blob Storage**: Create the blob storage container and upload all policy documents from the local folder
2. **Create Search Index**: Set up the Azure AI Search index with vector search and semantic search capabilities
3. **Create Data Source**: Configure the blob storage container as a data source for the search service
4. **Create Skillset**: Set up document processing skills including text splitting and embedding generation
5. **Create and Run Indexer**: Create the indexer to process documents and start the indexing process

## What Gets Created

- **Search Index**: `policies-index` with fields for content, metadata, and vector embeddings
- **Data Source**: `policies-index-datasource` pointing to the blob storage container
- **Skillset**: `policies-index-skillset` with text processing and embedding generation
- **Indexer**: `policies-index-indexer` that processes documents and runs on a schedule

## Features

- **Vector Search**: Uses Azure OpenAI embeddings for semantic similarity search
- **Semantic Search**: Leverages Azure AI Search's semantic capabilities for relevance ranking
- **Automatic Processing**: Indexer runs every hour to process new/updated documents
- **Idempotent Operations**: Safe to run multiple times - updates existing resources instead of failing

## Troubleshooting

- Ensure you're authenticated with Azure CLI: `az login`
- Check that all required Azure resources are deployed and accessible
- Verify the service principal/managed identity has appropriate permissions for Storage and AI Search
- Monitor the indexer status in the Azure portal if documents aren't being processed