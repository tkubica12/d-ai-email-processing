# Implementation Log

Key architectural decisions, technical insights, and implementation progress for the AI Email Processing System.

## Architecture Overview

**Technology Stack:**
- **FastHTML** - Rapid Python web UI development
- **uv** - Modern Python dependency management  
- **Azure OpenAI** - Enterprise embeddings and GPT-4.1 with Entra authentication
- **Terraform** - Infrastructure as Code with RBAC
- **Pydantic** - Type-safe data models throughout

**Development Workflow:**
Deploy infrastructure → Update `.env` → `az login` → `uv run python main.py`

**Event-Driven Architecture:**
- Azure Service Bus for message queuing
- Cosmos DB Change Feed for event processing
- Vector search with 3072-dimension embeddings (text-embedding-3-large)
- Security trimming via userId filtering
- Document chunking: 2000 chars with 200 char overlap

**Processing Pipeline:**
1. **Submission Intake** - Service Bus worker processing
2. **Document Parser** - Azure Document Intelligence → Cosmos DB  
3. **Document Classifier** - Azure OpenAI classification
4. **Search Indexer** - Chunking + vector embeddings → Azure AI Search
5. **Data Extractor** - Structured invoice data extraction

## Major Architecture Evolution

### System Simplification (July 2025)
- **Removed** docproc-aggregator service for complexity reduction
- **Enhanced** submission-analyzer with AI Foundry agent capabilities
- **Added** company-apis service for business data integration
- **Simplified** event flow with direct document processing

### AI Agent Integration
- RAG with Azure AI Search + security trimming
- Web search for entity verification
- Company APIs integration for financial data
- Multi-faceted submission analysis capabilities

### Vector Search Implementation
- Azure AI Search with HNSW algorithm for semantic search
- 3072-dimension vector support for Azure OpenAI embeddings
- Index validation and auto-recreation for schema changes
- Comprehensive metadata preservation (userId, submissionId, documentId)

**Key Technical Achievements:**
- Vector field definitions with `SearchField(Collection(SearchFieldDataType.Single))`
- Azure OpenAI migration with Entra authentication
- Security trimming for multi-tenant access
- Policies search with blob storage integration

## Azure Services Integration

### Company APIs Service
- FastAPI with realistic mock data generation
- Seeded random generation for consistent user data
- Cross-platform timezone compatibility (`datetime.timezone.utc`)
- Bearer token authentication

**API Endpoints:**
- `/users/{userId}/products` - Subscriptions and services
- `/users/{userId}/financial-score` - 5 financial health dimensions  
- `/users/{userId}/income` - Configurable granularity aggregation

### AI Search Tools Integration
- Azure AI Search tool integration for AI Foundry agent
- Entra ID authentication for secure access
- Document search capabilities within agent tools
- Semantic and keyword search support

**Configuration:**
- Environment variables: `AZURE_SEARCH_SERVICE_NAME`, `AZURE_SEARCH_INDEX_NAME`, `AZURE_SEARCH_CONNECTION_ID`
- Authentication via DefaultAzureCredential
- Uses `AzureAISearchTool` from Azure AI Projects SDK

### Policies Search Setup
- Comprehensive Azure AI Search setup for policy documents
- Blob storage integration with automatic document upload
- Skillset pipeline with text splitting and embedding generation
- Idempotent operations for safe re-execution

**Implementation Features:**
- Index fields: id, title, content, filename, metadata, content_vector
- HNSW algorithm with cosine similarity
- Hourly indexer scheduling
- Python script approach for complex AI Search configuration

## Critical Technical Insights

### Event System Architecture
- Standardized event structure with `documentId` and `submissionId` partition keys
- Use `model_dump_json()` for datetime serialization
- Explicit Azure SDK dependencies in `pyproject.toml`
- Service Bus renamed `email-events` → `new-submissions` for clarity

### Azure OpenAI Integration Patterns
- Flatten complex nested models for structured outputs
- Use stable API versions (`2024-06-01`)
- Enterprise compliance via Azure OpenAI vs OpenAI API
- Jinja2 templates for dynamic prompt generation

### Change Feed Processing Best Practices
- Use `start_time="Beginning"` when no continuation token exists
- Direct iteration: `async for event_data in feed_iterator`
- Proper continuation token management after processing
- Limited replicas (1-3) for stateful processing services

### Cross-Platform Compatibility
- `datetime.timezone.utc` instead of `ZoneInfo("UTC")` for Windows compatibility
- Include `tzdata` package for timezone support
- Test enum values in mock data dictionaries

### Data Model Evolution
- Migrated dictionaries → Pydantic models with `submittedAt` timestamps
- Flat models preferred for Azure OpenAI structured outputs
- Standardized event patterns across all services

