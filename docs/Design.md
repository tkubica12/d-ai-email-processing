# Email Processing System Design

## Overview
This system processes incoming emails containing submission requests using AI to extract relevant information and generate potential responses. The system is built on Azure services with a focus on scalability, reliability, and maintainability.

## Process Flow
1. **Request Ingestion**: User submits a request via email or web form
   - **Email Trigger**: Traditional email-based submissions processed automatically
   - **Client Web Application**: Browser-based form allowing users to create submissions with:
     - Source email address entry
     - Message body composition
     - Multiple file attachments (0 or more)
     - Generates unique submission GUID
     - Stores files in Azure Blob Storage container (named with submission GUID)
     - Publishes event to Service Bus Topic with user ID, submission GUID, and document URLs
2. **Request Registration**: System generates unique identifier for the submission
3. **Content Storage**: Message body and attachments are stored for processing
5. **Document Analysis**: AI analyzes all submitted documents through a multi-step pipeline:
   - **Content Extraction**: Azure Document Intelligence converts documents to structured Markdown
   - **Classification & Summarization**: LLM classifies document types and generates summaries
   - **Search Indexing**: Content is indexed in Azure AI Search with metadata
   - **Data Extraction**: LLM extracts structured information based on document type
   - **Aggregation**: System tracks completion of all processing steps per document
5. **Submission Evaluation**: AI agent evaluates the complete submission to:
   - Identify missing information
   - Detect inconsistencies or errors
   - Generate evaluation results
6. **Operator Support**: AI-powered interface enables operators to:
   - Chat about user submissions and documents
   - Get recommended actions
   - Generate email responses

## Solution Architectures

### Architecture Option 1: Workflow Orchestration with Logic Apps
This approach leverages the orchestration capabilities of Azure Logic Apps to manage the entire process flow as a coordinated workflow.

**Characteristics:**
- Centralized orchestration through Logic Apps workflow
- Sequential and parallel processing controlled by the orchestrator
- Direct service-to-service communication without intermediate messaging
- Workflow state management handled by Logic Apps runtime
- Error handling and retry logic built into workflow definition
- Real-time processing with immediate feedback
- Simpler data model without intermediate state tracking

**Process Implementation:**
- Single Logic App workflow triggered by email/web form submission
- Workflow orchestrates all steps from content storage through final evaluation
- Direct calls to Azure services (Blob Storage, AI services, Cosmos DB, AI Search)
- Parallel document processing managed by workflow branching
- Synchronous processing with workflow waiting for completion of each step
- Final results available immediately upon workflow completion

### Architecture Option 2: Choreography with Event Sourcing
This approach uses event-driven architecture with event sourcing patterns to implement asynchronous processing through coordinated services.

**Characteristics:**
- Decoupled services communicating through events
- Event sourcing pattern using Cosmos DB as event store
- Change feed triggers for asynchronous processing
- Each service responds to relevant events and publishes new events
- Natural scalability and resilience through loose coupling
- Complete audit trail through event history
- Eventually consistent processing model

**Process Implementation:**
- Initial submission creates events in Cosmos DB event store
- Change feed triggers subsequent processing steps
- Each processing stage (storage, analysis, evaluation) operates independently
- Services listen to change feed for relevant events and process accordingly
- Document analysis services process events in parallel
- Final evaluation triggered when all document processing events are complete
- Event sourcing provides complete history and enables replay/recovery
- Asynchronous processing allows for high throughput and scalability

#### Detailed Architecture

**Event Store:** Cosmos DB container with Change Feed enabled
- Container: `events`
- Partition Key: `submissionId`
- Events are immutable and append-only

