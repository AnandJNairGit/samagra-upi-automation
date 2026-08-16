"""Course Pydantic schemas."""

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class CourseCreate(BaseModel):
    """Schema for creating a course (status defaults to ACTIVE, ARCHIVED is forbidden)."""

    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    status: str = Field(default="ACTIVE")

    @field_validator("name")
    @classmethod
    def validate_non_blank_name(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Course name cannot be empty or whitespace only.")
        return clean

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            clean = v.strip()
            return clean if clean else None
        return None

    @field_validator("status")
    @classmethod
    def validate_create_status(cls, v: str) -> str:
        upper = v.upper().strip()
        if upper not in ("ACTIVE", "INACTIVE"):
            raise ValueError("Creation status must be either 'ACTIVE' or 'INACTIVE'. 'ARCHIVED' is not allowed on creation.")
        return upper


class CourseUpdate(BaseModel):
    """Schema for updating a course."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    status: Optional[str] = None

    @field_validator("name")
    @classmethod
    def validate_non_blank_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            clean = v.strip()
            if not clean:
                raise ValueError("Course name cannot be empty or whitespace only.")
            return clean
        return v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            clean = v.strip()
            return clean if clean else None
        return None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            upper = v.upper().strip()
            if upper not in ("ACTIVE", "INACTIVE", "ARCHIVED"):
                raise ValueError("Status must be 'ACTIVE', 'INACTIVE', or 'ARCHIVED'.")
            return upper
        return v


class CourseResponse(BaseModel):
    """Public representation of a course."""

    public_id: uuid.UUID
    name: str
    description: Optional[str] = None
    status: str
    batch_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

