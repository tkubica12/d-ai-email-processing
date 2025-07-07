"""
Client Web Application for Email Processing System

This application provides a web interface for users to submit requests
similar to email submissions. It integrates with Azure Blob Storage
and Service Bus for processing.
"""

import os
import uuid
import logging
import asyncio
import uvicorn
from datetime import datetime, UTC
from pathlib import Path
from typing import Optional, Dict

from fasthtml.common import *
from azure.storage.blob import BlobServiceClient
from azure.servicebus import ServiceBusClient, ServiceBusMessage
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

from models import SubmissionMessage

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_azure_clients():
    """Initialize Azure service clients using DefaultAzureCredential for authentication."""
    credential = DefaultAzureCredential()
    
    # Get configuration from environment
    storage_account_name = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
    service_bus_fqdn = os.getenv("AZURE_SERVICE_BUS_FQDN")
    
    if not storage_account_name or not service_bus_fqdn:
        raise ValueError(
            "Missing required environment variables: "
            "AZURE_STORAGE_ACCOUNT_NAME, AZURE_SERVICE_BUS_FQDN"
        )
    
    # Initialize clients
    blob_service_client = BlobServiceClient(
        account_url=f"https://{storage_account_name}.blob.core.windows.net",
        credential=credential
    )
    
    service_bus_client = ServiceBusClient(
        fully_qualified_namespace=service_bus_fqdn,
        credential=credential
    )
    
    return blob_service_client, service_bus_client

# Initialize Azure clients
try:
    blob_client, service_bus_client = get_azure_clients()
    logger.info("Azure clients initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Azure clients: {e}")
    logger.error("Application requires Azure integration to function properly")
    raise SystemExit(1)

# Initialize FastHTML app
app, rt = fast_app()

# Simple tracking for submission results (in production, use Redis or database)
submission_results: Dict[str, Dict] = {}

def create_submission_form():
    """Create the main submission form."""
    return Form(
        Div(
            H2("Email Processing System - Request Submission"),
            P("Submit your request below. You can attach documents for processing."),
            cls="header-section"
        ),
        
        Div(
            Label("Email Address:", For="email"),
            Input(
                type="email",
                id="email",
                name="email",
                required=True,
                placeholder="your.email@example.com"
            ),
            cls="form-group"
        ),
        
        Div(
            Label("Message Body:", For="message"),
            Textarea(
                id="message",
                name="message",
                required=True,
                placeholder="Describe your request here...",
                rows="6"
            ),
            cls="form-group"
        ),
        
        Div(
            Label("Attachments (optional):", For="attachments"),
            Input(
                type="file",
                id="attachments",
                name="attachments",
                multiple=True,
                accept=".pdf,.doc,.docx,.txt,.jpg,.jpeg,.png"
            ),
            P("Supported formats: PDF, Word documents, text files, images", cls="help-text"),
            cls="form-group"
        ),
        
        Div(
            Button(
                "Submit Request",
                type="submit",
                cls="submit-btn",
                id="submit-btn"
            ),
            cls="form-group"
        ),
        
        action="/submit",
        method="post",
        enctype="multipart/form-data",
        cls="submission-form"
    )

