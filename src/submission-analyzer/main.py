"""
Main entry point for the submission analyzer service.
"""

import logging
from agent import SubmissionAnalyzerAgent
from config import AppConfig, setup_logging
from datetime import datetime, timezone
import uuid


def format_analysis_results(result, pretty_print=True):
    """
    Format the analysis results for console output.
    
    Args:
        result: Analysis results from the agent
        pretty_print: Whether to use pretty formatting or simple logging
    """
    logger = logging.getLogger(__name__)
    
    if pretty_print:
        # Original detailed pretty output
        print("\n" + "="*80)
        print("🔍 SUBMISSION ANALYSIS RESULTS")
        print("="*80)
        
        # Show run status
        status = result['run_result']['status']
        if status == "completed":
            print(f"✅ Analysis Status: {status.upper()}")
        elif status == "failed":
            print(f"❌ Analysis Status: {status.upper()}")
            if result['run_result']['last_error']:
                print(f"❌ Error: {result['run_result']['last_error']}")
        else:
            print(f"⏳ Analysis Status: {status.upper()}")
        
        # Show tool usage if available
        if 'tool_usage' in result['run_result'] and result['run_result']['tool_usage']:
            print("\n" + "-"*80)
            print("🛠️  TOOLS USED")
            print("-"*80)
            
            for i, tool in enumerate(result['run_result']['tool_usage'], 1):
                print(f"\n🔧 Tool {i}: {tool.get('name', 'unknown')}")
                print(f"   Type: {tool.get('type', 'unknown')}")
                print(f"   ID: {tool.get('id', 'unknown')}")
                
                # Show timing information
                if tool.get('duration_seconds'):
                    print(f"   Duration: {tool['duration_seconds']} seconds")
                
                # Show token usage if available
                if tool.get('usage'):
                    usage = tool['usage']
                    print(f"   Token Usage: {usage.get('total_tokens', 0)} total ({usage.get('prompt_tokens', 0)} prompt + {usage.get('completion_tokens', 0)} completion)")
                
                # Show input parameters
                if tool.get('input'):
                    print("   Input:")
                    for key, value in tool['input'].items():
                        # Format value nicely
                        if isinstance(value, str):
                            # Clean up the value display
                            clean_value = value.replace('\\n', '\n').replace('%20', ' ')
                            if len(clean_value) > 100:
                                formatted_value = clean_value[:100] + "..."
                            else:
                                formatted_value = clean_value
                        else:
                            formatted_value = str(value)
                        print(f"     {key}: {formatted_value}")
                
                # Show metadata if available
                if tool.get('metadata'):
                    print(f"   Metadata: {tool['metadata']}")
                
                # Show output if available
                if tool.get('output'):
                    print("   Output:")
                    output_text = tool['output'].replace('\\n', '\n')
                    output_preview = output_text[:300] + "..." if len(output_text) > 300 else output_text
                    print(f"     {output_preview}")
                
                # Show a separator between tools
                if i < len(result['run_result']['tool_usage']):
                    print("   " + "-"*50)
        else:
            print("\n" + "-"*80)
            print("🛠️  TOOLS USED")
            print("-"*80)
            print("   No detailed tool usage information available")
            print("   (Tools may have been used but details not captured)")
        
        print("\n" + "-"*80)
        print("💬 CONVERSATION FLOW")
        print("-"*80)
        
        # Reverse messages to show chronological order (oldest first)
        messages = list(reversed(result['messages']))
        
        for i, message in enumerate(messages, 1):
            role = message['role']
            content = message['content']
            
            if role == "user":
                print(f"\n👤 USER MESSAGE ({i}):")
                # Parse user message content
                parsed_content = parse_message_content(content)
                print_formatted_content(parsed_content, "   ")
            elif role == "assistant":
                print(f"\n🤖 ASSISTANT RESPONSE ({i}):")
                # Parse assistant response content
                parsed_content = parse_message_content(content)
                print_formatted_content(parsed_content, "   ")
            
            if i < len(messages):
                print("\n" + "."*50)
        
        print("\n" + "="*80)
        print("✨ ANALYSIS COMPLETE")
        print("="*80)
    
    else:
        # Simple logging output
        status = result['run_result']['status']
        logger.info(f"Analysis completed with status: {status}")
        
        if status == "failed" and result['run_result']['last_error']:
            logger.error(f"Analysis failed with error: {result['run_result']['last_error']}")
        
        # Log tool usage summary
        if 'tool_usage' in result['run_result'] and result['run_result']['tool_usage']:
            tool_names = [tool.get('name', 'unknown') for tool in result['run_result']['tool_usage']]
            logger.info(f"Tools used: {', '.join(tool_names)}")
        else:
            logger.info("No tool usage information available")
        
        # Log message count
        message_count = len(result['messages'])
        logger.info(f"Conversation contained {message_count} messages")
        
        # Log final assistant response if available
        messages = result['messages']
        if messages and messages[0]['role'] == 'assistant':
            assistant_response = parse_message_content(messages[0]['content'])
            logger.info(f"Assistant response: {assistant_response[:200]}{'...' if len(assistant_response) > 200 else ''}")

