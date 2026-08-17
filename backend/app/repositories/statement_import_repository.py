"""StatementImport repository for persistence operations on statement_imports table."""

import uuid
from typing import List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.statement_import import StatementImport
from app.models.admin_user import AdminUser


class StatementImportRepository:
    """Repository for StatementImport database operations."""

    async def get_by_canonical_hash(
        self, db: AsyncSession, canonical_mapping_hash: str
    ) -> Optional[StatementImport]:
        """Fetch completed statement import by canonical mapping hash for exact-file idempotency."""
        result = await db.execute(
            select(StatementImport)
            .where(
                StatementImport.canonical_mapping_hash == canonical_mapping_hash,
                StatementImport.status == "COMPLETED",
            )
            .order_by(StatementImport.created_at.desc())
            .limit(1)
        )
        return result.scalars().first()

    async def create(self, db: AsyncSession, statement_import: StatementImport) -> StatementImport:
        """Persist a new StatementImport entity."""
        db.add(statement_import)
        await db.flush()
        return statement_import

    async def get_by_public_id(
        self, db: AsyncSession, public_id: uuid.UUID
    ) -> Optional[Tuple[StatementImport, str]]:
        """Fetch single StatementImport with admin user full_name/email."""
        query = (
            select(StatementImport, func.coalesce(AdminUser.full_name, AdminUser.email).label("imported_by_name"))
            .join(AdminUser, StatementImport.imported_by == AdminUser.id)
            .where(StatementImport.public_id == public_id)
        )
        result = await db.execute(query)
        row = result.first()
        if not row:
            return None
        return row[0], row[1]

    async def list_paginated(
        self, db: AsyncSession, page: int = 1, page_size: int = 20
    ) -> Tuple[List[Tuple[StatementImport, str]], int]:
        """Fetch paginated statement imports ordered by created_at DESC, id DESC."""
        offset = (page - 1) * page_size

        count_query = select(func.count(StatementImport.id))
        total_result = await db.execute(count_query)
        total = total_result.scalar_one_or_none() or 0

        query = (
            select(StatementImport, func.coalesce(AdminUser.full_name, AdminUser.email).label("imported_by_name"))
            .join(AdminUser, StatementImport.imported_by == AdminUser.id)
            .order_by(StatementImport.created_at.desc(), StatementImport.id.desc())
            .offset(offset)
            .limit(page_size)
        )

        result = await db.execute(query)
        items = list(result.all())

        return items, total
