"""Reconciliation repository for database operations on reconciliation_runs and reconciliation_results."""

import uuid
from typing import List, Optional, Tuple
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.bank_transaction import BankTransaction
from app.models.payment_session import PaymentSession
from app.models.payment_submission import PaymentSubmission
from app.models.reconciliation_result import ReconciliationResult
from app.models.reconciliation_run import ReconciliationRun
from app.models.statement_import import StatementImport


class ReconciliationRepository:
    """Repository for Reconciliation database operations."""

    async def create_run(self, session: AsyncSession, run: ReconciliationRun) -> ReconciliationRun:
        """Persist a new ReconciliationRun record."""
        session.add(run)
        await session.flush()
        return run

    async def update_run(self, session: AsyncSession, run: ReconciliationRun) -> ReconciliationRun:
        """Update an existing ReconciliationRun record."""
        await session.flush()
        return run

    async def get_run_by_public_id(
        self, session: AsyncSession, public_id: uuid.UUID
    ) -> Optional[tuple[ReconciliationRun, StatementImport]]:
        """Fetch ReconciliationRun by public_id joined with StatementImport."""
        stmt = (
            select(ReconciliationRun, StatementImport)
            .join(StatementImport, ReconciliationRun.statement_import_id == StatementImport.id)
            .where(ReconciliationRun.public_id == public_id)
        )
        result = await session.execute(stmt)
        return result.first()

    async def list_runs_paginated(
        self,
        session: AsyncSession,
        statement_import_id: Optional[int] = None,
        batch_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[tuple[ReconciliationRun, StatementImport]], int]:
        """List paginated reconciliation runs with statement import details."""
        base_stmt = select(ReconciliationRun, StatementImport).join(
            StatementImport, ReconciliationRun.statement_import_id == StatementImport.id
        )

        if statement_import_id is not None:
            base_stmt = base_stmt.where(ReconciliationRun.statement_import_id == statement_import_id)

        if batch_id is not None:
            base_stmt = base_stmt.where(ReconciliationRun.batch_id == batch_id)

        subq = base_stmt.subquery()
        count_stmt = select(func.count()).select_from(subq)
        total_result = await session.execute(count_stmt)
        total = total_result.scalar_one()

        offset = (page - 1) * page_size
        paginated_stmt = (
            base_stmt.order_by(ReconciliationRun.created_at.desc(), ReconciliationRun.id.desc())
            .offset(offset)
            .limit(page_size)
        )

        result = await session.execute(paginated_stmt)
        items = list(result.all())
        return items, total

    async def bulk_create_results(
        self, session: AsyncSession, results: List[ReconciliationResult]
    ) -> None:
        """Bulk persist list of ReconciliationResult entities."""
        if not results:
            return
        session.add_all(results)
        await session.flush()

    async def list_results_for_run_paginated(
        self,
        session: AsyncSession,
        run_id: int,
        status: Optional[str] = None,
        reason_code: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[tuple[ReconciliationResult, BankTransaction, Optional[PaymentSession], Optional[PaymentSubmission]]], int]:
        """List paginated results for a reconciliation run with joined entities."""
        base_stmt = (
            select(ReconciliationResult, BankTransaction, PaymentSession, PaymentSubmission)
            .join(BankTransaction, ReconciliationResult.bank_transaction_id == BankTransaction.id)
            .outerjoin(PaymentSession, ReconciliationResult.payment_session_id == PaymentSession.id)
            .outerjoin(PaymentSubmission, ReconciliationResult.payment_submission_id == PaymentSubmission.id)
            .where(ReconciliationResult.reconciliation_run_id == run_id)
        )

        conditions = []
        if status:
            conditions.append(ReconciliationResult.status == status)
        if reason_code:
            conditions.append(ReconciliationResult.reason_code == reason_code)
        if search and search.strip():
            clean_search = f"%{search.strip()}%"
            conditions.append(
                or_(
                    BankTransaction.reference_id.ilike(clean_search),
                    BankTransaction.utr.ilike(clean_search),
                    BankTransaction.counterparty_name.ilike(clean_search),
                    PaymentSession.reference_id.ilike(clean_search),
                    PaymentSession.full_name.ilike(clean_search),
                    PaymentSubmission.utr.ilike(clean_search),
                )
            )

        if conditions:
            base_stmt = base_stmt.where(*conditions)

        subq = base_stmt.subquery()
        count_stmt = select(func.count()).select_from(subq)
        total_result = await session.execute(count_stmt)
        total = total_result.scalar_one()

        offset = (page - 1) * page_size
        paginated_stmt = (
            base_stmt.order_by(ReconciliationResult.id.asc())
            .offset(offset)
            .limit(page_size)
        )

        result = await session.execute(paginated_stmt)
        items = list(result.all())
        return items, total

    async def get_result_detail_by_public_id(
        self, session: AsyncSession, public_id: uuid.UUID
    ) -> Optional[tuple[ReconciliationResult, BankTransaction, Optional[PaymentSession], Optional[PaymentSubmission], StatementImport]]:
        """Fetch complete detail for a single reconciliation result."""
        stmt = (
            select(ReconciliationResult, BankTransaction, PaymentSession, PaymentSubmission, StatementImport)
            .join(BankTransaction, ReconciliationResult.bank_transaction_id == BankTransaction.id)
            .join(StatementImport, BankTransaction.statement_import_id == StatementImport.id)
            .outerjoin(PaymentSession, ReconciliationResult.payment_session_id == PaymentSession.id)
            .outerjoin(PaymentSubmission, ReconciliationResult.payment_submission_id == PaymentSubmission.id)
            .where(ReconciliationResult.public_id == public_id)
        )
        result = await session.execute(stmt)
        return result.first()

    async def delete_runs_by_statement_import_id(self, session: AsyncSession, statement_import_id: int) -> int:
        """Delete all reconciliation runs (and cascaded results) associated with a statement import."""
        from sqlalchemy import delete
        stmt = delete(ReconciliationRun).where(ReconciliationRun.statement_import_id == statement_import_id)
        result = await session.execute(stmt)
        await session.flush()
        return result.rowcount

    async def delete_runs_by_batch_id(self, session: AsyncSession, batch_id: int) -> int:
        """Delete all reconciliation runs (and cascaded results) associated with a batch."""
        from sqlalchemy import delete
        stmt = delete(ReconciliationRun).where(ReconciliationRun.batch_id == batch_id)
        result = await session.execute(stmt)
        await session.flush()
        return result.rowcount


