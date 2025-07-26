# AI Email Processing System

An Azure-based email processing system that uses AI to analyze incoming submission requests, extract information from documents, and assist operators with generating responses. The system supports both email triggers and web form submissions with file attachments.

## Why This System?

Modern businesses receive countless document submissions that require human review and processing. This system automates the initial analysis using AI to:
- **Extract and classify** document content using Azure Document Intelligence
- **Analyze submissions** with AI agents that can search previous documents, investigate entities, and access company data
- **Generate insights** to help operators make faster, more informed decisions
- **Ensure security** through user-specific document isolation and access controls

## Architecture Overview

The system offers multiple architectural approaches for different scalability and complexity needs:
- **Event Sourcing**: Event-driven architecture with Cosmos DB for extreme scale and audit trails
- **Workflow Orchestration**: Azure Logic Apps for simpler, visual workflow management
- **Agentic Orchestration**: AI-driven coordination without predetermined paths

📖 **See [Design.md](docs/Design.md) for detailed architecture comparison, data models, and implementation patterns.**

## Quick Start

### Prerequisites
- Azure CLI installed and authenticated (`az login`)
- Terraform installed
- Python 3.12+ with uv package manager

### Infrastructure Deployment

1. **Deploy Azure Resources**
   ```bash
   cd infra
   terraform init
   terraform plan
   terraform apply
   ```

2. **Get deployment outputs for configuration**
   ```bash
   terraform output -json
   ```

3. **Deploy Logic Apps via GitHub Actions**
   - Logic Apps workflows and connections are deployed automatically via GitHub Actions
   - Terraform creates the Logic Apps infrastructure and connectors
   - GitHub Actions deploys the workflow definitions and configuration
   - Push to `main` branch triggers automatic deployment of Logic Apps Standard

### Running Services

The system consists of multiple services that work together:

#### Web Client (User Interface)
```bash
cd src/client-web
uv sync
uv run python main.py
# Access at http://localhost:8000
```

#### Background Processing Services

**Durable Functions Submission Processing:**
```bash
# Main orchestration service for document processing
cd submissions-durable-functions
func start --python
# Or use VS Code Azure Functions extension for debugging
```

**Document Processing Pipeline:**
```bash
# Document content extraction
cd src/docproc-parser-foundry && uv sync && uv run python main.py

# Document classification
cd src/docproc-classifier && uv sync && uv run python main.py

# Data extraction
cd src/docproc-data-extractor && uv sync && uv run python main.py

# Search indexing
cd src/docproc-search-indexer && uv sync && uv run python main.py
```

**Submission Processing:**
```bash
# Intake processing
cd src/submission-intake && uv sync && uv run python main.py
```

**Business APIs:**
```bash
# Company data APIs
cd src/company-apis && uv sync && uv run python main.py
```

## Testing Document Processing Workflow

### End-to-End Flow Testing

1. **Start Required Services**
   ```bash
   # Terminal 1: Start Durable Functions
   cd submissions-durable-functions
   func start --python
   
   # Terminal 2: Start Web Client (optional for direct testing)
   cd src/client-web && uv run python main.py
   ```

2. **Test Document Processing**
   - Upload documents through web interface or place test files in demo-submissions/
   - Monitor processing through Azure Storage Explorer and Cosmos DB Data Explorer
   - Check function logs for orchestration progress
   - Verify document records show completed classification and extraction status

3. **Expected Processing Flow**
   ```
   Document Upload → Service Bus Message → Main Orchestrator
   ↓
   Store Submission → Document Suborchestrators (parallel)
   ↓  
   Parse Document → Classification + Data Extraction (parallel)
   ↓
   Updated Cosmos DB Records with structured data
   ```

### Monitoring Processing Status

Check document processing status in Cosmos DB:
```json
{
  "id": "document-id",
  "submissionId": "submission-id", 
  "classificationStatus": "completed",  // pending → completed/failed
  "dataExtractionStatus": "completed",  // pending → completed/failed
  "documentType": "invoice",            // Set by classifier
  "extractedData": { ... },             // Set by extractor
  "summary": "Document summary..."       // Set by classifier
}
```
```bash
# Intake processing
cd src/submission-intake && uv sync && uv run python main.py
```

