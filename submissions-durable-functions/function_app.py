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

from models import SubmissionMessage
from actions import DocumentParser, SubmissionStorage

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
    
    try:
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
        
    except Exception as e:
        logging.error(f'Failed to process submission message: {e}')
        raise


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
    
    logging.info(f'Starting orchestration for submission {submission_id} with {len(document_urls)} documents')
    
    results = {
        "submissionId": submission_id,
        "userId": user_id,
        "documentCount": len(document_urls),
        "submissionStored": False,
        "documentsProcessed": [],
        "status": "processing"
    }
    
    try:
        # Step 1: Store submission record
        yield context.call_activity(
            "store_submission_activity", 
            submission_data
        )
        results["submissionStored"] = True
        logging.info(f'Stored submission record for {submission_id}')
        
        # Step 2: Process all documents in parallel
        if document_urls:
            document_tasks = []
            for document_url in document_urls:
                document_task_input = {
                    "submissionId": submission_id,
                    "documentUrl": document_url,
                    "userId": user_id
                }
                task = context.call_activity("parse_document_activity", document_task_input)
                document_tasks.append(task)
            
            # Wait for all documents to be processed
            document_results = yield context.task_all(document_tasks)
            results["documentsProcessed"] = document_results
            
            successful_docs = [r for r in document_results if r.get("status") == "success"]
            failed_docs = [r for r in document_results if r.get("status") == "error"]
            
            logging.info(f'Document processing completed for {submission_id}: {len(successful_docs)} successful, {len(failed_docs)} failed')
        
        # Step 3: Mark orchestration as complete
        results["status"] = "completed"
        logging.info(f'Orchestration completed successfully for submission {submission_id}')
        
        return results
        
    except Exception as e:
        logging.error(f'Orchestration failed for submission {submission_id}: {e}')
        results["status"] = "failed"
        results["error"] = str(e)
        return results


@app.activity_trigger(input_name="submission_data")
def store_submission_activity(submission_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Activity function to store submission record in Cosmos DB.
    
    Args:
        submission_data: Submission data from the orchestrator
        
    Returns:
        Dict containing storage results
    """
    storage = SubmissionStorage()
    return storage.store_submission(submission_data)


@app.activity_trigger(input_name="document_task_input")
def parse_document_activity(document_task_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Activity function to parse a document using Azure Document Intelligence.
    
    Args:
        document_task_input: Dictionary containing submissionId, documentUrl, and userId
        
    Returns:
        Dict containing parsing results
    """
    parser = DocumentParser()
    return parser.parse_document(
        document_task_input["submissionId"],
        document_task_input["documentUrl"],
        document_task_input["userId"]
    )
