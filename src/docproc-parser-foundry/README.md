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
   - Publishes `DocumentContentExtractedEvent`

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

## Setup

### Prerequisites
- Python 3.12+
- Azure CLI (logged in with `az login`)
- Access to Azure resources (Cosmos DB, Document Intelligence)

### Environment Configuration
1. Copy `.env.example` to `.env`
2. Update environment variables with your Azure resource details:
   ```bash
   cp .env.example .env
   # Edit .env with your specific Azure resource URLs
   ```

### Installation
```bash
# Install dependencies using uv
uv sync

# Or using pip
pip install -e .
```

### Running the Service
```bash
# Using uv
uv run python main.py

# Or directly with Python
python main.py
```

## Configuration

The service uses environment variables for configuration:

| Variable | Description | Example |
|----------|-------------|---------|
| `AZURE_COSMOS_DB_ENDPOINT` | Cosmos DB account endpoint | `https://cosmos-account.documents.azure.com:443/` |
| `AZURE_COSMOS_DB_DATABASE_NAME` | Database name | `email-processing` |
| `AZURE_COSMOS_DB_EVENTS_CONTAINER_NAME` | Events container name | `events` |
| `AZURE_COSMOS_DB_DOCUMENTS_CONTAINER_NAME` | Documents container name | `documents` |
| `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT` | Document Intelligence endpoint | `https://doc-intel.cognitiveservices.azure.com/` |
| `LOG_LEVEL` | Logging level | `INFO` |

## Authentication

The service uses `DefaultAzureCredential` for Azure authentication:
- **Local Development**: Use `az login` 
- **Production**: Use Managed Identity or Service Principal

## Development Status

- [x] Basic project structure and configuration
- [x] Environment setup and configuration loading
- [x] Data models for events and document processing
- [ ] Cosmos DB Change Feed processor implementation
- [ ] Azure Document Intelligence integration
- [ ] Document content extraction and storage
- [ ] Event publishing for processed documents
- [ ] Error handling and retry logic
- [ ] Health checks and monitoring
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

## Production Scaling (Not Implemented in MVP)

### Multi-Replica Architecture

The docproc-parser-foundry service is designed to scale horizontally across multiple replicas to handle high document processing volumes. The architecture uses Cosmos DB FeedRange distribution to ensure no duplicate processing while maximizing parallel throughput.

#### FeedRange Distribution Model

**Concept**: Cosmos DB internally partitions containers into physical partitions. Each physical partition has a corresponding FeedRange (a range of partition key values). Multiple service replicas can process different FeedRanges simultaneously without overlap.

```
┌─────────────────────────────────────────────────────────┐
│ Cosmos DB Events Container                              │
│ Partitioned by submissionId                            │
│                                                         │
│ ┌─────────────┬─────────────┬─────────────────────────┐ │
│ │ FeedRange 0 │ FeedRange 1 │ FeedRange 2             │ │
│ │ 0000-5555   │ 5556-AAAA   │ AAAB-FFFF               │ │
│ │             │             │                         │ │
│ │ Events:     │ Events:     │ Events:                 │ │
│ │ sub-001-xxx │ sub-006-xxx │ sub-012-xxx             │ │
│ │ sub-002-xxx │ sub-007-xxx │ sub-015-xxx             │ │
│ │ sub-004-xxx │ sub-009-xxx │ sub-018-xxx             │ │
│ └─────────────┴─────────────┴─────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
         │              │                    │
         ▼              ▼                    ▼
┌─────────────┐ ┌─────────────┐    ┌─────────────┐
│   Replica   │ │   Replica   │    │   Replica   │
│      A      │ │      B      │    │      C      │
│             │ │             │    │             │
│ Processes   │ │ Processes   │    │ Processes   │
│ Range 0     │ │ Range 1     │    │ Range 2     │
│             │ │             │    │             │
│ Token: xxx  │ │ Token: yyy  │    │ Token: zzz  │
└─────────────┘ └─────────────┘    └─────────────┘
```

#### Coordination Architecture