def get_styles():
    """Return CSS styles for the application."""
    return Style("""
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f5f5;
            padding: 20px;
        }
        
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .header-section {
            margin-bottom: 30px;
            text-align: center;
        }
        
        h2 {
            color: #2c3e50;
            margin-bottom: 10px;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: 600;
            color: #555;
        }
        
        input[type="email"],
        input[type="file"],
        textarea {
            width: 100%;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 5px;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        
        input[type="email"]:focus,
        textarea:focus {
            outline: none;
            border-color: #007acc;
        }
        
        .submit-btn {
            background-color: #007acc;
            color: white;
            padding: 12px 30px;
            border: none;
            border-radius: 5px;
            font-size: 16px;
            cursor: pointer;
            transition: background-color 0.3s;
        }
        
        .submit-btn:hover {
            background-color: #005fa3;
        }
        
        .help-text {
            font-size: 14px;
            color: #666;
            margin-top: 5px;
        }
        
        .success-message {
            background-color: #d4edda;
            color: #155724;
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 20px;
            border: 1px solid #c3e6cb;
        }
        
        .error-message {
            background-color: #f8d7da;
            color: #721c24;
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 20px;
            border: 1px solid #f5c6cb;
        }
        
        .submission-details {
            background-color: #f8f9fa;
            padding: 20px;
            border-radius: 5px;
            margin-top: 20px;
        }
        
        .submission-details h3 {
            margin-bottom: 15px;
            color: #2c3e50;
        }
        
        .submission-details p {
            margin-bottom: 10px;
        }
        
        .submission-details strong {
            color: #333;
        }
        
        /* Progress indicator styles */
        .progress-message {
            font-weight: 600;
            color: #007acc;
            margin-bottom: 15px;
            font-size: 18px;
            text-align: center;
        }
        
        .progress-step {
            font-size: 14px;
            color: #666;
            font-style: italic;
            text-align: center;
            margin-top: 10px;
        }
        
        .submit-btn:disabled {
            background-color: #ccc;
            cursor: not-allowed;
        }
        
        /* Animated progress indicators */
        .progress-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 40px 20px;
        }
        
        .progress-icon {
            font-size: 48px;
            margin-bottom: 20px;
            animation: spin 2s linear infinite;
        }
        
        .progress-message.animated {
            animation: pulse 1.5s ease-in-out infinite;
        }
        
        .progress-dots {
            display: inline-block;
            animation: dots 1.5s infinite;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.6; }
        }
        
        @keyframes dots {
            0%, 20% { content: ''; }
            40% { content: '.'; }
            60% { content: '..'; }
            80%, 100% { content: '...'; }
        }
    """)

@rt("/")
def get():
    """Home page with submission form."""
    return Html(
        Head(
            Title("Email Processing System"),
            get_styles(),
            Script(src="https://unpkg.com/htmx.org@1.9.10")
        ),
        Body(
            Div(
                create_submission_form(),
                cls="container"
            )
        )
    )

@rt("/submit", methods=["POST"])
async def post(request):
    """Handle form submission and redirect to progress page."""
    try:
        # Parse form data
        form = await request.form()
        email = form.get("email")
        message = form.get("message")
        
        # Handle file attachments
        attachments = []
        if "attachments" in form:
            files = form.getlist("attachments")
            for file in files:
                if hasattr(file, 'filename') and file.filename:
                    attachments.append(file)
        
        # Generate unique submission ID
        submission_id = str(uuid.uuid4())
        
        # Validate inputs
        if not email or not message:
            raise ValueError("Email and message are required")
        
        # Store submission data for background processing and results page
        submission_results[submission_id] = {
            'status': 'waiting',  # Not processing yet
            'email': email,
            'message_body': message,
            'attachments': attachments,
            'message_length': len(message),
            'attachment_count': len(attachments)
        }
        
        logger.info(f"Created submission {submission_id} from {email}")
        
        # Return progress page that will start processing after it loads
        return Html(
            Head(
                Title("Processing Submission"),
                get_styles(),
                Script(src="https://unpkg.com/htmx.org@1.9.10")
            ),
            Body(
                Div(
                    H2("Processing Your Submission"),
                    Div(
                        Div("⚙️", cls="progress-icon"),
                        Div("Processing your request", cls="progress-message animated"),
                        Div("This may take a few moments", cls="progress-step"),
                        Div(
                            "Please wait",
                            Span(cls="progress-dots"),
                            cls="progress-step"
                        ),
                        hx_trigger="load delay:100ms",
                        hx_get=f"/start/{submission_id}",
                        hx_target="this",
                        hx_swap="outerHTML",
                        cls="progress-container",
                        id="progress-container"
                    ),
                    cls="container"
                )
            )
        )
        
    except ValueError as e:
        error_message = f"Validation error: {str(e)}"
        logger.error(f"Validation error in submission: {error_message}")
        
        return Html(
            Head(
                Title("Submission Error"),
                get_styles()
            ),
            Body(
                Div(
                    Div(error_message, cls="error-message"),
                    A("Try Again", href="/", cls="submit-btn", style="display: inline-block; text-decoration: none;"),
                    cls="container"
                )
            )
        )
    except Exception as e:
        error_message = f"Error processing submission: {str(e)}"
        logger.error(f"Unexpected error in submission: {error_message}", exc_info=True)
        
        return Html(
            Head(
                Title("Submission Error"),
                get_styles()
            ),
            Body(
                Div(
                    Div("An unexpected error occurred. Please try again later.", cls="error-message"),
                    A("Try Again", href="/", cls="submit-btn", style="display: inline-block; text-decoration: none;"),
                    cls="container"
                )
            )
        )

