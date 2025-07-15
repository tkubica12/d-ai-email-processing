# Implementation Log

Key architectural decisions, technical insights, and implementation progress for the AI Email Processing System.

## Core Architecture

**Technology Stack:**
- **FastHTML** - Rapid Python web UI development
- **uv** - Modern Python dependency management  
- **Azure OpenAI** - Enterprise embeddings with Entra authentication
- **Terraform** - Infrastructure as Code with RBAC
- **Pydantic** - Type-safe data models throughout

**Development Workflow:**
Deploy infrastructure → Update `.env` → `az login` → `uv run python main.py`

**Architectural Principles:**
- Event-driven with Azure Service Bus and Cosmos DB Change Feed
- Vector search with 3072-dimension embeddings (text-embedding-3-large)
- Security trimming via userId filtering
- Document chunking: 2000 chars with 200 char overlap

## Document Processing Pipeline

**Service Flow:**
1. **Submission Intake** - Service Bus worker processing
2. **Document Parser** - Azure Document Intelligence → Cosmos DB  
3. **Document Classifier** - Azure OpenAI classification
4. **Search Indexer** - Chunking + vector embeddings → Azure AI Search
5. **Data Extractor** - Structured invoice data extraction

**Common Patterns:**
- Change Feed processing for event-driven services
- Azure OpenAI structured outputs with flat Pydantic models
- Continuation token persistence for stateful processing
- Async operations with proper resource cleanup

## Major Architecture Changes (July 11, 2025)

**Simplification:**
- **Removed** docproc-aggregator (complexity elimination)
- **Enhanced** submission-analyzer → AI Foundry agent
- **Added** company-apis service for business data
- **Enhanced** search indexer with security trimming

**AI Agent Capabilities:**
- RAG with Azure AI Search + security trimming
- Web search for entity verification
- Company APIs integration
- Multi-faceted submission analysis

**Event Flow Simplification:**
- Direct document events → submission-analyzer
- Eliminated intermediate aggregation events
- Multiple simultaneous processing streams

## Azure AI Search Implementation (July 14, 2025)

**Key Achievements:**
- Vector field definitions with `SearchField(Collection(SearchFieldDataType.Single))`
- HNSW algorithm configuration for semantic search
- Index validation and auto-recreation for schema changes
- 3072-dimension vector support for Azure OpenAI embeddings

**Document Processing:**
- Chunking service: 2000 chars, 200 char overlap
- Async Azure OpenAI client with bearer token auth
- Comprehensive metadata preservation (userId, submissionId, documentId)
- Security trimming for multi-tenant access

**Technical Challenges Resolved:**
- Vector field SDK differences (`SearchField` vs non-existent `VectorSearchField`)
- Algorithm configuration (`HnswAlgorithmConfiguration`)
- OpenAI API → Azure OpenAI migration with Entra auth
- Index schema validation and recreation

## Company APIs Service (July 11, 2025)

**Implementation:**
- FastAPI with realistic mock data generation
- Seeded random generation for consistent user data
- Cross-platform timezone compatibility (`datetime.timezone.utc`)
- Bearer token auth for development

**API Endpoints:**
- `/users/{userId}/products` - Subscriptions and services
- `/users/{userId}/financial-score` - 5 financial health dimensions  
- `/users/{userId}/income` - Configurable granularity aggregation

**Container Deployment:**
- Dockerfile with uv package manager
- Port 8003, managed identity with RBAC
- GitHub Container Registry integration

## AI Search Tool Integration (July 14, 2025)

**Enhanced Submission Analyzer:**
- **Added** Azure AI Search tool integration to Azure AI Foundry agent
- **Configured** Entra ID authentication for secure access to search index
- **Implemented** document search capabilities within agent tools
- **Updated** system prompt to include AI Search tool instructions

**Technical Implementation:**
- Uses `AzureAISearchTool` from Azure AI Projects SDK
- Configured with connection ID for secure authentication
- Integrated with existing document index from search-indexer service
- Supports both semantic and keyword search capabilities

**Configuration:**
- Environment variables: `AZURE_SEARCH_SERVICE_NAME`, `AZURE_SEARCH_INDEX_NAME`, `AZURE_SEARCH_CONNECTION_ID`
- Authentication via DefaultAzureCredential (Entra ID)
- Consistent configuration format across all services

