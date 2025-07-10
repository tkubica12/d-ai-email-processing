"""
Document data extractor service using Azure OpenAI API.

This module provides document data extraction functionality using Azure OpenAI
with structured outputs to extract structured information from documents.
"""
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime
import uuid

from openai import AsyncAzureOpenAI
from azure.identity.aio import DefaultAzureCredential
from azure.cosmos.aio import CosmosClient
from azure.core.exceptions import ResourceNotFoundError
from jinja2 import Environment, FileSystemLoader

from config import AzureOpenAIConfig, CosmosDBConfig
from models import DocumentRecord, LLMDataExtractionResponse, DocumentDataExtractedEvent, DocumentDataExtractedEventData


class DocumentDataExtractor:
    """
    Document data extraction service using Azure OpenAI API.
    
    This service extracts structured data from documents using Azure OpenAI with structured outputs
    to ensure consistent response format matching the system prompt template.
    """
    
    def __init__(self, openai_config: AzureOpenAIConfig, cosmos_config: CosmosDBConfig):
        """
        Initialize the document data extractor.
        
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
            azure_endpoint=self.openai_config.endpoint,
            azure_ad_token_provider=self._get_azure_ad_token,
            api_version="2024-08-01-preview"
        )
        
        # Initialize Cosmos client
        self.cosmos_client = CosmosClient(
            url=self.cosmos_config.endpoint,
            credential=self.credential
        )
        
        # Load system prompt template
        template_dir = Path(__file__).parent
        env = Environment(loader=FileSystemLoader(template_dir))
        self.system_prompt_template = env.get_template("system_prompt.jinja2")
        
        self.logger.info("Document data extractor initialized")
    
    async def _get_azure_ad_token(self) -> str:
        """
        Get Azure AD token for OpenAI API authentication.
        
        Returns:
            Azure AD access token
        """
        token = await self.credential.get_token("https://cognitiveservices.azure.com/.default")
        return token.token
    
    async def extract_document_data(self, document: DocumentRecord) -> LLMDataExtractionResponse:
        """
        Extract structured data from document using Azure OpenAI API.
        
        Args:
            document: Document record containing content to extract data from
            
        Returns:
            LLMDataExtractionResponse containing extracted structured data
            
        Raises:
            Exception: If data extraction fails
        """
        try:
            system_prompt = self.system_prompt_template.render()
            
            self.logger.debug(f"Extracting data from document {document.id}")
            self.logger.debug(f"System prompt: {system_prompt}")
            
            # Call OpenAI API with structured output
            response = await self.openai_client.beta.chat.completions.parse(
                model=self.openai_config.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": document.content}
                ],
                response_format=LLMDataExtractionResponse,
                temperature=0,
                max_tokens=1000
            )
            
            extraction_result = response.choices[0].message.parsed
            
            self.logger.info(f"Successfully extracted data from document {document.id}")
            self.logger.debug(f"Extraction result: {extraction_result}")
            
            return extraction_result
            
        except Exception as e:
            self.logger.error(f"Failed to extract data from document {document.id}: {str(e)}")
            raise

    async def update_document_extraction(self, document_id: str, submission_id: str, extraction: LLMDataExtractionResponse) -> None:
        """
        Update document record with extracted data.
        
        Args:
            document_id: ID of the document to update
            submission_id: Submission ID for partition key
            extraction: Extracted data to store
            
        Raises:
            Exception: If document update fails
        """
        try:
            database = self.cosmos_client.get_database_client(self.cosmos_config.database_name)
            container = database.get_container_client(self.cosmos_config.documents_container_name)
            
            # Update document with extracted data
            extracted_data_dict = {
                "invoiceNumber": extraction.invoiceNumber,
                "totalAmount": extraction.totalAmount,
                "currency": extraction.currency,
                "dueDate": extraction.dueDate,
                "vendor": extraction.vendor
            }
            
            await container.patch_item(
                item=document_id,
                partition_key=submission_id,
                patch_operations=[
                    {
                        "op": "replace",
                        "path": "/extractedData",
                        "value": extracted_data_dict
                    },
                    {
                        "op": "replace",
                        "path": "/lastProcessedAt",
                        "value": datetime.utcnow().isoformat()
                    }
                ]
            )
            
            self.logger.info(f"Updated document {document_id} with extracted data")
            
        except Exception as e:
            self.logger.error(f"Failed to update document {document_id}: {str(e)}")
            raise

    async def extract_and_update_document(self, document: DocumentRecord) -> LLMDataExtractionResponse:
        """
        Extract data from document and update the document record.
        
        Args:
            document: Document record to process
            
        Returns:
            LLMDataExtractionResponse containing extracted data
            
        Raises:
            Exception: If extraction or update fails
        """
        try:
            # Extract data from document
            extraction_result = await self.extract_document_data(document)
            
            # Update document record with extracted data
            await self.update_document_extraction(
                document.id, 
                document.submissionId, 
                extraction_result
            )
            
            # Emit data extracted event
            await self._emit_document_data_extracted_event(
                document, 
                extraction_result,
                success=True
            )
            
            return extraction_result
            
        except Exception as e:
            self.logger.error(f"Failed to extract and update document {document.id}: {str(e)}")
            
            # Emit failure event
            await self._emit_document_data_extracted_event(
                document, 
                None,
                success=False
            )
            
            raise
    
    async def _emit_document_data_extracted_event(
        self, 
        document: DocumentRecord, 
        extraction_result: Optional[LLMDataExtractionResponse],
        success: bool = True
    ) -> None:
        """
        Emit DocumentDataExtractedEvent to the events container.
        
        Args:
            document: Document record that was processed
            extraction_result: Extraction result (None if failed)
            success: Whether extraction was successful
        """
        try:
            extracted_data_dict = {}
            if extraction_result:
                extracted_data_dict = {
                    "invoiceNumber": extraction_result.invoiceNumber,
                    "totalAmount": extraction_result.totalAmount,
                    "currency": extraction_result.currency,
                    "dueDate": extraction_result.dueDate,
                    "vendor": extraction_result.vendor
                }
            
            event_data = DocumentDataExtractedEventData(
                documentUrl=document.documentUrl,
                documentId=document.id,
                documentType="invoice",  # Default to invoice since we're extracting invoice data
                extractedData=extracted_data_dict,
                success=success
            )
            
            event = DocumentDataExtractedEvent(
                id=str(uuid.uuid4()),
                submissionId=document.submissionId,
                userId=document.userId,
                timestamp=datetime.utcnow(),
                data=event_data
            )
            
            # Store event in events container
            database = self.cosmos_client.get_database_client(self.cosmos_config.database_name)
            events_container = database.get_container_client(self.cosmos_config.events_container_name)
            
            # Use mode='json' to properly serialize datetime objects
            await events_container.create_item(event.model_dump(mode='json'))
            
            self.logger.info(f"Emitted DocumentDataExtractedEvent for document {document.id}")
            
        except Exception as e:
            self.logger.error(f"Failed to emit DocumentDataExtractedEvent for document {document.id}: {str(e)}")

    async def close(self):
        """
        Close the data extractor and cleanup resources.
        """
        try:
            await self.openai_client.close()
            await self.cosmos_client.close()
            await self.credential.close()
            self.logger.info("Document data extractor closed")
        except Exception as e:
            self.logger.error(f"Error closing document data extractor: {str(e)}")
