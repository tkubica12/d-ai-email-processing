# Client Web Application

## Overview
The Client Web Application provides a web-based interface for users to submit requests similar to email submissions. Users can enter their email address, compose a message body, and attach documents for processing by the email processing system.

## Features
- **User-friendly Form**: Simple web interface for submission creation
- **File Uploads**: Support for multiple document attachments
- **Azure Integration**: Seamless integration with Azure Blob Storage and Service Bus
- **Secure Authentication**: Uses Entra ID with Managed Identity for Azure services

## Architecture

### Technology Stack
- **Framework**: Python with FastHTML for rapid UI development
- **Package Manager**: uv (no requirements.txt or pip dependencies)
- **Containerization**: Docker for consistent deployment
- **Hosting**: Azure Container Apps for scalable cloud hosting
- **Authentication**: Entra ID Managed Identity for Azure service access

### High-Level Flow
1. User accesses the web form
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
  {submission-guid}/
  ├── body.txt
  ├── attachment1.pdf
  ├── attachment2.docx
  └── ...
  ```

### Service Bus Topic
- **Authentication**: Entra ID Managed Identity (no connection strings)
- **Message Format**: JSON containing:
  - `userId`: User's email address
  - `submissionId`: Generated GUID
  - `documentUrls`: Array of blob URLs for each stored document
  - `timestamp`: Submission timestamp
  - `metadata`: Additional submission information

### Example Service Bus Message
```json
{
  "userId": "user@example.com",
  "submissionId": "123e4567-e89b-12d3-a456-426614174000",
  "documentUrls": [
    "https://storage.blob.core.windows.net/{submission-guid}/body.txt",
    "https://storage.blob.core.windows.net/{submission-guid}/document1.pdf",
    "https://storage.blob.core.windows.net/{submission-guid}/document2.docx"
  ],
  "timestamp": "2025-07-07T10:30:00Z",
  "metadata": {
    "sourceType": "web-form",
    "attachmentCount": 2,
    "bodyLength": 1024
  }
}
```

## Security Considerations
- **Managed Identity**: No stored credentials or connection strings
- **File Validation**: Input validation and file type restrictions
- **Container Isolation**: Each submission isolated in separate blob container
- **Secure Transmission**: HTTPS-only communication

## Deployment

### Container Apps Configuration
- **CPU/Memory**: Configurable based on expected load
- **Scaling**: Auto-scaling based on HTTP requests
- **Environment Variables**:
  - `STORAGE_ACCOUNT_NAME`: Azure Storage account name
  - `SERVICE_BUS_NAMESPACE`: Service Bus namespace
  - `SERVICE_BUS_TOPIC`: Topic name for events
  - `ALLOWED_FILE_TYPES`: Comma-separated list of allowed file extensions

### Prerequisites
- Azure Container Apps environment
- Azure Storage Account with appropriate permissions
- Azure Service Bus namespace and topic
- Managed Identity with required role assignments:
  - Storage Blob Data Contributor (for Blob Storage)
  - Azure Service Bus Data Sender (for Service Bus Topic)

## Development

### Local Development
```bash
# Install uv package manager
# Run application locally with Azure credentials
uv run python main.py
```

### Building Container
```bash
# Build Docker image
docker build -t client-web-app .

# Run container locally
docker run -p 8000:8000 client-web-app
```

## Monitoring and Logging
- Application logs for debugging and monitoring
- Azure Monitor integration for performance metrics
- Service Bus message tracking for event delivery confirmation
- Blob Storage access logs for file upload verification