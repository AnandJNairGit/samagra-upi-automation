"""Health check endpoints for application and database."""

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.core.database import check_db_connectivity
from app.core.logging import logger

router = APIRouter()


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Application health endpoint."""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "env": settings.APP_ENV,
    }


@router.get("/health/db")
async def database_health_check():
    """PostgreSQL database connectivity check endpoint."""
    is_connected = await check_db_connectivity()
    if is_connected:
        return {
            "status": "ok",
            "database": "connected",
        }
    else:
        logger.error("Health check reported database unavailable")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unavailable",
                "database": "disconnected",
            },
        )