**Document Store:** Cosmos DB container for processed document results
- Container: `documents` 
- Partition Key: `documentUrl` (unique identifier)
- Document ID: `documentUrl`
- Schema:
  ```json
  {
    "id": "https://storage.blob.core.windows.net/submission-guid/document1.pdf",
    "documentUrl": "https://storage.blob.core.windows.net/submission-guid/document1.pdf",
    "content": "# Document Title\n\nFull markdown content extracted from document using Azure Document Intelligence...",
    "type": "invoice",
    "summary": "AI-generated summary of document content...",
    "extractedData": {
      "invoiceNumber": "INV-2025-001",
      "amount": 1250.00,
      "currency": "USD",
      "dueDate": "2025-08-07",
      "vendor": "Acme Corp"
    },
    "metadata": {
      "processingTimestamp": "2025-07-07T10:05:00Z",
      "documentLength": 15000,
      "language": "en",
      "confidence": 0.95,
      "indexed": true
    }
  }
  ```

**Submission Store:** Cosmos DB container for submission records
- Container: `submissions`
- Partition Key: `submissionId`
- Schema:
  ```json
  {
    "id": "submission-guid",
    "submissionId": "submission-guid", 
    "userId": "user@example.com",
    "submittedAt": "2025-07-07T10:00:00Z",
    "documents": [
      {
        "documentUrl": "https://storage.blob.core.windows.net/submission-guid/document1.pdf",
        "processed": true,
        "type": "invoice"
      },
      {
        "documentUrl": "https://storage.blob.core.windows.net/submission-guid/document2.docx",
        "processed": true,
        "type": "contract"
      }
    ],
    "evaluationResults": {
      "completeness": 0.85,
      "recommendations": ["Request additional documentation for item X"],
      "issues": [],
      "analysisTimestamp": "2025-07-07T10:15:00Z"
    }
  }
  ```

**Service Architecture:**
1. **submission-intake**
   - Listens to Service Bus topic for new submissions
   - Creates submission record in submissions container
   - Emits `SubmissionCreated` event with document URLs
   - Emits `DocumentUploadedEvent` for each document

2. **docproc-parser-foundry**
   - Listens to Change Feed for `DocumentUploadedEvent`
   - Processes documents using Azure Document Intelligence to convert to Markdown
   - Stores content in documents container
   - Emits `DocumentContentExtractedEvent`

3. **docproc-classifier**
   - Listens to Change Feed for `DocumentContentExtractedEvent`
   - Uses LLM to classify document type and generate summary
   - Updates document record with type and summary
   - Emits `DocumentClassifiedEvent`

4. **docproc-search-indexer**
   - Listens to Change Feed for `DocumentContentExtractedEvent`
   - Ingests document content into Azure AI Search with metadata
   - Emits `DocumentIndexedEvent`

5. **docproc-data-extractor**
   - Listens to Change Feed for `DocumentContentExtractedEvent`
   - Uses LLM to extract structured information
   - Updates document record with extractedData
   - Emits `DocumentDataExtractedEvent`

6. **docproc-aggregator**
   - Listens to Change Feed for `DocumentClassifiedEvent` and `DocumentDataExtractedEvent`
   - Tracks completion of classification and data extraction for each document
   - Emits `DocumentFullyProcessedEvent` when both are complete
   - Emits `SubmissionDocumentsCompleteEvent` when all documents in submission are processed

7. **submission-analyzer**
   - Listens to Change Feed for `SubmissionDocumentsCompleteEvent`
   - Updates submission record with processed flags and types for each document
   - Performs final AI analysis of complete submission
   - Updates submission record with evaluation results
   - Emits `SubmissionAnalysisCompleteEvent`

#### Event Formats

**SubmissionCreated**
```json
{
  "id": "uuid",
  "eventType": "SubmissionCreated",
  "submissionId": "submission-guid",
  "userId": "user@example.com",
  "timestamp": "2025-07-07T10:00:00Z",
  "data": {
    "documentUrls": [
      "https://storage.blob.core.windows.net/submission-guid/document1.pdf",
      "https://storage.blob.core.windows.net/submission-guid/document2.docx"
    ],
    "containerName": "submission-guid"
  }
}
```

