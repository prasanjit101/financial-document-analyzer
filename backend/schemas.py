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


