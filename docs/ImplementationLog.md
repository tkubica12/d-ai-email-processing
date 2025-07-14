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
