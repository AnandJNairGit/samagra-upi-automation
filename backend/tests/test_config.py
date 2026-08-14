"""Unit tests for configuration management."""

from app.core.config import Settings


def test_default_settings():
    """Verify default settings load cleanly."""
    cfg = Settings()
    assert cfg.APP_NAME == "samagra-upi-automation"
    assert cfg.APP_PORT == 8000
    assert not cfg.is_production


def test_cors_origins_parsing():
    """Verify comma-separated string parses into list of origins."""
    cfg = Settings(CORS_ORIGINS="http://localhost:5173, http://127.0.0.1:5173")
    assert cfg.CORS_ORIGINS == ["http://localhost:5173", "http://127.0.0.1:5173"]

    empty_cfg = Settings(CORS_ORIGINS="")
    assert empty_cfg.CORS_ORIGINS == []


def test_jwt_secret_validation():
    """Verify JWT secret length validation."""
    import pytest
    with pytest.raises(ValueError, match="JWT_SECRET_KEY must be at least 32 characters long"):
        Settings(JWT_SECRET_KEY="too_short")

    valid_cfg = Settings(JWT_SECRET_KEY="valid_long_secret_key_with_sufficient_entropy_123")
    assert valid_cfg.JWT_SECRET_KEY == "valid_long_secret_key_with_sufficient_entropy_123"


def test_cookie_secure_resolution():
    """Verify cookie_secure resolution in development vs production."""
    dev_cfg = Settings(APP_ENV="development", AUTH_COOKIE_SECURE=None)
    assert dev_cfg.cookie_secure is False

    prod_cfg = Settings(APP_ENV="production", AUTH_COOKIE_SECURE=None)
    assert prod_cfg.cookie_secure is True

    explicit_override = Settings(APP_ENV="production", AUTH_COOKIE_SECURE=False)
    assert explicit_override.cookie_secure is False
