"""
Data models for the submission-trigger service.

This module contains Pydantic models used for data validation and serialization
in the submission-trigger service that tracks document processing status 
and triggers submission preparation completed events.
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


class DocumentIndexedEventData(BaseModel):
    """
    Data payload for DocumentIndexedEvent.
    
    Attributes:
        documentUrl: Azure Blob Storage URL for the document
        documentId: ID of the document record in the documents container
        searchIndexName: Name of the search index where document was indexed
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
        description="Name of the search index where document was indexed",
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
    
    This event is triggered when the search indexer has successfully
    indexed a document in Azure AI Search.
    
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


class DocumentDataExtractedEventData(BaseModel):
    """
    Data payload for DocumentDataExtractedEvent.
    
    Attributes:
        documentUrl: Azure Blob Storage URL for the document
        documentId: ID of the document record in the documents container
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
    
    success: bool = Field(
        ...,
        description="Whether data extraction was successful",
        example=True
    )


class DocumentDataExtractedEvent(BaseModel):
    """
    Event model emitted after document data extraction is complete.
    
    This event is triggered when the data extractor has successfully
    extracted structured data from a document.
    
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


class SubmissionCreatedEventData(BaseModel):
    """
    Data payload for SubmissionCreated event.
    
    Attributes:
        documentUrls: List of Azure Blob Storage URLs for submitted documents
        containerName: Name of the blob container storing the documents
    """
    
    documentUrls: List[str] = Field(
        ...,
        description="List of Azure Blob Storage URLs for submitted documents",
        example=[
            "https://storage.blob.core.windows.net/submission-guid/document1.pdf",
            "https://storage.blob.core.windows.net/submission-guid/document2.docx"
        ]
    )
    
    containerName: str = Field(
        ...,
        description="Name of the blob container storing the documents",
        example="submission-guid"
    )


