"""
Data models for the docproc-parser-foundry service.

This module contains Pydantic models used for data validation and serialization
in the document processing service using Azure Document Intelligence.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime


class DocumentUploadedEventData(BaseModel):
    """
    Data payload for DocumentUploadedEvent.
    
    Attributes:
        submissionId: Unique identifier for the submission
        documentUrl: Azure Blob Storage URL for the document
        documentType: Type of document (optional)
        uploadedAt: ISO 8601 timestamp when document was uploaded
    """
    
    submissionId: str = Field(
        ...,
        description="Unique identifier for the submission",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    
    documentUrl: str = Field(
        ...,
        description="Azure Blob Storage URL for the document",
        example="https://storage.blob.core.windows.net/submissions/123e4567-e89b-12d3-a456-426614174000/document1.pdf"
    )
    
    documentType: Optional[str] = Field(
        None,
        description="Type of document (optional)",
        example="pdf"
    )
    
    uploadedAt: datetime = Field(
        ...,
        description="ISO 8601 timestamp when document was uploaded",
        example="2025-07-07T14:30:00.123456Z"
    )


class DocumentUploadedEvent(BaseModel):
    """
    Event model for document upload events from Cosmos DB Change Feed.
    
    This event is triggered when a new document is uploaded and stored
    in the submissions container.
    
    Attributes:
        id: Unique event identifier
        eventType: Type of event (DocumentUploadedEvent)
        data: Event data payload
        timestamp: ISO 8601 timestamp when event was created
        submissionId: Partition key for the event
    """
    
    id: str = Field(
        ...,
        description="Unique event identifier",
        example="evt_123e4567-e89b-12d3-a456-426614174000"
    )
    
    eventType: str = Field(
        ...,
        description="Type of event",
        example="DocumentUploadedEvent"
    )
    
    data: DocumentUploadedEventData = Field(
        ...,
        description="Event data payload"
    )
    
    timestamp: datetime = Field(
        ...,
        description="ISO 8601 timestamp when event was created",
        example="2025-07-07T14:30:00.123456Z"
    )
    
    submissionId: str = Field(
        ...,
        description="Partition key for the event",
        example="123e4567-e89b-12d3-a456-426614174000"
    )


class DocumentContentExtractedEventData(BaseModel):
    """
    Data payload for DocumentContentExtractedEvent.
    
    Attributes:
        submissionId: Unique identifier for the submission
        documentUrl: Azure Blob Storage URL for the document
        extractedContent: Extracted content in Markdown format
        extractedAt: ISO 8601 timestamp when content was extracted
        processingDuration: Processing duration in seconds
        documentType: Detected document type
    """
    
    submissionId: str = Field(
        ...,
        description="Unique identifier for the submission",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    
    documentUrl: str = Field(
        ...,
        description="Azure Blob Storage URL for the document",
        example="https://storage.blob.core.windows.net/submissions/123e4567-e89b-12d3-a456-426614174000/document1.pdf"
    )
    
    extractedContent: str = Field(
        ...,
        description="Extracted content in Markdown format",
        example="# Document Title\n\nThis is the extracted content..."
    )
    
    extractedAt: datetime = Field(
        ...,
        description="ISO 8601 timestamp when content was extracted",
        example="2025-07-07T14:35:00.123456Z"
    )
    
    processingDuration: float = Field(
        ...,
        description="Processing duration in seconds",
        example=5.234
    )
    
    documentType: Optional[str] = Field(
        None,
        description="Detected document type",
        example="invoice"
    )


class DocumentContentExtractedEvent(BaseModel):
    """
    Event model for document content extraction completion.
    
    This event is emitted after successful processing of a document
    using Azure Document Intelligence.
    
    Attributes:
        id: Unique event identifier
        eventType: Type of event (DocumentContentExtractedEvent)
        data: Event data payload
        timestamp: ISO 8601 timestamp when event was created
        submissionId: Partition key for the event
    """
    
    id: str = Field(
        ...,
        description="Unique event identifier",
        example="evt_456e7890-f12a-34b5-c678-901234567890"
    )
    
    eventType: str = Field(
        default="DocumentContentExtractedEvent",
        description="Type of event"
    )
    
    data: DocumentContentExtractedEventData = Field(
        ...,
        description="Event data payload"
    )
    
    timestamp: datetime = Field(
        ...,
        description="ISO 8601 timestamp when event was created",
        example="2025-07-07T14:35:00.123456Z"
    )
    
    submissionId: str = Field(
        ...,
        description="Partition key for the event",
        example="123e4567-e89b-12d3-a456-426614174000"
    )


class DocumentRecord(BaseModel):
    """
    Document record stored in Cosmos DB documents container.
    
    This represents the processed document content and metadata
    stored after successful extraction.
    
    Attributes:
        id: Document identifier (derived from documentUrl)
        documentUrl: Azure Blob Storage URL for the document (partition key)
        submissionId: Unique identifier for the submission
        content: Extracted content in Markdown format
        processedAt: ISO 8601 timestamp when document was processed
        processingDuration: Processing duration in seconds
        documentType: Detected document type
        extractionMetadata: Additional metadata from extraction process
    """
    
    id: str = Field(
        ...,
        description="Document identifier (derived from documentUrl)",
        example="doc_123e4567-e89b-12d3-a456-426614174000"
    )
    
    documentUrl: str = Field(
        ...,
        description="Azure Blob Storage URL for the document (partition key)",
        example="https://storage.blob.core.windows.net/submissions/123e4567-e89b-12d3-a456-426614174000/document1.pdf"
    )
    
    submissionId: str = Field(
        ...,
        description="Unique identifier for the submission",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    
    content: str = Field(
        ...,
        description="Extracted content in Markdown format",
        example="# Document Title\n\nThis is the extracted content..."
    )
    
    processedAt: datetime = Field(
        ...,
        description="ISO 8601 timestamp when document was processed",
        example="2025-07-07T14:35:00.123456Z"
    )
    
    processingDuration: float = Field(
        ...,
        description="Processing duration in seconds",
        example=5.234
    )
    
    documentType: Optional[str] = Field(
        None,
        description="Detected document type",
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
