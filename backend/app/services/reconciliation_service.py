"""Reconciliation service for executing deterministic transaction matching algorithms."""

import uuid
from collections import Counter
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin_user import AdminUser
from app.models.bank_transaction import BankTransaction
from app.models.payment_session import PaymentSession
from app.models.payment_submission import PaymentSubmission
from app.models.reconciliation_result import ReconciliationResult
from app.models.reconciliation_run import ReconciliationRun
from app.models.statement_import import StatementImport
from app.repositories.bank_transaction_repository import BankTransactionRepository
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
    ):
        self.reconciliation_repo = reconciliation_repo or ReconciliationRepository()
        self.statement_import_repo = statement_import_repo or StatementImportRepository()
        self.bank_tx_repo = bank_tx_repo or BankTransactionRepository()
        self.payment_session_repo = payment_session_repo or PaymentSessionRepository()

    async def run_reconciliation(
        self,
        db: AsyncSession,
        statement_import_public_id: uuid.UUID,
        admin_user: AdminUser,
    ) -> ReconciliationRunResponse:
        """Execute deterministic payment reconciliation against an imported bank statement file."""
        # 1. Fetch statement import and verify readiness
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

        # 2. Create initial ReconciliationRun entity in RUNNING state
        run = ReconciliationRun(
            statement_import_id=statement_import.id,
            initiated_by=admin_user.id,
            status="RUNNING",
            started_at=now_utc,
        )
        await self.reconciliation_repo.create_run(db, run)

        try:
            # 3. Fetch all bank transactions for statement import
            # We fetch all transactions for this import
            from sqlalchemy import select
            stmt = select(BankTransaction).where(BankTransaction.statement_import_id == statement_import.id).order_by(BankTransaction.id.asc())
            res = await db.execute(stmt)
            all_txs = list(res.scalars().all())

            # 4. Extract CREDIT transactions and reference IDs
            credit_txs = [tx for tx in all_txs if (tx.direction or "").upper() == "CREDIT"]
            debit_txs = [tx for tx in all_txs if (tx.direction or "").upper() != "CREDIT"]

            ref_ids = [tx.reference_id.strip() for tx in credit_txs if tx.reference_id and tx.reference_id.strip()]

            # Count reference occurrences among CREDIT transactions in this run (to detect duplicate reference submissions)
            ref_counts = Counter(ref_ids)

            # 5. Bulk lookup PaymentSessions (and active PaymentSubmissions) in O(N)
            payment_map = await self.payment_session_repo.get_by_reference_ids_bulk(db, ref_ids)

            # 6. Execute deterministic classification for each BankTransaction
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
                is_credit = (tx.direction or "").upper() == "CREDIT"
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
                        # Reference code unknown in DB
                        result_status = "UNKNOWN_REFERENCE"
                        reason_code = "UNKNOWN_REFERENCE"
                        explanation = f"No PaymentSession exists with reference code '{raw_ref}'."
                        ref_match = False
                        amt_match = None
                        utr_match = None
                        ps_id = None
                        sub_id = None
                        unknown_reference_count += 1
                    else:
                        ps, sub = payment_tuple
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

            # 7. Update run metrics and set COMPLETED
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
                filename=statement_import.filename,
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
        return ReconciliationRunResponse(
            public_id=run.public_id,
            statement_import_public_id=statement_import.public_id,
            filename=statement_import.filename,
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
        page: int = 1,
        page_size: int = 20,
    ) -> ReconciliationRunListResponse:
        """List paginated reconciliation runs."""
        statement_import_id = None
        if statement_import_public_id:
            imp_res = await self.statement_import_repo.get_by_public_id(db, statement_import_public_id)
            if imp_res:
                statement_import_id = imp_res[0].id


        items, total = await self.reconciliation_repo.list_runs_paginated(
            db, statement_import_id=statement_import_id, page=page, page_size=page_size
        )

        response_items = [
            ReconciliationRunResponse(
                public_id=run.public_id,
                statement_import_public_id=si.public_id,
                filename=si.filename,
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
            for run, si in items
        ]

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
