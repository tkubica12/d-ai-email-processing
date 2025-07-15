# Submission Intake Service

## Overview
The Submission Intake service is the entry point for the event sourcing workflow. It processes incoming submission messages from Service Bus, creates submission records, and initiates document processing by emitting events to the event store.

## Architecture Decisions

### Event Sourcing Pattern
- **Event Store**: Cosmos DB container `events` with Change Feed enabled
- **Event Publishing**: Appends events to event store, triggering downstream processing
- **Immutable Events**: All events are append-only and provide complete audit trail

### Data Storage
- **Submissions Container**: Cosmos DB container for submission metadata
- **Partition Key**: `submissionId` for optimal performance
- **Document URLs**: Stores blob storage URLs for each submitted document

## Responsibilities

1. **Service Bus Processing**
   - Listens to Service Bus topic `new-submissions`
   - Processes submission messages from client-web application
   - Extracts document URLs from blob storage references

2. **Submission Registration**
   - Creates submission record in `submissions` container
   - Tracks submission metadata (user, timestamp, document count)
   - Generates unique document IDs for each uploaded file

3. **Event Emission**
   - Emits `SubmissionCreated` event with submission details
   - Emits `DocumentUploadedEvent` for each document in the submission
   - Events trigger downstream document processing services

## Event Flow

```
Service Bus Message → Submission Record Creation → Event Emission
                                                      ↓
                                            SubmissionCreated Event
                                                      ↓
                                          DocumentUploadedEvent (per document)
```

## Technology Stack
- **Runtime**: Python 3.12+ with async/await
- **Message Processing**: Azure Service Bus with async client
- **Storage**: Azure Cosmos DB with async client
- **Authentication**: DefaultAzureCredential with Managed Identity
- **Data Validation**: Pydantic models
- **Logging**: Python logging with structured format

## Data Models

### Submission Document Schema
Following the Design.md specification:

```json
{
  "id": "submission-guid",
  "submissionId": "submission-guid",
  "userId": "user@example.com",
  "submittedAt": "2025-07-07T10:00:00Z",
  "documents": [
    {
      "documentUrl": "https://storage.blob.core.windows.net/submission-guid/document1.pdf",
      "processed": null,
      "type": null
    }
  ],
  "evaluationResults": null
}
```

### Document Record Schema
Individual document records created in the documents container:

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "documentUrl": "https://storage.blob.core.windows.net/submission-guid/document1.pdf",
  "submissionId": "submission-guid",
  "userId": "user@example.com",
  "content": null,
  "type": null,
  "summary": null,
  "extractedData": null,
  "firstProcessedAt": "2025-07-07T10:00:00Z",
  "lastProcessedAt": "2025-07-07T10:00:00Z"
}
```

**Note**: The `id` field is a generated GUID for each document record, while `documentUrl` serves as the partition key for efficient queries.

### Processing Flow
1. **Message Reception**: Service Bus message with submission details
2. **Data Validation**: Pydantic model validation of message content
3. **Document Storage**: Create submission document in Cosmos DB
4. **Event Emission**: (Future) Emit events for document processing pipeline

## Development Setup

### Prerequisites
- Python 3.12+
- Azure CLI logged in (`az login`)
- Access to Azure Service Bus namespace

### Local Development
1. **Install dependencies**:
   ```bash
   cd src/submission-intake
   pip install -e .
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your Azure Service Bus configuration
   ```

3. **Deploy infrastructure** (if not already deployed):
   ```bash
   cd infra
   terraform plan
   terraform apply
   ```

4. **Run the service**:
   ```bash
   python main.py
   ```

### Environment Variables
- `AZURE_SERVICE_BUS_FQDN`: Service Bus namespace FQDN
- `AZURE_SERVICE_BUS_TOPIC_NAME`: Topic name for submissions
- `AZURE_SERVICE_BUS_SUBSCRIPTION_NAME`: Subscription name for this service
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

### Testing
The service will log received messages and acknowledge them automatically. Monitor logs to verify message processing:

```bash
# Run with debug logging
LOG_LEVEL=DEBUG python main.py
```

## Service Behavior
- **Message Reception**: Receives messages from Service Bus topic
- **Validation**: Validates message format using Pydantic models
- **Logging**: Logs submission details and processing status
- **Acknowledgment**: Acknowledges successful processing to prevent redelivery
- **Error Handling**: Abandons messages on processing errors for redelivery
- **Port**: 8001 (for local development)

## Key Features
- **Idempotent Processing**: Handles duplicate Service Bus messages safely
- **Error Handling**: Comprehensive error handling with retry logic
- **Monitoring**: Health check endpoints and structured logging
- **Scalability**: Stateless design enables horizontal scaling

## Container Deployment

The service is deployed as a Container App with:
- **Background Service**: No ingress configuration (internal service)
- **Minimum 1 replica**: Ensures continuous message processing
- **CPU-based auto-scaling**: Scales based on processing load
- **Managed identity authentication**: Secure access to Azure services
- **Full RBAC permissions**: Service Bus, Cosmos DB, Storage access

### Environment Variables in Container
- `AZURE_CLIENT_ID` - Managed identity client ID
- `AZURE_SERVICE_BUS_FQDN` - Service Bus namespace endpoint
- `AZURE_SERVICE_BUS_TOPIC_NAME` - Topic name for submission events
- `AZURE_SERVICE_BUS_SUBSCRIPTION_NAME` - Subscription name
- `AZURE_COSMOS_DB_ENDPOINT` - Cosmos DB account endpoint
- `AZURE_COSMOS_DB_DATABASE_NAME` - Database name
- `AZURE_COSMOS_DB_*_CONTAINER_NAME` - Container names
- `AZURE_STORAGE_ACCOUNT_NAME` - Storage account name
- `APPLICATIONINSIGHTS_CONNECTION_STRING` - Application monitoring
