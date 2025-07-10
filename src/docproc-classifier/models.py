"""
Data models for the docproc-classifier service.

This module contains Pydantic models used for data validation and serialization
in the document classification service using OpenAI API.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime


class DocumentContentExtractedEventData(BaseModel):
    """
    Data payload for DocumentContentExtractedEvent.
    
    Attributes:
        documentUrl: Azure Blob Storage URL for the document
        documentId: ID of the document record in the documents container
        contentLength: Length of extracted content in characters
        success: Whether content extraction was successful
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
    
    contentLength: int = Field(
        ...,
        description="Length of extracted content in characters",
        example=15000
    )
    
    success: bool = Field(
        ...,
        description="Whether content extraction was successful",
        example=True
    )


class DocumentContentExtractedEvent(BaseModel):
    """
    Event model for document content extraction events from Cosmos DB Change Feed.
    
    This event is triggered when Document Intelligence has successfully
    extracted content from a document and stored it in the documents container.
    
    Attributes:
        id: Unique event identifier
        eventType: Type of event (DocumentContentExtractedEvent)
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
        default="DocumentContentExtractedEvent",
        description="Type of event",
        example="DocumentContentExtractedEvent"
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
    
    data: DocumentContentExtractedEventData = Field(
        ...,
        description="Event data payload"
    )


class DocumentClassificationResult(BaseModel):
    """
    Result of document classification using OpenAI API.
    
    Attributes:
        type: Classified document type
        summary: Summary of the document content
    """
    
    type: str = Field(
        ...,
        description="Classified document type",
        example="invoice"
    )
    
    summary: str = Field(
        ...,
        description="Summary of the document content",
        example="Invoice for consulting services rendered in December 2024"
    )


class DocumentRecord(BaseModel):
    """
    Document record stored in Cosmos DB documents container.
    
    This represents the processed document content and metadata
    stored after successful extraction and classification.
    
    Schema matches Design.md specification:
    - Container: documents
    - Partition Key: submissionId (groups documents by submission)
    - Document ID: Generated GUID for each document record
    """
    
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
    
    fileName: str = Field(
        ...,
        description="Original filename of the document",
        example="invoice-2024-12.pdf"
    )
    
    contentType: str = Field(
        ...,
        description="MIME type of the document",
        example="application/pdf"
    )
    
    extractedContent: str = Field(
        ...,
        description="Extracted content from the document in markdown format",
        example="# Invoice\n\nInvoice Number: INV-2024-001..."
    )
    
    contentLength: int = Field(
        ...,
        description="Length of extracted content in characters",
        example=15000
    )
    
    classification: Optional[DocumentClassificationResult] = Field(
        None,
        description="Classification result if available"
    )
    
    uploadTimestamp: datetime = Field(
        ...,
        description="Timestamp when the document was uploaded"
    )
    
    processedTimestamp: datetime = Field(
        ...,
        description="Timestamp when the document was processed"
    )
    
    classifiedTimestamp: Optional[datetime] = Field(
        None,
        description="Timestamp when the document was classified"
    )
    """
    Event model emitted after document content extraction is complete.
    
    This event is triggered when Document Intelligence has successfully
    extracted content from a document and stored it in the documents container.
    
    Attributes:
        id: Unique event identifier
        eventType: Type of event (DocumentContentExtractedEvent)
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
        default="DocumentContentExtractedEvent",
        description="Type of event",
        example="DocumentContentExtractedEvent"
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
    
    data: DocumentContentExtractedEventData = Field(
        ...,
        description="Event data payload"
    )


class DocumentRecord(BaseModel):
    """
    Document record stored in Cosmos DB documents container.
    
    This represents the processed document content and metadata
    stored after successful extraction.
    
    Schema matches Design.md specification:
    - Container: documents
    - Partition Key: submissionId (groups documents by submission)
    - Document ID: Generated GUID for each document record
    """
    
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
        description="Unique identifier for the submission (partition key)",
        example="submission-guid"
    )
    
    userId: str = Field(
        ...,
        description="User who uploaded the document",
        example="user@example.com"
    )
    
    content: str = Field(
        ...,
        description="Full markdown content extracted from document using Azure Document Intelligence",
        example="# Document Title\n\nFull markdown content extracted from document using Azure Document Intelligence..."
    )
    
    firstProcessedAt: datetime = Field(
        ...,
        description="ISO 8601 timestamp when document was first processed",
        example="2025-07-07T10:00:00Z"
    )
    
    lastProcessedAt: datetime = Field(
        ...,
        description="ISO 8601 timestamp when document was last processed",
        example="2025-07-07T10:05:00Z"
    )
    
    # Optional fields that will be populated by other services
    type: Optional[str] = Field(
        None,
        description="Document type (populated by classifier service)",
        example="invoice"
    )
    
    summary: Optional[str] = Field(
        None,
        description="AI-generated summary of document content (populated by classifier service)",
        example="AI-generated summary of document content..."
    )
    
    extractedData: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured data extracted from document (populated by data extractor service)",
        example={
            "invoiceNumber": "INV-2025-001",
            "amount": 1250.00,
            "currency": "USD",
            "dueDate": "2025-08-07",
            "vendor": "Acme Corp"
        }
    )