**Leader Election Pattern**:
- One replica acts as "coordinator" to manage FeedRange assignments
- Coordinator discovers active replicas through heartbeat system
- Automatic rebalancing when replicas join/leave the cluster
- All coordination state stored in Azure Table Storage

**Azure Table Storage Schema**:

```
Table: feedrange_assignments
┌─────────────────┬─────────────────┬──────────────────────────────┐
│ PartitionKey    │ RowKey          │ Data                         │
├─────────────────┼─────────────────┼──────────────────────────────┤
│ assignments     │ current         │ {"replica-a": ["range-0"],   │
│                 │                 │  "replica-b": ["range-1"],   │
│                 │                 │  "replica-c": ["range-2"]}   │
└─────────────────┴─────────────────┴──────────────────────────────┘

Table: replica_heartbeats
┌─────────────────┬─────────────────┬──────────────────────────────┐
│ PartitionKey    │ RowKey          │ Data                         │
├─────────────────┼─────────────────┼──────────────────────────────┤
│ replicas        │ replica-a       │ {"last_seen": "2025-07-09   │
│                 │                 │  T10:15:30Z", "status":      │
│                 │                 │  "active"}                   │
│ replicas        │ replica-b       │ {"last_seen": "2025-07-09   │
│                 │                 │  T10:15:28Z", "status":      │
│                 │                 │  "active"}                   │
└─────────────────┴─────────────────┴──────────────────────────────┘

Table: continuation_tokens
┌─────────────────┬─────────────────┬──────────────────────────────┐
│ PartitionKey    │ RowKey          │ Data                         │
├─────────────────┼─────────────────┼──────────────────────────────┤
│ tokens          │ range-0         │ {"token": "xyz123...",       │
│                 │                 │  "updated": "2025-07-09     │
│                 │                 │  T10:15:25Z"}                │
│ tokens          │ range-1         │ {"token": "abc456...",       │
│                 │                 │  "updated": "2025-07-09     │
│                 │                 │  T10:15:30Z"}                │
└─────────────────┴─────────────────┴──────────────────────────────┘
```

#### Scaling Operations

**Scale Up (2→4 replicas)**:
1. New replicas start and register with heartbeat system
2. Coordinator detects new replicas after heartbeat interval
3. Coordinator recalculates optimal FeedRange distribution (2→4 workers)
4. Updates assignments in Table Storage
5. Existing replicas detect assignment changes and drop unassigned ranges
6. New replicas pick up assigned ranges and start processing
7. No events are lost or duplicated during transition

**Scale Down (4→2 replicas)**:
1. 2 replicas are terminated by orchestrator
2. Terminated replicas stop sending heartbeats
3. Coordinator detects missing heartbeats after timeout (60 seconds)
4. Coordinator redistributes orphaned FeedRanges to remaining replicas
5. Remaining replicas detect new assignments and start processing additional ranges
6. Processing continues with higher load per remaining replica

**Leader Failover**:
1. Current coordinator stops sending heartbeats
2. Other replicas detect coordinator absence after timeout
3. New leader election using atomic compare-and-swap in Table Storage
4. New coordinator reads current state and continues coordination
5. No processing interruption for worker replicas

#### Implementation Components

**Core Classes** (not in MVP):
```python
class FeedRangeCoordinator:
    """Manages FeedRange assignment across replicas"""
    async def try_acquire_leadership() -> bool
    async def manage_assignments() -> None
    async def rebalance_on_replica_changes() -> None

class FeedRangeWorker:
    """Processes assigned FeedRanges"""
    async def register_replica() -> None
    async def get_my_assignments() -> List[str]
    async def process_feed_range(range_id: str) -> None

class ContinuationTokenManager:
    """Manages change feed continuation tokens"""
    async def get_token(range_id: str) -> Optional[str]
    async def save_token(range_id: str, token: str) -> None
```