**Business APIs:**
```bash
# Company data APIs
cd src/company-apis && uv sync && uv run python main.py
```

## Key Features

### Document Processing
- **Multi-format support**: PDF, DOCX, images via Azure Document Intelligence
- **AI Classification**: Automatic document type detection (invoices, contracts, etc.)
- **Data Extraction**: Structured data extraction using Azure OpenAI
- **Vector Search**: Semantic search with user-specific security trimming

### AI Agent Capabilities
- **RAG Search**: Retrieve user's previous documents and conversations
- **Entity Investigation**: Web search for vendor/company verification
- **Company Integration**: Access internal APIs for user products, financial scores, income data
- **Comprehensive Analysis**: Generate insights combining all data sources

### Security & Compliance
- **User Isolation**: Documents are strictly separated by user identity
- **Managed Identity**: Secure service-to-service authentication
- **Audit Trail**: Complete event history in Cosmos DB
- **Access Controls**: RBAC-based permissions for all Azure resources

## Infrastructure Components

### Core Services
- **Azure Storage**: Document blob storage with container-per-submission isolation
- **Azure Service Bus**: Reliable message queuing for processing pipeline
- **Azure Cosmos DB**: Serverless database with change feed for event processing
- **Azure Container Apps**: Auto-scaling serverless container hosting
- **Azure AI Search**: Vector search with semantic capabilities and security trimming
- **Azure OpenAI**: GPT-4 for analysis and text-embedding-3-large for search

### Processing Architecture
The system uses an event-driven architecture where document uploads trigger a cascade of AI processing:
1. **Document Upload** → Content extraction → Classification → Data extraction → Search indexing
2. **Submission Analysis** → AI agent combines search, web lookup, and company APIs
3. **Results Generation** → Comprehensive insights and recommendations

📖 **See [Design.md](docs/Design.md) for detailed service interactions, data schemas, and scaling patterns.**

## Container Apps Deployment

After infrastructure deployment, services are automatically deployed to Azure Container Apps with:
- **Auto-scaling**: Scale to zero when idle, scale up under load
- **Managed Identity**: Secure access to Azure services without secrets
- **HTTPS Ingress**: Automatic SSL termination for web services
- **Monitoring**: Application Insights integration for observability

Access the deployed web application using the `client_web_url` output from Terraform.

## Logic Apps Deployment

The system uses a hybrid deployment approach for Logic Apps:

### Infrastructure (Terraform)
- **Logic Apps Standard runtime**: Creates the hosting environment
- **API Connections**: Deploys connectors for external services (email, storage, etc.)
- **Access policies**: Configures managed identity and RBAC permissions

### Workflows (GitHub Actions)
- **Workflow definitions**: JSON-based Logic Apps workflows in `logic-apps/` folder
- **Connections configuration**: Runtime connection settings and parameters
- **Automatic deployment**: Triggered on push to main branch via `.github/workflows/`

This separation allows infrastructure to be managed through IaC while enabling rapid iteration on workflow logic through version control.

### Teams Integration Setup
After deployment, the Microsoft Teams connector requires manual authorization:

1. **Navigate to Azure Portal** → Logic Apps → your logic app → API connections
2. **Find the Teams connection** and click on it
3. **Click "Authorize"** to authenticate and grant permissions
4. **Configure operator account**: Set the `operator_user_name` variable in `terraform.tfvars` to specify which user account will be used for Teams notifications (default: `admin@tkubica.net`)

## Development

### Local Development
1. Authenticate with Azure: `az login`
2. Deploy infrastructure with Terraform
3. Configure services with Terraform outputs
4. Run services locally for development and testing

### Documentation
- **[Design.md](docs/Design.md)**: Complete architecture, data models, and service interactions
- **[ImplementationLog.md](docs/ImplementationLog.md)**: Development progress and technical decisions
- **[CommonErrors.md](docs/CommonErrors.md)**: Known issues and solutions