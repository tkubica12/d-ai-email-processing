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
- **Framework**: FastAPI for REST endpoints and health checks
- **Event Store**: Cosmos DB with Change Feed
- **Authentication**: DefaultAzureCredential with Managed Identity
- **Port**: 8001 (for local development)

## Key Features
- **Idempotent Processing**: Handles duplicate Service Bus messages safely
- **Error Handling**: Comprehensive error handling with retry logic
- **Monitoring**: Health check endpoints and structured logging
- **Scalability**: Stateless design enables horizontal scaling
