"""Reconciliation service for executing deterministic transaction matching algorithms."""

import uuid
from collections import Counter
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin_user import AdminUser
from app.models.bank_transaction import BankTransaction
from app.models.batch import Batch
from app.models.payment_session import PaymentSession
from app.models.payment_submission import PaymentSubmission
from app.models.reconciliation_result import ReconciliationResult
from app.models.reconciliation_run import ReconciliationRun
from app.models.statement_import import StatementImport
from app.repositories.bank_transaction_repository import BankTransactionRepository
from app.repositories.batch_repository import BatchRepository
from app.repositories.payment_session_repository import PaymentSessionRepository
from app.repositories.reconciliation_repository import ReconciliationRepository
from app.repositories.statement_import_repository import StatementImportRepository
from app.schemas.reconciliation import (
    ReconciliationResultDetailResponse,
    ReconciliationResultListResponse,
    ReconciliationResultResponse,
    ReconciliationRunListResponse,
    ReconciliationRunResponse,
)
from app.services.exceptions import (
    DomainError,
    ReconciliationResultNotFoundError,
    ReconciliationRunNotFoundError,
    StatementImportNotReadyError,
)


class ReconciliationService:
    """Service layer executing deterministic payment reconciliation."""

    def __init__(
        self,
        reconciliation_repo: Optional[ReconciliationRepository] = None,
        statement_import_repo: Optional[StatementImportRepository] = None,
        bank_tx_repo: Optional[BankTransactionRepository] = None,
        payment_session_repo: Optional[PaymentSessionRepository] = None,
        batch_repo: Optional[BatchRepository] = None,
    ):
        self.reconciliation_repo = reconciliation_repo or ReconciliationRepository()
        self.statement_import_repo = statement_import_repo or StatementImportRepository()
        self.bank_tx_repo = bank_tx_repo or BankTransactionRepository()
        self.payment_session_repo = payment_session_repo or PaymentSessionRepository()
        self.batch_repo = batch_repo or BatchRepository()

    async def run_reconciliation(
        self,
        db: AsyncSession,
        batch_public_id: uuid.UUID,
        statement_import_public_id: uuid.UUID,
        admin_user: AdminUser,
    ) -> ReconciliationRunResponse:
        """Execute deterministic payment reconciliation against an imported bank statement file for a specific batch."""
        if not batch_public_id:
            raise DomainError("A batch_public_id is required to initiate a reconciliation run.")

        # 1. Fetch batch and verify existence
        batch = await self.batch_repo.get_by_public_id_with_course(db, batch_public_id)
        if not batch:
            raise DomainError(f"Batch '{batch_public_id}' was not found.")

        # 2. Fetch statement import and verify readiness
        import_res = await self.statement_import_repo.get_by_public_id(db, statement_import_public_id)
        if not import_res:
            raise StatementImportNotReadyError(
                f"Statement import '{statement_import_public_id}' was not found."
            )
        statement_import, _ = import_res
        if statement_import.status not in ("COMPLETED", "COMPLETED_WITH_ERRORS"):
            raise StatementImportNotReadyError(
                f"Statement import '{statement_import_public_id}' is not ready for reconciliation."
            )

        now_utc = datetime.now(timezone.utc)

        # 3. Clean up previous reconciliation runs for this batch (no history retention)
        await self.reconciliation_repo.delete_runs_by_batch_id(db, batch.id)

        # 4. Create new ReconciliationRun entity in RUNNING state with batch_id
        run = ReconciliationRun(
            statement_import_id=statement_import.id,
            batch_id=batch.id,
            initiated_by=admin_user.id,
            status="RUNNING",
            started_at=now_utc,
        )
        await self.reconciliation_repo.create_run(db, run)

        try:
            # 4. Fetch all bank transactions for statement import
            from sqlalchemy import select
            stmt = select(BankTransaction).where(BankTransaction.statement_import_id == statement_import.id).order_by(BankTransaction.id.asc())
            res = await db.execute(stmt)
            all_txs = list(res.scalars().all())

            # 5. Extract CREDIT transactions and reference IDs
            # If direction is NULL (not mapped during import), treat as CREDIT
            # (the importer skips rows with no amount, so only credit rows land here)
            credit_txs = [tx for tx in all_txs if (tx.direction or "CREDIT").upper() == "CREDIT"]
            debit_txs = [tx for tx in all_txs if (tx.direction or "CREDIT").upper() != "CREDIT"]

            ref_ids = [tx.reference_id.strip() for tx in credit_txs if tx.reference_id and tx.reference_id.strip()]

            # Count reference occurrences among CREDIT transactions in this run
            ref_counts = Counter(ref_ids)

            # 6. Bulk lookup PaymentSessions restricted directly at SQL-level to selected batch_id
            payment_map = await self.payment_session_repo.get_by_reference_ids_bulk(
                db, ref_ids, batch_id=batch.id
            )

            # 7. Execute deterministic classification for each BankTransaction
            results_to_create: List[ReconciliationResult] = []

            matched_count = 0
            amount_mismatch_count = 0
            unknown_reference_count = 0
            no_reference_count = 0
            utr_mismatch_count = 0
            duplicate_transaction_count = 0
            needs_review_count = 0
            unmatched_count = 0

            for tx in all_txs:
                # If direction is NULL (not mapped), default to CREDIT
                is_credit = (tx.direction or "CREDIT").upper() == "CREDIT"
                raw_ref = (tx.reference_id or "").strip()

                if not is_credit:
                    # Non-credit transaction (e.g. DEBIT)
                    result_status = "UNMATCHED"
                    reason_code = "NON_CREDIT_TRANSACTION"
                    explanation = "Non-credit transaction (e.g. debit or fee adjustment) excluded from participant payment matching."
                    ref_match = None
                    amt_match = None
                    utr_match = None
                    ps_id = None
                    sub_id = None
                    unmatched_count += 1

                elif not raw_ref:
                    # Missing reference ID
                    result_status = "NO_REFERENCE"
                    reason_code = "NO_REFERENCE"
                    explanation = "Statement transaction does not contain a configured payment reference code."
                    ref_match = None
                    amt_match = None
                    utr_match = None
                    ps_id = None
                    sub_id = None
                    no_reference_count += 1

                elif ref_counts.get(raw_ref, 0) > 1:
                    # Duplicate reference code across multiple CREDIT bank transactions in this import
                    payment_tuple = payment_map.get(raw_ref)
                    ps = payment_tuple[0] if payment_tuple else None
                    sub = payment_tuple[1] if payment_tuple else None

                    # Invariant Check: Ensure matched session belongs to run.batch_id
                    if ps and ps.batch_id != batch.id:
                        ps = None
                        sub = None

                    ps_id = ps.id if ps else None
                    sub_id = sub.id if sub else None

                    result_status = "DUPLICATE_TRANSACTION"
                    reason_code = "DUPLICATE_TRANSACTION"
                    explanation = f"Multiple bank transactions in this statement file ({ref_counts[raw_ref]}) share the payment reference code '{raw_ref}'."
                    ref_match = True if ps else False
                    amt_match = None
                    utr_match = None
                    duplicate_transaction_count += 1

                else:
                    # Single CREDIT transaction with non-empty reference ID
                    payment_tuple = payment_map.get(raw_ref)

                    if not payment_tuple:
                        # Reference code unknown in DB for this batch
                        result_status = "UNKNOWN_REFERENCE"
                        reason_code = "UNKNOWN_REFERENCE"
                        explanation = f"No PaymentSession exists for batch '{batch.name}' with reference code '{raw_ref}'."
                        ref_match = False
                        amt_match = None
                        utr_match = None
                        ps_id = None
                        sub_id = None
                        unknown_reference_count += 1
                    else:
                        ps, sub = payment_tuple

                        # Invariant Check: Ensure payment session belongs strictly to run.batch_id
                        if ps.batch_id != batch.id:
                            raise DomainError(
                                f"Batch isolation violation: PaymentSession {ps.id} (batch {ps.batch_id}) "
                                f"does not belong to run batch {batch.id}."
                            )

                        ps_id = ps.id
                        sub_id = sub.id if sub else None
                        ref_match = True

                        # Compare Amount
                        tx_amt = tx.amount_inr
                        ps_amt = ps.amount_inr  # Snapshot

                        if tx_amt != ps_amt:
                            # Amount mismatch
                            amt_match = False
                            # Check UTR if both present
                            tx_utr = tx.utr.strip() if tx.utr and tx.utr.strip() else None
                            sub_utr = sub.utr.strip() if sub and sub.utr and sub.utr.strip() else None
                            if tx_utr and sub_utr:
                                utr_match = (tx_utr == sub_utr)
                            else:
                                utr_match = None

                            result_status = "AMOUNT_MISMATCH"
                            reason_code = "AMOUNT_MISMATCH"
                            explanation = f"Reference code matched, but bank credit amount (₹{tx_amt or 0}) differs from expected payment amount (₹{ps_amt})."
                            amount_mismatch_count += 1

                        else:
                            # Amount matched!
                            amt_match = True
                            tx_utr = tx.utr.strip() if tx.utr and tx.utr.strip() else None
                            sub_utr = sub.utr.strip() if sub and sub.utr and sub.utr.strip() else None

                            if tx_utr and sub_utr:
                                utr_match = (tx_utr == sub_utr)
                            else:
                                utr_match = None

                            if utr_match is False:
                                # Differing UTRs
                                result_status = "UTR_MISMATCH"
                                reason_code = "UTR_MISMATCH"
                                explanation = f"Reference code and amount matched, but bank UTR ('{tx_utr}') differs from submitted UTR ('{sub_utr}')."
                                utr_mismatch_count += 1
                            else:
                                # Matched!
                                result_status = "MATCHED"
                                reason_code = "MATCHED_REFERENCE_AMOUNT"
                                utr_info = " UTR verified." if utr_match is True else " (UTR not provided or missing)."
                                explanation = f"Reference code and amount matched successfully.{utr_info}"
                                matched_count += 1
                                if ps:
                                    ps.status = "APPROVED"
                                if sub:
                                    sub.status = "APPROVED"

                res_obj = ReconciliationResult(
                    reconciliation_run_id=run.id,
                    bank_transaction_id=tx.id,
                    payment_session_id=ps_id,
                    payment_submission_id=sub_id,
                    status=result_status,
                    reference_match=ref_match,
                    amount_match=amt_match,
                    utr_match=utr_match,
                    payer_match=None,
                    reason_code=reason_code,
                    explanation=explanation,
                )
                results_to_create.append(res_obj)

            # 8. Update run metrics and set COMPLETED
            run.total_transactions = len(all_txs)
            run.credit_transactions = len(credit_txs)
            run.debit_transactions = len(debit_txs)
            run.matched_count = matched_count
            run.amount_mismatch_count = amount_mismatch_count
            run.unknown_reference_count = unknown_reference_count
            run.no_reference_count = no_reference_count
            run.utr_mismatch_count = utr_mismatch_count
            run.duplicate_transaction_count = duplicate_transaction_count
            run.needs_review_count = needs_review_count
            run.unmatched_count = unmatched_count
            run.status = "COMPLETED"
            run.completed_at = datetime.now(timezone.utc)

            # Bulk save results
            await self.reconciliation_repo.bulk_create_results(db, results_to_create)
            await self.reconciliation_repo.update_run(db, run)

            return ReconciliationRunResponse(
                public_id=run.public_id,
                statement_import_public_id=statement_import.public_id,
                batch_public_id=batch.public_id,
                filename=statement_import.filename,
                batch_name=batch.name,
                status=run.status,
                total_transactions=run.total_transactions,
                credit_transactions=run.credit_transactions,
                debit_transactions=run.debit_transactions,
                matched_count=run.matched_count,
                amount_mismatch_count=run.amount_mismatch_count,
                unknown_reference_count=run.unknown_reference_count,
                no_reference_count=run.no_reference_count,
                utr_mismatch_count=run.utr_mismatch_count,
                duplicate_transaction_count=run.duplicate_transaction_count,
                needs_review_count=run.needs_review_count,
                unmatched_count=run.unmatched_count,
                started_at=run.started_at,
                completed_at=run.completed_at,
                created_at=run.created_at,
            )

        except Exception as e:
            run.status = "FAILED"
            run.completed_at = datetime.now(timezone.utc)
            await self.reconciliation_repo.update_run(db, run)
            raise e

    async def get_run_by_public_id(
        self, db: AsyncSession, public_id: uuid.UUID
    ) -> ReconciliationRunResponse:
        """Fetch single reconciliation run details."""
        item = await self.reconciliation_repo.get_run_by_public_id(db, public_id)
        if not item:
            raise ReconciliationRunNotFoundError(str(public_id))
        run, statement_import = item

        batch_pub_id = None
        batch_title = None
        if run.batch_id:
            b_obj = await self.batch_repo.get_by_id(db, run.batch_id)
            if b_obj:
                batch_pub_id = b_obj.public_id
                batch_title = b_obj.name

        return ReconciliationRunResponse(
            public_id=run.public_id,
            statement_import_public_id=statement_import.public_id,
            batch_public_id=batch_pub_id,
            filename=statement_import.filename,
            batch_name=batch_title,
            status=run.status,
            total_transactions=run.total_transactions,
            credit_transactions=run.credit_transactions,
            debit_transactions=run.debit_transactions,
            matched_count=run.matched_count,
            amount_mismatch_count=run.amount_mismatch_count,
            unknown_reference_count=run.unknown_reference_count,
            no_reference_count=run.no_reference_count,
            utr_mismatch_count=run.utr_mismatch_count,
            duplicate_transaction_count=run.duplicate_transaction_count,
            needs_review_count=run.needs_review_count,
            unmatched_count=run.unmatched_count,
            started_at=run.started_at,
            completed_at=run.completed_at,
            created_at=run.created_at,
        )

    async def list_runs_paginated(
        self,
        db: AsyncSession,
        statement_import_public_id: Optional[uuid.UUID] = None,
        batch_public_id: Optional[uuid.UUID] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> ReconciliationRunListResponse:
        """List paginated reconciliation runs."""
        statement_import_id = None
        if statement_import_public_id:
            imp_res = await self.statement_import_repo.get_by_public_id(db, statement_import_public_id)
            if imp_res:
                statement_import_id = imp_res[0].id

        batch_id = None
        if batch_public_id:
            b_res = await self.batch_repo.get_by_public_id(db, batch_public_id)
            if b_res:
                batch_id = b_res.id

        items, total = await self.reconciliation_repo.list_runs_paginated(
            db, statement_import_id=statement_import_id, batch_id=batch_id, page=page, page_size=page_size
        )

        response_items = []
        for run, si in items:
            b_pub_id = None
            b_title = None
            if run.batch_id:
                b_obj = await self.batch_repo.get_by_id(db, run.batch_id)
                if b_obj:
                    b_pub_id = b_obj.public_id
                    b_title = b_obj.name

            response_items.append(
                ReconciliationRunResponse(
                    public_id=run.public_id,
                    statement_import_public_id=si.public_id,
                    batch_public_id=b_pub_id,
                    filename=si.filename,
                    batch_name=b_title,
                    status=run.status,
                    total_transactions=run.total_transactions,
                    credit_transactions=run.credit_transactions,
                    debit_transactions=run.debit_transactions,
                    matched_count=run.matched_count,
                    amount_mismatch_count=run.amount_mismatch_count,
                    unknown_reference_count=run.unknown_reference_count,
                    no_reference_count=run.no_reference_count,
                    utr_mismatch_count=run.utr_mismatch_count,
                    duplicate_transaction_count=run.duplicate_transaction_count,
                    needs_review_count=run.needs_review_count,
                    unmatched_count=run.unmatched_count,
                    started_at=run.started_at,
                    completed_at=run.completed_at,
                    created_at=run.created_at,
                )
            )

        total_pages = (total + page_size - 1) // page_size if total > 0 else 0

        return ReconciliationRunListResponse(
            items=response_items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def list_results_for_run_paginated(
        self,
        db: AsyncSession,
        run_public_id: uuid.UUID,
        status: Optional[str] = None,
        reason_code: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> ReconciliationResultListResponse:
        """List paginated reconciliation results for a run."""
        run_item = await self.reconciliation_repo.get_run_by_public_id(db, run_public_id)
        if not run_item:
            raise ReconciliationRunNotFoundError(str(run_public_id))
        run, _ = run_item

        items, total = await self.reconciliation_repo.list_results_for_run_paginated(
            db,
            run_id=run.id,
            status=status,
            reason_code=reason_code,
            search=search,
            page=page,
            page_size=page_size,
        )

        response_items = [
            ReconciliationResultResponse(
                public_id=res.public_id,
                reconciliation_run_public_id=run.public_id,
                bank_transaction_public_id=bt.public_id,
                payment_session_public_id=ps.public_id if ps else None,
                payment_submission_public_id=sub.public_id if sub else None,
                status=res.status,
                reason_code=res.reason_code,
                explanation=res.explanation,
                reference_match=res.reference_match,
                amount_match=res.amount_match,
                utr_match=res.utr_match,
                payer_match=res.payer_match,
                bank_reference_id=bt.reference_id,
                bank_amount_inr=bt.amount_inr,
                bank_utr=bt.utr,
                bank_transaction_at=bt.transaction_at,
                bank_counterparty_name=bt.counterparty_name,
                expected_reference_id=ps.reference_id if ps else None,
                expected_amount_inr=ps.amount_inr if ps else None,
                submitted_utr=sub.utr if sub else None,
                participant_name=ps.full_name if ps else None,
            )
            for res, bt, ps, sub in items
        ]

        total_pages = (total + page_size - 1) // page_size if total > 0 else 0

        return ReconciliationResultListResponse(
            items=response_items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def get_result_detail_by_public_id(
        self, db: AsyncSession, public_id: uuid.UUID
    ) -> ReconciliationResultDetailResponse:
        """Fetch full inspection detail for a single reconciliation result."""
        item = await self.reconciliation_repo.get_result_detail_by_public_id(db, public_id)
        if not item:
            raise ReconciliationResultNotFoundError(str(public_id))

        res, bt, ps, sub, si = item

        # Fetch run public ID
        run_item = await self.reconciliation_repo.get_run_by_public_id(db, res.reconciliation_run.public_id)
        run_pub_id = run_item[0].public_id if run_item else res.reconciliation_run.public_id

        return ReconciliationResultDetailResponse(
            public_id=res.public_id,
            reconciliation_run_public_id=run_pub_id,
            bank_transaction_public_id=bt.public_id,
            payment_session_public_id=ps.public_id if ps else None,
            payment_submission_public_id=sub.public_id if sub else None,
            status=res.status,
            reason_code=res.reason_code,
            explanation=res.explanation,
            reference_match=res.reference_match,
            amount_match=res.amount_match,
            utr_match=res.utr_match,
            payer_match=res.payer_match,
            bank_reference_id=bt.reference_id,
            bank_amount_inr=bt.amount_inr,
            bank_utr=bt.utr,
            bank_transaction_at=bt.transaction_at,
            bank_counterparty_name=bt.counterparty_name,
            expected_reference_id=ps.reference_id if ps else None,
            expected_amount_inr=ps.amount_inr if ps else None,
            submitted_utr=sub.utr if sub else None,
            participant_name=ps.full_name if ps else None,
            statement_filename=si.filename,
            bank_direction=bt.direction,
            bank_description=bt.description,
            payment_session_status=ps.status if ps else None,
            course_name_snapshot=ps.course_name_snapshot if ps else None,
            batch_name_snapshot=ps.batch_name_snapshot if ps else None,
            submission_status=sub.status if sub else None,
            submitted_at=sub.submitted_at if sub else None,
        )
