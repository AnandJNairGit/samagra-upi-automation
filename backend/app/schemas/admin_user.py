"""Admin user Pydantic schemas."""

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class AdminUserBase(BaseModel):
    """Base schema for admin user data."""

    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=150)
    is_active: bool = True

    @field_validator("full_name")
    @classmethod
    def validate_non_blank_name(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("full_name cannot be empty or whitespace only")
        return clean


class AdminUserCreate(AdminUserBase):
    """Schema for creating a new admin user."""

    password: str = Field(..., min_length=8)


class AdminUserResponse(AdminUserBase):
    """Public representation of an admin user."""

    public_id: uuid.UUID
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
