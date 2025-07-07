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
   Open your browser to `http://localhost:5001`

## Infrastructure Components

### Current Deployment Includes:
- **Azure Storage Account**: Blob storage for submission files
- **Azure Service Bus**: Event messaging for processing pipeline
- **Azure Cosmos DB**: Serverless database for event sourcing and data persistence
  - Events container: Event sourcing with change feed
  - Documents container: Processed document results
  - Submissions container: Submission records
- **RBAC Configuration**: Proper permissions for local development

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