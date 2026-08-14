"""Pydantic schemas for authentication and admin authorization."""

import uuid
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    """Admin login credentials request schema."""

    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr = Field(description="Administrator email address")
    password: str = Field(min_length=8, description="Administrator password")


class AdminProfileResponse(BaseModel):
    """Sanitized administrator profile response schema."""

    model_config = ConfigDict(from_attributes=True)

    public_id: uuid.UUID
    email: str
    full_name: str
    is_active: bool


class LoginResponse(BaseModel):
    """Authentication success response returning access token and sanitized profile."""

    model_config = ConfigDict(from_attributes=True)

    access_token: str = Field(description="Short-lived JWT access token")
    token_type: str = Field(default="bearer", description="Token type header prefix")
    expires_in: int = Field(description="Access token lifetime in seconds")
    admin: AdminProfileResponse = Field(description="Authenticated admin profile")


class AdminHealthResponse(BaseModel):
    """Response schema for protected admin health verification endpoint."""

    model_config = ConfigDict(from_attributes=True)

    status: str = Field(default="ok", description="Health check status")
    authenticated: bool = Field(default=True, description="Authentication confirmation")
    admin_email: str = Field(description="Authenticated admin email")
    admin_public_id: uuid.UUID = Field(description="Authenticated admin public UUID")