def parse_message_content(content):
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
                        # If no 'text' field, try to extract string representation
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
                    # Last resort - convert to string
                    parsed_parts.append(str(item))
            else:
                # Not a dict, just convert to string
                parsed_parts.append(str(item))
        
        # Join parts and clean up
        result = '\n'.join(parsed_parts)
        # Remove any remaining escaped newlines
        result = result.replace('\\n', '\n')
        return result
    else:
        return str(content)


def print_formatted_content(content, indent=""):
    """
    Print content with proper formatting, handling newlines and indentation.
    
    Args:
        content: Content to print
        indent: Indentation string to use
    """
    if not content:
        return
    
    # Split content into lines and print each with proper indentation
    lines = content.split('\n')
    for line in lines:
        print(f"{indent}{line}")


def main():
    """
    Main function to demonstrate the submission analyzer agent.
    """
    # Load configuration
    config = AppConfig.from_env()
    
    # Setup logging
    setup_logging(config.logging)
    logger = logging.getLogger(__name__)
    
    if config.pretty_print:
        print("🚀 Starting Submission Analyzer Service...")
    logger.info("Starting submission analyzer service...")
    
    try:
        # Create and use the agent with context manager for automatic cleanup
        with SubmissionAnalyzerAgent(config) as agent:
            # Example submission content that would benefit from all tools
            sample_submission = """
            Dear Support Team,
            
            I am writing to inquire about my financial situation and available products. 
            I need to understand my current financial standing and explore options for 
            improving my financial health.
            
            My email is john.doe@example.com and I would like to:
            1. Get my current financial score and whether some of my products might have negative impacts on it
            2. As an accountant, I need to understand my financial prospects given Artificial Intelligence taking over.
            3. Have I provided PUMA invoice already?
            4. What are the company policies regarding credit limit increases?
            
            Please provide simple structured answers to these questions.

            Best regards,
            John Doe
            """
            
            if config.pretty_print:
                print("🔄 Analyzing submission...")
            logger.info("Analyzing sample submission...")
            
            # Generate test data for Service Bus message
            submission_id = str(uuid.uuid4())
            user_id = "john.doe@example.com"
            submitted_at = datetime.now(timezone.utc)
            
            # Analyze the submission with Service Bus integration
            result = agent.analyze_submission(
                submission_content=sample_submission,
                submission_id=submission_id,
                user_id=user_id,
                submitted_at=submitted_at
            )
            
            logger.info(f"Analysis completed with status: {result['run_result']['status']}")
            
            # Display the formatted results
            format_analysis_results(result, config.pretty_print)
            
            # Show Service Bus information if available
            if config.pretty_print:
                print(f"\n📤 Service Bus Message:")
                print(f"   Topic: {config.service_bus.topic_name}")
                print(f"   Submission ID: {submission_id}")
                print(f"   User ID: {user_id}")
                print(f"   Message sent with analysis results")
            
    except Exception as e:
        if config.pretty_print:
            print(f"❌ Error in submission analyzer: {e}")
        logger.error(f"Error in submission analyzer: {e}")
        raise


if __name__ == "__main__":
    main()
