# Implementation Log

This log captures key implementation decisions, technical insights, and architectural changes for the Email Processing System. Entries are organized by major themes for quick reference and future understanding.

---

## 1. Project Architecture & Technology Stack

**Core Technology Decisions:**
- **FastHTML**: Rapid Python web UI development with single-file simplicity
- **uv**: Modern Python dependency management and execution
- **DefaultAzureCredential**: Secure, secretless Azure authentication
- **Terraform**: Infrastructure as Code with RBAC for local development
- **Pydantic**: Type-safe data models and validation throughout

**Development Workflow:**
1. Deploy infrastructure → 2. Update `.env` from Terraform outputs → 3. Authenticate with `az login` → 4. Run with `uv run python main.py`

**Key Architectural Principles:**
- Event-driven architecture with Azure Service Bus
- Stateless, container-ready applications
- No secrets in code; all config via environment variables
- Structured logging and comprehensive error handling

---

## 2. Document Processing Pipeline

**Service Overview:**
The system implements a multi-stage document processing pipeline:

1. **Submission Intake** → Service Bus worker processing new submissions
2. **Document Parser** → Azure Document Intelligence extraction to Cosmos DB
3. **Document Classifier** → Azure OpenAI classification into document types
4. **Data Extractor** → Structured data extraction from invoices

**Common Patterns Established:**
- **Change Feed Processing**: Cosmos DB event-driven service pattern
- **Azure OpenAI Integration**: Structured outputs with Pydantic models
- **Event Emission**: Consistent event structure with proper datetime serialization
- **Error Handling**: Graceful failures with continued processing

---

## 3. Critical Technical Fixes & Lessons Learned

**Event System Consistency:**
- **Issue**: Missing `documentId` in event data and inconsistent partition keys
- **Solution**: Standardized event data structure and corrected partition key usage (`submissionId`)
- **Impact**: Reliable event processing across all document services

**Pydantic & OpenAI Integration:**
- **Issue**: Complex nested models causing OpenAI structured output failures
- **Solution**: Flattened data models for better API compatibility
- **Learning**: OpenAI structured outputs work best with simple, flat schemas

**Event Serialization:**
- **Issue**: DateTime objects not JSON serializable in event emission
- **Solution**: Use `model_dump(mode='json')` for proper datetime handling
- **Impact**: Prevents runtime errors during event publishing

**Azure SDK Dependencies:**
- **Issue**: Missing Azure SDK packages causing import errors
- **Solution**: Explicitly declare all Azure SDK dependencies in `pyproject.toml`
- **Learning**: Don't rely on transitive dependencies for Azure services

---

## 4. Service Implementation Insights

**Document Classification Service:**
- Implemented enum-based document types (`invoice`, `contract`, `bankStatement`, `submissionNotes`, `other`)
- Used Jinja2 templates for system prompts enabling easy customization
- Established pattern for Azure OpenAI integration with structured outputs

**Document Data Extractor Service:**
- Evolved from classifier to focus on structured invoice data extraction
- Simplified from nested to flat data models for better OpenAI compatibility
- Implemented invoice-specific fields: `invoiceNumber`, `totalAmount`, `currency`, `dueDate`, `vendor`

**Common Service Patterns:**
- **Configuration**: Environment variables with consistent naming
- **Processing**: Async operations with proper resource cleanup
- **Error Recovery**: Continue processing on individual document failures
- **State Management**: Optional continuation token persistence via Azure Table Storage

---

## 5. UI/UX Evolution

**Progress Feedback Simplification:**
- **Initial**: Complex HTMX-based step-by-step progress tracking
- **Final**: Simple status indicators ("processing", "complete", "error")
- **Rationale**: Users prefer clear feedback over detailed but potentially misleading progress steps

**Setup Simplification:**
- Removed helper scripts (`configure.py`, `run_dev.py`) for manual setup
- Direct execution model reduces complexity and improves reliability

---

## 6. Configuration & Naming Improvements

**Service Bus Topic Renaming:**
- Changed from `email-events` to `new-submissions` for clarity
- Updated all references across code, infrastructure, and documentation

**Data Model Evolution:**
- Migrated from plain dictionaries to Pydantic models for Service Bus messages
- Added `submittedAt` timestamp for traceability
- Enabled automatic JSON schema generation for future API documentation

---

**This log focuses on architectural decisions, critical fixes, and lessons learned. For detailed implementation, see source code and service-specific documentation.**
