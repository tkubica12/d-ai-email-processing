"""
Data models for the docproc-data-extractor service.

This module contains Pydantic models used for data validation and serialization
in the document data extraction service using OpenAI API.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from enum import Enum


class DocumentType(str, Enum):
    """
    Enumeration of supported document types for data extraction.
    """
    INVOICE = "invoice"
    CONTRACT = "contract"
    BANK_STATEMENT = "bankStatement"
    SUBMISSION_NOTES = "submissionNotes"
    OTHER = "other"


class LLMDataExtractionResponse(BaseModel):
    """
    Structured response model for OpenAI data extraction API.
    
    This model ensures the LLM response matches the expected JSON structure
    defined in the system_prompt.jinja2 template.
    
    Attributes:
        invoiceNumber: The unique identifier for the invoice
        totalAmount: The total amount due as a numeric value without currency symbols
        currency: The currency code in ISO 4217 format (USD, EUR, GBP, etc.)
        dueDate: The payment due date in ISO 8601 date format (YYYY-MM-DD)
        vendor: The name of the company or vendor issuing the invoice
    """
    
    # Flatten the extracted data fields to avoid nested structure
    invoiceNumber: Optional[str] = Field(
        None,
        description="The unique identifier for the invoice",
        example="INV-2025-001"
    )
    
    totalAmount: Optional[float] = Field(
        None,
        description="The total amount due as a numeric value without currency symbols",
        example=1250.00
    )
    
    currency: Optional[str] = Field(
        None,
        description="The currency code in ISO 4217 format (USD, EUR, GBP, etc.)",
        example="USD"
    )
    
    dueDate: Optional[str] = Field(
        None,
        description="The payment due date in ISO 8601 date format (YYYY-MM-DD)",
        example="2025-08-07"
    )
    
    vendor: Optional[str] = Field(
        None,
        description="The name of the company or vendor issuing the invoice",
        example="Acme Corp"
    )


class DocumentRecord(BaseModel):
    """
    Document record stored in Cosmos DB documents container.
    
    This represents the processed document content and metadata
    stored after successful extraction and classification.
    
    Schema matches the actual Cosmos DB document structure.
    - Container: documents
    - Partition Key: submissionId (groups documents by submission)
    - Document ID: Generated GUID for each document record
    """
    
    model_config = ConfigDict(extra="ignore")  # Ignore Cosmos DB internal fields like _rid, _self, etc.
    
    id: str = Field(
        ...,
        description="Generated GUID for document record",
        example="550e8400-e29b-41d4-a716-446655440000"
    )
    
    documentUrl: str = Field(
        ...,
        description="Azure Blob Storage URL for the document",
        example="https://storage.blob.core.windows.net/submission-guid/document1.pdf"
    )
    
    submissionId: str = Field(
        ...,
        description="Unique identifier for the submission",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    
    userId: str = Field(
        ...,
        description="User who uploaded the document",
        example="user@example.com"
    )
    
    content: str = Field(
        ...,
        description="Extracted content from the document",
        example="Invoice content text..."
    )
    
    type: Optional[str] = Field(
        None,
        description="Classified document type",
        example="invoice"
    )
    
    summary: Optional[str] = Field(
        None,
        description="Summary of the document content",
        example="Invoice for consulting services rendered in December 2024"
    )
    
    extractedData: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional extracted data from the document"
    )
    
    firstProcessedAt: datetime = Field(
        ...,
        description="Timestamp when the document was first processed",
        example="2025-07-10T09:00:42.696433"
    )
    
    lastProcessedAt: datetime = Field(
        ...,
        description="Timestamp when the document was last processed",
        example="2025-07-10T10:10:58.682950"
    )


class DocumentDataExtractedEventData(BaseModel):
    """
    Data payload for DocumentDataExtractedEvent.
    
    Attributes:
        documentUrl: Azure Blob Storage URL for the document
        documentId: ID of the document record in the documents container
        documentType: Identified document type
        extractedData: Extracted structured data
        success: Whether data extraction was successful
    """
    
    documentUrl: str = Field(
        ...,
        description="Azure Blob Storage URL for the document",
        example="https://storage.blob.core.windows.net/submissions/123e4567-e89b-12d3-a456-426614174000/document1.pdf"
    )
    
    documentId: str = Field(
        ...,
        description="ID of the document record in the documents container",
        example="550e8400-e29b-41d4-a716-446655440000"
    )
    
    documentType: str = Field(
        ...,
        description="Identified document type",
        example="invoice"
    )
    
    extractedData: Dict[str, Any] = Field(
        ...,
        description="Extracted structured data",
        example={
            "invoiceNumber": "INV-2025-001",
            "totalAmount": 1250.00,
            "currency": "USD",
            "dueDate": "2025-08-07",
            "vendor": "Acme Corp"
        }
    )
    
    success: bool = Field(
        ...,
        description="Whether data extraction was successful",
        example=True
    )


class DocumentDataExtractedEvent(BaseModel):
    """
    Event model emitted after document data extraction is complete.
    
    This event is triggered when the data extractor has successfully
    extracted structured data from a document and updated the document record in Cosmos DB.
    
    Attributes:
        id: Unique event identifier
        eventType: Type of event (DocumentDataExtractedEvent)
        submissionId: Unique identifier for the submission
        userId: User who uploaded the document
        timestamp: ISO 8601 timestamp when event was created
        data: Event data payload
    """
    
    id: str = Field(
        ...,
        description="Unique event identifier",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    
    eventType: str = Field(
        default="DocumentDataExtractedEvent",
        description="Type of event",
        example="DocumentDataExtractedEvent"
    )
    
    submissionId: str = Field(
        ...,
        description="Unique identifier for the submission",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    
    userId: str = Field(
        ...,
        description="User who uploaded the document",
        example="user@example.com"
    )
    
    timestamp: datetime = Field(
        ...,
        description="ISO 8601 timestamp when event was created"
    )
    
    data: DocumentDataExtractedEventData = Field(
        ...,
        description="Event data payload"
    )