async def process_submission_azure(submission_id: str, email: str, message: str, attachments=None):
    """
    Process submission using Azure services.
    
    Args:
        submission_id: Unique identifier for the submission
        email: User's email address
        message: Message content
        attachments: List of uploaded files
        
    Raises:
        Exception: If Azure processing fails
    """
    try:
        logger.info(f"Starting Azure processing for submission {submission_id}")
        
        # Create container
        container_name = submission_id.lower()
        container_client = blob_client.get_container_client(container_name)
        
        try:
            container_client.create_container()
            logger.info(f"Created blob container: {container_name}")
        except Exception as e:
            if "ContainerAlreadyExists" not in str(e):
                logger.error(f"Failed to create container {container_name}: {e}")
                raise
            logger.info(f"Container {container_name} already exists")
        
        # Upload message body
        body_blob_client = container_client.get_blob_client("body.txt")
        body_blob_client.upload_blob(message, overwrite=True)
        logger.info(f"Uploaded message body for submission {submission_id}")
        
        # Upload attachments if any
        attachment_names = []
        if attachments:
            for i, attachment in enumerate(attachments, 1):
                if hasattr(attachment, 'filename') and hasattr(attachment, 'file'):
                    filename = attachment.filename
                    file_content = attachment.file.read()
                    
                    # Upload file to blob storage
                    file_blob_client = container_client.get_blob_client(filename)
                    file_blob_client.upload_blob(file_content, overwrite=True)
                    attachment_names.append(filename)
                    logger.info(f"Uploaded attachment {i}/{len(attachments)}: {filename}")
        
        # Send message to Service Bus
        logger.info(f"Preparing Service Bus message for submission {submission_id}")
        topic_name = os.getenv("AZURE_SERVICE_BUS_TOPIC_NAME", "new-submissions")
        
        with service_bus_client:
            sender = service_bus_client.get_topic_sender(topic_name=topic_name)
            
            # Create document URLs for the uploaded files
            storage_account_name = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
            document_urls = []
            
            # Add body.txt URL
            body_url = f"https://{storage_account_name}.blob.core.windows.net/{container_name}/body.txt"
            document_urls.append(body_url)
            
            # Add attachment URLs
            for attachment_name in attachment_names:
                attachment_url = f"https://{storage_account_name}.blob.core.windows.net/{container_name}/{attachment_name}"
                document_urls.append(attachment_url)
            
            # Create Pydantic model for Service Bus message
            submission_message = SubmissionMessage(
                submissionId=submission_id,
                userId=email,
                documentUrls=document_urls,
                submittedAt=datetime.now(UTC)
            )
            
            # Create Service Bus message using the Pydantic model
            service_bus_message = ServiceBusMessage(
                body=submission_message.model_dump_json(),
                content_type="application/json"
            )
            
            sender.send_messages(service_bus_message)
            sender.close()
            logger.info(f"Sent Service Bus message for submission {submission_id}")
        
        # Mark as complete
        submission_results[submission_id].update({
            'status': 'complete'
        })
        logger.info(f"Successfully completed processing for submission {submission_id}")
        
    except Exception as e:
        logger.error(f"Error in Azure processing for submission {submission_id}: {e}", exc_info=True)
        submission_results[submission_id].update({
            'status': 'error',
            'error_message': str(e)
        })
        raise