**DocumentUploadedEvent**
```json
{
  "id": "uuid",
  "eventType": "DocumentUploadedEvent", 
  "submissionId": "submission-guid",
  "userId": "user@example.com",
  "timestamp": "2025-07-07T10:00:00Z",
  "data": {
    "documentUrl": "https://storage.blob.core.windows.net/submission-guid/document1.pdf"
  }
}
```

**DocumentContentExtractedEvent**
```json
{
  "id": "uuid",
  "eventType": "DocumentContentExtractedEvent",
  "submissionId": "submission-guid",
  "userId": "user@example.com", 
  "timestamp": "2025-07-07T10:02:00Z",
  "data": {
    "documentUrl": "https://storage.blob.core.windows.net/submission-guid/document1.pdf",
    "contentLength": 15000,
    "success": true
  }
}
```

**DocumentClassifiedEvent**
```json
{
  "id": "uuid",
  "eventType": "DocumentClassifiedEvent",
  "submissionId": "submission-guid",
  "userId": "user@example.com", 
  "timestamp": "2025-07-07T10:05:00Z",
  "data": {
    "documentUrl": "https://storage.blob.core.windows.net/submission-guid/document1.pdf",
    "documentType": "invoice",
    "confidence": 0.95,
    "success": true
  }
}
```

**DocumentIndexedEvent**
```json
{
  "id": "uuid",
  "eventType": "DocumentIndexedEvent",
  "submissionId": "submission-guid",
  "userId": "user@example.com", 
  "timestamp": "2025-07-07T10:04:00Z",
  "data": {
    "documentUrl": "https://storage.blob.core.windows.net/submission-guid/document1.pdf",
    "searchIndexId": "doc-uuid-in-search",
    "success": true
  }
}
```

**DocumentDataExtractedEvent**
```json
{
  "id": "uuid",
  "eventType": "DocumentDataExtractedEvent",
  "submissionId": "submission-guid",
  "userId": "user@example.com", 
  "timestamp": "2025-07-07T10:06:00Z",
  "data": {
    "documentUrl": "https://storage.blob.core.windows.net/submission-guid/document1.pdf",
    "extractedFields": ["invoiceNumber", "amount", "currency", "dueDate", "vendor"],
    "success": true
  }
}
```

**DocumentProcessedEvent**
```json
{
  "id": "uuid",
  "eventType": "DocumentProcessedEvent",
  "submissionId": "submission-guid",
  "userId": "user@example.com", 
  "timestamp": "2025-07-07T10:07:00Z",
  "data": {
    "documentUrl": "https://storage.blob.core.windows.net/submission-guid/document1.pdf",
    "processingStepsComplete": ["classification", "dataExtraction"],
    "success": true
  }
}
```

**DocumentFullyProcessedEvent**
```json
{
  "id": "uuid",
  "eventType": "DocumentFullyProcessedEvent",
  "submissionId": "submission-guid",
  "userId": "user@example.com",
  "timestamp": "2025-07-07T10:08:00Z",
  "data": {
    "documentUrl": "https://storage.blob.core.windows.net/submission-guid/document1.pdf",
    "allProcessingComplete": true,
    "documentType": "invoice"
  }
}
```

**SubmissionDocumentsCompleteEvent**
```json
{
  "id": "uuid",
  "eventType": "SubmissionDocumentsCompleteEvent",
  "submissionId": "submission-guid",
  "userId": "user@example.com",
  "timestamp": "2025-07-07T10:10:00Z",
  "data": {
    "totalDocuments": 2,
    "processedDocuments": 2,
    "documentTypes": ["invoice", "contract"]
  }
}
```

**SubmissionAnalysisCompleteEvent**
```json
{
  "id": "uuid",
  "eventType": "SubmissionAnalysisCompleteEvent",
  "submissionId": "submission-guid",
  "userId": "user@example.com",
  "timestamp": "2025-07-07T10:15:00Z",
  "data": {
    "analysisResults": {
      "completeness": 0.85,
      "recommendations": ["Request additional documentation for item X"],
      "issues": []
    }
  }
}
```

