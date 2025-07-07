# Email Submission AI Processing
This repo contains demo scenario for processing incoming emails using AI to extract relevant information and generate potential responses.

- New email is received containing request to process submission
- AI is triggered to analyze the email content
- Information about user and related information is extracted from IT 1.0
- Documents attached to email are processed and analyzed
- AI extract key data from documents and decides what is missing and what is submitted
- Based on this information AI generates potential response to user and send it to representative for review

More design details can be found in [Design Document](./docs/Design.md).

Implementation plan is available in [Implementation Plan](./docs/ImplementationPlan.md).

Implementation log is available in [Implementation Log](./docs/ImplementationLog.md).

Common errors and pitfalls are documented in [Common Errors](./docs/CommonErrors.md).

## Quick Start

### Prerequisites
- Azure Developer CLI (azd) installed
- Azure subscription with permissions to create resources
- Azure Functions Core Tools v4.0.5455 or later
- Visual Studio Code with Azure Logic Apps (Standard) extension

### Local Development Setup

1. **Clone and setup project**:
   ```powershell
   git clone <repository-url>
   cd d-ai-email-processing
   ```

2. **Install dependencies**:
   ```powershell
   cd src/logic-app
   npm install
   ```

3. **Start local development**:
   ```powershell
   func start
   ```

### Deployment

1. **Deploy to Azure**:
   ```powershell
   azd up
   ```

2. **Authorize Office 365 Connection**:
   After deployment, you need to authorize the Office 365 connection:
   - Go to Azure Portal > Resource Groups > [your-resource-group]
   - Find the Office 365 connection (office365-[prefix])
   - Click "Edit API connection"
   - Click "Authorize" and sign in with your Office 365 account
   - Save the connection

3. **Verify deployment**:
   - Check Azure portal for Logic App Standard resources
   - Ensure Functions runtime shows v4.x
   - Verify no runtime errors in Application Insights
   - Test the workflow by sending an email with subject containing "DEMO"

### Troubleshooting Runtime Issues

If you encounter "System.IO.Path loading error" or "Functions runtime deprecation" warnings:

1. **Check runtime version**:
   - Ensure `FUNCTIONS_EXTENSION_VERSION` is set to `~4`
   - Verify `FUNCTIONS_INPROC_NET8_ENABLED` is set to `1`

2. **Update local environment**:
   ```powershell
   npm install azure-functions-core-tools@latest
   ```

3. **Redeploy with updated configuration**:
   ```powershell
   azd deploy
   ```

For detailed troubleshooting, see [Common Errors](./docs/CommonErrors.md).