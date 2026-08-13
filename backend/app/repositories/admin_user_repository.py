"""Admin user repository for pure persistence operations."""

import uuid
from typing import Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.admin_user import AdminUser


class AdminUserRepository:
    """Persistence operations for admin users."""

    async def get_by_id(self, session: AsyncSession, user_id: int) -> Optional[AdminUser]:
        """Fetch admin user by internal ID."""
        stmt = select(AdminUser).where(AdminUser.id == user_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_public_id(
        self, session: AsyncSession, public_id: uuid.UUID
    ) -> Optional[AdminUser]:
        """Fetch admin user by public UUID."""
        stmt = select(AdminUser).where(AdminUser.public_id == public_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, session: AsyncSession, email: str) -> Optional[AdminUser]:
        """Fetch admin user by email (case-insensitive)."""
        stmt = select(AdminUser).where(func.lower(AdminUser.email) == email.strip().lower())
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, session: AsyncSession, user: AdminUser) -> AdminUser:
        """Persist a new admin user."""
        session.add(user)
        await session.flush()
        return user

    async def update(self, session: AsyncSession, user: AdminUser) -> AdminUser:
        """Update an existing admin user."""
        await session.flush()
        return user
