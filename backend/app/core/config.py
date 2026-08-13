"""Centralized strongly-typed application configuration."""

from typing import List, Union
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


# Singleton configuration instance
settings = Settings()
