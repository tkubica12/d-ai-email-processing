# Submission Trigger Service

The submission-trigger service monitors document processing events and maintains a projection of submission status. It emits a `SubmissionPreparationCompletedEvent` when all documents in a submission have been fully processed by the three docproc services.

## Purpose

This service tracks the processing status of documents within submissions and determines when a submission is ready for analysis by the submission-analyzer service.

## Monitored Events

The service listens to the following events from the Cosmos DB change feed:

- **SubmissionCreated**: Creates initial projection with all documents marked as unprocessed
- **DocumentClassifiedEvent**: Marks document as classified when successful
- **DocumentIndexedEvent**: Marks document as indexed when successful  
- **DocumentDataExtractedEvent**: Marks document as data extracted when successful

## Event Emission

When all documents in a submission have been:
- Classified (DocumentClassifiedEvent)
- Indexed (DocumentIndexedEvent)
- Data extracted (DocumentDataExtractedEvent)

The service emits a `SubmissionPreparationCompletedEvent` to trigger the submission-analyzer service.

## Data Storage

The service maintains a projection in the `submissionstrigger` Cosmos DB container with the following structure:

```json
{
  "id": "submission-guid",
  "submissionId": "submission-guid",
  "userId": "user@example.com",
  "totalDocuments": 3,
  "documents": {
    "https://storage.blob.core.windows.net/submission-guid/doc1.pdf": {
      "classified": true,
      "indexed": true,
      "dataExtracted": false
    },
    "https://storage.blob.core.windows.net/submission-guid/doc2.pdf": {
      "classified": false,
      "indexed": false,
      "dataExtracted": false
    }
  },
  "createdAt": "2025-07-16T10:00:00Z",
  "updatedAt": "2025-07-16T10:05:00Z"
}
```

## Configuration

The service is configured via environment variables:

- `AZURE_COSMOS_DB_ENDPOINT`: Cosmos DB endpoint URL
- `AZURE_COSMOS_DB_DATABASE_NAME`: Database name (email-processing)
- `AZURE_COSMOS_DB_EVENTS_CONTAINER_NAME`: Events container name (events)
- `AZURE_COSMOS_DB_DOCUMENTS_CONTAINER_NAME`: Documents container name (documents)
- `AZURE_COSMOS_DB_SUBMISSIONS_CONTAINER_NAME`: Submissions container name (submissions)
- `AZURE_COSMOS_DB_SUBMISSIONS_TRIGGER_CONTAINER_NAME`: Trigger container name (submissionstrigger)
- `AZURE_STORAGE_ACCOUNT_NAME`: Storage account for continuation tokens
- `AZURE_TABLE_STORAGE_ENABLED`: Enable persistent continuation tokens (optional)
- `LOG_LEVEL`: Logging level (INFO, DEBUG, etc.)

## Running the Service

```bash
# Install dependencies
uv sync

# Run the service
uv run python main.py
```

## Architecture

The service uses:
- **Change Feed Processing**: Monitors Cosmos DB events container for relevant events
- **Projection Maintenance**: Maintains document processing status in submissionstrigger container
- **Event Emission**: Publishes completion events to the events container
- **Continuation Tokens**: Supports persistent processing state across restarts  