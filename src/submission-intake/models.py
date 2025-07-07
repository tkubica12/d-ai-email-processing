"""
Data models for the submission-intake service.

This module contains Pydantic models used for data validation and serialization
in the email processing system.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID
from datetime import datetime


class DocumentInfo(BaseModel):
    """
    Document information as stored in submission records (Design.md schema).
    
    This represents the document structure within a submission record,
    tracking the processing state of each document.
    
    Attributes:
        documentUrl: Azure Blob Storage URL for the document
        processed: Timestamp when document processing completed (null if not processed)
        type: Document type detected during processing (null until processed)
    """
    
    documentUrl: str = Field(
        ...,
        description="Azure Blob Storage URL for the document",
        example="https://storage.blob.core.windows.net/submission-guid/document1.pdf"
    )
    
    processed: Optional[datetime] = Field(
        None,
        description="ISO 8601 timestamp when document processing completed",
        example="2025-07-07T10:30:00Z"
    )
    
    type: Optional[str] = Field(
        None,
        description="Document type detected during processing",
        example="application_form"
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
    """
    
    id: str = Field(
        ...,
        description="Document ID for Cosmos DB (same as submissionId)",
        example="submission-guid"
    )
    
    submissionId: str = Field(
        ...,
        description="Unique GUID identifier for the submission (partition key)",
        example="submission-guid"
    )
    
    userId: str = Field(
        ...,
        description="Email address of the user submitting the request",
        example="user@example.com"
    )
    
    submittedAt: datetime = Field(
        ...,
        description="ISO 8601 timestamp when the submission was created"
    )
    
    documents: List[DocumentInfo] = Field(
        default_factory=list,
        description="List of documents in this submission with processing status"
    )
    
    class Config:
        """Pydantic configuration for the model."""
        json_schema_extra = {
            "example": {
                "id": "submission-guid",
                "submissionId": "submission-guid",
                "userId": "user@example.com",
                "submittedAt": "2025-07-07T10:00:00Z",
                "documents": [
                    {
                        "documentUrl": "https://storage.blob.core.windows.net/submission-guid/document1.pdf",
                        "processed": None,
                        "type": None
                    },
                    {
                        "documentUrl": "https://storage.blob.core.windows.net/submission-guid/document2.docx",
                        "processed": None,
                        "type": None
                    }
                ]
            }
        }


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
