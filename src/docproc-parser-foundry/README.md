# Document Parser - Foundry Service

## Overview
The Document Parser Foundry service processes documents using Azure Document Intelligence (formerly Form Recognizer) for enterprise-grade document analysis. It's one of two parallel document processing services in the fan-out pattern.

## Architecture Decisions

### Event Sourcing Pattern
- **Event Consumption**: Listens to Cosmos DB Change Feed for `DocumentUploadedEvent`
- **Event Publishing**: Emits `DocumentProcessedEvent` after processing completion
- **Idempotent Processing**: Uses event IDs to prevent duplicate processing

### Data Storage
- **Documents Container**: Cosmos DB container for processed document results
- **Partition Key**: `submissionId` for query optimization
- **Result Storage**: Stores extracted text, structured data, and analysis results

## Processing Approach

### Azure Document Intelligence Pipeline
1. **Document Analysis**: Uses Azure Document Intelligence for:
   - Optical Character Recognition (OCR)
   - Layout analysis and structure detection
   - Form field extraction
   - Table and key-value pair identification
   - Handwriting recognition

2. **Structured Extraction**: Produces:
   - Raw text content
   - Document structure metadata
   - Confidence scores for extracted data
   - Bounding box coordinates for layout

### Supported Document Types
- PDFs (text and image-based)
- Images (JPEG, PNG, BMP, TIFF)
- Microsoft Office documents
- Forms and structured documents
- Invoices and receipts
- Business cards and IDs

## Responsibilities

1. **Event Processing**
   - Monitors Change Feed for `DocumentUploadedEvent`
   - Filters events for documents requiring Document Intelligence processing
   - Maintains processing state to avoid duplicates

2. **Document Analysis**
   - Submits documents to Azure Document Intelligence service
   - Handles asynchronous processing results
   - Extracts structured data and metadata
   - Generates confidence scores and quality metrics

3. **Result Storage**
   - Stores processed results in `documents` container
   - Includes processor identifier (`foundry`)
   - Maintains detailed analysis metadata and confidence scores

4. **Event Emission**
   - Emits `DocumentProcessedEvent` with structured results
   - Includes processing status and detailed metrics
   - Triggers aggregation service for fan-in processing

## Event Flow

```
DocumentUploadedEvent → Document Upload to Document Intelligence
                                      ↓
                              Async Processing Wait
                                      ↓
                              Result Retrieval
                                      ↓
                           Structured Data Storage
                                      ↓
                          DocumentProcessedEvent
```

## Technology Stack
- **Framework**: FastAPI for health checks and monitoring
- **Document Processing**: Azure Document Intelligence SDK
- **Event Store**: Cosmos DB Change Feed
- **Authentication**: DefaultAzureCredential with Managed Identity
- **Port**: 8003 (for local development)

## Key Features
- **Enterprise-Grade OCR**: High-accuracy text extraction from complex documents
- **Structured Analysis**: Extracts forms, tables, and key-value pairs
- **Confidence Scoring**: Provides quality metrics for extracted data
- **Async Processing**: Handles long-running document analysis operations
- **Multi-Format Support**: Processes various document types and formats
