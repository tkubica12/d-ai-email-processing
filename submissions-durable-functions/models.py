"""
Data models for the durable functions submission processing.

This module contains Pydantic models used for data validation and serialization
in the durable functions orchestration workflow.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime


class SubmissionMessage(BaseModel):
    """
    Message payload received from Service Bus for new submissions.
    
    Attributes:
        submissionId: Unique identifier for the submission
        userId: User who uploaded the documents
        documentUrls: List of Azure Blob Storage URLs for the documents
        submittedAt: ISO 8601 timestamp when submission was created
    """
    
    submissionId: str = Field(
        ...,
        description="Unique identifier for the submission",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    
    userId: str = Field(
        ...,
        description="User who uploaded the documents",
        example="user@example.com"
    )
    
    documentUrls: List[str] = Field(
        ...,
        description="List of Azure Blob Storage URLs for the documents",
        example=[
            "https://storage.blob.core.windows.net/submissions/123e4567-e89b-12d3-a456-426614174000/document1.pdf",
            "https://storage.blob.core.windows.net/submissions/123e4567-e89b-12d3-a456-426614174000/document2.docx"
        ]
    )
    
    submittedAt: str = Field(
        ...,
        description="ISO 8601 timestamp when submission was created",
        example="2025-07-07T14:30:00.123456Z"
    )


class DocumentRecord(BaseModel):
    """
    Document record stored in Cosmos DB documents container.
    
    Attributes:
        id: Unique document identifier
        submissionId: Reference to the submission this document belongs to
        documentUrl: Azure Blob Storage URL for the document
        fileName: Original filename of the document
        contentType: MIME type of the document
        content: Extracted text content from the document
        metadata: Additional metadata extracted from the document
        processingStatus: Current processing status
        createdAt: Timestamp when record was created
        updatedAt: Timestamp when record was last updated
    """
    
    id: str = Field(
        ...,
        description="Unique document identifier",
        example="550e8400-e29b-41d4-a716-446655440000"
    )
    
    submissionId: str = Field(
        ...,
        description="Reference to the submission this document belongs to",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    
    documentUrl: str = Field(
        ...,
        description="Azure Blob Storage URL for the document",
        example="https://storage.blob.core.windows.net/submissions/123e4567-e89b-12d3-a456-426614174000/document1.pdf"
    )
    
    fileName: str = Field(
        ...,
        description="Original filename of the document",
        example="financial_statement.pdf"
    )
    
    contentType: str = Field(
        ...,
        description="MIME type of the document",
        example="application/pdf"
    )
    
    content: str = Field(
        ...,
        description="Extracted text content from the document"
    )
    
    documentType: Optional[str] = Field(
        default=None,
        description="Classified document type (invoice, contract, bankStatement, submissionNotes, other)",
        example="invoice"
    )
    
    summary: Optional[str] = Field(
        default=None,
        description="AI-generated summary of the document content"
    )
    
    extractedData: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Structured data extracted from the document"
    )
    
    classificationStatus: str = Field(
        default="pending",
        description="Status of document classification",
        example="completed"
    )
    
    dataExtractionStatus: str = Field(
        default="pending", 
        description="Status of document data extraction",
        example="completed"
    )
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata extracted from the document"
    )
    
    createdAt: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when record was created"
    )
    
    updatedAt: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when record was last updated"
    )


class SubmissionRecord(BaseModel):
    """
    Submission record stored in Cosmos DB submissions container.
    
    Attributes:
        id: Unique submission identifier (same as submissionId)
        submissionId: Unique identifier for the submission
        userId: User who uploaded the documents
        documentUrls: List of document URLs in this submission
        status: Current processing status of the submission
        createdAt: Timestamp when submission was created
        updatedAt: Timestamp when submission was last updated
        metadata: Additional metadata about the submission
    """
    
    id: str = Field(
        ...,
        description="Unique submission identifier (same as submissionId)",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    
    submissionId: str = Field(
        ...,
        description="Unique identifier for the submission",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    
    userId: str = Field(
        ...,
        description="User who uploaded the documents",
        example="user@example.com"
    )
    
    documentUrls: List[str] = Field(
        ...,
        description="List of document URLs in this submission"
    )
    
    status: str = Field(
        default="processing",
        description="Current processing status of the submission",
        example="processing"
    )
    
    createdAt: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when submission was created"
    )
    
    updatedAt: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when submission was last updated"
    )
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the submission"
    )
