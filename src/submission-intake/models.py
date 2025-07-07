"""
Data models for the submission-intake service.

This module contains Pydantic models used for data validation and serialization
in the email processing system.
"""

from pydantic import BaseModel, Field
from typing import List
from uuid import UUID
from datetime import datetime


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
