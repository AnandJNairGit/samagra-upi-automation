"""Concurrency integration tests for refresh token rotation and row-level locking."""

import asyncio
import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.auth.hashing import hash_password
from app.core.config import settings
from app.models.admin_user import AdminUser
from app.services.auth_service import AuthService
from app.services.exceptions import RefreshTokenReplayError


@pytest.mark.asyncio
async def test_concurrent_refresh_token_rotation_row_locking():
    """Mandatory Concurrency Test:

    Two simultaneous refresh operations using the EXACT SAME refresh token.
    Because refresh_session acquires a SELECT ... FOR UPDATE row lock on admin_sessions:
    - Exactly ONE request must succeed (acquiring the lock first and rotating the token).
    - The competing request must acquire the lock second, observe the hash mismatch,
      detect a replay attack, and be rejected with RefreshTokenReplayError.
    """
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    admin_public_id = uuid.uuid4()
    admin_email = f"concur.admin.{uuid.uuid4().hex[:6]}@samagra.org"
    pwd = "SecurePassword123!"

    # 1. Setup initial admin and session
    async with async_session() as setup_session:
        admin = AdminUser(
            public_id=admin_public_id,
            email=admin_email,
            password_hash=hash_password(pwd),
            full_name="Concurrency Admin",
            is_active=True,
        )
        setup_session.add(admin)
        await setup_session.flush()

        service = AuthService()
        raw_refresh, access_token, _, _ = await service.create_session(
            setup_session,
            admin=admin,
        )
        await setup_session.commit()

    # 2. Define concurrent worker calling refresh_session on separate DB transactions
    async def refresh_worker(worker_id: int):
        async with async_session() as session:
            service = AuthService()
            try:
                result = await service.refresh_session(
                    session,
                    raw_refresh_token=raw_refresh,
                    user_agent=f"Worker-{worker_id}",
                    ip_address=f"10.0.0.{worker_id}",
                )
                await session.commit()
                return {"status": "success", "worker": worker_id, "data": result}
            except RefreshTokenReplayError as exc:
                await session.commit()  # Replay handler sets revoked_at
                return {"status": "replay_detected", "worker": worker_id, "error": str(exc)}
            except Exception as exc:
                await session.rollback()
                return {"status": "error", "worker": worker_id, "error": str(exc)}

    # 3. Launch both competing refresh requests simultaneously
    results = await asyncio.gather(
        refresh_worker(1),
        refresh_worker(2),
        return_exceptions=False,
    )

    successes = [r for r in results if r["status"] == "success"]
    replays = [r for r in results if r["status"] == "replay_detected"]

    # Exactly one must succeed and one must be detected as replay
    assert len(successes) == 1, f"Expected 1 success, got {len(successes)}: {results}"
    assert len(replays) == 1, f"Expected 1 replay detection, got {len(replays)}: {results}"

    await engine.dispose()
