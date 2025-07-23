# Demo Utils

Scripts to help with demos and testing.

## Available Scripts

### agent_create.py
A script to create two connected Azure AI Foundry Agents for comprehensive email processing and document analysis.

**What it does:**
- Creates `companyPoliciesAgent` - Subordinate agent specializing in policy and regulatory guidance with AI Search access to company policies
- Creates `submissionAnalyzer` - Primary agent with Bing Search, AI Search (documents), Company APIs, and connected to the policies agent
- Automatically configures the connected agent relationship for seamless policy delegation

**Prerequisites:**
- Azure AI Foundry project set up with required connections (Bing Search, AI Search, OpenAPI)
- Azure CLI installed and logged in (`az login`)
- Connection IDs configured in the script (modify PROJECT_ENDPOINT and connection IDs as needed)

**Usage:**
```bash
# Install dependencies
uv sync

# Ensure you're logged into Azure
az login

# Run the script (modify connection IDs in the script first)
uv run python agent_create.py
```

### cleanup_demo_data.py
A utility script to clean up demo data from Azure resources.

**What it does:**
- Deletes all records from Cosmos DB containers (events, documents, submissions)
- Deletes all storage containers in GUID format (preserves policies-docs container)

**Usage:**
```bash
# Install dependencies
uv sync

# Ensure you're logged into Azure
az login

# Run the cleanup
uv run python cleanup_demo_data.py
```

### submit_demo_processed.py
A utility script to send a demo processed submission message to Service Bus.

**What it does:**
- Sends a single demo message to the processed submissions Service Bus topic
- Uses predefined JSON content with sample processed submission data
- Useful for testing downstream components that consume processed submission messages

**Usage:**
```bash
# Install dependencies
uv sync

# Ensure you're logged into Azure
az login

# Run the demo processed message submission
uv run python submit_demo_processed.py
```

### submit_demo_data.py
A utility script to submit demo data from the demo-submissions folder.

**What it does:**
- Processes all subfolders in the configured demo submissions directory
- For each subfolder, uploads all files (including body.txt) to Azure Blob Storage
- Sends Service Bus messages to trigger the email processing pipeline
- Mimics the client-web application behavior for testing purposes

**Usage:**
```bash
# Install dependencies
uv sync

# Ensure you're logged into Azure
az login

# Run the demo data submission
uv run python submit_demo_data.py
```

**Prerequisites:**
- Azure CLI installed and authenticated (`az login`)
- Proper environment variables set in `.env` file
- Required permissions to delete resources in the configured Azure subscription

**Environment Variables:**
The script reads configuration from `.env` file. See `.env.example` for required variables.