# Implementation Log

Key architectural decisions, technical insights, and implementation progress for the AI Email Processing System.

## System Architecture

**Technology Stack:**
- **FastHTML** - Python web UI framework
- **uv** - Modern Python dependency management  
- **Azure OpenAI** - Enterprise GPT-4.1 with Entra authentication
- **Terraform** - Infrastructure as Code with RBAC
- **Pydantic** - Type-safe data models
- **Azure Logic Apps Standard** - Email processing workflows

**Development Workflow:**
Deploy infrastructure → Update `.env` → `az login` → `uv run python main.py`

**Event-Driven Processing Pipeline:**
1. **Logic App** - Email processing workflow orchestration
2. **Submission Intake** - Service Bus worker processing
3. **Document Parser** - Azure Document Intelligence → Cosmos DB  
4. **Document Classifier** - Azure OpenAI classification
5. **Search Indexer** - Chunking + vector embeddings → Azure AI Search
6. **Data Extractor** - Structured invoice data extraction
7. **Submission Trigger** - Completion event coordination

**Core Infrastructure:**
- Azure Service Bus for message queuing
- Cosmos DB Change Feed for event processing  
- Vector search with 3072-dimension embeddings (text-embedding-3-large)
- Security trimming via userId filtering
- Document chunking: 2000 chars with 200 char overlap

## Major Architectural Evolution

### Infrastructure & Security (July 2025)
- **Modularized RBAC**: Split rbac.tf into service-specific files (identities, storage, messaging, ai, search)
- **Logic Apps Standard**: Deployed with managed identity authentication and elastic scaling
- **Managed Identities**: Eliminated connection strings for enhanced security
- **Container Apps**: Background services with CPU-based scaling and OTEL monitoring

### Processing Pipeline Enhancements (July 2025)
- **Submission Trigger Service**: Coordinates document processing completion across services
- **Document Classification**: Dual updates to maintain consistency between document and submission records
- **Schema Simplification**: Removed redundant `processed` field, added `userMessage` field
- **Event-Driven Coordination**: Tracks processing status via SubmissionTriggerProcessor

### AI & Search Integration
- **RAG Implementation**: Azure AI Search with security trimming and vector embeddings
- **Company APIs**: FastAPI service with mock financial data and bearer token auth
- **Policies Search**: Comprehensive policy document search with HNSW algorithm
- **AI Foundry Agent**: Multi-faceted submission analysis with web search and company data integration

## Technical Implementation Insights

### Azure OpenAI Integration
- **Authentication**: Entra ID for enterprise compliance
- **Structured Outputs**: Flat models preferred over nested for better results
- **API Version**: Stable `2024-06-01` version for production
- **Template Engine**: Jinja2 for dynamic prompt generation

### Event Processing Patterns
- **Change Feed**: Direct iteration with continuation token management
- **Event Structure**: Standardized with `documentId` and `submissionId` partition keys
- **Serialization**: `model_dump_json()` for datetime handling
- **Scaling**: Limited replicas (1-3) for stateful processing services

### Data Models & Storage
- **Cosmos DB**: Partition key strategy by userId for submissions, submissionId for triggers
- **Schema Evolution**: Migrated from dictionaries to Pydantic models with timestamps
- **Status Tracking**: Event-driven pipeline replaces static boolean flags
- **Cross-Platform**: `datetime.timezone.utc` for Windows compatibility

### Azure Search Configuration
- **Vector Fields**: `SearchField(Collection(SearchFieldDataType.Single))` for embeddings
- **HNSW Algorithm**: Cosine similarity for semantic search
- **Security**: Trimming via userId filtering for multi-tenant access
- **Implementation**: Python scripts preferred over Terraform for complex configurations

## Recent Critical Fixes & Updates

### Document Classification Enhancement (July 15, 2025)
- **Fixed** partition key usage in submissions container (userId, not submissionId)
- **Enhanced** docproc-classifier to maintain consistency between document and submission records
- **Added** dual update capability for both containers with proper partition key handling
- **Benefit**: Enables faster submission queries without container joins

### Schema Simplification (July 16, 2025)
- **Removed** redundant `processed` field from documents array
- **Added** `userMessage` field to submission root level for email body content
- **Updated** submission-intake service to read user message from `body.txt` in blob storage
- **Impact**: Event-driven processing state replaces static boolean flags

---

**This log focuses on architectural decisions and critical technical insights. For detailed implementation, see source code and service-specific documentation.**
