# Implementation Log

Core architectural decisions, technical insights, and implementation progress for the AI Email Processing System.

## Azure OpenAI Integration & Document Processing (July 2025)

### Real LLM Integration Implementation
**Decision**: Replaced mock responses with Azure OpenAI API integration using structured outputs for consistent JSON responses.

**Key Architecture Changes**:
- **Configuration**: `AzureOpenAIConfig` class with endpoint and model settings
- **Prompt Templates**: Jinja2 templates in `actions/prompts/` for classifier and extractor
- **Structured Models**: `LLMDataExtractionResponse` with optional invoice fields
- **Authentication**: `DefaultAzureCredential` with cognitive services token scope

**Critical Design Principle**: Data extraction operates independently of classification results. All documents are processed by both classification and extraction services concurrently, with extraction returning null values for non-relevant document types.

### Parallel Document Processing Architecture
**Implementation**: Suborchestrator pattern enabling parallel processing after document parsing.

**Architecture Components**:
1. **Main Orchestrator**: Stores submission record, starts document suborchestrators in parallel
2. **Document Suborchestrator**: Parses with Document Intelligence, runs classification/extraction concurrently

**Benefits**: Multiple documents processed simultaneously with nested parallelism, fault isolation, and dedicated retry policies.

### Cosmos DB Concurrency & Critical SDK Fix
**Issue**: All operations failing with `TypeError: ClientSession._request() got an unexpected keyword argument 'if_match_etag'`

**Root Cause**: Incorrect parameter usage - Python SDK uses different parameter names than REST API documentation.

**Solution**:
```python
# ❌ WRONG - Causes TypeError
request_options = {"if_match_etag": etag}

# ✅ CORRECT - Proper Python SDK syntax
from azure.core import MatchConditions
kwargs = {"etag": etag, "match_condition": MatchConditions.IfNotModified}
```

**Implementation**: Cosmos DB Patch API with ETag-based concurrency control for safe concurrent updates from classifier and extractor services.

## Azure Durable Functions Critical Fixes (July 2025)

### Silent Failure Resolution
**Critical Issue**: Functions executing successfully (7-43ms) but producing no application output or database writes.

**Root Cause**: Module-level imports like `from models import SubmissionMessage` causing Azure Functions runtime crashes during initialization, with errors being silently swallowed.

**Solution**: Moved all custom imports inside function bodies to prevent module-level crashes and make import errors visible.

```python
# ❌ WRONG - Module level import causes silent crashes
from models import SubmissionMessage

# ✅ CORRECT - Function level import
@app.activity_trigger(input_name="data")
async def my_function(data):
    from models import SubmissionMessage  # Import inside function
```

**Status**: ✅ Functions now execute properly with normal execution times (8-47ms).

### Determinism & Performance Optimizations
**Determinism Fix**: Removed all logging from orchestrator functions to prevent determinism violations (Durable Functions replay orchestrator code multiple times).

**Performance Improvements**:
- Converted activity functions from sync to async for optimal I/O performance
- Eliminated `asyncio.run()` anti-pattern that blocks event loop
- Streamlined from 3-method to 2-method pattern following KISS principle

**Retry Strategy**: Dual-layer approach with activity-level (tenacity) and orchestrator-level (RetryOptions) retry mechanisms.

## Core Architecture & Technology Stack

### System Architecture
**Processing Pipeline**: Event-driven 7-stage pipeline:
Logic App → Submission Intake → Document Parser → Document Classifier → Search Indexer → Data Extractor → Submission Trigger

**Infrastructure Components**:
- **AI Services**: Azure AI Foundry with GPT-4.1 and text-embedding-3-large
- **Storage**: Cosmos DB with partition strategies (userId/submissionId)
- **Search**: Azure AI Search with vector embeddings and security trimming
- **Messaging**: Azure Service Bus with change feed processing
- **Orchestration**: Azure Durable Functions for stateful workflow management

### Technology Stack
- **Backend**: Python with FastHTML web framework, uv dependency management
- **Infrastructure**: Terraform with comprehensive RBAC and managed identities
- **Email Processing**: Azure Logic Apps Standard with elastic scaling
- **Container Services**: Container Apps with CPU-based scaling and OTEL monitoring

### Key Implementation Patterns

**Security & Authentication**:
- Entra ID authentication throughout with `DefaultAzureCredential`
- Eliminated connection strings across all services
- User-specific document filtering with OData filters in Azure AI Search

**AI Integration**:
- Structured outputs with flat Pydantic models
- Jinja2 template engine for dynamic prompt generation
- API version `2024-06-01` for production reliability
- Tenacity retry decorators for rate limit handling

**Data Processing**:
- Event processing with change feed and continuation token management
- Parallel document processing with fault isolation
- ETag-based concurrency control for safe concurrent updates

## Historical Evolution

### Infrastructure Modernization (2024-2025)
- **AI Foundry Migration**: Moved from traditional Azure OpenAI to AI Foundry project management
- **RBAC Modularization**: Split into service-specific files (identities, storage, messaging, ai, search)
- **Schema Evolution**: Removed redundant fields, added `userMessage` for email body content
- **Event-Driven State**: Replaced static boolean flags with processing events

### Development Tools & CI/CD
- **Demo Utilities**: `submit_demo_processed.py` for testing with Service Bus integration
- **GitHub Actions**: Fixed Logic Apps deployment workflow (removed unnecessary .NET build steps)
- **Azure Developer CLI**: Used for local development and deployment workflows

---

**Development Workflow**: Deploy infrastructure → Update `.env` → `az login` → `uv run python main.py`

**Key Insight**: Event-driven architecture with managed identities provides enterprise-grade security while maintaining development simplicity.
