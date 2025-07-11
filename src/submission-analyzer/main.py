"""
Main entry point for the submission analyzer service.
"""

import logging
from agent import SubmissionAnalyzerAgent
from config import AppConfig, setup_logging


def main():
    """
    Main function to demonstrate the submission analyzer agent.
    """
    # Load configuration
    config = AppConfig.from_env()
    
    # Setup logging
    setup_logging(config.logging)
    logger = logging.getLogger(__name__)
    
    logger.info("Starting submission analyzer service...")
    
    try:
        # Create and use the agent with context manager for automatic cleanup
        with SubmissionAnalyzerAgent(config) as agent:
            # Example submission content that would benefit from both tools
            sample_submission = """
            Dear Support Team,
            
            I am writing to inquire about my financial situation and available products. 
            I need to understand my current financial standing and explore options for 
            improving my financial health.
            
            My email is john.doe@example.com and I would like to:
            1. Get my current financial score
            2. See what products I currently have
            3. Get information about my recent income trends
            4. Understand current market conditions that might affect my finances
            
            Please provide a comprehensive analysis and recommendations.
            
            Best regards,
            John Doe
            """
            
            logger.info("Analyzing sample submission...")
            
            # Analyze the submission
            result = agent.analyze_submission(sample_submission)
            
            logger.info(f"Analysis completed with status: {result['run_result']['status']}")
            
            # Display the conversation
            print("\n=== Submission Analysis Results ===")
            for message in result['messages']:
                print(f"\n{message['role'].upper()}:")
                print(message['content'])
                print("-" * 50)
            
    except Exception as e:
        logger.error(f"Error in submission analyzer: {e}")
        raise


if __name__ == "__main__":
    main()
