# Document Parser - Foundry Service

## Overview
The Document Parser Foundry service processes documents using Azure Document Intelligence (formerly Form Recognizer) for enterprise-grade document analysis. It's one of two parallel document processing services in the fan-out pattern.

## Architecture Decisions

### Event Sourcing Pattern
- **Event Consumption**: Listens to Cosmos DB Change Feed for `DocumentUploadedEvent`
- **Event Publishing**: Emits `DocumentContentExtractedEvent` after processing completion
- **Idempotent Processing**: Uses event IDs to prevent duplicate processing

### Data Storage
- **Events Container**: Cosmos DB container `events` with Change Feed enabled
  - Partition Key: `submissionId`
  - Events are immutable and append-only
- **Documents Container**: Cosmos DB container `documents` for processed document results
  - Partition Key: `documentUrl` (unique identifier)
  - Document ID: Generated GUID for each document record
  - Content stored in `content` attribute as Markdown

## Processing Approach

### Azure Document Intelligence Layout Analysis
1. **Document Processing Pipeline**:
   - Receives `DocumentUploadedEvent` from Change Feed
   - Downloads blob from Azure Storage using document URL
   - Submits to Azure Document Intelligence Layout API
   - Converts extracted content to structured Markdown format
   - Stores result in Cosmos DB documents container

2. **Layout Analysis Features**:
   - Optical Character Recognition (OCR) for all text
   - Document structure detection (headings, paragraphs, lists)
   - Table extraction with proper Markdown formatting
   - Reading order optimization for logical flow
   - Multi-column layout handling

3. **Markdown Output Structure**:
   - Hierarchical headings (H1-H6) 
   - Formatted tables with proper alignment
   - Preserved text formatting (bold, italic)
   - Ordered and unordered lists
   - Document metadata and confidence scores

### Supported Document Types
- PDFs (text and image-based)
- Images (JPEG, PNG, BMP, TIFF)
- Microsoft Office documents
- Forms and structured documents
- Invoices and receipts
- Business cards and IDs

## Responsibilities

1. **Event Processing**
   - Monitors Cosmos DB Change Feed on `events` container
   - Filters for `DocumentUploadedEvent` event type
   - Maintains processing state to avoid duplicate processing
   - Handles event ordering and potential delays

2. **Document Download**
   - Retrieves document from Azure Blob Storage using URL from event
   - Handles various document formats (PDF, images, Office docs)
   - Manages temporary storage for processing
   - Implements retry logic for download failures

3. **Document Intelligence Processing**
   - Submits documents to Azure Document Intelligence Layout API
   - Polls for completion of asynchronous processing
   - Handles API rate limiting and throttling
   - Manages processing timeouts and failures

4. **Content Storage**
   - Stores extracted Markdown content in `documents` container
   - Updates document record with `content` attribute
   - Includes processing metadata and confidence scores
   - Maintains document processing history

5. **Event Emission**
   - Emits `DocumentContentExtractedEvent` to events container
   - Includes processing status and metadata
   - Triggers downstream services for further processing

## Event Flow

```
Cosmos DB Change Feed → DocumentUploadedEvent Detection
                                     ↓
                              Event Filtering & Validation
                                     ↓
                              Blob Download from Storage
                                     ↓
                        Document Intelligence Layout API
                                     ↓
                              Async Processing Wait
                                     ↓
                           Markdown Content Extraction
                                     ↓
                      Store Content in Documents Container
                                     ↓
                        Emit DocumentContentExtractedEvent
```

## Data Structures

### Input Event: DocumentUploadedEvent
```json
{
  "id": "event-guid",
  "eventType": "DocumentUploadedEvent",
  "submissionId": "submission-guid",
  "documentUrl": "https://storage.blob.core.windows.net/...",
  "fileName": "document.pdf",
  "contentType": "application/pdf",
  "timestamp": "2025-07-09T10:00:00Z"
}
```

### Document Store Record
```json
{
  "id": "document-guid",
  "documentUrl": "https://storage.blob.core.windows.net/...",
  "submissionId": "submission-guid",
  "fileName": "document.pdf",
  "content": "# Document Title\n\nExtracted markdown content...",
  "processingMetadata": {
    "processor": "foundry",
    "apiVersion": "2023-07-31",
    "confidenceScore": 0.95,
    "processedAt": "2025-07-09T10:05:00Z"
  }
}
```

### Output Event: DocumentContentExtractedEvent
```json
{
  "id": "event-guid",
  "eventType": "DocumentContentExtractedEvent",
  "submissionId": "submission-guid",
  "documentUrl": "https://storage.blob.core.windows.net/...",
  "documentId": "document-guid",
  "contentLength": 15420,
  "confidenceScore": 0.95,
  "timestamp": "2025-07-09T10:05:00Z"
}
```

## Technology Stack
- **Framework**: FastAPI for health checks and monitoring
- **Document Processing**: Azure Document Intelligence SDK (Layout API)
- **Event Store**: Cosmos DB Change Feed monitoring
- **Storage**: Azure Blob Storage for document retrieval
- **Authentication**: DefaultAzureCredential with Managed Identity
- **Port**: 8003 (for local development)

## Key Features
- **Markdown Conversion**: Converts documents to structured Markdown format
- **Layout Preservation**: Maintains document structure and formatting
- **Change Feed Processing**: Real-time event processing from Cosmos DB
- **Idempotent Operations**: Prevents duplicate processing of documents
- **Error Recovery**: Robust handling of processing failures and retries
- **Multi-Format Support**: Processes PDFs, images, and Office documents

## Setup and Configuration

### Environment Variables
- `AZURE_COSMOSDB_ENDPOINT`: Cosmos DB account endpoint
- `AZURE_COSMOSDB_DATABASE_NAME`: Database name (default: email-processing)
- `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT`: Document Intelligence service endpoint
- `AZURE_STORAGE_ACCOUNT_NAME`: Storage account for blob access
- `PORT`: Service port (default: 8003)

### Required Permissions
- **Cosmos DB**: Read access to events container, write access to documents container
- **Document Intelligence**: Analyze documents permission
- **Storage Account**: Blob read access for document retrieval
