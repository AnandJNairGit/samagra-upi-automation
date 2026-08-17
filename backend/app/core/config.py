"""Centralized strongly-typed application configuration."""

from typing import List, Optional, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings schema validated with Pydantic."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # General App Settings
    APP_NAME: str = "samagra-upi-automation"
    APP_ENV: str = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://app_user:change_me_to_a_secure_password@postgres:5432/training_payments",
        description="Async PostgreSQL connection URL",
    )

    # CORS Configuration
    CORS_ORIGINS: Union[str, List[str]] = Field(
        default="",
        description="Comma-separated string or list of allowed CORS origins",
    )

    # Authentication & Security
    JWT_SECRET_KEY: str = Field(
        default="change_me_to_a_secure_jwt_secret_key_minimum_32_chars",
        description="Cryptographic secret key for signing JWT tokens",
    )
    JWT_ALGORITHM: str = Field(
        default="HS256",
        description="Algorithm for JWT signing",
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=15,
        description="Lifetime of access token in minutes",
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7,
        description="Lifetime of refresh token session in days",
    )
    AUTH_COOKIE_NAME: str = Field(
        default="samagra_refresh",
        description="HttpOnly cookie name for refresh token",
    )
    AUTH_COOKIE_SECURE: Optional[bool] = Field(
        default=None,
        description="Whether refresh cookie requires HTTPS. If None, defaults to is_production",
    )
    AUTH_COOKIE_SAMESITE: str = Field(
        default="lax",
        description="SameSite policy for refresh cookie",
    )
    DEV_ADMIN_PASSWORD: Optional[str] = Field(
        default=None,
        description="Password for seeding development admin account. Strictly None by default.",
    )

    # UPI & Payment Processing Configuration
    UPI_ID: str = Field(
        default="samagralearning@ibl",
        description="Primary UPI VPA ID for payment collection",
    )
    UPI_PAYEE_NAME: str = Field(
        default="Samagra Training",
        description="Merchant / Payee Name displayed in UPI app",
    )
    PAYMENT_SESSION_EXPIRE_MINUTES: int = Field(
        default=30,
        description="Payment session validity in minutes. Set to 0 to disable expiration.",
    )
    ADMIN_WHATSAPP_NUMBER: str = Field(
        default="919876543210",
        description="Administrator WhatsApp phone number with country code (digits only) for notification deep links",
    )

    @field_validator("JWT_SECRET_KEY", mode="after")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        """Ensure JWT secret is sufficiently long and cryptographically strong."""
        if not v or len(v.strip()) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters long.")
        return v

    @field_validator("CORS_ORIGINS", mode="after")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """Convert comma-separated origin string into a clean list."""
        if isinstance(v, str):
            if not v.strip():
                return []
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @property
    def is_production(self) -> bool:
        """Helper to determine if running in production mode."""
        return self.APP_ENV.lower() == "production"

    @property
    def cookie_secure(self) -> bool:
        """Determine whether cookie should set Secure flag."""
        if self.AUTH_COOKIE_SECURE is not None:
            return self.AUTH_COOKIE_SECURE
        return self.is_production


# Singleton configuration instance
settings = Settings()