#### Data Flow

```
Service Bus → submission-intake → SubmissionCreated Event
                                 ↓
                              DocumentUploadedEvent (per document)
                                 ↓
                           docproc-parser-foundry
                                 ↓
                         DocumentContentExtractedEvent
                                 ↓
              ┌──────────────────┼──────────────────┐
              ↓                  ↓                  ↓
    docproc-classifier  docproc-search-indexer  docproc-data-extractor
              ↓                  ↓                  ↓
  DocumentClassifiedEvent  DocumentIndexedEvent  DocumentDataExtractedEvent
              ↓                                   ↓
              └─────────────→ docproc-aggregator ←┘
                                 ↓
                        DocumentFullyProcessedEvent
                                 ↓
                      SubmissionDocumentsCompleteEvent
                                 ↓
                          submission-analyzer
                                 ↓
                      SubmissionAnalysisCompleteEvent
```

#### Process Flow Diagram

```mermaid
graph TD
    A[Service Bus Topic] --> B[submission-intake]
    B --> C[Create Submission Record]
    B --> D[Emit SubmissionCreated Event]
    B --> E[Emit DocumentUploadedEvent per document]
    
    E --> F[docproc-parser-foundry]
    F --> G[Azure Document Intelligence]
    G --> H[Extract Content as Markdown]
    H --> I[Store content in documents container]
    I --> J[Emit DocumentContentExtractedEvent]
    
    J --> K[docproc-classifier]
    J --> L[docproc-search-indexer]
    J --> M[docproc-data-extractor]
    
    K --> N[LLM Classification]
    N --> O[Update document with type & summary]
    O --> P[Emit DocumentClassifiedEvent]
    
    L --> Q[Azure AI Search]
    Q --> R[Index document content]
    R --> S[Emit DocumentIndexedEvent]
    
    M --> T[LLM Data Extraction]
    T --> U[Update document with extractedData]
    U --> V[Emit DocumentDataExtractedEvent]
    
    P --> W[docproc-aggregator]
    V --> W
    W --> X{All processing complete?}
    X -->|Yes| Y[Emit DocumentFullyProcessedEvent]
    X -->|No| Z[Wait for remaining events]
    Z --> W
    
    Y --> AA{All documents processed?}
    AA -->|Yes| BB[Emit SubmissionDocumentsCompleteEvent]
    AA -->|No| CC[Wait for more documents]
    CC --> AA
    
    BB --> DD[submission-analyzer]
    DD --> EE[Update submission with processed flags]
    EE --> FF[LLM Analysis]
    FF --> GG[Update submission with evaluation results]
    GG --> HH[Emit SubmissionAnalysisCompleteEvent]
    
    style A fill:#e1f5fe
    style G fill:#fff3e0
    style N fill:#e8f5e8
    style Q fill:#fff3e0
    style T fill:#e8f5e8
    style FF fill:#e8f5e8
```

#### Error Handling and Resilience

- **Retry Logic:** Each service implements exponential backoff for failed operations
- **Dead Letter Handling:** Failed events after max retries go to dead letter queue
- **Idempotency:** All event handlers are idempotent using event IDs
- **Compensation:** Event sourcing enables replay and compensation for failed workflows
- **Monitoring:** Change Feed provides built-in monitoring of event processing

### Architecture Comparison

**Workflow Orchestration with Logic Apps:**
- ✅ Built-in monitoring and error handling
- ✅ Visual workflow and progress tracking
- ✅ Simpler to understand and debug
- ✅ Azure-native tooling
- ❌ Azure-specific, less flexibility

**Choreography with Event Sourcing:**
- ✅ Code-first Python approach
- ✅ Multi-cloud portability
- ✅ Complete audit trail
- ✅ Fine-grained control
- ❌ Complex to write and troubleshoot

**Key Trade-off:** Simplicity vs. Control
