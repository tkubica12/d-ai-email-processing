"""
Main script to create both agents in Azure AI Foundry Project with connected agent configuration.

This script creates:
1. companyPoliciesAgent - Subordinate agent specializing in policy and regulatory guidance
2. submissionAnalyzer - Primary agent with document search, web access, user data capabilities, 
   and connected to the policies agent

Files:
- agent_create.py - This main script
- agent_submission_analyzer.py - Configuration for the primary agent
- agent_company_policies.py - Configuration for the subordinate policies agent

Connected Agents Setup:
The script automatically configures the submissionAnalyzer agent to use the companyPoliciesAgent
as a connected agent. This allows the primary agent to automatically delegate policy-related
queries to the specialized policies agent using the ConnectedAgentTool.

No manual portal configuration is required!
"""

import os
from azure.ai.projects import AIProjectClient
from azure.ai.agents.models import ConnectedAgentTool
from azure.identity import DefaultAzureCredential

from agent_submission_analyzer import create_submission_analyzer_config
from agent_company_policies import create_company_policies_config

# Configuration - modify these values as needed
PROJECT_ENDPOINT = "https://ai-foundry-email-dev-vwyh.services.ai.azure.com/api/projects/email-dev-vwyh-project"
MODEL_DEPLOYMENT_NAME = "gpt-4.1"

# Connection IDs - get these from your AI Foundry project's "Connected resources" section
BING_CONNECTION_ID = "/subscriptions/673af34d-6b28-41dc-bc7b-f507418045e6/resourceGroups/rg-email-dev-vwyh/providers/Microsoft.CognitiveServices/accounts/ai-foundry-email-dev-vwyh/projects/email-dev-vwyh-project/connections/bing-grounding-connection"
AI_SEARCH_CONNECTION_ID = "/subscriptions/673af34d-6b28-41dc-bc7b-f507418045e6/resourceGroups/rg-email-dev-vwyh/providers/Microsoft.CognitiveServices/accounts/ai-foundry-email-dev-vwyh/projects/email-dev-vwyh-project/connections/ai-search-connection"

# Index names
DOCUMENTS_INDEX_NAME = "documents-index"
POLICIES_INDEX_NAME = "policies-index"

# Company API endpoint
COMPANY_API_BASE_URL = "https://company-apis-vwyh.redground-3db75dd7.swedencentral.azurecontainerapps.io/"

def create_agent(project_client, agent_config):
    """
    Create an agent using the provided configuration.
    
    Args:
        project_client: Azure AI Project Client
        agent_config: Agent configuration dictionary
        
    Returns:
        Created agent object
    """
    print(f"\n🤖 Creating {agent_config['name']} agent...")
    print(f"   Description: {agent_config['description']}")
    
    agent = project_client.agents.create_agent(
        model=agent_config["model"],
        name=agent_config["name"],
        instructions=agent_config["instructions"],
        tools=agent_config["tools"],
        tool_resources=agent_config.get("tool_resources"),
        headers={"x-ms-enable-preview": "true"}
    )
    
    print(f"   ✅ Agent created successfully!")
    print(f"   Agent ID: {agent.id}")
    print(f"   Agent Name: {agent.name}")
    print(f"   Model: {agent.model}")
    
    return agent

def main():
    """Main function to create both agents."""
    print("🚀 Creating Azure AI Foundry Agents...")
    print(f"Project: {PROJECT_ENDPOINT}")
    print(f"Model: {MODEL_DEPLOYMENT_NAME}")
    print("=" * 80)
    
    # Create AI Project Client
    project_client = AIProjectClient(
        endpoint=PROJECT_ENDPOINT,
        credential=DefaultAzureCredential(),
    )
    
    # Store agent results
    created_agents = {}
    
    with project_client:
        # Create Company Policies Agent first (it will be the connected agent)
        print("\n🏛️ Configuring Company Policies Agent...")
        policies_agent_config = create_company_policies_config(
            ai_search_connection_id=AI_SEARCH_CONNECTION_ID,
            policies_index_name=POLICIES_INDEX_NAME,
            model_deployment_name=MODEL_DEPLOYMENT_NAME
        )
        
        print(f"   ✓ Configured {len(policies_agent_config['tools'])} tool functions")
        policies_agent = create_agent(project_client, policies_agent_config)
        created_agents['companyPoliciesAgent'] = policies_agent
        
        # Create the connected agent tool for policies agent
        print(f"\n🔗 Setting up connected agent tool...")
        connected_policies_agent = ConnectedAgentTool(
            id=policies_agent.id,
            name="company_policies_advisor",
            description="Specialized agent for company policy guidance and regulatory compliance. Use when queries involve policy interpretation, compliance checking, regulatory requirements, or need for policy-specific guidance."
        )
        print(f"   ✓ Connected agent tool configured: company_policies_advisor")
        
        # Create Submission Analyzer Agent (Primary Agent) with connected agent
        print("\n📝 Configuring Submission Analyzer Agent with connected agent...")
        submission_analyzer_config = create_submission_analyzer_config(
            bing_connection_id=BING_CONNECTION_ID,
            ai_search_connection_id=AI_SEARCH_CONNECTION_ID,
            documents_index_name=DOCUMENTS_INDEX_NAME,
            model_deployment_name=MODEL_DEPLOYMENT_NAME,
            company_api_base_url=COMPANY_API_BASE_URL
        )
        
        # Add connected agent tools to the submission analyzer's tools
        all_tools = submission_analyzer_config['tools'] + connected_policies_agent.definitions
        submission_analyzer_config['tools'] = all_tools
        
        print(f"   ✓ Configured {len(submission_analyzer_config['tools'])} tool functions (including connected agent)")
        submission_analyzer = create_agent(project_client, submission_analyzer_config)
        created_agents['submissionAnalyzer'] = submission_analyzer
    
    # Summary
    print("\n" + "=" * 80)
    print("🎉 AGENTS CREATED SUCCESSFULLY!")
    print("=" * 80)
    
    for agent_name, agent in created_agents.items():
        print(f"📋 {agent_name}:")
        print(f"   ID: {agent.id}")
        print(f"   Name: {agent.name}")
        print(f"   Model: {agent.model}")
        print("")
    
    print("🔗 CONNECTED AGENTS SETUP:")
    print("   ✅ submissionAnalyzer is connected to companyPoliciesAgent")
    print("   ✅ Policy-related queries will be automatically delegated")
    print("   ✅ Connected agent name: company_policies_advisor")
    print("")
    print("📝 USAGE:")
    print("   The submissionAnalyzer agent can now automatically delegate")
    print("   policy-related questions to the specialized companyPoliciesAgent.")
    print("   No manual portal configuration needed!")
    print("=" * 80)

if __name__ == "__main__":
    main()
