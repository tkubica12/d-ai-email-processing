# Implementation Log

Key architectural decisions, technical insights, and implementation progress for the AI Email Processing System.

## Architecture Overview

### Technology Stack
- **FastHTML** - Python web UI framework with **uv** dependency management
- **Azure AI Foundry** - Enterprise AI services (GPT-4.1, text-embedding-3-large)
- **Terraform** - Infrastructure as Code with comprehensive RBAC
- **Azure Logic Apps Standard** - Email workflow orchestration

### Processing Pipeline
Event-driven architecture with 7-stage pipeline:
1. **Logic App** → 2. **Submission Intake** → 3. **Document Parser** → 4. **Document Classifier** → 5. **Search Indexer** → 6. **Data Extractor** → 7. **Submission Trigger**

### Core Infrastructure
- **Messaging**: Azure Service Bus with change feed processing
- **Storage**: Cosmos DB with partition strategies (userId/submissionId)
- **Search**: Azure AI Search with vector embeddings (3072-dim) and security trimming
- **AI**: Azure AI Foundry with Entra ID authentication

## Key Architectural Evolution

### AI Foundry Migration (January 2025)
Migrated from traditional Azure OpenAI to AI Foundry with project management capabilities:
- Updated to `2024-06-01-preview` API version using azapi provider
- Preserved model deployments and updated RBAC for new resource structure
- Fixed deprecated `connection_strings` → `primary_sql_connection_string`

### Infrastructure Modernization (July 2025)
Enhanced security and modularity:
- **RBAC Modularization**: Split into service-specific files (identities, storage, messaging, ai, search)
- **Managed Identities**: Eliminated connection strings across all services
- **Logic Apps Standard**: Deployed with elastic scaling and managed identity auth
- **Container Apps**: Background services with CPU-based scaling and OTEL monitoring

### Pipeline & Data Model Evolution (July 2025)
- **Submission Trigger Service**: Event-driven completion coordination
- **Schema Simplification**: Removed `processed` field, added `userMessage` for email body
- **Document Classification**: Dual container updates for consistency
- **Event-Driven State**: Replaced static boolean flags with processing events

## Technical Implementation Patterns

### AI Integration
- **Authentication**: Entra ID for enterprise compliance
- **Structured Outputs**: Flat Pydantic models preferred over nested structures
- **Template Engine**: Jinja2 for dynamic prompt generation
- **API Version**: Stable `2024-06-01` for production reliability
- **Rate Limit Handling**: Tenacity retry decorators with exponential backoff for Azure AI agent calls

### Error Handling & Resilience
- **Retry Logic**: Implemented on submission-analyzer agent calls using tenacity
  - 3 retry attempts with exponential backoff (4-10 seconds)
  - Specific handling for 429 (rate limit), 401/403 (auth), and connection errors
  - Comprehensive logging for retry attempts and failures

### Security & Data Isolation
- **User-specific Document Filtering**: Azure AI Search tool configured with OData filters
  - Filter syntax: `userId eq 'user_value'` applied at tool creation time
  - New agent instance created per submission for proper security isolation
  - Prevents cross-user data access in document search results

### Data Processing & Storage
- **Event Processing**: Change feed with continuation token management
- **Partition Strategy**: userId for submissions, submissionId for triggers
- **Serialization**: `model_dump_json()` for datetime compatibility
- **Cross-Platform**: `datetime.timezone.utc` for Windows support

### Search & Security
- **Vector Configuration**: HNSW algorithm with cosine similarity
- **Security Trimming**: Multi-tenant access via userId filtering
- **Document Chunking**: 2000 chars with 200 char overlap
- **Implementation Approach**: Python scripts over Terraform for complex search configurations

## Critical Implementation Fixes

### Document Classification Enhancement (July 15, 2025)
- Fixed partition key usage in submissions container (userId vs submissionId)
- Enhanced dual container updates for document-submission consistency
- Enables faster queries without cross-container joins

### Schema & Agent Integration (July 16-21, 2025)
- Simplified schema: removed `processed` field, added `userMessage` for email body
- Created automated AI Foundry agent setup script with comprehensive tool integration
- Added Bing Grounding, dual AI Search indexes, and OpenAPI connections for Logic Apps

---

**Development Workflow**: Deploy infrastructure → Update `.env` → `az login` → `uv run python main.py`

**Key Insight**: Event-driven architecture with managed identities provides enterprise-grade security while maintaining development simplicity.