**Benefits:**
- Agent can now search through submitted documents and previous submissions
- Provides contextual information for more accurate analysis
- Seamless integration with existing document processing pipeline
- Secure access with proper authentication and authorization

## Policies Search Setup (July 15, 2025)

**Implementation Overview:**
Implemented comprehensive setup script for Azure AI Search with vector search capabilities for policy documents.

**Key Features:**
- **Blob Storage Integration**: Automatic upload of policy documents from local folder
- **Vector Search**: Azure OpenAI text-embedding-3-large integration (3072 dimensions)
- **Semantic Search**: Built-in Azure AI Search semantic capabilities
- **Skillset Pipeline**: Text splitting (2000 chars, 200 overlap) + embedding generation
- **Idempotent Operations**: Safe to run multiple times, updates existing resources

**Technical Implementation:**
- **Index Fields**: id, title, content, filename, metadata, content_vector
- **Vector Configuration**: HNSW algorithm with cosine similarity
- **Indexer Schedule**: Hourly processing of new/updated documents
- **Authentication**: DefaultAzureCredential for managed identity support

**Architecture Decision:**
Chose Python script over Terraform for AI Search configuration due to complexity of skillsets and indexer field mappings. This allows for better error handling and step-by-step logging.

**Dependencies Added:**
- `azure-storage-blob` for blob operations
- `azure-search-documents` for index management
- Enhanced error handling and progress logging

**Usage:**
```bash
uv run main.py
```

**Next Steps:**
- Add document status monitoring
- Implement search query interface
- Add indexer failure recovery mechanisms

## Critical Technical Lessons

**Event System:**
- Standardized event structure with `documentId` and `submissionId` partition keys
- Use `model_dump_json()` for datetime serialization
- Explicit Azure SDK dependencies in `pyproject.toml`

**Azure OpenAI Integration:**
- Flatten complex nested models for structured outputs
- Use stable API versions (`2024-06-01`)
- Enterprise compliance via Azure OpenAI vs OpenAI API

**Change Feed Processing:**
- Use `start_time="Beginning"` when no continuation token
- Direct iteration: `async for event_data in feed_iterator`
- Proper continuation token management after processing

**Cross-Platform Compatibility:**
- `datetime.timezone.utc` instead of `ZoneInfo("UTC")` for Windows
- Include `tzdata` package for timezone support
- Test enum values in mock data dictionaries

## Configuration Evolution

**Service Bus:** Renamed `email-events` → `new-submissions` for clarity

**Data Models:** Migrated dictionaries → Pydantic models with `submittedAt` timestamps

**UI/UX:** Simplified from complex HTMX progress tracking → simple status indicators

**Infrastructure:** Standard SKU for semantic search, RBAC for Azure OpenAI access

**Next Steps for Full Implementation:**
1. Upgrade to newer Azure Search SDK version supporting vectorizers
2. Configure automatic embedding generation for hybrid search
3. Improve semantic field configuration for better captions/answers
4. Add more diverse document content for comprehensive testing

**Key Learning**: Semantic search requires both service-level enablement (via Terraform `semantic_search_sku`) and proper index configuration. The feature works well for text-based semantic ranking even without vectorizers configured.

---

**This log focuses on architectural decisions, critical fixes, and lessons learned. For detailed implementation, see source code and service-specific documentation.**

## Container App Deployment - Client Web (July 15, 2025)

**Infrastructure Enhancement:**
- Added Container App deployment for client-web service
- Created user-assigned managed identity for Azure authentication
- Configured proper RBAC assignments for Storage Account and Service Bus access

**Docker Configuration:**
- Updated Dockerfile CMD to use uvicorn directly for better container runtime
- Exposed port 8000 to match FastHTML application default
- Used uv for efficient dependency management

**Environment Variables:**
- `AZURE_CLIENT_ID` - Managed identity authentication
- `AZURE_STORAGE_ACCOUNT_NAME` - Storage account reference
- `AZURE_SERVICE_BUS_FQDN` - Service Bus namespace endpoint
- `AZURE_SERVICE_BUS_TOPIC_NAME` - Topic name for submission events
- `APPLICATIONINSIGHTS_CONNECTION_STRING` - Application monitoring

