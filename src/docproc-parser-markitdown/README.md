# Document Parser - Markitdown Service

## Overview
The Document Parser Markitdown service processes documents using LLM and Markitdown library for text extraction and analysis. It's one of two parallel document processing services in the fan-out pattern.

## Architecture Decisions

### Event Sourcing Pattern
- **Event Consumption**: Listens to Cosmos DB Change Feed for `DocumentUploadedEvent`
- **Event Publishing**: Emits `DocumentProcessedEvent` after processing completion
- **Idempotent Processing**: Uses event IDs to prevent duplicate processing

### Data Storage
- **Documents Container**: Cosmos DB container for processed document results
- **Partition Key**: `submissionId` for query optimization
- **Result Storage**: Stores extracted text, metadata, and processing artifacts

## Processing Approach

### Markitdown + LLM Pipeline
1. **Document Download**: Retrieves document from Azure Blob Storage
2. **Text Extraction**: Uses Markitdown library for initial text extraction
3. **LLM Enhancement**: Applies LLM for:
   - Text cleanup and formatting
   - Metadata extraction
   - Content summarization
   - Structure identification

### Supported Document Types
- PDF documents
- Microsoft Word (.docx, .doc)
- Text files (.txt)
- Images with OCR capabilities
- PowerPoint presentations

## Responsibilities

1. **Event Processing**
   - Monitors Change Feed for `DocumentUploadedEvent`
   - Filters events for documents requiring LLM processing
   - Maintains processing state to avoid duplicates

2. **Document Processing**
   - Downloads documents from blob storage
   - Extracts text using Markitdown
   - Enhances extraction with LLM analysis
   - Generates structured metadata

3. **Result Storage**
   - Stores processed text in `documents` container
   - Includes processor identifier (`markitdown`)
   - Maintains processing timestamps and status

4. **Event Emission**
   - Emits `DocumentProcessedEvent` with results
   - Includes success/failure status and error details
   - Triggers aggregation service for fan-in processing

## Event Flow

```
DocumentUploadedEvent → Document Download → Markitdown Processing
                                                  ↓
                                            LLM Enhancement
                                                  ↓
                                           Result Storage
                                                  ↓
                                        DocumentProcessedEvent
```

## Technology Stack
- **Framework**: FastAPI for health checks and monitoring
- **Text Processing**: Markitdown library
- **LLM Integration**: Azure OpenAI or other LLM providers
- **Event Store**: Cosmos DB Change Feed
- **Port**: 8002 (for local development)

## Key Features
- **Parallel Processing**: Designed for concurrent document processing
- **Error Recovery**: Comprehensive error handling with retry mechanisms
- **Quality Assurance**: LLM validation of extracted text quality
- **Monitoring**: Detailed logging and processing metrics
