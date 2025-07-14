"""
Data models for the docproc-search-indexer service.

This module contains Pydantic models used for data validation and serialization
in the document search indexing service.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime


class DocumentUploadedEventData(BaseModel):
    """
    Data payload for DocumentUploadedEvent.
    
    Attributes:
        documentUrl: Azure Blob Storage URL for the document
        documentId: ID of the document record in the documents container
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


class DocumentUploadedEvent(BaseModel):
    """
    Event model for document upload events from Cosmos DB Change Feed.
    
    This event is triggered when a new document is uploaded and stored
    in the submissions container.
    
    Attributes:
        id: Unique event identifier
        eventType: Type of event (DocumentUploadedEvent)
        submissionId: Unique identifier for the submission
        userId: User who uploaded the document
        timestamp: ISO 8601 timestamp when event was created
        data: Event data payload (contains documentUrl)
    """
    
    id: str = Field(
        ...,
        description="Unique event identifier",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    
    eventType: str = Field(
        default="DocumentUploadedEvent",
        description="Type of event",
        example="DocumentUploadedEvent"
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
    
    data: DocumentUploadedEventData = Field(
        ...,
        description="Event data payload"
    )


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


class ProcessingResult(BaseModel):
    """
    Result of document processing operation.
    
    Attributes:
        success: Whether processing was successful
        documentUrl: Azure Blob Storage URL for the document
        extractedContent: Extracted content in Markdown format (if successful)
        processingDuration: Processing duration in seconds
        documentType: Detected document type (if successful)
        extractionMetadata: Additional metadata from extraction process
        errorMessage: Error message if processing failed
    """
    
    success: bool = Field(
        ...,
        description="Whether processing was successful",
        example=True
    )
    
    documentUrl: str = Field(
        ...,
        description="Azure Blob Storage URL for the document",
        example="https://storage.blob.core.windows.net/submissions/123e4567-e89b-12d3-a456-426614174000/document1.pdf"
    )
    
    extractedContent: Optional[str] = Field(
        None,
        description="Extracted content in Markdown format (if successful)",
        example="# Document Title\n\nThis is the extracted content..."
    )
    
    processingDuration: float = Field(
        ...,
        description="Processing duration in seconds",
        example=5.234
    )
    
    documentType: Optional[str] = Field(
        None,
        description="Detected document type (if successful)",
        example="invoice"
    )
    
    extractionMetadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata from extraction process",
        example={
            "pageCount": 3,
            "confidence": 0.95,
            "apiVersion": "2023-07-31"
        }
    )
    
    errorMessage: Optional[str] = Field(
        None,
        description="Error message if processing failed",
        example="Document format not supported"
    )


class DocumentIndexedEventData(BaseModel):
    """
    Data payload for DocumentIndexedEvent.
    
    Attributes:
        documentUrl: Azure Blob Storage URL for the document
        documentId: ID of the document record in the documents container
        searchIndexName: Name of the search index where document was added
        success: Whether indexing was successful
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
    
    searchIndexName: str = Field(
        ...,
        description="Name of the search index where document was added",
        example="documents-index"
    )
    
    success: bool = Field(
        ...,
        description="Whether indexing was successful",
        example=True
    )


class DocumentIndexedEvent(BaseModel):
    """
    Event model emitted after document indexing is complete.
    
    This event is triggered when a document has been successfully
    indexed into Azure AI Search with proper metadata and security trimming.
    
    Attributes:
        id: Unique event identifier
        eventType: Type of event (DocumentIndexedEvent)
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
        default="DocumentIndexedEvent",
        description="Type of event",
        example="DocumentIndexedEvent"
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
    
    data: DocumentIndexedEventData = Field(
        ...,
        description="Event data payload"
    )
