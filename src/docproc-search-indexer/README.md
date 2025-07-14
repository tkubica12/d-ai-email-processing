# Document Search Indexer Service

This service listens to DocumentContentExtractedEvent events from the Cosmos DB Change Feed and processes them for Azure AI Search indexing.

## Overview

The `docproc-search-indexer` service is part of the email processing pipeline that:

1. Listens to the Cosmos DB Change Feed for `DocumentContentExtractedEvent` events
2. Processes these events to index document content into Azure AI Search
3. Adds userId metadata for security trimming
4. Emits `DocumentIndexedEvent` events when indexing is complete

## Configuration

The service requires the following environment variables:

### Required Variables

- `AZURE_COSMOS_DB_ENDPOINT`: Cosmos DB account endpoint
- `AZURE_COSMOS_DB_DATABASE_NAME`: Database name (default: email-processing)
- `AZURE_COSMOS_DB_EVENTS_CONTAINER_NAME`: Events container name (default: events)
- `AZURE_COSMOS_DB_DOCUMENTS_CONTAINER_NAME`: Documents container name (default: documents)
- `AZURE_STORAGE_ACCOUNT_NAME`: Azure Storage account name for continuation tokens

### Optional Variables

- `AZURE_TABLE_STORAGE_ENABLED`: Enable persistent continuation token storage (default: false)
- `AZURE_TABLE_STORAGE_TABLE_NAME`: Table name for continuation tokens (default: continuationtokens)
- `LOG_LEVEL`: Logging level (default: INFO)

## Running the Service

### Prerequisites

1. Ensure you have the required Azure infrastructure deployed (Cosmos DB, Storage Account)
2. Authenticate with Azure CLI: `az login`
3. Set the appropriate environment variables in `.env` file

### Local Development

```bash
# Install dependencies
uv sync

# Run the service
uv run python main.py
```

### Current Implementation Status

**Phase 1 - Basic Event Processing**: ✅ Implemented
- [x] Listen to Change Feed for DocumentContentExtractedEvent
- [x] Parse and validate incoming events
- [x] Print event details to console
- [x] Prepare DocumentIndexedEvent structure
- [x] Continuation token storage support

**Phase 2 - Search Indexing**: 🚧 TODO
- [ ] Implement Azure AI Search client
- [ ] Create search index schema
- [ ] Index document content with metadata
- [ ] Handle indexing failures
- [ ] Emit DocumentIndexedEvent

## Service Architecture

The service follows the established patterns from other document processing services:

- **Event-driven**: Responds to Change Feed events
- **Asynchronous**: Uses asyncio for non-blocking operations
- **Resilient**: Includes retry logic and error handling
- **Stateful**: Maintains continuation tokens for reliable processing
- **Configurable**: Environment-based configuration

## Logging

The service uses structured logging with the following levels:

- **DEBUG**: Detailed processing information
- **INFO**: Normal operational messages
- **WARNING**: Potential issues that don't stop processing
- **ERROR**: Errors that may affect specific document processing
- **CRITICAL**: Service-level failures

Azure SDK logs are automatically remapped to WARNING level to reduce noise.

## Error Handling

The service includes comprehensive error handling:

- **Change Feed errors**: Retries with exponential backoff
- **Event parsing errors**: Logs and continues processing
- **Indexing failures**: Will be handled gracefully when implemented
- **Service shutdown**: Graceful cleanup of resources

## Testing

Run the service locally and verify it correctly processes DocumentContentExtractedEvent events by monitoring the logs for event details and prepared DocumentIndexedEvent structures.