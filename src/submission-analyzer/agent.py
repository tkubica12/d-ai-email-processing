"""
Azure AI Agent wrapper for submission analysis.
"""

import json
import jsonref
import logging
import os
from typing import Optional, List, Dict, Any
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.core.exceptions import HttpResponseError, ClientAuthenticationError
from azure.ai.agents.models import (
    BingGroundingTool, 
    OpenApiTool,
    OpenApiAnonymousAuthDetails,
    AzureAISearchTool,
    AzureAISearchQueryType,
    ConnectedAgentTool
)
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    after_log
)

from config import AppConfig, setup_logging
from agent_company_policies import create_company_policies_config
from service_bus_client import SubmissionServiceBusClient

class SubmissionAnalyzerAgent:
    """
    Azure AI Agent for analyzing email submissions.
    
    This class provides a wrapper around Azure AI Projects agent functionality
    to analyze and process email submissions with connected policy agent and
    Service Bus messaging capabilities.
    """
    
    def __init__(
        self,
        config: Optional[AppConfig] = None,
        agent_name: str = "submission-analyzer-agent",
        instructions: Optional[str] = None
    ):
        """
        Initialize the SubmissionAnalyzerAgent.
        
        Args:
            config: Application configuration. If None, loads from environment.
            agent_name: Name for the agent
            instructions: Instructions for the agent behavior. If None, loads from system_prompt.jinja2
        """
        # Load configuration
        self.config = config or AppConfig.from_env()
        
        # Setup logging
        setup_logging(self.config.logging)
        self.logger = logging.getLogger(__name__)
        
        self.agent_name = agent_name
        self.instructions = instructions or self._load_system_prompt()
        self.pretty_print = self.config.pretty_print
        
        # Initialize the AI Project Client
        self.project_client = AIProjectClient(
            endpoint=self.config.ai_projects.project_endpoint,
            credential=DefaultAzureCredential(),
        )
        
        # Initialize Service Bus client
        self.service_bus_client = SubmissionServiceBusClient(self.config.service_bus)
        
        self.agent_id: Optional[str] = None
        self.policies_agent_id: Optional[str] = None
        self.thread_id: Optional[str] = None
        
        self.logger.info(f"Initialized SubmissionAnalyzerAgent with endpoint: {self.config.ai_projects.project_endpoint}")
    
    def _load_system_prompt(self) -> str:
        """
        Load the system prompt from the system_prompt.jinja2 file.
        
        Returns:
            str: The loaded system prompt
            
        Raises:
            FileNotFoundError: If system_prompt.jinja2 file is not found
            Exception: If there's an error loading or rendering the template
        """
        try:
            # Get the directory containing this file
            current_dir = os.path.dirname(__file__)
            
            # Set up Jinja2 environment
            env = Environment(loader=FileSystemLoader(current_dir))
            
            # Load and render the template
            template = env.get_template("system_prompt.jinja2")
            rendered_prompt = template.render()
            
            self.logger.info("Successfully loaded system prompt from system_prompt.jinja2")
            return rendered_prompt
            
        except FileNotFoundError:
            self.logger.error("system_prompt.jinja2 file not found")
            raise FileNotFoundError("system_prompt.jinja2 file not found in the current directory")
        except Exception as e:
            self.logger.error(f"Error loading system prompt: {e}")
            raise Exception(f"Error loading system prompt: {e}")
    
    def _log_or_print(self, message: str, level: str = "info", emoji: str = ""):
        """
        Log a message or print it based on pretty_print setting.
        
        Args:
            message: The message to log or print
            level: Log level (info, warning, error)
            emoji: Emoji to include in pretty print mode
        """
        if self.pretty_print:
            print(f"{emoji} {message}" if emoji else message)
        else:
            log_func = getattr(self.logger, level.lower(), self.logger.info)
            log_func(message)
    
    def _log_or_print_error(self, message: str, emoji: str = "❌"):
        """Helper for error messages."""
        self._log_or_print(message, "error", emoji)
    
    def _log_or_print_info(self, message: str, emoji: str = ""):
        """Helper for info messages."""
        self._log_or_print(message, "info", emoji)
    
    def _log_or_print_warning(self, message: str, emoji: str = "⚠️"):
        """Helper for warning messages."""
        self._log_or_print(message, "warning", emoji)
    
    def create_agent(self, user_id: Optional[str] = None) -> str:
        """
        Create an Azure AI agent with Bing grounding, Company API, AI Search tools, and connected policies agent.
        
        Args:
            user_id: Optional user ID to filter search results. If provided, Azure AI Search will only return documents for this user.
        
        Returns:
            str: The created agent ID
            
        Raises:
            Exception: If agent creation fails
        """
        try:
            # First create the Company Policies Agent (subordinate agent)
            self._log_or_print("Creating Company Policies Agent...", "info", "🏛️")
            policies_agent_config = create_company_policies_config(
                ai_search_connection_id=self.config.search.connection_id,
                policies_index_name="policies-index",  # Use policies index
                model_deployment_name=self.config.ai_projects.model_deployment_name
            )
            
            policies_agent = self.project_client.agents.create_agent(
                model=policies_agent_config["model"],
                name=policies_agent_config["name"],
                instructions=policies_agent_config["instructions"],
                tools=policies_agent_config["tools"],
                tool_resources=policies_agent_config.get("tool_resources"),
            )
            
            self.policies_agent_id = policies_agent.id
            self._log_or_print(f"Company Policies Agent created with ID: {self.policies_agent_id}", "info", "✅")
            
            # Create connected agent tool for the policies agent
            connected_policies_agent = ConnectedAgentTool(
                id=policies_agent.id,
                name="company_policies_advisor",
                description="Specialized agent for company policy guidance and regulatory compliance. Use when queries involve policy interpretation, compliance checking, regulatory requirements, or need for policy-specific guidance."
            )
            
            self._log_or_print("Setting up main agent tools...", "info", "🛠️")
            
            # Create Bing grounding tool
            self._log_or_print("Configuring Bing search tool...", "info", "🔍")
            bing = BingGroundingTool(connection_id=self.config.ai_projects.bing_connection_id)
            
            # Create Azure AI Search tool for document search
            self._log_or_print("Configuring Azure AI Search tool...", "info", "🔍")
            
            # Create user-specific filter for security
            search_filter = ""
            if user_id:
                search_filter = f"userId eq '{user_id}'"
                self._log_or_print(f"Applying security filter: {search_filter}", "info", "🔒")
            else:
                self._log_or_print("No user filter applied - agent will see all documents", "warning", "⚠️")
            
            ai_search = AzureAISearchTool(
                index_connection_id=self.config.search.connection_id,
                index_name=self.config.search.index_name,
                # query_type=AzureAISearchQueryType.VECTOR_SEMANTIC_HYBRID,  # Use hybrid search (vector + semantic)
                top_k=5,  # Retrieve top 5 results
                filter=search_filter  # Security filter to restrict documents by userId
            )
            
            # Load Company API OpenAPI specification
            self._log_or_print("Loading Company API specification...", "info", "🏢")
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
            self._log_or_print(f"Company API endpoint: {self.config.company_api.base_url}", "info", "🌐")
            
            # Create Company API OpenAPI tool with anonymous authentication
            self._log_or_print("Using anonymous authentication (no auth required)", "info", "🔓")
            auth = OpenApiAnonymousAuthDetails()
            company_api_tool = OpenApiTool(
                name="company_apis",
                spec=company_api_spec,
                description="Access company internal APIs to retrieve user products, financial scores, and income data",
                auth=auth
            )
            
            # Combine tool definitions including connected agent
            all_tools = (bing.definitions + 
                        ai_search.definitions + 
                        company_api_tool.definitions + 
                        connected_policies_agent.definitions)
            
            self._log_or_print(f"Configured {len(all_tools)} tool functions (including connected agent)", "info", "✅")
            
            self._log_or_print("Creating main AI agent...", "info", "🤖")
            agent = self.project_client.agents.create_agent(
                model=self.config.ai_projects.model_deployment_name,
                name=self.agent_name,
                instructions=self.instructions,
                tools=all_tools,
                tool_resources=ai_search.resources,
            )
            
            self.agent_id = agent.id
            self._log_or_print(f"Main agent created successfully with ID: {self.agent_id}", "info", "✅")
            self._log_or_print("Connected agents setup complete", "info", "🔗")
            self.logger.info(f"Created agent with ID: {self.agent_id}")
            return self.agent_id
            
        except Exception as e:
            self._log_or_print_error(f"Failed to create agent: {e}")
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
            self._log_or_print("Creating conversation thread...", "info", "💬")
            thread = self.project_client.agents.threads.create()
            self.thread_id = thread.id
            self._log_or_print(f"Thread created successfully with ID: {self.thread_id}", "info", "✅")
            self.logger.info(f"Created thread with ID: {self.thread_id}")
            return self.thread_id
            
        except Exception as e:
            self._log_or_print_error(f"Failed to create thread: {e}")
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
            self._log_or_print("Sending message to agent...", "info", "📝")
            message = self.project_client.agents.messages.create(
                thread_id=self.thread_id,
                role=role,
                content=content,
            )
            
            message_id = message['id']
            self._log_or_print(f"Message sent successfully with ID: {message_id}", "info", "✅")
            self.logger.info(f"Sent message with ID: {message_id}")
            return message_id
            
        except Exception as e:
            self._log_or_print_error(f"Failed to send message: {e}")
            self.logger.error(f"Failed to send message: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((HttpResponseError, ClientAuthenticationError, TimeoutError, ConnectionError)),
        before_sleep=before_sleep_log(logging.getLogger(__name__), logging.WARNING),
        after=after_log(logging.getLogger(__name__), logging.INFO)
    )
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
            self._log_or_print("Creating agent run...", "info", "🔧")
            run = self.project_client.agents.runs.create_and_process(
                thread_id=self.thread_id,
                agent_id=self.agent_id
            )
            
            self._log_or_print(f"Agent run finished with status: {run.status}", "info", "🎯")
            self.logger.info(f"Agent run finished with status: {run.status}")
            self.logger.debug(f"Run object type: {type(run)}")
            self.logger.debug(f"Run object attributes: {dir(run)}")
            
            # Capture tool usage information
            tool_usage = []
            
            if run.status == "failed":
                self._log_or_print_error(f"Agent run failed: {run.last_error}")
                self.logger.error(f"Agent run failed: {run.last_error}")
            elif run.status == "completed":
                self._log_or_print("Agent run completed successfully", "info", "✅")
                
                # Get detailed run steps to capture tool usage
                try:
                    self.logger.debug("Attempting to access run steps...")
                    self.logger.debug(f"Project client agents type: {type(self.project_client.agents)}")
                    self.logger.debug(f"Project client agents attributes: {dir(self.project_client.agents)}")
                    
                    # Access run steps through the run_steps attribute
                    self.logger.debug("Calling run_steps.list()...")
                    run_steps = self.project_client.agents.run_steps.list(
                        thread_id=self.thread_id,
                        run_id=run.id
                    )
                    
                    self.logger.debug(f"Run steps response type: {type(run_steps)}")
                    self.logger.debug(f"Run steps response: {run_steps}")
                    
                    if hasattr(run_steps, '__dict__'):
                        self.logger.debug(f"Run steps attributes: {run_steps.__dict__}")
                    
                    if hasattr(run_steps, 'data'):
                        self.logger.debug(f"Run steps data type: {type(run_steps.data)}")
                        self.logger.debug(f"Run steps data length: {len(run_steps.data) if run_steps.data else 'None'}")
                        
                    if hasattr(run_steps, 'value'):
                        self.logger.debug(f"Run steps value type: {type(run_steps.value)}")
                        self.logger.debug(f"Run steps value length: {len(run_steps.value) if run_steps.value else 'None'}")
                    
                    if run_steps:
                        # ItemPaged is an iterator, so we need to convert it to a list
                        try:
                            steps_data = list(run_steps)
                            self.logger.debug(f"Retrieved {len(steps_data)} steps from ItemPaged")
                        except Exception as e:
                            self.logger.debug(f"Error converting ItemPaged to list: {e}")
                            steps_data = []
                        
                        if steps_data and len(steps_data) > 0:
                            self._log_or_print(f"Processing {len(steps_data)} execution steps...", "info", "🛠️")
                            self.logger.debug(f"Processing {len(steps_data)} steps...")
                            
                            for i, step in enumerate(steps_data, 1):
                                self.logger.debug(f"Step {i}: {type(step)}")
                                self.logger.debug(f"Step {i} attributes: {dir(step)}")
                                
                                if hasattr(step, '__dict__'):
                                    self.logger.debug(f"Step {i} dict: {step.__dict__}")
                                
                                # Extract timing information
                                created_at = getattr(step, 'created_at', None)
                                completed_at = getattr(step, 'completed_at', None)
                                duration = None
                                if created_at and completed_at:
                                    duration = completed_at - created_at
                                
                                if hasattr(step, 'step_details') and step.step_details:
                                    step_type = getattr(step.step_details, 'type', 'unknown')
                                    self.logger.debug(f"Step {i} type: {step_type}")
                                    self.logger.debug(f"Step {i} step_details: {step.step_details}")
                                    
                                    if step_type == 'tool_calls' and hasattr(step.step_details, 'tool_calls'):
                                        self.logger.debug(f"Step {i} has tool_calls: {len(step.step_details.tool_calls)}")
                                        for j, tool_call in enumerate(step.step_details.tool_calls):
                                            self.logger.debug(f"Tool call {j}: {type(tool_call)}")
                                            self.logger.debug(f"Tool call {j} attributes: {dir(tool_call)}")
                                            if hasattr(tool_call, '__dict__'):
                                                self.logger.debug(f"Tool call {j} dict: {tool_call.__dict__}")
                                            
                                            tool_info = self._parse_tool_call(tool_call)
                                            if tool_info:
                                                # Add timing information
                                                tool_info["created_at"] = created_at
                                                tool_info["completed_at"] = completed_at
                                                tool_info["duration_seconds"] = duration
                                                
                                                # Add usage information if available
                                                if hasattr(step, 'usage') and step.usage:
                                                    tool_info["usage"] = {
                                                        "prompt_tokens": getattr(step.usage, 'prompt_tokens', 0),
                                                        "completion_tokens": getattr(step.usage, 'completion_tokens', 0),
                                                        "total_tokens": getattr(step.usage, 'total_tokens', 0)
                                                    }
                                                
                                                tool_usage.append(tool_info)
                                                self._log_or_print(f"Tool used: {tool_info.get('name', 'unknown')}", "info", "🔧")
                                                self.logger.debug(f"Parsed tool info: {tool_info}")
                                    else:
                                        self.logger.debug(f"Step {i} is not a tool_calls step or has no tool_calls")
                                else:
                                    self.logger.debug(f"Step {i} has no step_details or step_details is None")
                        else:
                            self._log_or_print("🛠️  No execution steps with tool calls found")
                            self.logger.debug("No steps data found or steps data is empty")
                    else:
                        self._log_or_print("🛠️  Could not access run steps - method not available")
                        self.logger.debug("Run steps is None or empty")
                    
                except Exception as e:
                    self.logger.warning(f"Could not retrieve detailed tool usage: {e}")
                    self.logger.debug(f"Exception details: {type(e).__name__}: {e}")
                    self.logger.debug(f"Exception traceback:", exc_info=True)
                    self._log_or_print(f"⚠️  Could not retrieve detailed tool usage information: {e}", "warning")
            
            return {
                "status": run.status,
                "last_error": getattr(run, 'last_error', None),
                "run_id": run.id,
                "tool_usage": tool_usage
            }
            
        except HttpResponseError as e:
            if e.status_code == 429:
                self.logger.warning(f"Rate limit exceeded (429). Will retry after backoff. Error: {e}")
                raise  # Let tenacity handle the retry
            elif e.status_code in [401, 403]:
                self.logger.warning(f"Authentication error ({e.status_code}). Will retry after backoff. Error: {e}")
                raise ClientAuthenticationError(f"Authentication failed: {e}") from e
            else:
                self.logger.error(f"HTTP error {e.status_code} from Azure AI Projects: {e}")
                self._log_or_print(f"❌ HTTP error {e.status_code} from Azure AI Projects: {e}", "error")
                raise
        except Exception as e:
            self._log_or_print(f"❌ Failed to run agent: {e}", "error")
            self.logger.error(f"Failed to run agent: {e}")
            raise
    
    def _parse_tool_call(self, tool_call) -> Dict[str, Any]:
        """
        Parse a tool call to extract useful information.
        
        Args:
            tool_call: Tool call object from the agent run
            
        Returns:
            Dict[str, Any]: Parsed tool call information
        """
        try:
            tool_info = {
                "id": getattr(tool_call, 'id', 'unknown'),
                "type": getattr(tool_call, 'type', 'unknown'),
                "name": "unknown",
                "input": {},
                "output": None
            }
            
            tool_type = getattr(tool_call, 'type', 'unknown')
            
            # Parse function calls (OpenAPI tools)
            if tool_type == 'function' and hasattr(tool_call, 'function'):
                tool_info["name"] = getattr(tool_call.function, 'name', 'unknown')
                
                # Parse function arguments
                if hasattr(tool_call.function, 'arguments'):
                    try:
                        args_str = getattr(tool_call.function, 'arguments', '{}')
                        if args_str:
                            tool_info["input"] = json.loads(args_str)
                    except (json.JSONDecodeError, AttributeError):
                        tool_info["input"] = {"raw": str(getattr(tool_call.function, 'arguments', ''))}
                        
                # Get function output
                if hasattr(tool_call.function, 'output') and tool_call.function.output:
                    output_str = str(tool_call.function.output)
                    tool_info["output"] = output_str[:500] + "..." if len(output_str) > 500 else output_str
                    
            # Parse OpenAPI calls (newer format)
            elif tool_type == 'openapi' and hasattr(tool_call, '_data'):
                # Extract from the _data attribute which contains the full tool call info
                data = tool_call._data
                if 'function' in data:
                    func_data = data['function']
                    tool_info["name"] = func_data.get('name', 'unknown')
                    
                    # Parse arguments
                    if 'arguments' in func_data:
                        try:
                            args_str = func_data['arguments']
                            if args_str:
                                tool_info["input"] = json.loads(args_str)
                        except (json.JSONDecodeError, TypeError):
                            tool_info["input"] = {"raw": str(func_data.get('arguments', ''))}
                    
                    # Get output
                    if 'output' in func_data and func_data['output']:
                        output_str = str(func_data['output'])
                        tool_info["output"] = output_str[:500] + "..." if len(output_str) > 500 else output_str
            
            # Parse Bing grounding calls
            elif tool_type == 'bing_grounding':
                tool_info["name"] = "bing_grounding"
                tool_info["type"] = "bing_grounding"
                
                # Try to extract from different possible attributes
                if hasattr(tool_call, 'bing_grounding'):
                    # Extract query from requesturl if available
                    if hasattr(tool_call.bing_grounding, 'requesturl'):
                        request_url = tool_call.bing_grounding.requesturl
                        # Extract query from URL
                        if '?q=' in request_url:
                            query_part = request_url.split('?q=')[1].split('&')[0]
                            tool_info["input"] = {"query": query_part.replace('%20', ' ')}
                    
                    # Extract metadata if available
                    if hasattr(tool_call.bing_grounding, 'response_metadata'):
                        tool_info["metadata"] = tool_call.bing_grounding.response_metadata
                        
                elif hasattr(tool_call, '_data') and 'bing_grounding' in tool_call._data:
                    # Extract from _data
                    bing_data = tool_call._data['bing_grounding']
                    if 'requesturl' in bing_data:
                        request_url = bing_data['requesturl']
                        if '?q=' in request_url:
                            query_part = request_url.split('?q=')[1].split('&')[0]
                            tool_info["input"] = {"query": query_part.replace('%20', ' ')}
                    
                    if 'response_metadata' in bing_data:
                        tool_info["metadata"] = bing_data['response_metadata']
            
            # Parse Azure AI Search calls
            elif tool_type == 'azure_ai_search':
                tool_info["name"] = "azure_ai_search"
                tool_info["type"] = "azure_ai_search"
                
                # Try to extract from different possible attributes
                if hasattr(tool_call, 'azure_ai_search'):
                    # Extract input query
                    if hasattr(tool_call.azure_ai_search, 'input'):
                        tool_info["input"] = {"query": str(tool_call.azure_ai_search.input)}
                    
                    # Extract output/results
                    if hasattr(tool_call.azure_ai_search, 'output'):
                        output_str = str(tool_call.azure_ai_search.output)
                        tool_info["output"] = output_str[:500] + "..." if len(output_str) > 500 else output_str
                        
                elif hasattr(tool_call, '_data') and 'azure_ai_search' in tool_call._data:
                    # Extract from _data
                    search_data = tool_call._data['azure_ai_search']
                    if 'input' in search_data:
                        tool_info["input"] = {"query": str(search_data['input'])}
                    
                    if 'output' in search_data:
                        output_str = str(search_data['output'])
                        tool_info["output"] = output_str[:500] + "..." if len(output_str) > 500 else output_str
            
            # Handle other tool types
            elif hasattr(tool_call, tool_type):
                tool_info["name"] = tool_type
                tool_attr = getattr(tool_call, tool_type)
                if hasattr(tool_attr, 'input'):
                    tool_info["input"] = {"query": str(tool_attr.input)}
            
            return tool_info
            
        except Exception as e:
            self.logger.warning(f"Could not parse tool call: {e}")
            return {
                "id": "unknown",
                "type": "unknown", 
                "name": "unknown",
                "input": {},
                "output": None
            }
    
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
            self._log_or_print("Retrieving messages from thread...", "info", "📥")
            messages = self.project_client.agents.messages.list(thread_id=self.thread_id)
            
            formatted_messages = []
            for message in messages:
                formatted_messages.append({
                    "role": message.role,
                    "content": message.content
                })
            
            self._log_or_print(f"Retrieved {len(formatted_messages)} messages", "info", "✅")
            self.logger.info(f"Retrieved {len(formatted_messages)} messages")
            return formatted_messages
            
        except Exception as e:
            self._log_or_print_error(f"Failed to retrieve messages: {e}")
            self.logger.error(f"Failed to retrieve messages: {e}")
            raise
    
    def analyze_submission(
        self, 
        submission_content: str,
        submission_id: Optional[str] = None,
        user_id: Optional[str] = None,
        submitted_at: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Analyze a submission using the AI agent and send results to Service Bus.
        
        Args:
            submission_content: The submission content to analyze
            submission_id: Optional submission ID for Service Bus message
            user_id: Optional user ID for Service Bus message
            submitted_at: Optional submission timestamp for Service Bus message
            
        Returns:
            Dict[str, Any]: Analysis results including messages and run status
        """
        try:
            # Create agent and thread if not already created
            if not self.agent_id:
                self.create_agent(user_id=user_id)
            if not self.thread_id:
                self.create_thread()
            
            # Send the submission for analysis
            analysis_message = f"""Please analyze this submission for user {user_id}:

User ID: {user_id}
{f"Submission ID: {submission_id}" if submission_id else ""}

{submission_content}

Note: When searching documents, please filter results to only include documents for user ID: {user_id}"""
            
            message_id = self.send_message(analysis_message)
            
            # Run the agent
            run_result = self.run_agent()
            
            # Get all messages
            messages = self.get_messages()
            
            # Extract assistant response for Service Bus
            assistant_response = None
            if messages and messages[0]['role'] == 'assistant':
                assistant_response = self._parse_message_content(messages[0]['content'])
            
            # Send to Service Bus if we have the required information
            if all([submission_id, user_id, submitted_at, assistant_response]):
                try:
                    self._log_or_print("Sending analysis results to Service Bus...", "info", "📤")
                    self.service_bus_client.send_analysis_complete_message(
                        submission_id=submission_id,
                        user_id=user_id,
                        submitted_at=submitted_at,
                        results=assistant_response
                    )
                    self._log_or_print("Analysis results sent to Service Bus successfully", "info", "✅")
                except Exception as e:
                    self._log_or_print_warning(f"Failed to send Service Bus message: {e}")
                    self.logger.warning(f"Failed to send Service Bus message: {e}")
            else:
                self._log_or_print("Skipping Service Bus message - missing required parameters", "info", "⏭️")
            
            return {
                "message_id": message_id,
                "run_result": run_result,
                "messages": messages,
                "assistant_response": assistant_response
            }
            
        except Exception as e:
            self.logger.error(f"Failed to analyze submission: {e}")
            raise
    
    def _parse_message_content(self, content):
        """
        Parse message content which can be either a string or a list of content objects.
        
        Args:
            content: Message content (string or list)
            
        Returns:
            str: Parsed content as a string
        """
        if isinstance(content, str):
            return content
        elif isinstance(content, list):
            # Handle list of content objects
            parsed_parts = []
            for item in content:
                if isinstance(item, dict):
                    # Handle different content types
                    if 'type' in item and item['type'] == 'text':
                        # Extract text content
                        if 'text' in item:
                            if isinstance(item['text'], dict) and 'value' in item['text']:
                                parsed_parts.append(item['text']['value'])
                            elif isinstance(item['text'], str):
                                parsed_parts.append(item['text'])
                            else:
                                parsed_parts.append(str(item['text']))
                        else:
                            parsed_parts.append(str(item))
                    elif 'type' in item and item['type'] == 'image_file':
                        parsed_parts.append(f"[Image: {item.get('image_file', {}).get('file_id', 'unknown')}]")
                    elif 'type' in item and item['type'] == 'image_url':
                        parsed_parts.append(f"[Image URL: {item.get('image_url', {}).get('url', 'unknown')}]")
                    elif 'text' in item:
                        # Handle cases where there's no type but there's text
                        if isinstance(item['text'], dict) and 'value' in item['text']:
                            parsed_parts.append(item['text']['value'])
                        else:
                            parsed_parts.append(str(item['text']))
                    else:
                        parsed_parts.append(str(item))
                else:
                    parsed_parts.append(str(item))
            
            # Join parts and clean up
            result = '\n'.join(parsed_parts)
            result = result.replace('\\n', '\n')
            return result
        else:
            return str(content)

    def cleanup(self):
        """
        Clean up resources by deleting the agents and closing Service Bus client.
        """
        if self.agent_id:
            try:
                self._log_or_print("Cleaning up main agent resources...", "info", "🧹")
                self.project_client.agents.delete_agent(self.agent_id)
                self._log_or_print("Main agent deleted successfully", "info", "✅")
                self.logger.info(f"Deleted main agent with ID: {self.agent_id}")
                self.agent_id = None
            except Exception as e:
                self._log_or_print_error(f"Failed to delete main agent: {e}")
                self.logger.error(f"Failed to delete main agent: {e}")
        
        if self.policies_agent_id:
            try:
                self._log_or_print("Cleaning up policies agent resources...", "info", "🧹")
                self.project_client.agents.delete_agent(self.policies_agent_id)
                self._log_or_print("Policies agent deleted successfully", "info", "✅")
                self.logger.info(f"Deleted policies agent with ID: {self.policies_agent_id}")
                self.policies_agent_id = None
            except Exception as e:
                self._log_or_print_error(f"Failed to delete policies agent: {e}")
                self.logger.error(f"Failed to delete policies agent: {e}")
        
        # Close Service Bus client
        try:
            self.service_bus_client.close()
        except Exception as e:
            self.logger.error(f"Failed to close Service Bus client: {e}")
        
        self.thread_id = None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.cleanup()
