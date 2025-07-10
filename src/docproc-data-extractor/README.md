# Document Data Extractor Service

This service processes document data extraction by listening to Cosmos DB Change Feed for `DocumentContentExtractedEvent` events. It extracts structured information from documents using Azure OpenAI API and updates document records with extracted data.

## Features

- Listens to Cosmos DB Change Feed for `DocumentContentExtractedEvent` events
- Extracts structured information from documents using Azure OpenAI API
- Emits `DocumentDataExtractedEvent` after successful data extraction
- Stores continuation tokens in Azure Table Storage for stateful processing
- Supports graceful shutdown and error handling
- Uses structured outputs to ensure consistent data extraction results

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

## Document Data Extraction

The service extracts structured information from documents based on their type:
- `invoice`: Invoice number, total amount, currency, due date, vendor
- `contract`: Contract terms, parties, dates, amounts
- `bankStatement`: Account details, transactions, balances
- `submissionNotes`: Key points, requirements, deadlines
- `other`: Generic data extraction based on document content

## Event Flow

1. Service listens for `DocumentContentExtractedEvent` events
2. Fetches document content from Cosmos DB documents container
3. Extracts structured data using Azure OpenAI with system prompt template
4. Updates document record with extracted data (`extractedData` field)
5. Emits `DocumentDataExtractedEvent` for downstream processing

## Logging

The service uses structured logging with configurable log levels. Set `LOG_LEVEL` environment variable to control verbosity:
- `DEBUG`: Detailed debug information including OpenAI API calls
- `INFO`: General information (default)
- `WARNING`: Warning messages
- `ERROR`: Error messages
- `CRITICAL`: Critical errors