### Azure Search Implementation
- Vector field definitions with `SearchField(Collection(SearchFieldDataType.Single))`
- HNSW algorithm configuration for semantic search
- Semantic search requires both service-level enablement and proper index configuration
- Python scripts preferred over Terraform for complex AI Search configurations

---

**This log focuses on architectural decisions and critical technical insights. For detailed implementation, see source code and service-specific documentation.**

## Container App Deployment Strategy

### Infrastructure Architecture
- **Background Services**: No ingress, minimum 1 replica for continuous processing
- **Web Services**: Port 8000 with HTTPS ingress
- **Scaling**: CPU-based scaling at 70% threshold (max 3-5 replicas)
- **Authentication**: User-assigned managed identities with least-privilege RBAC
- **Monitoring**: Application Insights with OTEL integration

### Deployed Services
- **client-web** - FastHTML web application (port 8000)
- **submission-intake** - Service Bus message processing
- **docproc-parser-foundry** - Document Intelligence processing
- **docproc-classifier** - Document classification using Azure OpenAI GPT-4.1
- **docproc-data-extractor** - Structured data extraction using Azure OpenAI
- **docproc-search-indexer** - AI Search indexing with vector embeddings

### Key Implementation Decisions
- **Naming Strategy**: Simplified to `servicename-{random_string}` for cleaner Azure portal experience
- **Docker Configuration**: Python 3.12 slim base images with uv package manager
- **CI/CD**: GitHub Actions workflows for each service with automated Docker builds
- **Security**: Managed identities with specific RBAC assignments per service

**Change Feed Processing Pattern:**
- Stateful processing with continuation token persistence in Table Storage
- Limited replicas (1-3) for services processing change feeds
- Retry logic with exponential backoff for resilient processing

**Environment Variables Pattern:**
- `AZURE_CLIENT_ID` for managed identity authentication
- Service-specific Azure resource endpoints
- Application Insights connection strings
- Cosmos DB database and container names

## Demo and Testing Tools

### Demo Data Cleanup Utility (July 2025)
- **Purpose**: Clean up demo data from Azure resources for testing and demos
- **Features**:
  - Deletes all records from Cosmos DB containers (events, documents, submissions)
  - Deletes all storage containers in GUID format (preserves policies-docs)
  - Automatic partition key detection for Cosmos DB containers
  - Robust error handling with fallback strategies
- **Location**: `src/demo-utils/cleanup_demo_data.py`
- **Usage**: `python cleanup_demo_data.py` after `az login`

## Recent Updates

### Document Classifier Enhancement (July 15, 2025)
- **Enhanced** docproc-classifier to update submission records with document types
- **Added** submissions container configuration to support dual updates
- **Implemented** submission record models for type-safe operations
- **Modified** classification workflow to update both document and submission records
- **Fixed** partition key usage for submissions container (userId, not submissionId)
- **Architecture**: Document classification now maintains consistency between documents and submissions containers

**Technical Implementation:**
- Added `update_submission_document_type()` method to DocumentClassifier with correct partition key
- Extended CosmosDBConfig with submissions_container_name
- Added SubmissionRecord and SubmissionDocument Pydantic models
- Updated .env files with AZURE_COSMOS_DB_SUBMISSIONS_CONTAINER_NAME
- Updated Terraform configuration with submissions container environment variable
- Modified classify_and_update_document() to perform dual updates using correct partition key

**Benefits:**
- Ensures data consistency between document and submission records
- Enables faster submission queries without document container joins
- Maintains single source of truth for document classification results
- Supports submission-level analytics and reporting

**Bug Fix:**
- Corrected partition key usage in submissions container from submissionId to userId
- Updated Design.md to reflect actual implementation

## Schema Updates (July 16, 2025)

### Submission Schema Simplification
- **Removed** `processed` field from documents array in submissions container
- **Added** `userMessage` field to submissions container root level for email body content
- **Updated** submission-intake service to read user message from `body.txt` file in blob storage
- **Updated** docproc-classifier service models to match new schema

**Technical Details:**
- Modified `DocumentInfo` model to remove boolean `processed` field
- Added `userMessage` field to `SubmissionDocument` model  
- Updated `SubmissionRecord` model in docproc-classifier to include `userMessage`
- Added Azure Storage client to submission-intake service to read `body.txt` from blob storage
- User message is read from `{submissionId}/body.txt` in blob storage during submission processing
- Processing state now tracked through event-driven pipeline rather than static field

**Impact:**
- Simplified data model removes redundant state tracking
- Better separation of concerns between processing events and submission data
- Direct access to original user message from blob storage for AI analysis
- Maintains backward compatibility with existing processing pipeline and Service Bus message format
- Email body content accessible without requiring changes to Service Bus message structure
