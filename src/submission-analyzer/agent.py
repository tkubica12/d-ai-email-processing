"""
Azure AI Agent wrapper for submission analysis.
"""

import json
import jsonref
import logging
import os
from typing import Optional, List, Dict, Any
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.agents.models import (
    BingGroundingTool, 
    OpenApiTool, 
    OpenApiManagedAuthDetails, 
    OpenApiManagedSecurityScheme
)

from config import AppConfig, setup_logging


class SubmissionAnalyzerAgent:
    """
    Azure AI Agent for analyzing email submissions.
    
    This class provides a wrapper around Azure AI Projects agent functionality
    to analyze and process email submissions.
    """
    
    def __init__(
        self,
        config: Optional[AppConfig] = None,
        agent_name: str = "submission-analyzer-agent",
        instructions: str = """You are a helpful financial assistant that analyzes customer submissions and provides comprehensive support. 

You have access to two powerful tools:
1. Bing search capabilities to find current market information, financial news, and general information
2. Company internal APIs to access user-specific data including:
   - User products and subscriptions
   - Financial scores and risk assessments  
   - Income data and trends

When analyzing submissions:
- Extract user email addresses when provided to fetch their specific data
- Use company APIs to get personalized financial information
- Use Bing search for current market conditions, financial news, and general information
- Provide actionable recommendations based on both personal data and market context
- Always be helpful, accurate, and professional in your responses

If you cannot find user-specific data, explain what information you need and suggest alternative approaches.

You MUST always call some company API.
"""
    ):
        """
        Initialize the SubmissionAnalyzerAgent.
        
        Args:
            config: Application configuration. If None, loads from environment.
            agent_name: Name for the agent
            instructions: Instructions for the agent behavior
        """
        # Load configuration
        self.config = config or AppConfig.from_env()
        
        # Setup logging
        setup_logging(self.config.logging)
        self.logger = logging.getLogger(__name__)
        
        self.agent_name = agent_name
        self.instructions = instructions
        
        # Initialize the AI Project Client
        self.project_client = AIProjectClient(
            endpoint=self.config.ai_projects.project_endpoint,
            credential=DefaultAzureCredential(),
        )
        
        self.agent_id: Optional[str] = None
        self.thread_id: Optional[str] = None
        
        self.logger.info(f"Initialized SubmissionAnalyzerAgent with endpoint: {self.config.ai_projects.project_endpoint}")
    
    def create_agent(self) -> str:
        """
        Create an Azure AI agent with Bing grounding and Company API tools.
        
        Returns:
            str: The created agent ID
            
        Raises:
            Exception: If agent creation fails
        """
        try:
            # Create Bing grounding tool
            bing = BingGroundingTool(connection_id=self.config.ai_projects.bing_connection_id)
            
            # Load Company API OpenAPI specification
            openapi_spec_path = os.path.join(os.path.dirname(__file__), "company-apis-openapi.json")
            with open(openapi_spec_path, "r") as f:
                company_api_spec = jsonref.loads(f.read())
            
            # Update the server URL in the spec to use the configured base URL
            company_api_spec["servers"] = [
                {
                    "url": self.config.company_api.base_url,
                    "description": "Company APIs server"
                }
            ]
            
            # Create managed identity authentication for Company API
            company_api_auth = OpenApiManagedAuthDetails(
                security_scheme=OpenApiManagedSecurityScheme(
                    audience=self.config.company_api.audience
                )
            )
            
            # Create Company API OpenAPI tool
            company_api_tool = OpenApiTool(
                name="company_apis",
                spec=company_api_spec,
                description="Access company internal APIs to retrieve user products, financial scores, and income data",
                auth=company_api_auth
            )
            
            # Combine tool definitions
            all_tools = bing.definitions + company_api_tool.definitions
            
            agent = self.project_client.agents.create_agent(
                model=self.config.ai_projects.model_deployment_name,
                name=self.agent_name,
                instructions=self.instructions,
                tools=all_tools,
            )
            
            self.agent_id = agent.id
            self.logger.info(f"Created agent with ID: {self.agent_id}")
            return self.agent_id
            
        except Exception as e:
            self.logger.error(f"Failed to create agent: {e}")
            raise
    
    def create_thread(self) -> str:
        """
        Create a conversation thread for the agent.
        
        Returns:
            str: The created thread ID
            
        Raises:
            Exception: If thread creation fails
        """
        try:
            thread = self.project_client.agents.threads.create()
            self.thread_id = thread.id
            self.logger.info(f"Created thread with ID: {self.thread_id}")
            return self.thread_id
            
        except Exception as e:
            self.logger.error(f"Failed to create thread: {e}")
            raise
    
    def send_message(self, content: str, role: str = "user") -> str:
        """
        Send a message to the agent thread.
        
        Args:
            content: Message content to send
            role: Role of the message sender (default: "user")
            
        Returns:
            str: The created message ID
            
        Raises:
            ValueError: If thread is not created
            Exception: If message sending fails
        """
        if not self.thread_id:
            raise ValueError("Thread must be created before sending messages")
        
        try:
            message = self.project_client.agents.messages.create(
                thread_id=self.thread_id,
                role=role,
                content=content,
            )
            
            message_id = message['id']
            self.logger.info(f"Sent message with ID: {message_id}")
            return message_id
            
        except Exception as e:
            self.logger.error(f"Failed to send message: {e}")
            raise
    
    def run_agent(self) -> Dict[str, Any]:
        """
        Execute the agent to process messages in the thread.
        
        Returns:
            Dict[str, Any]: Run result with status and details
            
        Raises:
            ValueError: If agent or thread is not created
            Exception: If agent run fails
        """
        if not self.agent_id:
            raise ValueError("Agent must be created before running")
        if not self.thread_id:
            raise ValueError("Thread must be created before running")
        
        try:
            run = self.project_client.agents.runs.create_and_process(
                thread_id=self.thread_id,
                agent_id=self.agent_id
            )
            
            self.logger.info(f"Agent run finished with status: {run.status}")
            
            if run.status == "failed":
                self.logger.error(f"Agent run failed: {run.last_error}")
            
            return {
                "status": run.status,
                "last_error": getattr(run, 'last_error', None),
                "run_id": run.id
            }
            
        except Exception as e:
            self.logger.error(f"Failed to run agent: {e}")
            raise
    
    def get_messages(self) -> List[Dict[str, Any]]:
        """
        Retrieve all messages from the current thread.
        
        Returns:
            List[Dict[str, Any]]: List of messages with role and content
            
        Raises:
            ValueError: If thread is not created
            Exception: If message retrieval fails
        """
        if not self.thread_id:
            raise ValueError("Thread must be created before retrieving messages")
        
        try:
            messages = self.project_client.agents.messages.list(thread_id=self.thread_id)
            
            formatted_messages = []
            for message in messages:
                formatted_messages.append({
                    "role": message.role,
                    "content": message.content
                })
            
            self.logger.info(f"Retrieved {len(formatted_messages)} messages")
            return formatted_messages
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve messages: {e}")
            raise
    
    def analyze_submission(self, submission_content: str) -> Dict[str, Any]:
        """
        Analyze a submission using the AI agent.
        
        Args:
            submission_content: The submission content to analyze
            
        Returns:
            Dict[str, Any]: Analysis results including messages and run status
        """
        try:
            # Create agent and thread if not already created
            if not self.agent_id:
                self.create_agent()
            if not self.thread_id:
                self.create_thread()
            
            # Send the submission for analysis
            message_id = self.send_message(f"Please analyze this submission: {submission_content}")
            
            # Run the agent
            run_result = self.run_agent()
            
            # Get all messages
            messages = self.get_messages()
            
            return {
                "message_id": message_id,
                "run_result": run_result,
                "messages": messages
            }
            
        except Exception as e:
            self.logger.error(f"Failed to analyze submission: {e}")
            raise
    
    def cleanup(self):
        """
        Clean up resources by deleting the agent.
        """
        if self.agent_id:
            try:
                self.project_client.agents.delete_agent(self.agent_id)
                self.logger.info(f"Deleted agent with ID: {self.agent_id}")
                self.agent_id = None
                self.thread_id = None
            except Exception as e:
                self.logger.error(f"Failed to delete agent: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.cleanup()
