"""
Azure AI Agent wrapper for submission analysis.
"""

import json
import jsonref
import logging
import os
from typing import Optional, List, Dict, Any
from jinja2 import Environment, FileSystemLoader
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.agents.models import (
    BingGroundingTool, 
    OpenApiTool,
    OpenApiAnonymousAuthDetails
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
        
        self.agent_id: Optional[str] = None
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
    
    def create_agent(self) -> str:
        """
        Create an Azure AI agent with Bing grounding and Company API tools.
        
        Returns:
            str: The created agent ID
            
        Raises:
            Exception: If agent creation fails
        """
        try:
            self._log_or_print("Setting up agent tools...", "info", "🛠️")
            
            # Create Bing grounding tool
            self._log_or_print("Configuring Bing search tool...", "info", "🔍")
            bing = BingGroundingTool(connection_id=self.config.ai_projects.bing_connection_id)
            
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
            
            # Create Company API OpenAPI tool with autonomous authentication (no auth required)
            self._log_or_print("Using autonomous authentication (no auth required)", "info", "🔓")
            auth = OpenApiAnonymousAuthDetails()
            company_api_tool = OpenApiTool(
                name="company_apis",
                spec=company_api_spec,
                description="Access company internal APIs to retrieve user products, financial scores, and income data",
                auth=auth
            )
            
            # Combine tool definitions
            all_tools = bing.definitions + company_api_tool.definitions
            self._log_or_print(f"Configured {len(all_tools)} tool functions", "info", "✅")
            
            self._log_or_print("Creating AI agent...", "info", "🤖")
            agent = self.project_client.agents.create_agent(
                model=self.config.ai_projects.model_deployment_name,
                name=self.agent_name,
                instructions=self.instructions,
                tools=all_tools,
            )
            
            self.agent_id = agent.id
            self._log_or_print(f"Agent created successfully with ID: {self.agent_id}", "info", "✅")
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
                self._log_or_print("Cleaning up agent resources...", "info", "🧹")
                self.project_client.agents.delete_agent(self.agent_id)
                self._log_or_print("Agent deleted successfully", "info", "✅")
                self.logger.info(f"Deleted agent with ID: {self.agent_id}")
                self.agent_id = None
                self.thread_id = None
            except Exception as e:
                self._log_or_print_error(f"Failed to delete agent: {e}")
                self.logger.error(f"Failed to delete agent: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.cleanup()
