"""Payment submission service managing workflows, concurrency locking, and status synchronization."""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.payment_submission import PaymentSubmission
from app.repositories.payment_session_repository import PaymentSessionRepository
from app.repositories.payment_submission_repository import PaymentSubmissionRepository
from app.services.exceptions import (
    DuplicateUTRError,
    InvalidSessionStateError,
    SessionNotFoundError,
    SubmissionNotFoundError,
)


class PaymentSubmissionService:
    """Service handling UTR submissions and status lifecycle synchronization."""

    def __init__(
        self,
        session_repo: Optional[PaymentSessionRepository] = None,
        submission_repo: Optional[PaymentSubmissionRepository] = None,
    ):
        self.session_repo = session_repo or PaymentSessionRepository()
        self.submission_repo = submission_repo or PaymentSubmissionRepository()

    async def submit_utr(
        self,
        db: AsyncSession,
        payment_session_id: int,
        utr: str,
    ) -> PaymentSubmission:
        """Submit a UTR for a payment session with concurrency locking (SELECT FOR UPDATE)."""
        clean_utr = utr.strip()
        if not clean_utr:
            raise ValueError("UTR cannot be empty or whitespace only.")

        # 1. Lock payment session row
        payment_session = await self.session_repo.get_by_id_for_update(
            db, payment_session_id
        )
        if not payment_session:
            raise SessionNotFoundError(str(payment_session_id))

        # 2. Validate legal transition: only PENDING or REJECTED sessions can accept UTR submissions
        if payment_session.status not in ("PENDING", "REJECTED"):
            raise InvalidSessionStateError(
                current_status=payment_session.status,
                action="submit_utr",
            )

        # 3. Deactivate existing current submission for this session
        await self.submission_repo.deactivate_current_for_session(db, payment_session_id)

        # 4. Create new current submission
        new_submission = PaymentSubmission(
            payment_session_id=payment_session_id,
            utr=clean_utr,
            status="SUBMITTED",
            is_current=True,
        )

        try:
            await self.submission_repo.create(db, new_submission)
        except IntegrityError as exc:
            # Check if failure is due to UTR uniqueness constraint
            if "ux_payment_submissions_utr" in str(exc) or "utr" in str(exc).lower():
                raise DuplicateUTRError(clean_utr) from exc
            raise

        # 5. Synchronize payment session status to SUBMITTED
        payment_session.status = "SUBMITTED"
        await self.session_repo.update(db, payment_session)

        return new_submission

    async def approve_submission(
        self,
        db: AsyncSession,
        submission_id: int,
        admin_id: int,
    ) -> PaymentSubmission:
        """Approve a current submission and synchronize payment session to APPROVED with row locking."""
        # 1. Lock submission row
        submission = await self.submission_repo.get_by_id_for_update(db, submission_id)
        if not submission:
            raise SubmissionNotFoundError(str(submission_id))

        # 2. Validate submission state
        if submission.status not in ("SUBMITTED", "REVIEW_REQUIRED"):
            raise InvalidSessionStateError(
                current_status=submission.status,
                action="approve_submission",
            )

        # 3. Lock parent session row
        payment_session = await self.session_repo.get_by_id_for_update(
            db, submission.payment_session_id
        )
        if not payment_session:
            raise SessionNotFoundError(str(submission.payment_session_id))

        # 4. Validate session state
        if payment_session.status not in ("SUBMITTED", "REVIEW_REQUIRED"):
            raise InvalidSessionStateError(
                current_status=payment_session.status,
                action="approve_submission",
            )

        now_utc = datetime.now(timezone.utc)
        submission.status = "APPROVED"
        submission.reviewed_by = admin_id
        submission.reviewed_at = now_utc
        await self.submission_repo.update(db, submission)

        payment_session.status = "APPROVED"
        await self.session_repo.update(db, payment_session)

        return submission

    async def reject_submission(
        self,
        db: AsyncSession,
        submission_id: int,
        admin_id: int,
        reason: Optional[str] = None,
    ) -> PaymentSubmission:
        """Reject a current submission and synchronize payment session to REJECTED with row locking."""
        # 1. Lock submission row
        submission = await self.submission_repo.get_by_id_for_update(db, submission_id)
        if not submission:
            raise SubmissionNotFoundError(str(submission_id))

        # 2. Validate submission state
        if submission.status not in ("SUBMITTED", "REVIEW_REQUIRED"):
            raise InvalidSessionStateError(
                current_status=submission.status,
                action="reject_submission",
            )

        # 3. Lock parent session row
        payment_session = await self.session_repo.get_by_id_for_update(
            db, submission.payment_session_id
        )
        if not payment_session:
            raise SessionNotFoundError(str(submission.payment_session_id))

        # 4. Validate session state
        if payment_session.status not in ("SUBMITTED", "REVIEW_REQUIRED"):
            raise InvalidSessionStateError(
                current_status=payment_session.status,
                action="reject_submission",
            )

        now_utc = datetime.now(timezone.utc)
        submission.status = "REJECTED"
        submission.reviewed_by = admin_id
        submission.reviewed_at = now_utc
        submission.rejection_reason = reason
        await self.submission_repo.update(db, submission)

        payment_session.status = "REJECTED"
        await self.session_repo.update(db, payment_session)

        return submission