async def process_submission_background(submission_id: str, email: str, message: str, attachments=None):
    """Background task to process submission with Azure services."""
    try:
        # Process submission with Azure operations
        await process_submission_azure(submission_id, email, message, attachments)
        logger.info(f"Successfully processed submission {submission_id}")
        
    except Exception as e:
        logger.error(f"Error in background processing for {submission_id}: {e}", exc_info=True)
        submission_results[submission_id].update({
            'status': 'error',
            'error_message': str(e)
        })

@rt("/check/{submission_id}")
def check_completion(submission_id: str):
    """Check if submission processing is complete."""
    result = submission_results.get(submission_id, {})
    status = result.get('status', 'processing')
    
    logger.info(f"Checking completion for {submission_id}: status={status}")
    
    if status == 'complete':
        # Redirect to result page
        logger.info(f"Submission {submission_id} completed, redirecting to result page")
        return Div(
            Script("window.location.href = '/result/" + submission_id + "'")
        )
    elif status == 'error':
        # Show error message
        error_message = result.get('error_message', 'Unknown error occurred')
        logger.error(f"Error in submission {submission_id}: {error_message}")
        return Div(
            Div("Processing Error", cls="progress-message"),
            Div(f"Error: {error_message}", cls="error-message"),
            A("Try Again", href="/", cls="submit-btn", style="display: inline-block; text-decoration: none; margin-top: 10px;")
        )
    else:
        # Still processing - show animated progress
        return Div(
            Div("⚙️", cls="progress-icon"),
            Div("Processing your request", cls="progress-message animated"),
            Div("This may take a few moments", cls="progress-step"),
            Div(
                "Please wait",
                Span(cls="progress-dots"),
                cls="progress-step"
            ),
            hx_trigger="every 1s",
            hx_get=f"/check/{submission_id}",
            hx_target="this",
            hx_swap="outerHTML",
            cls="progress-container"
        )

@rt("/result/{submission_id}")
def get_result(submission_id: str):
    """Show final result page."""
    result = submission_results.get(submission_id, {})
    email = result.get('email', 'Unknown')
    message_length = result.get('message_length', 0)
    attachment_count = result.get('attachment_count', 0)
    
    return Html(
        Head(
            Title("Submission Successful"),
            get_styles()
        ),
        Body(
            Div(
                Div(f"Request submitted successfully! Submission ID: {submission_id}", cls="success-message"),
                Div(
                    H3("Submission Details"),
                    P(Strong("Submission ID: "), submission_id),
                    P(Strong("Email: "), email),
                    P(Strong("Message Length: "), f"{message_length} characters"),
                    P(Strong("Attachments: "), f"{attachment_count} files"),
                    cls="submission-details"
                ),
                A("Submit Another Request", href="/", cls="submit-btn", style="display: inline-block; text-decoration: none; margin-top: 20px;"),
                cls="container"
            )
        )
    )

@rt("/start/{submission_id}")
async def start_processing(submission_id: str):
    """Start background processing for a submission."""
    result = submission_results.get(submission_id, {})
    
    if not result:
        logger.error(f"No submission data found for {submission_id}")
        return Div("Error: Submission not found", cls="error-message")
    
    # Get submission data
    email = result.get('email', '')
    message = result.get('message_body', '')
    attachments = result.get('attachments', [])
    
    # Update status to processing
    submission_results[submission_id]['status'] = 'processing'
    
    # Start background processing
    asyncio.create_task(process_submission_background(submission_id, email, message, attachments))
    
    # Return polling div with animated progress
    return Div(
        Div("⚙️", cls="progress-icon"),
        Div("Processing your request", cls="progress-message animated"),
        Div("This may take a few moments", cls="progress-step"),
        Div(
            "Please wait",
            Span(cls="progress-dots"),
            cls="progress-step"
        ),
        hx_trigger="every 1s",
        hx_get=f"/check/{submission_id}",
        hx_target="this",
        hx_swap="outerHTML",
        cls="progress-container"
    )

def main():
    """Main entry point for the application."""
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    logger.info(f"Starting client-web application on {host}:{port}")
    logger.info("Azure integration enabled")
    
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    main()
