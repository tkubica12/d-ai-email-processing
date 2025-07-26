"""
Azure Durable Functions app for submission processing.

This module contains the orchestration workflow for processing submissions
including document parsing using Azure Document Intelligence.
"""

import azure.functions as func
import azure.durable_functions as df
import json
import logging
from typing import Dict, Any

# Configure logging for Azure SDK libraries
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)
logging.getLogger("azure.identity").setLevel(logging.WARNING)
logging.getLogger("azure.cosmos").setLevel(logging.WARNING)
logging.getLogger("azure.storage").setLevel(logging.WARNING)
logging.getLogger("azure.ai.documentintelligence").setLevel(logging.WARNING)

app = df.DFApp(http_auth_level=func.AuthLevel.FUNCTION)


@app.service_bus_topic_trigger(
    arg_name="azservicebus", 
    subscription_name="submission-intake-functions", 
    topic_name="new-submissions",
    connection="ServiceBusConnection"
) 
@app.durable_client_input(client_name="client")
async def submission_trigger(azservicebus: func.ServiceBusMessage, client):
    """
    Service Bus trigger that starts the durable function orchestration.
    
    This function receives messages from the Service Bus topic and starts
    the orchestration workflow for processing submissions.
    
    Args:
        azservicebus: Service Bus message containing submission data
        client: Durable Functions client for starting orchestrations
    """
    message_body = azservicebus.get_body().decode('utf-8')
    logging.info(f'Received submission message: {message_body}')
    
    # Import here to avoid module-level import issues
    from models import SubmissionMessage
    
    # Parse the message
    submission_data = json.loads(message_body)
    submission_message = SubmissionMessage(**submission_data)
    
    # Start the orchestration
    instance_id = await client.start_new(
        "submission_processor_orchestrator", 
        None, 
        submission_message.dict()
    )
    
    logging.info(f'Started orchestration {instance_id} for submission {submission_message.submissionId}')


@app.orchestration_trigger(context_name="context")
def submission_processor_orchestrator(context: df.DurableOrchestrationContext):
    """
    Main orchestrator function for processing submissions.
    
    This orchestrator coordinates the workflow:
    1. Store submission record
    2. Parse all documents in parallel using Document Intelligence
    3. Complete processing
    
    Args:
        context: Durable orchestration context
        
    Returns:
        Dict containing orchestration results
    """
    submission_data = context.get_input()
    submission_id = submission_data.get("submissionId")
    document_urls = submission_data.get("documentUrls", [])
    user_id = submission_data.get("userId")
    
    results = {
        "submissionId": submission_id,
        "userId": user_id,
        "documentCount": len(document_urls),
        "submissionStored": False,
        "documentsProcessed": [],
        "status": "processing"
    }
    
    # Define shared retry options for orchestrator-level retries
    # Retry every minute for at least 1 hour (60+ attempts)
    shared_retry_options = df.RetryOptions(
        first_retry_interval_in_milliseconds=60000,  # 1 minute
        max_number_of_attempts=65  # 65 minutes total retry time
    )
    
    # Step 1: Store submission record with retry
    yield context.call_activity_with_retry(
        "store_submission_activity", 
        shared_retry_options,
        submission_data
    )
    results["submissionStored"] = True
    
    # Step 2: Process all documents in parallel with retry
    if document_urls:
        document_tasks = []
        for document_url in document_urls:
            document_task_input = {
                "submissionId": submission_id,
                "documentUrl": document_url,
                "userId": user_id
            }
            # Use suborchestrator for each document
            task = context.call_sub_orchestrator_with_retry(
                "document_processor_suborchestrator",
                shared_retry_options,
                document_task_input
            )
            document_tasks.append(task)
        
        # Wait for all documents to be processed
        document_results = yield context.task_all(document_tasks)
        results["documentsProcessed"] = document_results
    
    # Step 3: Mark orchestration as complete
    results["status"] = "completed"
    
    return results


