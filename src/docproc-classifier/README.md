# Document Classifier Service

This service processes document classification by listening to Cosmos DB Change Feed for `DocumentContentExtractedEvent` events. It classifies documents using OpenAI API and updates document records with classification results.

## Features

- Listens to Cosmos DB Change Feed for `DocumentContentExtractedEvent` events
- Classifies documents using OpenAI API with predefined document types
- Stores continuation tokens in Azure Table Storage for stateful processing
- Supports graceful shutdown and error handling

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
- `OPENAI_API_KEY`: OpenAI API key
- `OPENAI_MODEL`: OpenAI model (default: gpt-4o-mini)

## Running the Service

1. Install dependencies:
```bash
uv sync
```

2. Set up environment variables in `.env` file

3. Run the service:
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

## Logging

The service uses structured logging with configurable log levels. Set `LOG_LEVEL` environment variable to control verbosity:
- `DEBUG`: Detailed debug information
- `INFO`: General information (default)
- `WARNING`: Warning messages
- `ERROR`: Error messages
- `CRITICAL`: Critical errors