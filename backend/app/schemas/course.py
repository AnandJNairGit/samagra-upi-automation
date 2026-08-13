"""Course Pydantic schemas."""

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class CourseBase(BaseModel):
    """Base schema for course data."""

    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    status: str = Field(default="ACTIVE")

    @field_validator("name")
    @classmethod
    def validate_non_blank_name(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Course name cannot be empty or whitespace only")
        return clean

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        upper = v.upper()
        if upper not in ("ACTIVE", "INACTIVE", "ARCHIVED"):
            raise ValueError("Status must be ACTIVE, INACTIVE, or ARCHIVED")
        return upper


class CourseCreate(CourseBase):
    """Schema for creating a course."""

    pass


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
                raise ValueError("Course name cannot be empty or whitespace only")
            return clean
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            upper = v.upper()
            if upper not in ("ACTIVE", "INACTIVE", "ARCHIVED"):
                raise ValueError("Status must be ACTIVE, INACTIVE, or ARCHIVED")
            return upper
        return v


class CourseResponse(CourseBase):
    """Public representation of a course."""

    public_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
