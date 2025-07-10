"""
Data models for the submission-intake service.

This module contains Pydantic models used for data validation and serialization
in the email processing system.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime


class DocumentInfo(BaseModel):
    """
    Document information as stored in submission records (Design.md schema).
    
    This represents the document structure within a submission record,
    tracking the processing state of each document.
    
    Attributes:
        documentUrl: Azure Blob Storage URL for the document
        processed: Boolean indicating if document processing completed
        type: Document type detected during processing (null until processed)
    """
    
    documentUrl: str = Field(
        ...,
        description="Azure Blob Storage URL for the document",
        example="https://storage.blob.core.windows.net/submission-guid/document1.pdf"
    )
    
    processed: Optional[bool] = Field(
        None,
        description="Boolean indicating if document processing completed",
        example=True
    )
    
    type: Optional[str] = Field(
        None,
        description="Document type detected during processing",
        example="invoice"
    )


class EvaluationResults(BaseModel):
    """
    Evaluation results for a submission.
    
    Attributes:
        completeness: Completeness score (0.0-1.0)
        recommendations: List of recommendations for the submission
        issues: List of identified issues
        analysisTimestamp: ISO 8601 timestamp when analysis was completed
    """
    
    completeness: float = Field(
        ...,
        description="Completeness score between 0.0 and 1.0",
        ge=0.0,
        le=1.0,
        example=0.85
    )
    
    recommendations: List[str] = Field(
        default_factory=list,
        description="List of recommendations for the submission",
        example=["Request additional documentation for item X"]
    )
    
    issues: List[str] = Field(
        default_factory=list,
        description="List of identified issues",
        example=[]
    )
    
    analysisTimestamp: datetime = Field(
        ...,
        description="ISO 8601 timestamp when analysis was completed",
        example="2025-07-07T10:15:00Z"
    )


class DocumentRecord(BaseModel):
    """
    Document record as stored in the documents container (Design.md schema).
    
    This represents how individual documents are stored in the Cosmos DB
    documents container for processing and retrieval.
    
    Attributes:
        id: Document ID (generated GUID for each document record)
        documentUrl: Azure Blob Storage URL for the document (partition key)
        submissionId: Unique identifier for the parent submission
        userId: Email address of the user who submitted the document
        content: Full markdown content extracted from document (null initially)
        type: Document type detected during processing (null initially)
        summary: AI-generated summary of document content (null initially)
        extractedData: Structured data extracted from document (null initially)
        firstProcessedAt: ISO 8601 timestamp when document was first processed
        lastProcessedAt: ISO 8601 timestamp when document was last processed
    """
    
    id: str = Field(
        ...,
        description="Document ID (generated GUID)",
        example="550e8400-e29b-41d4-a716-446655440000"
    )
    
    documentUrl: str = Field(
        ...,
        description="Azure Blob Storage URL for the document",
        example="https://storage.blob.core.windows.net/submission-guid/document1.pdf"
    )
    
    submissionId: str = Field(
        ...,
        description="Unique identifier for the parent submission",
        example="submission-guid"
    )
    
    userId: str = Field(
        ...,
        description="Email address of the user who submitted the document",
        example="user@example.com"
    )
    
    content: Optional[str] = Field(
        None,
        description="Full markdown content extracted from document",
        example="# Document Title\n\nFull markdown content..."
    )
    
    type: Optional[str] = Field(
        None,
        description="Document type detected during processing",
        example="invoice"
    )
    
    summary: Optional[str] = Field(
        None,
        description="AI-generated summary of document content",
        example="AI-generated summary of document content..."
    )
    
    extractedData: Optional[Dict[str, Any]] = Field(
        None,
        description="Structured data extracted from document",
        example={
            "invoiceNumber": "INV-2025-001",
            "amount": 1250.00,
            "currency": "USD",
            "dueDate": "2025-08-07",
            "vendor": "Acme Corp"
        }
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


class SubmissionDocument(BaseModel):
    """
    Cosmos DB document model for submission records (Design.md schema).
    
    This model represents how submissions are stored in the Cosmos DB
    submissions container, following the exact schema from Design.md.
    
    Attributes:
        id: Document ID (same as submissionId for Cosmos DB)
        submissionId: Unique identifier for the submission (partition key)
        userId: Email address of the user who submitted
        submittedAt: ISO 8601 timestamp when the submission was created
        documents: List of document URLs with processing status
        evaluationResults: Results of submission evaluation (null until evaluated)
    """
    
    id: str = Field(
        ...,
        description="Document ID (same as submissionId)",
        example="submission-guid"
    )
    
    submissionId: str = Field(
        ...,
        description="Unique identifier for the submission",
        example="submission-guid"
    )
    
    userId: str = Field(
        ...,
        description="Email address of the user who submitted",
        example="user@example.com"
    )
    
    submittedAt: datetime = Field(
        ...,
        description="ISO 8601 timestamp when the submission was created",
        example="2025-07-07T10:00:00Z"
    )
    
    documents: List[DocumentInfo] = Field(
        default_factory=list,
        description="List of document URLs with processing status"
    )
    
    evaluationResults: Optional[EvaluationResults] = Field(
        None,
        description="Results of submission evaluation (null until evaluated)"
    )


class SubmissionMessage(BaseModel):
    """
    Service Bus message format for new submission events.
    
    This model represents the JSON structure sent to Service Bus when a new
    submission is created through the client web application.
    
    Attributes:
        submissionId: Unique identifier for the submission (GUID)
        userId: Email address of the user submitting the request
        documentUrls: List of Azure Blob Storage URLs for uploaded documents
        submittedAt: ISO 8601 timestamp when the submission was created
    """
    
    submissionId: str = Field(
        ...,
        description="Unique GUID identifier for the submission",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    
    userId: str = Field(
        ...,
        description="Email address of the user submitting the request",
        example="user@example.com"
    )
    
    documentUrls: List[str] = Field(
        default_factory=list,
        description="List of Azure Blob Storage URLs for uploaded documents",
        example=[
            "https://storage.blob.core.windows.net/submissions/123e4567-e89b-12d3-a456-426614174000/document1.pdf",
            "https://storage.blob.core.windows.net/submissions/123e4567-e89b-12d3-a456-426614174000/document2.docx"
        ]
    )
    
    submittedAt: datetime = Field(
        ...,
        description="ISO 8601 timestamp when the submission was created",
        example="2025-07-07T14:30:00.123456Z"
    )
    
    class Config:
        """Pydantic configuration for the model."""
        json_schema_extra = {
            "example": {
                "submissionId": "123e4567-e89b-12d3-a456-426614174000",
                "userId": "user@example.com",
                "documentUrls": [
                    "https://storage.blob.core.windows.net/submissions/123e4567-e89b-12d3-a456-426614174000/document1.pdf",
                    "https://storage.blob.core.windows.net/submissions/123e4567-e89b-12d3-a456-426614174000/document2.docx"
                ],
                "submittedAt": "2025-07-07T14:30:00.123456Z"
            }
        }


class SubmissionCreatedData(BaseModel):
    """
    Data payload for SubmissionCreated event.
    
    Contains submission-specific information for the event.
    
    Attributes:
        documentUrls: List of Azure Blob Storage URLs for uploaded documents
        containerName: Azure Blob Storage container name (same as submissionId)
    """
    
    documentUrls: List[str] = Field(
        default_factory=list,
        description="List of Azure Blob Storage URLs for uploaded documents",
        example=[
            "https://storage.blob.core.windows.net/submission-guid/document1.pdf",
            "https://storage.blob.core.windows.net/submission-guid/document2.docx"
        ]
    )
    
    containerName: str = Field(
        ...,
        description="Azure Blob Storage container name (same as submissionId)",
        example="submission-guid"
    )


class SubmissionCreatedEvent(BaseModel):
    """
    Event model for SubmissionCreated events (Design.md schema).
    
    This event is emitted when a new submission is successfully created
    and stored in the submissions container.
    
    Attributes:
        id: Unique event identifier (UUID)
        eventType: Event type identifier
        submissionId: Submission identifier this event relates to
        userId: Email address of the user who submitted
        timestamp: ISO 8601 timestamp when the event occurred
        data: Event-specific data payload
    """
    
    id: str = Field(
        ...,
        description="Unique event identifier (UUID)",
        example="uuid"
    )
    
    eventType: str = Field(
        default="SubmissionCreated",
        description="Event type identifier",
        example="SubmissionCreated"
    )
    
    submissionId: str = Field(
        ...,
        description="Submission identifier this event relates to",
        example="submission-guid"
    )
    
    userId: str = Field(
        ...,
        description="Email address of the user who submitted",
        example="user@example.com"
    )
    
    timestamp: datetime = Field(
        ...,
        description="ISO 8601 timestamp when the event occurred",
        example="2025-07-07T10:00:00Z"
    )
    
    data: SubmissionCreatedData = Field(
        ...,
        description="Event-specific data payload"
    )
    
    class Config:
        """Pydantic configuration for the model."""
        json_schema_extra = {
            "example": {
                "id": "uuid",
                "eventType": "SubmissionCreated",
                "submissionId": "submission-guid",
                "userId": "user@example.com",
                "timestamp": "2025-07-07T10:00:00Z",
                "data": {
                    "documentUrls": [
                        "https://storage.blob.core.windows.net/submission-guid/document1.pdf",
                        "https://storage.blob.core.windows.net/submission-guid/document2.docx"
                    ],
                    "containerName": "submission-guid"
                }
            }
        }


class DocumentUploadedEventData(BaseModel):
    """
    Data payload for DocumentUploadedEvent.
    
    Contains document-specific information for the event.
    
    Attributes:
        documentUrl: Azure Blob Storage URL for the uploaded document
        documentId: ID of the document record in the documents container
    """
    
    documentUrl: str = Field(
        ...,
        description="Azure Blob Storage URL for the uploaded document",
        example="https://storage.blob.core.windows.net/submission-guid/document1.pdf"
    )
    
    documentId: str = Field(
        ...,
        description="ID of the document record in the documents container",
        example="550e8400-e29b-41d4-a716-446655440000"
    )


class DocumentUploadedEvent(BaseModel):
    """
    Event model for DocumentUploadedEvent events (Design.md schema).
    
    This event is emitted for each document when a submission is created,
    triggering document processing by parser services.
    
    Attributes:
        id: Unique event identifier (UUID)
        eventType: Event type identifier
        submissionId: Submission identifier this event relates to
        userId: Email address of the user who submitted
        timestamp: ISO 8601 timestamp when the event occurred
        data: Event-specific data payload
    """
    
    id: str = Field(
        ...,
        description="Unique event identifier (UUID)",
        example="uuid"
    )
    
    eventType: str = Field(
        default="DocumentUploadedEvent",
        description="Event type identifier",
        example="DocumentUploadedEvent"
    )
    
    submissionId: str = Field(
        ...,
        description="Submission identifier this event relates to",
        example="submission-guid"
    )
    
    userId: str = Field(
        ...,
        description="Email address of the user who submitted",
        example="user@example.com"
    )
    
    timestamp: datetime = Field(
        ...,
        description="ISO 8601 timestamp when the event occurred",
        example="2025-07-07T10:00:00Z"
    )
    
    data: DocumentUploadedEventData = Field(
        ...,
        description="Event-specific data payload"
    )
    
    class Config:
        """Pydantic configuration for the model."""
        json_schema_extra = {
            "example": {
                "id": "uuid",
                "eventType": "DocumentUploadedEvent",
                "submissionId": "submission-guid",
                "userId": "user@example.com",
                "timestamp": "2025-07-07T10:00:00Z",
                "data": {
                    "documentUrl": "https://storage.blob.core.windows.net/submission-guid/document1.pdf"
                }
            }
        }
