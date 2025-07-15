# Demo Utils

Scripts to help with demos and testing.

## Available Scripts

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