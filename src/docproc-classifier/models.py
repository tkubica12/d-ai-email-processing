"""
Data models for the docproc-classifier service.

This module contains Pydantic models used for data validation and serialization
in the document classification service using OpenAI API.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from enum import Enum


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


class DocumentType(str, Enum):
    """
    Enumeration of supported document types for classification.
    """
    INVOICE = "invoice"
    CONTRACT = "contract"
    BANK_STATEMENT = "bankStatement"
    SUBMISSION_NOTES = "submissionNotes"
    OTHER = "other"


class DocumentClassificationResult(BaseModel):
    """
    Result of document classification using OpenAI API.
    
    Attributes:
        type: Classified document type
        summary: Summary of the document content
    """
    
    type: DocumentType = Field(
        ...,
        description="Classified document type",
        example=DocumentType.INVOICE
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


class LLMClassificationResponse(BaseModel):
    """
    Structured response model for OpenAI classification API.
    
    This model ensures the LLM response matches the expected JSON structure
    defined in the system_prompt.jinja2 template.
    
    Attributes:
        type: Classified document type (one of predefined types)
        summary: One-paragraph summary of the document's key content
    """
    
    type: DocumentType = Field(
        ...,
        description="Classified document type",
        example=DocumentType.INVOICE
    )
    
    summary: str = Field(
        ...,
        description="One-paragraph summary of the document's key content",
        example="Invoice for consulting services rendered in December 2024, amount $1,250.00, due date January 15, 2025"
    )


class DocumentClassifiedEventData(BaseModel):
    """
    Data payload for DocumentClassifiedEvent.
    
    Attributes:
        documentUrl: Azure Blob Storage URL for the document
        documentId: ID of the document record in the documents container
        documentType: Classified document type
        success: Whether classification was successful
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
        description="Classified document type",
        example="invoice"
    )
    
    success: bool = Field(
        ...,
        description="Whether classification was successful",
        example=True
    )


class DocumentClassifiedEvent(BaseModel):
    """
    Event model emitted after document classification is complete.
    
    This event is triggered when the classifier has successfully
    classified a document and updated the document record in Cosmos DB.
    
    Attributes:
        id: Unique event identifier
        eventType: Type of event (DocumentClassifiedEvent)
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
        default="DocumentClassifiedEvent",
        description="Type of event",
        example="DocumentClassifiedEvent"
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
    
    data: DocumentClassifiedEventData = Field(
        ...,
        description="Event data payload"
    )


class SubmissionDocument(BaseModel):
    """
    Document reference in submission record.
    
    This model represents a document within a submission record,
    tracking its processing status and classified type.
    
    Attributes:
        documentUrl: Azure Blob Storage URL for the document
        processed: Whether the document has been processed
        type: Classified document type (optional until classification is complete)
    """
    
    documentUrl: str = Field(
        ...,
        description="Azure Blob Storage URL for the document",
        example="https://storage.blob.core.windows.net/submission-guid/document1.pdf"
    )
    
    processed: bool = Field(
        ...,
        description="Whether the document has been processed",
        example=True
    )
    
    type: Optional[str] = Field(
        None,
        description="Classified document type",
        example="invoice"
    )


class SubmissionRecord(BaseModel):
    """
    Submission record stored in Cosmos DB submissions container.
    
    This represents a complete submission with metadata and document references.
    
    Schema matches the actual Cosmos DB document structure.
    - Container: submissions
    - Partition Key: userId
    - Document ID: Same as submissionId
    """
    
    model_config = ConfigDict(extra="ignore")  # Ignore Cosmos DB internal fields
    
    id: str = Field(
        ...,
        description="Submission identifier (same as submissionId)",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    
    submissionId: str = Field(
        ...,
        description="Unique identifier for the submission",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    
    userId: str = Field(
        ...,
        description="User who created the submission",
        example="user@example.com"
    )
    
    submittedAt: datetime = Field(
        ...,
        description="ISO 8601 timestamp when submission was created"
    )
    
    documents: List[SubmissionDocument] = Field(
        ...,
        description="List of documents in the submission"
    )
    
    evaluationResults: Optional[Dict[str, Any]] = Field(
        None,
        description="Evaluation results from submission analysis"
    )

