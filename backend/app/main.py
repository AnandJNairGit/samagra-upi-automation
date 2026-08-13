"""Main FastAPI application entry point."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import logger
from app.core.database import engine, check_db_connectivity
from app.api.v1 import v1_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager for startup and shutdown events."""
    logger.info(f"Starting {settings.APP_NAME} in [{settings.APP_ENV}] environment...")

    # Verify initial database connectivity on startup
    db_connected = await check_db_connectivity()
    if db_connected:
        logger.info("Database connection established successfully.")
    else:
        logger.warning("Database connection could not be established on startup.")

    yield

    logger.info(f"Shutting down {settings.APP_NAME}...")
    await engine.dispose()
    logger.info("Database connection pool disposed.")


def create_application() -> FastAPI:
    """Factory to build and configure the FastAPI application."""
    application = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # CORS configuration
    allowed_origins = settings.CORS_ORIGINS
    if allowed_origins:
        logger.info(f"Configuring CORS with allowed origins: {allowed_origins}")
        application.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    else:
        logger.info("No external CORS origins configured (standard for same-origin reverse proxy).")

    # Mount API v1 router
    application.include_router(v1_router, prefix="/v1")

    @application.get("/", tags=["Root"])
    async def root():
        return {
            "service": settings.APP_NAME,
            "status": "online",
            "health_check": "/v1/health",
        }

    return application


app = create_application()