class SubmissionCreatedEvent(BaseModel):
    """
    Event model emitted when a new submission is created.
    
    This event is triggered when submission-intake creates a new submission
    record and uploads documents to blob storage.
    
    Attributes:
        id: Unique event identifier
        eventType: Type of event (SubmissionCreated)
        submissionId: Unique identifier for the submission
        userId: User who created the submission
        timestamp: ISO 8601 timestamp when event was created
        data: Event data payload
    """
    
    id: str = Field(
        ...,
        description="Unique event identifier",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    
    eventType: str = Field(
        default="SubmissionCreated",
        description="Type of event",
        example="SubmissionCreated"
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
    
    timestamp: datetime = Field(
        ...,
        description="ISO 8601 timestamp when event was created"
    )
    
    data: SubmissionCreatedEventData = Field(
        ...,
        description="Event data payload"
    )


class SubmissionPreparationCompletedEventData(BaseModel):
    """
    Data payload for SubmissionPreparationCompletedEvent.
    
    Attributes:
        documentsProcessed: Number of documents that completed processing
    """
    
    documentsProcessed: int = Field(
        ...,
        description="Number of documents that completed processing",
        example=3
    )


class SubmissionPreparationCompletedEvent(BaseModel):
    """
    Event model emitted when all documents in a submission are fully processed.
    
    This event is triggered by submission-trigger when all documents have
    received DocumentClassifiedEvent, DocumentIndexedEvent, and DocumentDataExtractedEvent.
    
    Attributes:
        id: Unique event identifier
        eventType: Type of event (SubmissionPreparationCompletedEvent)
        submissionId: Unique identifier for the submission
        userId: User who created the submission
        timestamp: ISO 8601 timestamp when event was created
        data: Event data payload
    """
    
    id: str = Field(
        ...,
        description="Unique event identifier",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    
    eventType: str = Field(
        default="SubmissionPreparationCompletedEvent",
        description="Type of event",
        example="SubmissionPreparationCompletedEvent"
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
    
    timestamp: datetime = Field(
        ...,
        description="ISO 8601 timestamp when event was created"
    )
    
    data: SubmissionPreparationCompletedEventData = Field(
        ...,
        description="Event data payload"
    )


class SubmissionTriggerProjection(BaseModel):
    """
    Projection document stored in submissionstrigger container.
    
    This document tracks the processing status of each document in a submission
    and is used to determine when all documents are fully processed.
    
    Attributes:
        id: Unique identifier for the projection (same as submissionId)
        submissionId: Unique identifier for the submission
        userId: User who created the submission
        totalDocuments: Total number of documents in the submission
        documents: Dictionary mapping document URLs to their processing status
        createdAt: Timestamp when the projection was created
        updatedAt: Timestamp when the projection was last updated
    """
    
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(
        ...,
        description="Unique identifier for the projection (same as submissionId)",
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
    
    totalDocuments: int = Field(
        ...,
        description="Total number of documents in the submission",
        example=3
    )
    
    documents: Dict[str, Dict[str, bool]] = Field(
        ...,
        description="Dictionary mapping document URLs to their processing status",
        example={
            "https://storage.blob.core.windows.net/submission-guid/document1.pdf": {
                "classified": True,
                "indexed": True,
                "dataExtracted": False
            },
            "https://storage.blob.core.windows.net/submission-guid/document2.docx": {
                "classified": False,
                "indexed": False,
                "dataExtracted": False
            }
        }
    )
    
    createdAt: datetime = Field(
        ...,
        description="Timestamp when the projection was created"
    )
    
    updatedAt: datetime = Field(
        ...,
        description="Timestamp when the projection was last updated"
    )


class SubmissionDocument(BaseModel):
    """
    Document structure within a submission record.
    
    Attributes:
        documentUrl: Azure Blob Storage URL for the document
        type: Document type (optional, set after classification)
    """
    
    documentUrl: str = Field(
        ...,
        description="Azure Blob Storage URL for the document",
        example="https://storage.blob.core.windows.net/submissions/123e4567-e89b-12d3-a456-426614174000/document1.pdf"
    )
    
    type: Optional[str] = Field(
        None,
        description="Document type (optional, set after classification)",
        example="invoice"
    )


class SubmissionRecord(BaseModel):
    """
    Submission record stored in submissions container.
    
    This represents a complete submission with all its documents and metadata.
    
    Attributes:
        id: Unique identifier for the submission
        submissionId: Unique identifier for the submission (same as id)
        userId: User who created the submission
        submittedAt: Timestamp when the submission was created
        userMessage: Message provided by the user with the submission
        documents: List of documents in the submission
        evaluationResults: Results of AI analysis (optional, set after analysis)
    """
    
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(
        ...,
        description="Unique identifier for the submission",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    
    submissionId: str = Field(
        ...,
        description="Unique identifier for the submission (same as id)",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    
    userId: str = Field(
        ...,
        description="User who created the submission",
        example="user@example.com"
    )
    
    submittedAt: datetime = Field(
        ...,
        description="Timestamp when the submission was created"
    )
    
    userMessage: str = Field(
        ...,
        description="Message provided by the user with the submission",
        example="Please review the attached invoices and contract documents for approval."
    )
    
    documents: List[SubmissionDocument] = Field(
        ...,
        description="List of documents in the submission"
    )
    
    evaluationResults: Optional[Dict[str, Any]] = Field(
        None,
        description="Results of AI analysis (optional, set after analysis)"
    )
    
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
    tracking its classified type.
    
    Attributes:
        documentUrl: Azure Blob Storage URL for the document
        type: Classified document type (optional until classification is complete)
    """
    
    documentUrl: str = Field(
        ...,
        description="Azure Blob Storage URL for the document",
        example="https://storage.blob.core.windows.net/submission-guid/document1.pdf"
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
    
    userMessage: str = Field(
        ...,
        description="Email body content from the user's submission",
        example="Please review the attached invoices and contract documents for approval. Let me know if you need any additional information."
    )
    
    documents: List[SubmissionDocument] = Field(
        ...,
        description="List of documents in the submission"
    )
    
    evaluationResults: Optional[Dict[str, Any]] = Field(
        None,
        description="Evaluation results from submission analysis"
    )

