from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# Represent Mongo ObjectId as a plain string for Pydantic v2 compatibility
PyObjectId = str


# Users
class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=60)
    password: str = Field(min_length=8, max_length=200)
    full_name: Optional[str] = None
    role: str = Field(default="viewer")  # "admin" or "viewer"

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if not re.search(r'[A-Za-z]', v):
            raise ValueError('Password must contain at least one letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one number')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        return v


class UserOut(BaseModel):
    id: PyObjectId = Field(alias="_id")
    username: str
    full_name: Optional[str] = None
    role: str
    createdAt: datetime

    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}


# Documents
class DocumentCreate(BaseModel):
    filename: str
    path: str
    size: int
    mime: Optional[str] = None
    uploadedBy: str


class DocumentOut(BaseModel):
    id: PyObjectId = Field(alias="_id")
    filename: str
    path: str
    size: int
    mime: Optional[str] = None
    uploadedBy: str
    createdAt: datetime

    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}


# -----------------------------
# Document endpoint responses
# -----------------------------
class AnalyzeJobQueuedResponse(BaseModel):
    status: str = Field(description="Current queue status, typically 'queued'")
    query: str
    file_processed: str
    documentId: str
    jobId: str


class DocumentsListResponse(BaseModel):
    items: list[DocumentOut]


class DocumentDeleteResponse(BaseModel):
    status: str
    documentId: str


class JobStatusResponse(BaseModel):
    id: Optional[str] = None
    status: str
    progress: Optional[int] = Field(default=None, ge=0, le=100)
    file_path: Optional[str] = None
    query: Optional[str] = None
    user_id: Optional[str] = None
    document_id: Optional[str] = None
    analysis_id: Optional[str] = None
    error: Optional[str] = None

    class Config:
        extra = "allow"  # Allow forward compatibility for unexpected metadata keys


# Analyses
class AnalysisCreate(BaseModel):
    documentId: str
    userId: str
    query: str
    summary: str


class AnalysisOut(BaseModel):
    id: PyObjectId = Field(alias="_id")
    documentId: str
    userId: str
    query: str
    summary: str
    createdAt: datetime

    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}


# Audit logs
class AuditLogOut(BaseModel):
    id: PyObjectId = Field(alias="_id")
    path: str
    method: str
    user: Optional[str] = None
    status: str
    createdAt: datetime

    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}


