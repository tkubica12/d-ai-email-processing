# Client Web Application

## Overview
The Client Web Application provides a web-based interface for users to submit requests similar to email submissions. Users can enter their email address, compose a message body, and attach documents for processing by the email processing system.

## Features
- **User-friendly Form**: Simple web interface for submission creation
- **File Uploads**: Support for multiple document attachments
- **Azure Integration**: Seamless integration with Azure Blob Storage and Service Bus
- **Secure Authentication**: Uses Entra ID with DefaultAzureCredential for Azure services
- **Development Mode**: Runs locally without Azure integration for development

## Architecture

### Technology Stack
- **Framework**: Python with FastHTML for rapid UI development
- **Package Manager**: uv (no requirements.txt or pip dependencies)
- **Containerization**: Docker for consistent deployment
- **Hosting**: Azure Container Apps for scalable cloud hosting (future)
- **Authentication**: Entra ID DefaultAzureCredential for Azure service access

### High-Level Flow
1. User accesses the web form at `/`
2. User enters email address and message body
3. User optionally uploads one or more attachments
4. Application generates unique GUID for the submission
5. Files are stored in Azure Blob Storage container (named with submission GUID)
6. Event is published to Azure Service Bus Topic with submission metadata

### Data Flow
```
Web Form → File Processing → Azure Blob Storage
    ↓
Service Bus Topic Event
    ↓
Email Processing Pipeline
```

## Azure Services Integration

### Blob Storage
- **Container Naming**: Each submission creates a new container named with the submission GUID
- **File Storage**: 
  - `body.txt`: Contains the message body text
  - Original attachment files with preserved names
- **Container Structure**:
  ```
  <submission-guid>/
  ├── body.txt
  ├── attachment1.pdf
  └── attachment2.docx
  ```

### Service Bus Topic
- **Authentication**: Entra ID DefaultAzureCredential (no connection strings)
- **Topic Name**: `email-events`
- **Message Format**: JSON containing:
  - `submissionId`: Unique GUID for the submission
  - `userId`: User's email address
  - `metadata`: Additional submission information

### Example Service Bus Message
```json
{
  "submissionId": "123e4567-e89b-12d3-a456-426614174000",
  "userId": "user@example.com",
  "metadata": {
    "messageLength": 245,
    "attachmentCount": 2,
    "attachmentNames": ["document.pdf", "image.jpg"],
    "containerName": "123e4567-e89b-12d3-a456-426614174000"
  }
}
```

## Prerequisites

### Local Development
- Python 3.12 or higher
- [uv package manager](https://docs.astral.sh/uv/getting-started/installation/)
- [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli)
- Azure subscription with deployed infrastructure

### Azure Infrastructure
- Azure Storage Account (deployed via Terraform)
- Azure Service Bus Namespace with `email-events` topic (deployed via Terraform)
- RBAC permissions for your user account (configured via Terraform)

## Setup Instructions

### 1. Deploy Infrastructure
First, deploy the Azure infrastructure using Terraform:

```powershell
cd ../../infra
terraform init
terraform plan
terraform apply
```

### 2. Configure Environment
Get Azure resource names from Terraform outputs and update the `.env` file:

```powershell
cd ../src/client-web
# Get storage account name from terraform output
terraform output -json | jq -r .storage_account_name.value

# Get service bus fqdn from terraform output  
terraform output -json | jq -r .service_bus_fqdn.value

# Manually update .env file with the values
# AZURE_STORAGE_ACCOUNT_NAME=your-storage-account-name
# AZURE_SERVICE_BUS_FQDN=your-namespace.servicebus.windows.net
```

### 3. Authenticate with Azure
Ensure you're logged in to Azure CLI:

```powershell
az login
```

The application uses `DefaultAzureCredential` which will automatically use your Azure CLI authentication.

### 4. Install Dependencies
Install the Python dependencies using uv:

```powershell
uv sync
```

### 5. Run the Application
Start the development server:

```powershell
uv run python main.py
```

The application will be available at: http://localhost:8000

## Development

### Project Structure
```
client-web/
├── main.py              # Main FastHTML application
├── Dockerfile          # Container configuration
├── pyproject.toml      # Python project configuration
├── uv.lock            # Dependency lock file
├── .env               # Environment variables
├── .env.example       # Example environment file
└── README.md          # This file
```

### Environment Variables
- `AZURE_STORAGE_ACCOUNT_NAME`: Name of the Azure Storage Account
- `AZURE_SERVICE_BUS_FQDN`: Fully qualified domain name of Service Bus namespace
- `AZURE_SERVICE_BUS_TOPIC_NAME`: Name of the Service Bus topic (default: email-events)
- `HOST`: Application host (default: 0.0.0.0)
- `PORT`: Application port (default: 8000)

### Development Mode
The application can run in development mode without Azure integration:
- If Azure authentication fails, the app continues in development mode
- Submissions are logged to console instead of being sent to Azure
- All form functionality works for testing the UI

### Adding Dependencies
Add new dependencies to `pyproject.toml`:

```toml
dependencies = [
    "new-package>=1.0.0",
]
```

Then run `uv sync` to install.

### Testing the Application

#### Manual Testing
1. Access http://localhost:8000
2. Fill in the form with:
   - Valid email address
   - Message body
   - Optional file attachments
3. Submit the form
4. Verify success message with submission ID

#### Azure Integration Testing
1. Check Azure Storage for created containers
2. Verify blob uploads in the container
3. Check Service Bus topic for published messages

### Troubleshooting

#### Common Issues

**Azure Authentication Errors**
```
Error: DefaultAzureCredential failed to retrieve a token
```
Solution: Run `az login` and ensure you have the correct Azure subscription selected.

**Missing Environment Variables**
```
Missing required environment variables: AZURE_STORAGE_ACCOUNT_NAME
```
Solution: Manually update the `.env` file with values from Terraform outputs.

**Permission Denied**
```
Error: (AuthorizationFailed) This request is not authorized
```
Solution: Verify that Terraform has applied the RBAC assignments. Check with `az role assignment list --assignee $(az account show --query user.name -o tsv)`.

**Dependencies Not Found**
```
Import "fasthtml.common" could not be resolved
```
Solution: Install dependencies with `uv sync`.

#### Verification Commands

Check Azure resources:
```powershell
# Check storage account
az storage account show --name <storage-account-name> --resource-group <resource-group>

# Check service bus namespace
az servicebus namespace show --name <namespace-name> --resource-group <resource-group>

# Check role assignments
az role assignment list --assignee $(az account show --query user.name -o tsv)
```

## Container Deployment

### Build Container
```powershell
docker build -t client-web .
```

### Run Container Locally
```powershell
docker run -p 8000:8000 --env-file .env client-web
```

Note: For container deployment with Azure integration, the container will need access to Azure credentials through environment variables or managed identity.

## Next Steps
- Azure Container Apps deployment configuration
- GitHub Actions workflow for CI/CD
- Production environment configuration
- Monitoring and logging integration
