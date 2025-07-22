"""
Configuration for the Company Policies Agent.

This agent is a subordinate agent that provides specialized policy guidance 
and regulatory compliance information.
"""

import os
from jinja2 import Environment, FileSystemLoader
from azure.ai.agents.models import AzureAISearchTool


def _load_policies_system_prompt() -> str:
    """
    Load the company policies system prompt from the company_policies_prompt.jinja2 file.
    
    Returns:
        str: The loaded system prompt
        
    Raises:
        FileNotFoundError: If company_policies_prompt.jinja2 file is not found
        Exception: If there's an error loading or rendering the template
    """
    try:
        # Get the directory containing this file
        current_dir = os.path.dirname(__file__)
        
        # Set up Jinja2 environment
        env = Environment(loader=FileSystemLoader(current_dir))
        
        # Load and render the template
        template = env.get_template("company_policies_prompt.jinja2")
        rendered_prompt = template.render()
        
        return rendered_prompt
        
    except FileNotFoundError:
        raise FileNotFoundError("company_policies_prompt.jinja2 file not found in the current directory")
    except Exception as e:
        raise Exception(f"Error loading company policies system prompt: {e}")


def create_company_policies_config(
    ai_search_connection_id: str,
    policies_index_name: str,
    model_deployment_name: str
):
    """
    Create configuration for the Company Policies Agent.
    
    Args:
        ai_search_connection_id: AI Search connection ID
        policies_index_name: Name of the policies search index
        model_deployment_name: Model deployment name
        
    Returns:
        dict: Agent configuration
    """
    
    # Load instructions from Jinja2 template
    instructions = _load_policies_system_prompt()
    
    # Initialize AI Search tool for policies
    ai_search_tool = AzureAISearchTool(
        index_connection_id=ai_search_connection_id,
        index_name=policies_index_name
    )
    
    return {
        "name": "companyPoliciesAgent",
        "model": model_deployment_name,
        "instructions": instructions,
        "tools": ai_search_tool.definitions,
        "tool_resources": ai_search_tool.resources,
        "description": "Subordinate agent specializing in company policies and regulatory compliance guidance"
    }