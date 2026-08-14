"""Admin session repository managing persistent session state, locking, and revocations."""

import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.admin_session import AdminSession


class AdminSessionRepository:
    """Repository handling database operations for AdminSession entities."""

    async def create(self, db: AsyncSession, session: AdminSession) -> AdminSession:
        """Persist a new AdminSession record."""
        db.add(session)
        await db.flush()
        await db.refresh(session)
        return session

    async def get_by_public_id(
        self,
        db: AsyncSession,
        public_id: uuid.UUID,
    ) -> Optional[AdminSession]:
        """Fetch an AdminSession by its public UUID."""
        stmt = select(AdminSession).where(AdminSession.public_id == public_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_public_id_for_update(
        self,
        db: AsyncSession,
        public_id: uuid.UUID,
    ) -> Optional[AdminSession]:
        """Fetch an AdminSession by its public UUID with an exclusive row lock."""
        stmt = (
            select(AdminSession)
            .where(AdminSession.public_id == public_id)
            .with_for_update()
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_by_admin_id(
        self,
        db: AsyncSession,
        admin_id: int,
    ) -> List[AdminSession]:
        """Retrieve all currently active (unrevoked and unexpired) sessions for an admin."""
        now_utc = datetime.now(timezone.utc)
        stmt = (
            select(AdminSession)
            .where(
                AdminSession.admin_user_id == admin_id,
                AdminSession.revoked_at.is_(None),
                AdminSession.expires_at > now_utc,
            )
            .order_by(AdminSession.created_at.desc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def update(self, db: AsyncSession, session: AdminSession) -> AdminSession:
        """Update an existing AdminSession record."""
        await db.flush()
        await db.refresh(session)
        return session

    async def revoke_all_for_admin(
        self,
        db: AsyncSession,
        admin_id: int,
        revoked_at: Optional[datetime] = None,
    ) -> int:
        """Revoke all active sessions for a specific admin user."""
        now_utc = revoked_at or datetime.now(timezone.utc)
        stmt = (
            update(AdminSession)
            .where(
                AdminSession.admin_user_id == admin_id,
                AdminSession.revoked_at.is_(None),
            )
            .values(revoked_at=now_utc)
        )
        result = await db.execute(stmt)
        await db.flush()
        return result.rowcount

    async def delete_expired_and_revoked(
        self,
        db: AsyncSession,
        older_than: datetime,
    ) -> int:
        """Clean up old sessions that expired or were revoked prior to older_than timestamp."""
        stmt = delete(AdminSession).where(
            (AdminSession.expires_at < older_than)
            | ((AdminSession.revoked_at.is_not(None)) & (AdminSession.revoked_at < older_than))
        )
        result = await db.execute(stmt)
        await db.flush()
        return result.rowcount
