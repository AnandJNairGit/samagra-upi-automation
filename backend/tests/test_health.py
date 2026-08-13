"""Tests for API health check endpoints."""

import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_app_health_endpoint():
    """Verify GET /v1/health returns 200 and status ok."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "app" in data
        assert "env" in data


@pytest.mark.asyncio
async def test_database_health_endpoint_success():
    """Verify GET /v1/health/db returns 200 when database is connected."""
    transport = ASGITransport(app=app)
    with patch("app.api.v1.health.check_db_connectivity", new_callable=AsyncMock) as mock_check:
        mock_check.return_value = True
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/v1/health/db")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["database"] == "connected"


@pytest.mark.asyncio
async def test_database_health_endpoint_failure():
    """Verify GET /v1/health/db returns 503 when database is unreachable."""
    transport = ASGITransport(app=app)
    with patch("app.api.v1.health.check_db_connectivity", new_callable=AsyncMock) as mock_check:
        mock_check.return_value = False
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/v1/health/db")
            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "unavailable"
            assert data["database"] == "disconnected"
