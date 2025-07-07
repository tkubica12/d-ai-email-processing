# Document Processing Aggregator Service

## Overview
The Document Processing Aggregator service implements the fan-in pattern, coordinating results from multiple document processors and determining when all processing is complete for each document and submission.

## Architecture Decisions

### Event Sourcing Pattern
- **Event Consumption**: Listens to Cosmos DB Change Feed for `DocumentProcessedEvent`
- **Event Publishing**: Emits aggregation events when processing milestones are reached
- **State Tracking**: Maintains processing state in Cosmos DB for coordination

### Data Storage
- **Processing State Container**: Cosmos DB container for tracking document processing status
- **Partition Key**: `submissionId` for efficient state queries
- **Aggregation Logic**: Tracks completion status across multiple processors

## Fan-In Coordination

### Document-Level Aggregation
1. **Processor Tracking**: Monitors completion from both processors:
   - `docproc-parser-markitdown`
   - `docproc-parser-foundry`

2. **Completion Detection**: Emits `DocumentFullyProcessedEvent` when:
   - Both processors have completed successfully
   - Or maximum retry attempts reached for failed processors

### Submission-Level Aggregation
1. **Document Counting**: Tracks total documents in submission
2. **Progress Monitoring**: Counts completed documents
3. **Submission Completion**: Emits `SubmissionDocumentsCompleteEvent` when all documents processed

## Responsibilities

1. **Event Processing**
   - Monitors Change Feed for `DocumentProcessedEvent`
   - Updates document processing state
   - Tracks processor completion status

2. **State Management**
   - Maintains document processing state in Cosmos DB
   - Tracks which processors have completed for each document
   - Monitors submission-level progress

3. **Aggregation Logic**
   - Determines when document processing is complete
   - Calculates submission-level completion status
   - Handles partial failures and retry scenarios

4. **Event Emission**
   - Emits `DocumentFullyProcessedEvent` for completed documents
   - Emits `SubmissionDocumentsCompleteEvent` for completed submissions
   - Triggers downstream analysis services

## Event Flow

```
DocumentProcessedEvent → State Update → Completion Check
                                             ↓
                                    DocumentFullyProcessedEvent
                                             ↓
                               Submission Progress Check
                                             ↓
                            SubmissionDocumentsCompleteEvent
```

## State Tracking Schema

### Document Processing State
```json
{
  "id": "document-guid",
  "submissionId": "submission-guid", 
  "processors": {
    "markitdown": {
      "status": "completed|failed|pending",
      "timestamp": "2025-07-07T10:00:00Z",
      "error": "error-message-if-failed"
    },
    "foundry": {
      "status": "completed|failed|pending", 
      "timestamp": "2025-07-07T10:00:00Z",
      "error": "error-message-if-failed"
    }
  },
  "allProcessorsComplete": true
}
```

### Submission Processing State
```json
{
  "id": "submission-guid",
  "submissionId": "submission-guid",
  "totalDocuments": 3,
  "completedDocuments": 2,
  "failedDocuments": 0,
  "allDocumentsProcessed": false,
  "lastUpdated": "2025-07-07T10:00:00Z"
}
```

## Technology Stack
- **Framework**: FastAPI for health checks and monitoring
- **Event Store**: Cosmos DB Change Feed
- **State Storage**: Cosmos DB with upsert operations
- **Authentication**: DefaultAzureCredential with Managed Identity
- **Port**: 8004 (for local development)

## Key Features
- **Coordination Logic**: Manages complex fan-in scenarios
- **Fault Tolerance**: Handles partial failures and processor timeouts
- **Progress Tracking**: Provides visibility into processing status
- **Idempotent Operations**: Safely handles duplicate events
- **Scalable Design**: Stateless processing with external state storage
