"""BankTransaction repository for persistence operations on bank_transactions table."""

import uuid
from typing import List, Set, Tuple
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bank_transaction import BankTransaction


class BankTransactionRepository:
    """Repository for BankTransaction database operations."""

    async def get_existing_keys(self, db: AsyncSession, source: str, keys: Set[str]) -> Set[str]:
        """Fetch set of source_transaction_keys that already exist in database for deduplication."""
        if not keys:
            return set()

        # Batch query existing keys in chunks of 500
        key_list = list(keys)
        chunk_size = 500
        existing: Set[str] = set()

        for i in range(0, len(key_list), chunk_size):
            chunk = key_list[i : i + chunk_size]
            query = select(BankTransaction.source_transaction_key).where(
                BankTransaction.source == source,
                BankTransaction.source_transaction_key.in_(chunk),
            )
            result = await db.execute(query)
            existing.update(result.scalars().all())

        return existing

    async def bulk_create(self, db: AsyncSession, transactions: List[BankTransaction]) -> None:
        """Bulk persist list of BankTransaction entities."""
        if not transactions:
            return
        db.add_all(transactions)
        await db.flush()

    async def list_by_import_id_paginated(
        self, db: AsyncSession, statement_import_id: int, page: int = 1, page_size: int = 20
    ) -> Tuple[List[BankTransaction], int]:
        """Fetch paginated bank transactions for a specific statement import."""
        offset = (page - 1) * page_size

        count_query = select(func.count(BankTransaction.id)).where(
            BankTransaction.statement_import_id == statement_import_id
        )
        total_result = await db.execute(count_query)
        total = total_result.scalar_one_or_none() or 0

        query = (
            select(BankTransaction)
            .where(BankTransaction.statement_import_id == statement_import_id)
            .order_by(BankTransaction.id.asc())
            .offset(offset)
            .limit(page_size)
        )

        result = await db.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def delete_by_import_id(self, db: AsyncSession, statement_import_id: int) -> int:
        """Delete all BankTransaction records linked to a specific statement import."""
        from sqlalchemy import delete
        stmt = delete(BankTransaction).where(BankTransaction.statement_import_id == statement_import_id)
        result = await db.execute(stmt)
        return result.rowcount or 0
