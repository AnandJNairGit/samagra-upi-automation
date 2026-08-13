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
