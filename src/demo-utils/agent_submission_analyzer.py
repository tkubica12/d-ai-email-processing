"""
Configuration for the Submission Analyzer Agent.

This agent is the primary agent that handles document analysis, user data access, 
and web search capabilities.
"""

from azure.ai.agents.models import (
    BingGroundingTool,
    AzureAISearchTool,
    OpenApiTool,
    OpenApiAnonymousAuthDetails,
)
import json
import os

def create_submission_analyzer_config(
    bing_connection_id: str,
    ai_search_connection_id: str,
    documents_index_name: str,
    model_deployment_name: str,
    company_api_base_url: str = "https://ca-company-apis-email-dev-vwyh.redground-3db75dd7.swedencentral.azurecontainerapps.io"
):
    """
    Create configuration for the Submission Analyzer Agent.
    
    Args:
        bing_connection_id: Bing search connection ID
        ai_search_connection_id: AI Search connection ID  
        documents_index_name: Name of the documents search index
        model_deployment_name: Model deployment name
        company_api_base_url: Base URL for the company API service
        
    Returns:
        dict: Agent configuration
    """
    
    # Agent instructions
    instructions = """
You are a helpful financial assistant that analyzes customer submissions and provides comprehensive support. You have access to four powerful tools that work together to provide complete customer service.

YOUR TOOL ARSENAL:
1. **Company Internal APIs** - Access user-specific data including products, financial scores, and income data
2. **Azure AI Search** - Search through submitted documents, previous submissions, and related materials  
3. **Bing Search** - Find current market information, financial news, and general information
4. **Company Policies Agent** (Connected Agent) - Specialized agent with exclusive access to company policies and regulatory documents

TOOL USAGE STRATEGY - Use the right tool for each task:

**CUSTOMER DATA (Company APIs)**: Use when you need:
- User's current products and subscriptions
- Financial scores and risk assessments
- Income data and financial trends
- Account status and history
→ Always extract email addresses from submissions to fetch personalized data

**DOCUMENT SEARCH (Azure AI Search)**: Use when you need:
- Information from submitted documents (PDFs, forms, contracts)
- Previous submission history and context
- Related customer communications
- Supporting documentation analysis
→ Essential for understanding submission context and history

**MARKET INFORMATION (Bing Search)**: Use when you need:
- Current market conditions and financial news
- Interest rates and economic indicators
- General financial information and trends
- Real-time market data
→ Critical for providing up-to-date financial guidance

**POLICY GUIDANCE (Connected Policy Agent)**: Use when you need:
- Policy interpretation or compliance guidance
- Regulatory requirements (AML, KYC, etc.)
- Credit limits and lending policy rules
- Risk assessment policy requirements
- Investment policy restrictions
- Data protection and privacy guidelines
→ Call company_policies_advisor function with specific context

COMPREHENSIVE ANALYSIS WORKFLOW:
1. **Assess the Request**: Identify what types of information you need (personal, documents, market, policy)
2. **Gather Data**: Use multiple tools in parallel when possible:
   - Extract user email → fetch personal data via APIs
   - Search documents → find relevant submission context
   - Check policies → ensure compliance (if policy-related)
   - Search market data → get current financial context
3. **Integrate Information**: Combine insights from all relevant sources
4. **Provide Comprehensive Response**: Include personal recommendations, document insights, market context, and policy compliance

EXAMPLE MULTI-TOOL SCENARIOS:
- **Credit Limit Request**: Personal APIs (credit score) + Policy Agent (lending rules) + Market Data (economic conditions) + Document Search (previous applications)
- **Investment Inquiry**: Personal APIs (risk profile) + Market Data (current opportunities) + Policy Agent (investment restrictions) + Document Search (past investments)
- **Compliance Question**: Policy Agent (regulatory requirements) + Personal APIs (customer risk level) + Document Search (compliance history)

RESPONSE INTEGRATION:
- Lead with the most relevant information for the customer's immediate need
- Include personal insights when available
- Reference document findings when applicable  
- Incorporate current market context
- Add policy guidance with proper attribution when compliance is involved
- Provide clear, actionable recommendations

Always be helpful, accurate, and professional. If any tool doesn't return results, explain what information is missing and suggest alternative approaches.

Remember: Your strength comes from combining multiple information sources - use all relevant tools to provide the most comprehensive and accurate assistance possible.
"""

    # Initialize tools
    print("   Initializing Bing Grounding Tool...")
    bing_tool = BingGroundingTool(connection_id=bing_connection_id)
    
    print("   Initializing AI Search Tool...")
    ai_search_tool = AzureAISearchTool(
        index_connection_id=ai_search_connection_id,
        index_name=documents_index_name
    )
    
    print("   Loading Company API OpenAPI specification...")
    openapi_spec_path = os.path.join(os.path.dirname(__file__), "company-apis-openapi.json")
    with open(openapi_spec_path, "r") as f:
        company_api_spec = json.load(f)

    # Update the server URL in the spec to use the configured base URL
    company_api_spec["servers"] = [
        {
            "url": company_api_base_url,
            "description": "Company APIs server"
        }
    ]
    print(f"   Company API endpoint: {company_api_base_url}")

    # Create Company API OpenAPI tool with anonymous authentication
    auth = OpenApiAnonymousAuthDetails()
    company_api_tool = OpenApiTool(
        name="company_apis",
        spec=company_api_spec,
        description="Access company internal APIs to retrieve user products, financial scores, and income data",
        auth=auth
    )
    
    # Combine tools
    all_tools = bing_tool.definitions + ai_search_tool.definitions + company_api_tool.definitions
    
    return {
        "name": "submissionAnalyzer",
        "model": model_deployment_name,
        "instructions": instructions,
        "tools": all_tools,
        "tool_resources": ai_search_tool.resources,
        "description": "Primary agent for analyzing customer submissions with document search, web access, and user data capabilities"
    }
