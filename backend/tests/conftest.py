"""Pytest configuration and async database fixtures.

Ensures tests run directly against the Alembic-migrated database schema
and automatically cleans up test data after execution.
"""

from typing import AsyncGenerator
import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import settings


@pytest.fixture(scope="session", autouse=True)
def apply_migrations():
    """Apply Alembic migrations to head before running test suite."""
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
    command.upgrade(alembic_cfg, "head")
    yield


@pytest_asyncio.fixture(autouse=True)
async def auto_clean_db_after_test():
    """Automatically truncate business tables after each test so no test data persists."""
    yield
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.execute(
            text("""
            TRUNCATE TABLE 
                reconciliation_results, 
                reconciliation_runs, 
                payment_submissions, 
                payment_sessions, 
                bank_transactions, 
                statement_imports, 
                batches, 
                courses 
            RESTART IDENTITY CASCADE;
        """)
        )
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide an isolated async database session."""
    test_engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
    )
    async_session = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with test_engine.connect() as connection:
        async with async_session(bind=connection) as session:
            yield session
            await session.rollback()

    await test_engine.dispose()
