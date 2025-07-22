"""
Cosmos DB Change Feed processor for the submission-analyzer service.

This module handles listening to the Cosmos DB Change Feed for SubmissionPreparationCompletedEvent
events and processes them for AI analysis.
"""

import asyncio
import logging
import uuid
import os
from datetime import datetime, timezone
from typing import Optional

from azure.cosmos.aio import CosmosClient
from azure.identity.aio import DefaultAzureCredential
from azure.core.exceptions import HttpResponseError, ClientAuthenticationError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    after_log
)

from config import AppConfig
from models import (
    SubmissionPreparationCompletedEvent, 
    SubmissionAnalysisCompleteEvent, 
    SubmissionAnalysisCompleteEventData,
    AnalysisResults,
    SubmissionRecord,
    EvaluationResults
)
from continuation_token_storage import ContinuationTokenStorage
from agent import SubmissionAnalyzerAgent


class ChangeFeedProcessor:
    """
    Processes Cosmos DB Change Feed for SubmissionPreparationCompletedEvent events.
    
    This class monitors the events container Change Feed, filters for
    SubmissionPreparationCompletedEvent types, and processes them for AI analysis.
    """
    
    def __init__(self, config: AppConfig):
        """
        Initialize the Change Feed processor.
        
        Args:
            config: Application configuration containing Cosmos DB settings
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.cosmos_client: Optional[CosmosClient] = None
        self.continuation_token: Optional[str] = None
        self.token_storage: Optional[ContinuationTokenStorage] = None
        self.analyzer_agent: Optional[SubmissionAnalyzerAgent] = None
        self.processor_id = "submission-analyzer"
        
    async def initialize(self) -> None:
        """
        Initialize the Change Feed processor and required Azure clients.
        
        Raises:
            Exception: If initialization fails
        """
        try:
            # Initialize credentials
            credential = DefaultAzureCredential()
            
            # Initialize Cosmos DB client
            self.cosmos_client = CosmosClient(
                url=self.config.cosmos_db.endpoint,
                credential=credential
            )
            
            # Initialize continuation token storage
            self.token_storage = ContinuationTokenStorage(self.config.table_storage)
            await self.token_storage.initialize()
            
            # Initialize analyzer agent
            self.analyzer_agent = SubmissionAnalyzerAgent(self.config)
            
            # Load continuation token if available
            if self.token_storage.config.enabled:
                self.continuation_token = await self.token_storage.load_continuation_token(self.processor_id)
                if self.continuation_token:
                    self.logger.info(f"Loaded continuation token from storage: {self.continuation_token[:20]}...")
                else:
                    self.logger.info("No continuation token found in storage - starting from beginning")
            
            self.logger.info(f"Change Feed processor initialized successfully")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize Change Feed processor: {str(e)}")
            raise
    
    async def start_processing(self) -> None:
        """
        Start processing the Change Feed for SubmissionPreparationCompletedEvent events.
        
        This method runs continuously, processing change feed batches and
        handling any errors that occur.
        """
        self.logger.info("Starting Change Feed processing...")
        
        try:
            database = self.cosmos_client.get_database_client(self.config.cosmos_db.database_name)
            container = database.get_container_client(self.config.cosmos_db.events_container_name)
            
            self.logger.info(f"Connected to database: {self.config.cosmos_db.database_name}")
            self.logger.info(f"Connected to container: {self.config.cosmos_db.events_container_name}")
            
            # Check if there are any SubmissionPreparationCompletedEvent events in the container
            try:
                query = "SELECT TOP 1 c.eventType FROM c WHERE c.eventType = 'SubmissionPreparationCompletedEvent'"
                items = container.query_items(query=query)
                found_events = []
                async for item in items:
                    found_events.append(item)
                
                if found_events:
                    self.logger.info("Found SubmissionPreparationCompletedEvent events in container")
                else:
                    self.logger.info("No SubmissionPreparationCompletedEvent events found in container")
                    
            except Exception as e:
                self.logger.warning(f"Could not query event count: {str(e)}")
            
            # Also check for any events at all
            try:
                query = "SELECT TOP 5 c.eventType FROM c"
                items = container.query_items(query=query)
                event_types = []
                async for item in items:
                    event_types.append(item.get('eventType'))
                
                if event_types:
                    self.logger.info(f"Found event types in container: {event_types}")
                else:
                    self.logger.info("No events found in container at all")
                    
            except Exception as e:
                self.logger.warning(f"Could not query event types: {str(e)}")
            
            # Check container properties for change feed
            try:
                container_properties = await container.read()
                self.logger.debug(f"Container properties: {container_properties}")
            except Exception as e:
                self.logger.warning(f"Could not read container properties: {str(e)}")
            
            while True:
                try:
                    await self._process_change_feed_batch(container)
                    await asyncio.sleep(5)  # Wait 5 seconds between batches
                    
                except Exception as e:
                    self.logger.error(f"Error processing change feed batch: {str(e)}")
                    await asyncio.sleep(10)  # Wait longer on error
                    
        except Exception as e:
            self.logger.error(f"Critical error in Change Feed processing: {str(e)}")
            raise
    
    async def _process_change_feed_batch(self, container) -> None:
        """
        Process a single batch of changes from the Change Feed.
        
        Args:
            container: Cosmos DB container client for events
        """
        try:
            # Query the change feed
            self.logger.debug(f"Querying change feed with continuation token: {self.continuation_token}")
            
            # If no continuation token, start from beginning
            if self.continuation_token:
                feed_iterator = container.query_items_change_feed(
                    continuation=self.continuation_token,
                    max_item_count=100
                )
            else:
                feed_iterator = container.query_items_change_feed(
                    start_time="Beginning",
                    max_item_count=100
                )
            
            events_processed = 0
            
            # Process all items from the change feed iterator
            async for event_data in feed_iterator:
                self.logger.debug(f"Found event in change feed: {event_data.get('eventType', 'unknown')}")
                await self._process_event(event_data)
                events_processed += 1
            
            # Update continuation token after processing batch
            headers = container.client_connection.last_response_headers
            if 'etag' in headers:
                old_token = self.continuation_token
                self.continuation_token = headers['etag']
                self.logger.debug(f"Updated continuation token: {self.continuation_token[:20]}...")
                
                # Save continuation token to storage if enabled and token changed
                if (self.token_storage and 
                    self.token_storage.config.enabled and 
                    old_token != self.continuation_token):
                    await self.token_storage.save_continuation_token(
                        self.processor_id, 
                        self.continuation_token
                    )
            
            if events_processed > 0:
                self.logger.info(f"Processed {events_processed} events from Change Feed")
            else:
                self.logger.debug("No new events in Change Feed")
                    
        except Exception as e:
            self.logger.error(f"Error processing change feed batch: {str(e)}")
            raise
    
    async def _process_event(self, event_data: dict) -> None:
        """
        Process a single event from the Change Feed.
        
        Args:
            event_data: Raw event data from Cosmos DB
        """
        try:
            event_type = event_data.get('eventType')
            
            if event_type == 'SubmissionPreparationCompletedEvent':
                self.logger.info(f"Processing SubmissionPreparationCompletedEvent: {event_data.get('id')}")
                
                # Parse the event
                event = SubmissionPreparationCompletedEvent(**event_data)
                
                # Handle the event
                await self._handle_submission_preparation_completed_event(event)
                
            else:
                self.logger.debug(f"Ignoring event type: {event_type}")
                
        except Exception as e:
            self.logger.error(f"Error processing event {event_data.get('id', 'unknown')}: {str(e)}")
            # Continue processing other events even if one fails
    
    async def _handle_submission_preparation_completed_event(self, event: SubmissionPreparationCompletedEvent) -> None:
        """
        Handle a SubmissionPreparationCompletedEvent by analyzing the submission.
        
        Args:
            event: The SubmissionPreparationCompletedEvent to process
        """
        self.logger.info(f"Received SubmissionPreparationCompletedEvent:")
        self.logger.info(f"  Event ID: {event.id}")
        self.logger.info(f"  Submission ID: {event.submissionId}")
        self.logger.info(f"  User ID: {event.userId}")
        self.logger.info(f"  Documents Processed: {event.data.documentsProcessed}")
        self.logger.info(f"  Timestamp: {event.timestamp}")
        
        try:
            # Get submission record from submissions container
            submission_record = await self._get_submission_record(event.submissionId, event.userId)
            
            if not submission_record:
                self.logger.error(f"Submission record not found for submission {event.submissionId}")
                return
            
            # Analyze submission using AI agent
            analysis_result = await self._analyze_submission(submission_record)
            
            # Update submission record with evaluation results
            await self._update_submission_record(submission_record, analysis_result)
            
            # Emit SubmissionAnalysisCompleteEvent
            await self._emit_submission_analysis_complete_event(event, analysis_result)
            
            # Send Service Bus message
            await self._send_service_bus_message(event, analysis_result)
            
            self.logger.info(f"Successfully processed submission analysis for {event.submissionId}")
            
        except Exception as e:
            self.logger.error(f"Error processing submission preparation completed event: {str(e)}")
            raise
    
    async def _get_submission_record(self, submission_id: str, user_id: str) -> Optional[SubmissionRecord]:
        """
        Get submission record from Cosmos DB submissions container.
        
        Args:
            submission_id: Submission ID
            user_id: User ID (partition key)
            
        Returns:
            SubmissionRecord if found, None otherwise
        """
        try:
            database = self.cosmos_client.get_database_client(self.config.cosmos_db.database_name)
            container = database.get_container_client(self.config.cosmos_db.submissions_container_name)
            
            # Query for the submission record
            response = await container.read_item(item=submission_id, partition_key=user_id)
            
            return SubmissionRecord(**response)
            
        except Exception as e:
            self.logger.error(f"Failed to get submission record {submission_id}: {str(e)}")
            return None
    
    async def _analyze_submission(self, submission_record: SubmissionRecord) -> AnalysisResults:
        """
        Analyze submission using AI agent.
        
        Args:
            submission_record: Submission record to analyze
            
        Returns:
            Analysis results
        """
        try:
            # Prepare submission content for analysis
            submission_content = f"""
            User Message: {submission_record.userMessage}
            
            Documents:
            """
            
            for doc in submission_record.documents:
                submission_content += f"- {doc.type}: {doc.documentUrl}\n"
            
            # Use agent to analyze submission
            result = self.analyzer_agent.analyze_submission(
                submission_content=submission_content,
                submission_id=submission_record.submissionId,
                user_id=submission_record.userId,
                submitted_at=submission_record.submittedAt
            )
            
            # Extract analysis results from agent response
            # This is a simplified parsing - in practice you might need more sophisticated parsing
            analysis_text = result.get('messages', [{}])[0].get('content', '')
            
            # For now, return mock results - you should implement proper parsing of the agent response
            return AnalysisResults(
                completeness=0.85,
                recommendations=["Review documents for completeness", "Verify vendor information"],
                issues=[]
            )
            
        except Exception as e:
            self.logger.error(f"Failed to analyze submission {submission_record.submissionId}: {str(e)}")
            raise
    
    async def _update_submission_record(self, submission_record: SubmissionRecord, analysis_result: AnalysisResults) -> None:
        """
        Update submission record with evaluation results.
        
        Args:
            submission_record: Submission record to update
            analysis_result: Analysis results to add
        """
        try:
            database = self.cosmos_client.get_database_client(self.config.cosmos_db.database_name)
            container = database.get_container_client(self.config.cosmos_db.submissions_container_name)
            
            # Create evaluation results
            evaluation_results = EvaluationResults(
                completeness=analysis_result.completeness,
                recommendations=analysis_result.recommendations,
                issues=analysis_result.issues,
                analysisTimestamp=datetime.now(timezone.utc)
            )
            
            # Update submission record
            submission_record.evaluationResults = evaluation_results
            
            # Convert to dict and update in Cosmos DB
            submission_dict = submission_record.model_dump(mode='json')
            
            await container.replace_item(item=submission_record.id, body=submission_dict)
            
            self.logger.info(f"Updated submission record {submission_record.submissionId} with evaluation results")
            
        except Exception as e:
            self.logger.error(f"Failed to update submission record {submission_record.submissionId}: {str(e)}")
            raise
    
    async def _emit_submission_analysis_complete_event(self, original_event: SubmissionPreparationCompletedEvent, analysis_result: AnalysisResults) -> None:
        """
        Emit a SubmissionAnalysisCompleteEvent to the Cosmos DB events container.
        
        Args:
            original_event: The original SubmissionPreparationCompletedEvent
            analysis_result: Analysis results
        """
        try:
            database = self.cosmos_client.get_database_client(self.config.cosmos_db.database_name)
            container = database.get_container_client(self.config.cosmos_db.events_container_name)
            
            # Create the analysis complete event
            event = SubmissionAnalysisCompleteEvent(
                id=str(uuid.uuid4()),
                submissionId=original_event.submissionId,
                userId=original_event.userId,
                timestamp=datetime.now(timezone.utc),
                data=SubmissionAnalysisCompleteEventData(
                    analysisResults=analysis_result
                )
            )
            
            # Convert event to JSON-serializable format
            event_json = event.model_dump(mode='json')
            
            # Emit the event
            await container.create_item(body=event_json)
            
            self.logger.info(f"Emitted SubmissionAnalysisCompleteEvent: {event.id}")
            
        except Exception as e:
            self.logger.error(f"Failed to emit SubmissionAnalysisCompleteEvent: {str(e)}")
            raise
    
    async def _send_service_bus_message(self, event: SubmissionPreparationCompletedEvent, analysis_result: AnalysisResults) -> None:
        """
        Send analysis complete message to Service Bus.
        
        Args:
            event: The original SubmissionPreparationCompletedEvent
            analysis_result: Analysis results
        """
        try:
            # Format analysis results as text
            results_text = f"""
            Analysis completed for submission {event.submissionId}
            
            Completeness Score: {analysis_result.completeness}
            
            Recommendations:
            """
            
            for rec in analysis_result.recommendations:
                results_text += f"- {rec}\n"
            
            if analysis_result.issues:
                results_text += "\nIssues:\n"
                for issue in analysis_result.issues:
                    results_text += f"- {issue}\n"
            
            # Use the analyzer agent's service bus client
            self.analyzer_agent.service_bus_client.send_analysis_complete_message(
                submission_id=event.submissionId,
                user_id=event.userId,
                submitted_at=event.timestamp,
                results=results_text
            )
            
            self.logger.info(f"Sent Service Bus message for submission {event.submissionId}")
            
        except Exception as e:
            self.logger.error(f"Failed to send Service Bus message for submission {event.submissionId}: {str(e)}")
            raise
    
    async def close(self) -> None:
        """
        Close all client connections and clean up resources.
        """
        if self.cosmos_client:
            await self.cosmos_client.close()
            
        if self.token_storage:
            await self.token_storage.close()
            
        if self.analyzer_agent:
            self.analyzer_agent.cleanup()
            
        self.logger.info("Change Feed processor closed")
