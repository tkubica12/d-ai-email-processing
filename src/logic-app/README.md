# Email Processing Logic App Standard - Setup Guide

## Overview
This Logic App Standard processes incoming emails with "DEMO" in the subject line, extracts content and attachments, and publishes events to Service Bus for downstream processing. Logic App Standard runs on Azure Functions, providing better integration with development tools and CI/CD.

## Prerequisites
- Azure Developer CLI (azd) installed
- Azure subscription with permissions to create resources
- Office 365 or Exchange Online mailbox to monitor
- Azure Functions Core Tools (for local development)

## Deployment Steps

### 1. Deploy Infrastructure and Logic App
```powershell
# Deploy the infrastructure and Logic App Standard
azd up
```

This will:
- Create Azure infrastructure (Function App, Storage, Service Bus, etc.)
- Deploy the Logic App workflow code
- Set up the Office 365 API connection (requires manual authentication)

### 2. Configure Office 365 Connection
After deployment, the Office 365 API connection requires manual authentication:

```powershell
# Run the setup script to get detailed instructions
.\scripts\setup-office365-connection.ps1
```

**Manual Steps:**
1. Open [Azure Portal](https://portal.azure.com)
2. Navigate to your resource group
3. Find the Office 365 API Connection (name: `office365-{prefix}`)
4. Click "Edit API connection"
5. Click "Authorize" and sign in with the email account you want to monitor
6. Save the connection

> **Important**: The email account you use for authorization will be the mailbox monitored by the Logic App. Make sure it's the correct account for your workflow.

## Local Development

### 1. Prerequisites
```powershell
# Install Azure Functions Core Tools
npm install -g azure-functions-core-tools@4 --unsafe-perm true
```

### 2. Run Locally
```powershell
cd src/logic-app
func start
```

## Testing the Logic App

### 1. Send Test Email
Send an email to the authenticated mailbox with:
- Subject containing "DEMO" (e.g., "DEMO Test Email")
- Some body content
- Optional attachments

### 2. Monitor Execution
1. Go to Azure Portal > Function Apps
2. Find your Logic App: `logic-{prefix}`
3. Go to "Logic Apps" > "Workflows" > "email-processing-workflow"
4. Check "Run History" to see triggered executions
5. Click on a run to see detailed execution steps

### 3. Expected Behavior
The Logic App should:
- Trigger when email arrives with "DEMO" in subject
- Generate a unique event ID (GUID)
- Extract email content and metadata
- Return HTTP 200 response with event details

## Troubleshooting

### Common Issues
1. **Logic App not triggering**: Check Office 365 connection authorization
2. **Permission errors**: Verify managed identity has correct role assignments
3. **Connection not found**: Ensure infrastructure deployment completed successfully
4. **Workflow not found**: Check that the workflow was deployed correctly

### Debug Steps
1. Check Function App logs in Azure Portal
2. Review workflow run history in Logic Apps section
3. Verify API connection status
4. Check Azure Activity Log for deployment issues

## Configuration

### Email Trigger Settings
Located in `email-processing-workflow/workflow.json`:
- **Folder**: Inbox
- **Subject Filter**: "DEMO"
- **Include Attachments**: Yes
- **Fetch Only With Attachments**: No
- **Importance**: Any

### Customization
To modify trigger settings, edit the workflow definition:
- Change `subjectFilter` to match different email subjects
- Modify `folderPath` to monitor different folders
- Adjust `fetchOnlyWithAttachment` if you only want emails with attachments

### Environment Variables
Key app settings (configured automatically):
- `APP_KIND`: "workflowApp" (enables Logic App features)
- `AzureFunctionsJobHost__extensionBundle__id`: Logic App extension bundle
- `WORKFLOWS_SUBSCRIPTION_ID`: Azure subscription for workflow management

## Project Structure
```
src/logic-app/
├── host.json                              # Function host configuration
├── local.settings.json                    # Local development settings
├── connections.json                       # API connections configuration
└── email-processing-workflow/
    └── workflow.json                       # Workflow definition
```

## Next Steps
This implementation covers task 2.1 (Email trigger configuration). Next tasks will add:
- Blob storage container creation (2.2)
- Email content processing (2.3)
- Attachment processing (2.4)
- Service Bus message publishing (2.5)
