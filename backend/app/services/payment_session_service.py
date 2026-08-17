"""Payment session domain service for Phase 6 checkout initiation and lookup."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.logging import logger
from app.models.payment_session import PaymentSession
from app.repositories.batch_repository import BatchRepository
from app.repositories.payment_session_repository import PaymentSessionRepository
from app.repositories.payment_submission_repository import PaymentSubmissionRepository
from app.schemas.payment_session import (
    PaymentSessionCreateRequest,
    PaymentSessionPublicResponse,
)
from app.services.exceptions import (
    PaymentSessionUnavailableError,
    PublicBatchUnavailableError,
)
from app.services.upi_service import build_upi_uri, generate_reference_id


class PaymentSessionService:
    """Domain service managing checkout session creation and public lookup."""

    def __init__(
        self,
        session_repo: Optional[PaymentSessionRepository] = None,
        batch_repo: Optional[BatchRepository] = None,
        submission_repo: Optional[PaymentSubmissionRepository] = None,
    ) -> None:
        self.session_repo = session_repo or PaymentSessionRepository()
        self.batch_repo = batch_repo or BatchRepository()
        self.submission_repo = submission_repo or PaymentSubmissionRepository()

    async def create_payment_session(
        self,
        db: AsyncSession,
        payload: PaymentSessionCreateRequest,
    ) -> PaymentSessionPublicResponse:
        """Create a new PaymentSession after re-validating active cohort availability.

        Financial & Snapshot Invariants:
            - Validates batch.status == 'ACTIVE' AND batch.course.status == 'ACTIVE'.
            - Derives authoritative amount_inr from batch.amount_inr.
            - Stores immutable snapshots of course name, batch name, amount, UPI ID, payee name, and UPI URI.
            - Initial status is strictly 'PENDING'.
            - Never creates PaymentSubmission records.
        """
        # 1. Authoritative Batch & Course Resolution
        batch = await self.batch_repo.get_by_public_id_with_course(db, payload.batch_public_id)
        if not batch or batch.status != "ACTIVE":
            logger.info(f"PAYMENT_SESSION_CREATION_FAILED: Batch [{payload.batch_public_id}] not found or inactive.")
            raise PublicBatchUnavailableError("This registration link is no longer available.")

        if not batch.course or batch.course.status != "ACTIVE":
            logger.info(
                f"PAYMENT_SESSION_CREATION_FAILED: Parent course for batch [{payload.batch_public_id}] "
                f"is inactive or missing."
            )
            raise PublicBatchUnavailableError("This registration link is no longer available.")

        # 2. Derive Authoritative Financial & UPI Data
        amount_inr = batch.amount_inr
        course_name_snapshot = batch.course.name
        batch_name_snapshot = batch.name
        upi_id_snapshot = settings.UPI_ID
        payee_name_snapshot = settings.UPI_PAYEE_NAME

        # 3. Calculate Expiration (if configured > 0)
        now_utc = datetime.now(timezone.utc)
        expires_at: Optional[datetime] = None
        if settings.PAYMENT_SESSION_EXPIRE_MINUTES > 0:
            expires_at = now_utc + timedelta(minutes=settings.PAYMENT_SESSION_EXPIRE_MINUTES)

        # 4. Generate Reference ID with safe bounded retry on collision
        max_attempts = 3
        payment_session = None

        for attempt in range(max_attempts):
            reference_id = generate_reference_id(payload.full_name, payload.phone)
            upi_uri = build_upi_uri(
                upi_id=upi_id_snapshot,
                payee_name=payee_name_snapshot,
                amount_inr=amount_inr,
                reference_id=reference_id,
            )

            candidate = PaymentSession(
                full_name=payload.full_name,
                phone=payload.phone,
                email=payload.email,
                course_id=batch.course.id,
                batch_id=batch.id,
                course_name_snapshot=course_name_snapshot,
                batch_name_snapshot=batch_name_snapshot,
                amount_inr=amount_inr,
                reference_id=reference_id,
                upi_id_snapshot=upi_id_snapshot,
                payee_name_snapshot=payee_name_snapshot,
                upi_uri=upi_uri,
                status="PENDING",
                expires_at=expires_at,
            )

            try:
                payment_session = await self.session_repo.create(db, candidate)
                break
            except IntegrityError as exc:
                # Handle unique reference_id collision safely
                logger.warning(
                    f"PAYMENT_REF_COLLISION: Collision on reference_id [{reference_id}], "
                    f"attempt {attempt + 1}/{max_attempts}."
                )
                await db.rollback()
                if attempt == max_attempts - 1:
                    logger.error(f"PAYMENT_REF_EXHAUSTED: Failed to generate unique reference ID after {max_attempts} attempts.")
                    raise RuntimeError("Unable to generate unique payment reference. Please try again.") from exc

        if not payment_session:
            raise RuntimeError("Unable to create payment session. Please try again.")

        logger.info(
            f"PAYMENT_SESSION_CREATED: Public ID [{payment_session.public_id}], "
            f"Ref [{payment_session.reference_id}], Amount [₹{payment_session.amount_inr}]."
        )
        return PaymentSessionPublicResponse.from_orm_model(payment_session)

    async def get_public_payment_session(
        self,
        db: AsyncSession,
        session_public_id: uuid.UUID,
    ) -> PaymentSessionPublicResponse:
        """Fetch safe public payment session representation for rendering the payment page."""
        session = await self.session_repo.get_by_public_id(db, session_public_id)
        if not session:
            logger.info(f"PAYMENT_SESSION_LOOKUP_FAILED: Session [{session_public_id}] not found.")
            raise PaymentSessionUnavailableError("This payment session is no longer available.")

        current_submission = None
        if session.status == "SUBMITTED":
            current_submission = await self.submission_repo.get_current_for_session(db, session.id)

        return PaymentSessionPublicResponse.from_orm_model(session, current_submission=current_submission)
