# Document Classifier Service

This service processes document classification by listening to Cosmos DB Change Feed for `DocumentContentExtractedEvent` events. It classifies documents using Azure OpenAI API and updates document records with classification results.

## Features

- Listens to Cosmos DB Change Feed for `DocumentContentExtractedEvent` events
- Classifies documents using Azure OpenAI API with predefined document types
- Emits `DocumentClassifiedEvent` after successful classification
- Stores continuation tokens in Azure Table Storage for stateful processing
- Supports graceful shutdown and error handling
- Uses structured outputs to ensure consistent classification results

## Configuration

Configuration is loaded from environment variables. Copy `.env.example` to `.env` and update with your values:

```bash
cp .env.example .env
```

Required environment variables:
- `AZURE_COSMOS_DB_ENDPOINT`: Cosmos DB endpoint URL
- `AZURE_COSMOS_DB_DATABASE_NAME`: Database name
- `AZURE_COSMOS_DB_EVENTS_CONTAINER_NAME`: Events container name
- `AZURE_COSMOS_DB_DOCUMENTS_CONTAINER_NAME`: Documents container name
- `AZURE_STORAGE_ACCOUNT_NAME`: Storage account name
- `AZURE_OPENAI_ENDPOINT`: Azure OpenAI service endpoint
- `AZURE_OPENAI_MODEL`: Azure OpenAI model deployment name (default: gpt-4o-mini)

## Running the Service

1. Install dependencies:
```bash
uv sync
```

2. Ensure you are authenticated with Azure:
```bash
az login
```

3. Set up environment variables in `.env` file

4. Run the service:
```bash
uv run python main.py
```

## Document Types

The service classifies documents into the following types:
- `invoice`: Invoice documents  
- `contract`: Contract documents
- `bankStatement`: Bank statement documents
- `submissionNotes`: Submission notes
- `other`: Other document types

## Event Flow

1. Service listens for `DocumentContentExtractedEvent` events
2. Fetches document content from Cosmos DB documents container
3. Classifies document using Azure OpenAI with system prompt template
4. Updates document record with classification results (`type` and `summary` fields)
5. Emits `DocumentClassifiedEvent` for downstream processing

## Logging

The service uses structured logging with configurable log levels. Set `LOG_LEVEL` environment variable to control verbosity:
- `DEBUG`: Detailed debug information including OpenAI API calls
- `INFO`: General information (default)
- `WARNING`: Warning messages
- `ERROR`: Error messages
- `CRITICAL`: Critical errors

## Container Deployment

The service is deployed as a Container App with:
- **Background Service**: No ingress configuration (internal change feed processor)
- **Minimum 1 replica**: Ensures continuous change feed processing
- **Maximum 3 replicas**: Limited due to stateful change feed processing
- **CPU-based auto-scaling**: Scales based on AI processing workload
- **Managed identity authentication**: Secure access to Azure services

### Environment Variables in Container
- `AZURE_CLIENT_ID` - Managed identity client ID
- `AZURE_COSMOS_DB_ENDPOINT` - Cosmos DB account endpoint
- `AZURE_COSMOS_DB_DATABASE_NAME` - Database name
- `AZURE_COSMOS_DB_EVENTS_CONTAINER_NAME` - Events container for change feed
- `AZURE_COSMOS_DB_DOCUMENTS_CONTAINER_NAME` - Documents container for updates
- `AZURE_OPENAI_ENDPOINT` - Azure OpenAI service endpoint
- `AZURE_OPENAI_MODEL` - GPT-4.1 model deployment name
- `AZURE_STORAGE_ACCOUNT_NAME` - Storage account name
- `AZURE_TABLE_STORAGE_ENABLED` - Enable continuation token persistence
- `AZURE_TABLE_STORAGE_TABLE_NAME` - Table name for continuation tokens
- `APPLICATIONINSIGHTS_CONNECTION_STRING` - Application monitoring

### RBAC Permissions
- **Cosmos DB**: Custom role for data plane operations
- **Storage Account**: Blob Data Contributor for document access
- **Storage Account**: Table Data Contributor for continuation tokens
- **Azure OpenAI**: Cognitive Services OpenAI User for classification

### Docker Configuration
- Python 3.12 slim base image with OpenAI SDK
- UV for efficient dependency management
- Async processing with structured AI outputs
- Jinja2 templating for dynamic prompts