@app.orchestration_trigger(context_name="context")
def document_processor_suborchestrator(context: df.DurableOrchestrationContext):
    """
    Suborchestrator function for processing individual documents.
    
    This orchestrator coordinates the workflow for a single document:
    1. Parse document using Document Intelligence
    2. Run classification and data extraction in parallel
    3. Return processing results
    
    Args:
        context: Durable orchestration context
        
    Returns:
        Dict containing document processing results
    """
    document_task_input = context.get_input()
    submission_id = document_task_input.get("submissionId")
    
    # Define retry options for suborchestrator activities
    retry_options = df.RetryOptions(
        first_retry_interval_in_milliseconds=30000,  # 30 seconds
        max_number_of_attempts=5
    )
    
    # Step 1: Parse the document
    parse_result = yield context.call_activity_with_retry(
        "parse_document_activity",
        retry_options,
        document_task_input
    )
    
    # Check if parsing was successful
    if "error" in parse_result.get("status", ""):
        return parse_result
    
    document_id = parse_result.get("documentId")
    
    # Step 2: Run classification and data extraction in parallel
    classification_input = {
        "documentId": document_id,
        "submissionId": submission_id
    }
    
    extraction_input = {
        "documentId": document_id,
        "submissionId": submission_id
    }
    
    # Run both tasks in parallel
    classification_task = context.call_activity_with_retry(
        "classify_document_activity",
        retry_options,
        classification_input
    )
    
    extraction_task = context.call_activity_with_retry(
        "extract_document_data_activity",
        retry_options,
        extraction_input
    )
    
    # Wait for both tasks to complete
    parallel_results = yield context.task_all([classification_task, extraction_task])
    classification_result, extraction_result = parallel_results
    
    # Combine results
    return {
        "documentId": document_id,
        "fileName": parse_result.get("fileName"),
        "contentLength": parse_result.get("contentLength"),
        "parseStatus": parse_result.get("status"),
        "documentType": classification_result.get("documentType"),
        "summary": classification_result.get("summary"),
        "classificationStatus": classification_result.get("status"),
        "extractedData": extraction_result.get("extractedData"),
        "extractionStatus": extraction_result.get("status"),
        "status": "completed"
    }


@app.activity_trigger(input_name="submission_data")
async def store_submission_activity(submission_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Activity function to store submission record in Cosmos DB.
    
    Args:
        submission_data: Submission data from the orchestrator
        
    Returns:
        Dict containing storage results
    """
    from actions import SubmissionStorage
    
    storage = SubmissionStorage()
    return await storage.store_submission_async(submission_data)


@app.activity_trigger(input_name="document_task_input")
async def parse_document_activity(document_task_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Activity function to parse a document using Azure Document Intelligence.
    
    Args:
        document_task_input: Dictionary containing submissionId, documentUrl, and userId
        
    Returns:
        Dict containing parsing results
    """
    import uuid
    from actions import DocumentParser
    
    submission_id = document_task_input.get("submissionId", "unknown")
    document_url = document_task_input.get("documentUrl", "unknown")
    user_id = document_task_input.get("userId")
    
    try:
        parser = DocumentParser()
        return await parser.parse_document_async(
            submission_id=submission_id,
            document_url=document_url,
            user_id=user_id
        )
    except Exception as e:
        return {
            "documentId": f"error-{uuid.uuid4()}",
            "fileName": document_url.split('/')[-1] if '/' in document_url else "unknown",
            "contentLength": 0,
            "status": f"error: {str(e)}"
        }


@app.activity_trigger(input_name="classification_input")
async def classify_document_activity(classification_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Activity function to classify a document using mocked LLM analysis.
    
    Args:
        classification_input: Dictionary containing documentId and submissionId
        
    Returns:
        Dict containing classification results
    """
    from actions import DocumentClassifier
    
    document_id = classification_input.get("documentId")
    submission_id = classification_input.get("submissionId")
    
    classifier = DocumentClassifier()
    return await classifier.classify_document_async(
        document_id=document_id,
        submission_id=submission_id
    )


@app.activity_trigger(input_name="extraction_input")
async def extract_document_data_activity(extraction_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Activity function to extract structured data from a document using mocked LLM analysis.
    
    Args:
        extraction_input: Dictionary containing documentId and submissionId
        
    Returns:
        Dict containing data extraction results
    """
    from actions import DocumentDataExtractor
    
    document_id = extraction_input.get("documentId")
    submission_id = extraction_input.get("submissionId")
    
    extractor = DocumentDataExtractor()
    return await extractor.extract_document_data_async(
        document_id=document_id,
        submission_id=submission_id
    )
