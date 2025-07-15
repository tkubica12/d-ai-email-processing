# AI Email Processing System

An Azure-based email processing system that uses AI to analyze incoming submission requests, extract information from documents, and assist operators with generating responses. The system supports both email triggers and web form submissions with file attachments.

## Architecture

The system offers two architectural approaches:
- **Workflow Orchestration**: Using Azure Logic Apps for centralized orchestration
- **Event Sourcing**: Using event-driven architecture with Cosmos DB

See [Design.md](docs/Design.md) for detailed architecture comparison and implementation options.

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

2. **Configure Environment Variables**
   After deployment, update your application's `.env` file with the output values:
   ```bash
   # Get outputs from Terraform
   terraform output -json
   ```

### Running the Web Client

1. **Navigate to client application**
   ```bash
   cd src/client-web
   ```

2. **Install dependencies**
   ```bash
   uv sync
   ```

3. **Run the application**
   ```bash
   uv run python main.py
   ```

4. **Access the application**
   Open your browser to `http://localhost:8000`

### Running the Submission Intake Service (Background)

The submission-intake service is a background worker that processes Service Bus messages:

1. **Navigate to submission-intake service**
   ```bash
   cd src/submission-intake
   ```

2. **Install dependencies**
   ```bash
   uv sync
   ```

3. **Run the service**
   ```bash
   uv run python main.py
   ```

The service will continuously listen for messages from the Service Bus topic and process them.

### Running the Document Parser Foundry Service (Background)

The docproc-parser-foundry service is a background worker that processes Cosmos DB Change Feed events:

1. **Navigate to docproc-parser-foundry service**
   ```bash
   cd src/docproc-parser-foundry
   ```

2. **Install dependencies**
   ```bash
   uv sync
   ```

3. **Run the service**
   ```bash
   uv run python main.py
   ```

The service will continuously monitor the Cosmos DB Change Feed for DocumentUploadedEvent events and process them using Azure Document Intelligence.

### Running the Document Classifier Service (Background)

The docproc-classifier service is a background worker that processes Cosmos DB Change Feed events for document classification:

1. **Navigate to docproc-classifier service**
   ```bash
   cd src/docproc-classifier
   ```

2. **Install dependencies**
   ```bash
   uv sync
   ```

3. **Run the service**
   ```bash
   uv run python main.py
   ```

The service will continuously monitor the Cosmos DB Change Feed for DocumentContentExtractedEvent events and classify them using Azure OpenAI.

### Running the Document Data Extractor Service (Background)

The docproc-data-extractor service is a background worker that processes Cosmos DB Change Feed events for structured data extraction:

1. **Navigate to docproc-data-extractor service**
   ```bash
   cd src/docproc-data-extractor
   ```

2. **Install dependencies**
   ```bash
   uv sync
   ```

3. **Run the service**
   ```bash
   uv run python main.py
   ```

The service will continuously monitor the Cosmos DB Change Feed for DocumentContentExtractedEvent events and extract structured data using Azure OpenAI.

### Running the Document Search Indexer Service (Background)

The docproc-search-indexer service is a background worker that processes Cosmos DB Change Feed events for Azure AI Search indexing:

1. **Navigate to docproc-search-indexer service**
   ```bash
   cd src/docproc-search-indexer
   ```

2. **Install dependencies**
   ```bash
   uv sync
   ```

3. **Run the service**
   ```bash
   uv run python main.py
   ```

The service will continuously monitor the Cosmos DB Change Feed for DocumentContentExtractedEvent events and index document content into Azure AI Search with embeddings.

### Running in Container Apps

After infrastructure deployment, the client-web service is automatically deployed as a Container App with the following features:
- **Managed Identity Authentication**: Secure access to Azure services
- **Auto-scaling**: Scale to zero when not in use
- **HTTPS Ingress**: Automatic SSL termination
- **Monitoring**: Application Insights integration

Access the deployed web application using the `client_web_url` output from Terraform.

## Infrastructure Components

### Current Deployment Includes:
- **Azure Storage Account**: Blob storage for submission files
- **Azure Service Bus**: Event messaging for processing pipeline
- **Azure Cosmos DB**: Serverless database for event sourcing and data persistence
  - Events container: Event sourcing with change feed
  - Documents container: Processed document results
  - Submissions container: Submission records
- **Azure Container Apps**: Serverless container hosting for web services
  - Client Web: User interface for document submission
  - Company APIs: Business data integration endpoints
  - Submission Intake: Background service for processing Service Bus messages
  - Document Parser Foundry: Change feed processor for document content extraction
  - Document Classifier: AI-powered document classification using Azure OpenAI
  - Document Data Extractor: Structured data extraction from documents using Azure OpenAI
  - Document Search Indexer: AI-powered search indexing with vector embeddings using Azure AI Search
- **Azure AI Search**: Vector search with semantic capabilities for document retrieval
- **Azure OpenAI**: GPT-4.1 for classification/extraction and text-embedding-3-large for vector search
- **RBAC Configuration**: Proper permissions for local development and managed identities

### Cosmos DB Configuration
The system uses serverless Cosmos DB with three containers:
- `events`: Change feed enabled for event processing pipeline
- `documents`: Document analysis results with `/documentUrl` partition key
- `submissions`: Submission records with `/submissionId` partition key

## Development

### Local Development Setup
1. Ensure you're authenticated with Azure CLI: `az login`
2. Deploy infrastructure with Terraform
3. Configure environment variables from Terraform outputs
4. Install dependencies and run applications

See [ImplementationLog.md](docs/ImplementationLog.md) for detailed implementation progress and technical decisions.