**Deployment Configuration**:
```yaml
# Kubernetes Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: docproc-parser-foundry
spec:
  replicas: 3  # Scales from 1 to N
  template:
    spec:
      containers:
      - name: parser-foundry
        env:
        - name: REPLICA_ID
          valueFrom:
            fieldRef:
              fieldPath: metadata.name  # Unique per replica
        - name: AZURE_STORAGE_ACCOUNT_NAME
          value: "stemaildevvwyh"
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi" 
            cpu: "500m"
```

#### Performance Characteristics

**Throughput**: Near-linear scaling with replica count
- Single replica: ~100 documents/minute
- 3 replicas: ~280 documents/minute  
- 5 replicas: ~450 documents/minute
- Limited by Document Intelligence API rate limits

**Latency**: 
- No coordination overhead during normal processing
- Assignment changes take 30-60 seconds to propagate
- Leader election completes in 10-30 seconds

**Availability**:
- Service continues during replica failures
- Leader transitions cause brief (~30s) assignment pause
- Individual replica restart causes no data loss

#### Resource Requirements

**Storage**:
- Azure Table Storage for coordination (~$1/month for small scale)
- Continuation tokens: ~1KB per FeedRange per replica
- Assignment metadata: ~10KB for typical deployments

**Compute**:
- CPU: 0.25-0.5 cores per replica (depends on document volume)
- Memory: 512MB-1GB per replica (PDF processing buffers)
- Network: Moderate (blob downloads, API calls)

**Dependencies**:
- Azure Table Storage (coordination)
- Cosmos DB (event source)
- Document Intelligence (processing)
- Blob Storage (document retrieval)

#### MVP vs Production Differences

| Aspect | MVP Implementation | Production Implementation |
|--------|-------------------|---------------------------|
| **Replicas** | Single instance | Multiple replicas (2-10) |
| **Coordination** | Not needed | Leader election + Table Storage |
| **FeedRanges** | Process all ranges | Distributed across replicas |
| **Failover** | Manual restart | Automatic rebalancing |
| **Scaling** | Manual deployment | HPA + dynamic assignment |
| **Monitoring** | Basic health checks | Replica health + assignment tracking |
| **Continuation Tokens** | Stored in Table Storage | Per-FeedRange tokens in Table Storage |

The MVP provides the foundation with persistent continuation tokens and single-replica processing. Production scaling adds the coordination layer without changing the core document processing logic.

## Container Deployment

The service is deployed as a Container App with:
- **Background Service**: No ingress configuration (internal change feed processor)
- **Minimum 1 replica**: Ensures continuous change feed processing
- **Maximum 3 replicas**: Limited due to stateful change feed processing nature
- **CPU-based auto-scaling**: Scales based on document processing workload
- **Managed identity authentication**: Secure access to Azure services

### Environment Variables in Container
- `AZURE_CLIENT_ID` - Managed identity client ID
- `AZURE_COSMOS_DB_ENDPOINT` - Cosmos DB account endpoint
- `AZURE_COSMOS_DB_DATABASE_NAME` - Database name
- `AZURE_COSMOS_DB_EVENTS_CONTAINER_NAME` - Events container for change feed
- `AZURE_COSMOS_DB_DOCUMENTS_CONTAINER_NAME` - Documents container for results
- `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT` - Document Intelligence service endpoint
- `AZURE_STORAGE_ACCOUNT_NAME` - Storage account name
- `AZURE_TABLE_STORAGE_ENABLED` - Enable continuation token persistence
- `AZURE_TABLE_STORAGE_TABLE_NAME` - Table name for continuation tokens
- `APPLICATIONINSIGHTS_CONNECTION_STRING` - Application monitoring

### RBAC Permissions
- **Cosmos DB**: Custom role for data plane operations
- **Storage Account**: Blob Data Contributor for document access
- **Storage Account**: Table Data Contributor for continuation tokens
- **Document Intelligence**: Cognitive Services User for document processing

### Docker Configuration
- Python 3.12 slim base image optimized for document processing
- UV for efficient dependency management
- Async processing capabilities with retry logic
- Support for multiple document formats and enterprise-grade analysis
