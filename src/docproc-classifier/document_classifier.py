"""
Document classifier service using Azure OpenAI API.

This module provides document classification functionality using Azure OpenAI
with structured outputs to classify documents and generate summaries.
"""

import logging
import uuid
from pathlib import Path
from typing import Optional
from datetime import datetime

from openai import AsyncAzureOpenAI
from azure.identity.aio import DefaultAzureCredential
from azure.cosmos.aio import CosmosClient
from azure.core.exceptions import ResourceNotFoundError
from jinja2 import Environment, FileSystemLoader

from config import AzureOpenAIConfig, CosmosDBConfig
from models import DocumentRecord, LLMClassificationResponse, DocumentClassifiedEvent, DocumentClassifiedEventData, DocumentType, SubmissionRecord


class DocumentClassifier:
    """
    Document classification service using Azure OpenAI API.
    
    This service classifies documents using Azure OpenAI with structured outputs
    to ensure consistent response format matching the system prompt template.
    """
    
    def __init__(self, openai_config: AzureOpenAIConfig, cosmos_config: CosmosDBConfig):
        """
        Initialize the document classifier.
        
        Args:
            openai_config: Azure OpenAI configuration settings
            cosmos_config: Cosmos DB configuration settings
        """
        self.openai_config = openai_config
        self.cosmos_config = cosmos_config
        self.logger = logging.getLogger(__name__)
        self.credential = DefaultAzureCredential()
        
        # Initialize Azure OpenAI client with DefaultAzureCredential
        self.openai_client = AsyncAzureOpenAI(
            azure_endpoint=openai_config.endpoint,
            azure_ad_token_provider=self._get_azure_ad_token,
            api_version="2024-08-01-preview"
        )
        
        # Initialize Cosmos DB client
        self.cosmos_client = CosmosClient(
            url=cosmos_config.endpoint,
            credential=self.credential
        )
        
        # Initialize Jinja2 template environment
        template_dir = Path(__file__).parent
        env = Environment(loader=FileSystemLoader(template_dir))
        self.system_prompt_template = env.get_template("system_prompt.jinja2")
        
        self.logger.info(f"Document classifier initialized with model: {openai_config.model}")
    
    async def _get_azure_ad_token(self) -> str:
        """
        Get Azure AD token for authentication.
        
        Returns:
            str: Azure AD access token
        """
        token = await self.credential.get_token("https://cognitiveservices.azure.com/.default")
        return token.token
    
    async def classify_document(self, document: DocumentRecord) -> LLMClassificationResponse:
        """
        Classify a document using Azure OpenAI API.
        
        Args:
            document: Document record containing extracted content
            
        Returns:
            LLMClassificationResponse: Classification result with type and summary
            
        Raises:
            Exception: If classification fails
        """
        try:
            # Render system prompt template
            system_prompt = self.system_prompt_template.render()
            
            # Prepare user message with document content
            user_message = document.content
            
            self.logger.debug(f"Classifying document {document.id} with content length: {len(user_message)}")
            
            # Call Azure OpenAI API with structured output
            response = await self.openai_client.beta.chat.completions.parse(
                model=self.openai_config.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                response_format=LLMClassificationResponse,
                temperature=0.1  # Low temperature for consistent classification
            )
            
            # Extract the structured response
            classification_result = response.choices[0].message.parsed
            
            self.logger.debug(f"Classification result for document {document.id}: {classification_result}")
            
            return classification_result
            
        except Exception as e:
            self.logger.error(f"Failed to classify document {document.id}: {str(e)}")
            raise

    async def update_document_classification(self, document_id: str, submission_id: str, classification: LLMClassificationResponse) -> None:
        """
        Update document record in Cosmos DB with classification results.
        
        Args:
            document_id: ID of the document to update
            submission_id: Submission ID (used as partition key)
            classification: Classification result to store
            
        Raises:
            Exception: If update fails
        """
        try:
            database = self.cosmos_client.get_database_client(self.cosmos_config.database_name)
            container = database.get_container_client(self.cosmos_config.documents_container_name)
            
            # Read the current document
            try:
                current_doc = await container.read_item(
                    item=document_id,
                    partition_key=submission_id
                )
            except ResourceNotFoundError:
                self.logger.error(f"Document {document_id} not found in submission {submission_id}")
                raise
            
            # Update the document with classification results
            current_doc['type'] = classification.type.value if hasattr(classification.type, 'value') else str(classification.type)
            current_doc['summary'] = classification.summary
            current_doc['lastProcessedAt'] = datetime.utcnow().isoformat()
            
            # Save the updated document
            await container.replace_item(
                item=document_id,
                body=current_doc
            )
            
            self.logger.info(f"Updated document {document_id} with classification: type={current_doc['type']}, summary_length={len(classification.summary)}")
            
        except Exception as e:
            self.logger.error(f"Failed to update document {document_id} classification: {str(e)}")
            raise

    async def classify_and_update_document(self, document: DocumentRecord) -> LLMClassificationResponse:
        """
        Classify a document and update the record in Cosmos DB.
        
        Args:
            document: Document record containing extracted content
            
        Returns:
            LLMClassificationResponse: Classification result
            
        Raises:
            Exception: If classification or update fails
        """
        try:
            # Classify the document
            classification = await self.classify_document(document)
            
            # Update the document in Cosmos DB
            await self.update_document_classification(
                document_id=document.id,
                submission_id=document.submissionId,
                classification=classification
            )
            
            # Update the submission record with document type
            try:
                await self.update_submission_document_type(
                    submission_id=document.submissionId,
                    user_id=document.userId,
                    document_url=document.documentUrl,
                    document_type=classification.type.value
                )
            except Exception as submission_error:
                self.logger.error(f"Failed to update submission record for document {document.id}: {submission_error}")
                # Continue processing even if submission update fails
            
            # Emit DocumentClassifiedEvent
            await self._emit_document_classified_event(document, classification, success=True)
            
            return classification
            
        except Exception as e:
            self.logger.error(f"Failed to classify and update document {document.id}: {e}")
            
            # Emit failure event
            try:
                dummy_classification = LLMClassificationResponse(
                    type=DocumentType.OTHER,
                    summary="Classification failed due to error"
                )
                await self._emit_document_classified_event(document, dummy_classification, success=False)
            except Exception as emit_error:
                self.logger.error(f"Failed to emit failure event for document {document.id}: {emit_error}")
            
            raise
    
    async def _emit_document_classified_event(
        self, 
        document: DocumentRecord, 
        classification_result: LLMClassificationResponse,
        success: bool = True
    ) -> None:
        """
        Emit a DocumentClassifiedEvent to the events container.
        
        Args:
            document: The document record that was classified
            classification_result: The classification result
            success: Whether classification was successful
        """
        try:
            event_data = DocumentClassifiedEventData(
                documentUrl=document.documentUrl,
                documentId=document.id,
                documentType=classification_result.type.value if success else "unknown",
                success=success
            )
            
            event = DocumentClassifiedEvent(
                id=str(uuid.uuid4()),
                submissionId=document.submissionId,
                userId=document.userId,
                timestamp=datetime.utcnow(),
                data=event_data
            )
            
            # Store event in Cosmos DB events container
            database = self.cosmos_client.get_database_client(self.cosmos_config.database_name)
            events_container = database.get_container_client(self.cosmos_config.events_container_name)
            
            # Convert to dict with proper JSON serialization
            event_dict = event.model_dump(mode='json')
            
            await events_container.create_item(body=event_dict)
            
            self.logger.info(f"Emitted DocumentClassifiedEvent: {event.id} for document: {document.id}")
            
        except Exception as e:
            self.logger.error(f"Failed to emit DocumentClassifiedEvent for document {document.id}: {e}")
            # Don't raise exception to avoid breaking the processing pipeline

    async def update_submission_document_type(self, submission_id: str, user_id: str, document_url: str, document_type: str) -> None:
        """
        Update document type in the submission record.
        
        Args:
            submission_id: ID of the submission to update (item ID)
            user_id: User ID (used as partition key for submissions container)
            document_url: URL of the document to update
            document_type: Classified document type
            
        Note:
            The submissions container is partitioned by userId, not submissionId.
            This design allows for efficient queries by user while maintaining
            submission records grouped by user.
        """
        try:
            database = self.cosmos_client.get_database_client(self.cosmos_config.database_name)
            container = database.get_container_client(self.cosmos_config.submissions_container_name)
            
            # Retrieve the current submission record using userId as partition key
            try:
                current_submission = await container.read_item(
                    item=submission_id,
                    partition_key=user_id
                )
            except ResourceNotFoundError:
                self.logger.warning(f"Submission record {submission_id} not found for user {user_id}, skipping submission update")
                return
            
            # Update the document type in the documents array
            updated = False
            for doc in current_submission.get('documents', []):
                if doc.get('documentUrl') == document_url:
                    doc['type'] = document_type
                    updated = True
                    break
            
            if not updated:
                self.logger.warning(f"Document URL {document_url} not found in submission {submission_id}")
                return
            
            # Save the updated submission
            await container.replace_item(
                item=submission_id,
                body=current_submission
            )
            
            self.logger.info(f"Updated submission {submission_id} with document type {document_type} for URL {document_url}")
            
        except Exception as e:
            self.logger.error(f"Failed to update submission {submission_id} document type: {str(e)}")
            # Don't raise exception to avoid breaking the document processing pipeline

    async def close(self):
        """Close the Azure OpenAI and Cosmos DB clients."""
        if hasattr(self.openai_client, 'close'):
            await self.openai_client.close()
        
        if self.cosmos_client:
            await self.cosmos_client.close()