**GitHub Actions:**
- Created `client-web-build.yaml` workflow for automated Docker image building
- Configured to trigger on changes to `src/client-web/**` path
- Images pushed to GitHub Container Registry

**Security:**
- Used managed identity instead of connection strings for Azure services
- Applied principle of least privilege with specific RBAC assignments
- Configured secure ingress with HTTPS termination

**Architecture Decision:** 
Container Apps provide better scalability and managed runtime compared to App Service for this stateless web application. The service can scale to zero when not in use and automatically handle traffic spikes.

## Container App Deployment - Submission Intake (July 15, 2025)

**Background Service Architecture:**
- Deployed submission-intake as a background Container App service (no ingress)
- Configured minimum 1 replica to ensure continuous message processing from Service Bus
- Used CPU-based scaling rules for automatic scaling based on processing load

**Authentication & Authorization:**
- Created user-assigned managed identity for Azure service authentication
- Configured RBAC assignments for Service Bus Data Receiver, Storage Blob/Table Contributor
- Added Cosmos DB role assignment for data plane operations

**Environment Variables:**
- `AZURE_CLIENT_ID` - Managed identity authentication
- `AZURE_SERVICE_BUS_FQDN` - Service Bus namespace endpoint
- `AZURE_SERVICE_BUS_TOPIC_NAME` - Topic name for submission events
- `AZURE_SERVICE_BUS_SUBSCRIPTION_NAME` - Subscription name for message processing
- `AZURE_COSMOS_DB_ENDPOINT` - Cosmos DB account endpoint
- `AZURE_COSMOS_DB_DATABASE_NAME` - Database name
- `AZURE_COSMOS_DB_*_CONTAINER_NAME` - Container names for events, submissions, documents
- `AZURE_STORAGE_ACCOUNT_NAME` - Storage account reference
- `APPLICATIONINSIGHTS_CONNECTION_STRING` - Application monitoring

**Docker Configuration:**
- Used Python 3.12 slim base image for optimal performance
- Implemented uv for efficient dependency management
- Simple CMD execution for background service operation

**GitHub Actions:**
- Created `submission-intake-build.yaml` workflow for automated Docker image building
- Configured to trigger on changes to `src/submission-intake/**` path
- Images pushed to GitHub Container Registry

**Scaling Strategy:**
- Minimum 1 replica to ensure message processing continuity
- Maximum 5 replicas for burst capacity
- CPU-based scaling at 70% utilization threshold
- Future enhancement: Service Bus message count-based scaling

## Naming Strategy Optimization (July 15, 2025)

**Simplified Container App Naming:**
- Changed from `ca-servicename-project-env-random` to `servicename-random`
- Uses existing `random_string.suffix` from main.tf for uniqueness
- Managed identities follow same pattern: `servicename-random`
- Results in cleaner, shorter resource names while maintaining uniqueness

**Benefits:**
- Reduced resource name length (Azure has limits)
- Cleaner Azure portal experience
- Consistent naming across container apps and managed identities
- Leverages existing randomization infrastructure

**Examples:**
- Container App: `client-web-vwyh` instead of `ca-client-web-email-dev-vwyh`
- Managed Identity: `client-web-vwyh` instead of `id-client-web-email-dev-vwyh`

## Container App Deployment - Document Parser Foundry (July 15, 2025)

**Change Feed Processing Architecture:**
- Deployed docproc-parser-foundry as a background Container App service
- Processes Cosmos DB Change Feed for DocumentUploadedEvent events
- Uses Azure Document Intelligence for enterprise-grade document content extraction
- Stores processed content in documents container and emits DocumentContentExtractedEvent

**Scaling Strategy:**
- Minimum 1 replica for continuous change feed processing
- Maximum 3 replicas (limited due to stateful change feed processing)
- CPU-based scaling to handle document processing workload
- Stateful processing with continuation token persistence in Table Storage

**Authentication & Authorization:**
- Created user-assigned managed identity for Azure service authentication
- Configured RBAC assignments for:
  - Cosmos DB custom role for data plane operations
  - Storage Blob/Table Data Contributor for document and token storage
  - Cognitive Services User for Document Intelligence access

