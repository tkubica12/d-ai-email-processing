# Submission Analyzer Service

## Overview
The Submission Analyzer service performs AI-powered analysis of submission content using Azure AI Projects. It analyzes email submissions, complaints, or support requests to provide comprehensive insights and recommendations using multiple AI tools.

## Features
- **Bing Grounding Tool**: Access to current web information and market data
- **Company API Integration**: Access to internal company data including:
  - User products and subscriptions
  - Financial scores and assessments
  - Income data and trends
- **Azure AI Search Integration**: Search through submitted documents and previous submissions to find relevant information
- **Managed Identity Authentication**: Secure access to company APIs and Azure services using Azure Managed Identity
- **Comprehensive Analysis**: Combines personal data, document context, and market information for actionable recommendations

## Quick Start

### Prerequisites
- Python 3.12 or higher
- Azure CLI installed and authenticated (`az login`)
- Access to Azure AI Foundry and related services
- Company APIs service running (for full functionality)

### Installation
```bash
# Install dependencies
uv sync

# Copy environment configuration
cp .env.example .env

# Edit .env with your Azure service endpoints
```

### Configuration
Update the `.env` file with your Azure service configurations:

```bash
# Azure AI Foundry Configuration
AZURE_FOUNDRY_PROJECT_ENDPOINT=https://your-instance.services.ai.azure.com/api/projects/your-project
AZURE_OPENAI_MODEL=gpt-4.1
BING_CONNECTION_ID=/subscriptions/xxx/resourceGroups/xxx/providers/Microsoft.CognitiveServices/accounts/xxx/projects/xxx/connections/xxx

# Company API Configuration
COMPANY_API_BASE_URL=http://localhost:8003
COMPANY_API_AUDIENCE=fake-audience

# Azure AI Search Configuration
AZURE_SEARCH_SERVICE_NAME=your-search-service
AZURE_SEARCH_INDEX_NAME=documents-index
AZURE_SEARCH_CONNECTION_ID=/subscriptions/xxx/resourceGroups/xxx/providers/Microsoft.MachineLearningServices/workspaces/xxx/connections/xxx

# Application Configuration
LOG_LEVEL=INFO
```

### Running the Service
```bash
# Run the example analysis
python main.py

# Or using uv
uv run main.py
```

## Architecture
### Core Components

#### SubmissionAnalyzerAgent
- **Purpose**: Wrapper around Azure AI Projects for submission analysis
- **Features**: Context management, message handling, and automatic cleanup
- **Tools**: Integrated Bing grounding and Company API access
- **Configuration**: Uses centralized config management with environment variables

#### Configuration Management
- **Pattern**: Pydantic-based configuration with environment validation
- **Structure**: Separate configs for AI Projects, Cosmos DB, OpenAI, Company APIs, and logging
- **Validation**: Automatic validation of required environment variables
- **Security**: Managed Identity authentication for company APIs

## Usage

### Basic Analysis
```python
from agent import SubmissionAnalyzerAgent
from config import AppConfig

# Load configuration
config = AppConfig.from_env()

# Analyze submission with context manager
with SubmissionAnalyzerAgent(config) as agent:
    result = agent.analyze_submission("Your submission content here")
    print(f"Analysis status: {result['run_result']['status']}")
```

### Manual Agent Management
```python
# Create agent
agent = SubmissionAnalyzerAgent(config)

# Analyze submission
result = agent.analyze_submission("Your submission content here")

# Clean up resources
agent.cleanup()
```

## Analysis Capabilities

### Content Analysis
1. **Document Understanding**: Processes and analyzes submission content
2. **Information Extraction**: Identifies key data points and entities
3. **Context Awareness**: Maintains conversation context across interactions
4. **Insight Generation**: Provides structured analysis results

### AI Features
1. **Code Interpreter**: Built-in code execution capabilities
2. **Conversation Management**: Maintains thread state and message history
3. **Error Handling**: Robust error management and logging
4. **Resource Cleanup**: Automatic cleanup of Azure resources

## Technology Stack
- **AI Platform**: Azure AI Projects
- **Authentication**: DefaultAzureCredential with Managed Identity
- **Configuration**: Pydantic models with environment variables
- **Logging**: Structured logging with Azure SDK noise reduction
- **Error Handling**: Comprehensive exception handling and recovery

## Available Tools

### Bing Grounding Tool
Provides access to current web information including:
- Market data and financial news
- General information and research
- Real-time search capabilities

### Company API Tool
Accesses internal company data through OpenAPI specification:
- **User Products**: `/api/v1/users/{userId}/products`
- **Financial Scores**: `/api/v1/users/{userId}/financial-score`
- **Income Data**: `/api/v1/users/{userId}/income`

Authentication uses Azure Managed Identity with configurable audience.

## Development

### Project Structure
```
submission-analyzer/
├── agent.py                    # Main agent implementation
├── config.py                   # Configuration management
├── main.py                     # Example usage and entry point
├── company-apis-openapi.json   # Company API OpenAPI specification
├── models.py                   # Data models (if needed)
├── pyproject.toml              # Dependencies and project metadata
├── README.md                   # This file
├── .env                        # Environment configuration
└── .env.example               # Environment configuration template
```

### Testing
```bash
# Run the example
python main.py

# With debug logging
LOG_LEVEL=DEBUG python main.py
```

## Configuration Reference

### Required Environment Variables
- `AZURE_FOUNDRY_PROJECT_ENDPOINT`: Azure AI Foundry project endpoint URL
- `AZURE_OPENAI_MODEL`: AI model deployment name
- `BING_CONNECTION_ID`: Bing connection ID for grounding tool

### Company API Configuration
- `COMPANY_API_BASE_URL`: Base URL for company APIs (default: http://localhost:8003)
- `COMPANY_API_AUDIENCE`: Audience for managed identity authentication (default: fake-audience)

### Legacy Configuration (for reference)
- `PROJECT_ENDPOINT`: Azure AI Projects endpoint URL
- `MODEL_DEPLOYMENT_NAME`: AI model deployment name
- `AZURE_OPENAI_ENDPOINT`: Azure OpenAI endpoint (fallback)

### Optional Environment Variables
- `AZURE_OPENAI_MODEL`: OpenAI model name (default: gpt-4.1)
- `LOG_LEVEL`: Logging level (default: INFO)
- Additional Cosmos DB and Storage configurations for future features

## Troubleshooting

### Common Issues
1. **Authentication Errors**: Ensure you're logged in with `az login`
2. **Missing Environment Variables**: Check `.env` file configuration
3. **Model Deployment**: Verify model deployment name matches Azure configuration
4. **Endpoint URLs**: Ensure all endpoints are accessible and correct
