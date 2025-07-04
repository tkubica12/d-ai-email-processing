# Email Processing System Design

## Overview
This system processes incoming emails containing submission requests using AI to extract relevant information and generate potential responses. The system is built on Azure services with a focus on scalability, reliability, and maintainability.

## Architecture Components

### 1. Email Ingestion and Initial Processing

#### Trigger: Logic App Email Connector
- **Purpose**: Monitor a designated mailbox for incoming emails
- **Trigger Type**: When a new email arrives in the specified mailbox
- **Configuration**: 
  - Email connector configured to monitor specific mailbox
  - Polling frequency: Real-time or configurable interval
  - Email filtering capabilities if needed

#### Event Processing Workflow
1. **Event ID Generation**: 
   - Generate unique GUID for each email processing event
   - This GUID serves as the correlation ID throughout the entire workflow

2. **Blob Storage Container Creation**:
   - Create a new container in Azure Blob Storage using the generated GUID as container name
   - Container naming convention: `email-{GUID}`
   - Set appropriate access policies and retention settings

3. **Email Content Storage**:
   - Extract email body content
   - Store email body as `body.txt` file in the created container
   - Preserve original formatting and encoding

4. **Attachment Processing**:
   - Extract all email attachments
   - Store each attachment as a separate file in the same container
   - Maintain original filenames and file extensions
   - Handle duplicate filenames by appending numeric suffixes

5. **Event Notification**:
   - Emit JSON message to Azure Service Bus Topic
   - Message structure:
     ```json
     {
       "eventId": "generated-guid",
       "timestamp": "ISO-8601-datetime",
       "containerUrl": "https://storageaccount.blob.core.windows.net/email-{guid}",
       "files": [
         {
           "name": "body.txt",
           "url": "https://storageaccount.blob.core.windows.net/email-{guid}/body.txt",
           "type": "email-body"
         },
         {
           "name": "attachment1.pdf",
           "url": "https://storageaccount.blob.core.windows.net/email-{guid}/attachment1.pdf",
           "type": "attachment"
         }
       ]
     }
     ```

## Infrastructure Requirements

### Azure Resources
- **Logic App**: Standard tier for email processing workflow
- **Storage Account**: General Purpose v2 with blob storage for file storage
- **Service Bus Namespace**: Standard tier with topic for event messaging
- **Resource Group**: To contain all related resources

### Deployment Strategy
- **Infrastructure as Code**: Terraform for resource provisioning
- **Application Deployment**: Azure Developer CLI (azd) for unified development and deployment experience
- **CI/CD**: GitHub Actions for automated deployment pipeline

### Security Considerations
- **Email Access**: Secure authentication to email system (OAuth2 or similar)
- **Storage Access**: Managed identity for Logic App to access storage
- **Service Bus**: Shared access policies with minimal required permissions
- **Network Security**: Consider private endpoints for production environments

## Next Steps
This initial phase establishes the foundation for email ingestion and file storage. Subsequent phases will include:
- AI-powered document analysis
- Information extraction from external systems
- Response generation
- Human review workflow