**Environment Variables:**
- `AZURE_CLIENT_ID` - Managed identity authentication
- `AZURE_COSMOS_DB_ENDPOINT` - Cosmos DB account endpoint
- `AZURE_COSMOS_DB_DATABASE_NAME` - Database name
- `AZURE_COSMOS_DB_EVENTS_CONTAINER_NAME` - Events container for change feed
- `AZURE_COSMOS_DB_DOCUMENTS_CONTAINER_NAME` - Documents container for results
- `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT` - Document Intelligence service endpoint
- `AZURE_STORAGE_ACCOUNT_NAME` - Storage account for document access
- `AZURE_TABLE_STORAGE_ENABLED` - Enable continuation token persistence
- `AZURE_TABLE_STORAGE_TABLE_NAME` - Table name for continuation tokens
- `APPLICATIONINSIGHTS_CONNECTION_STRING` - Application monitoring

**Docker Configuration:**
- Python 3.12 slim base image optimized for document processing
- UV for efficient dependency management including Document Intelligence SDK
- Async processing capabilities for high-throughput document analysis

**GitHub Actions:**
- Created `docproc-parser-foundry-build.yaml` workflow
- Triggers on changes to `src/docproc-parser-foundry/**` path
- Automated Docker image building and registry push

**Technical Architecture:**
- Event-driven processing using Cosmos DB Change Feed
- Retry logic with exponential backoff for resilient document processing
- Support for multiple document formats (PDF, images, Office documents)
- Stateful processing with continuation token management for service restarts

## Container App Deployment - Document Classifier (July 15, 2025)

**AI-Powered Document Classification:**
- Deployed docproc-classifier as a background Container App service
- Processes Cosmos DB Change Feed for DocumentContentExtractedEvent events
- Uses Azure OpenAI GPT-4.1 model for intelligent document classification
- Classifies documents into categories: invoice, contract, bank statement, submission notes, other
- Generates document summaries using structured AI outputs

**Azure OpenAI Integration:**
- Uses `azurerm_cognitive_deployment.gpt_41` for document classification
- Configured with "Cognitive Services OpenAI User" RBAC role
- Structured outputs ensure consistent classification results
- Jinja2 templates for dynamic prompt generation

**Scaling Strategy:**
- Minimum 1 replica for continuous change feed processing
- Maximum 3 replicas (limited due to stateful change feed processing)
- CPU-based scaling for AI processing workload
- Stateful processing with continuation token persistence

**Authentication & Authorization:**
- Created user-assigned managed identity for Azure service authentication
- Configured RBAC assignments for:
  - Cosmos DB custom role for data plane operations
  - Storage Blob/Table Data Contributor for document and token storage
  - Cognitive Services OpenAI User for Azure OpenAI access

**Environment Variables:**
- `AZURE_CLIENT_ID` - Managed identity authentication
- `AZURE_COSMOS_DB_ENDPOINT` - Cosmos DB account endpoint
- `AZURE_COSMOS_DB_DATABASE_NAME` - Database name
- `AZURE_COSMOS_DB_EVENTS_CONTAINER_NAME` - Events container for change feed
- `AZURE_COSMOS_DB_DOCUMENTS_CONTAINER_NAME` - Documents container for updates
- `AZURE_OPENAI_ENDPOINT` - Azure OpenAI service endpoint
- `AZURE_OPENAI_MODEL` - GPT-4.1 model deployment name
- `AZURE_STORAGE_ACCOUNT_NAME` - Storage account for continuation tokens
- `AZURE_TABLE_STORAGE_ENABLED` - Enable continuation token persistence
- `AZURE_TABLE_STORAGE_TABLE_NAME` - Table name for continuation tokens
- `APPLICATIONINSIGHTS_CONNECTION_STRING` - Application monitoring

**Docker Configuration:**
- Python 3.12 slim base image with OpenAI SDK
- UV for efficient dependency management
- Async processing with structured AI outputs
- Jinja2 templating for dynamic prompts

**GitHub Actions:**
- Created `docproc-classifier-build.yaml` workflow
- Triggers on changes to `src/docproc-classifier/**` path
- Automated Docker image building and registry push

**Event Processing Flow:**
1. Monitors Change Feed for DocumentContentExtractedEvent
2. Fetches document content from Cosmos DB
3. Classifies document using Azure OpenAI with structured outputs
4. Updates document record with classification results
5. Emits DocumentClassifiedEvent for downstream processing
