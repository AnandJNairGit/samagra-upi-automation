"""Public registration domain service for resolving batch availability and validating participants."""

import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.logging import logger
from app.repositories.batch_repository import BatchRepository
from app.schemas.public import (
    PublicBatchResponse,
    PublicRegistrationValidateRequest,
    PublicRegistrationValidateResponse,
)
from app.services.exceptions import PublicBatchUnavailableError


class PublicRegistrationService:
    """Handles public batch resolution and registration validation."""

    def __init__(self, batch_repo: Optional[BatchRepository] = None) -> None:
        self.batch_repo = batch_repo or BatchRepository()

    async def get_active_batch_by_public_id(
        self,
        db: AsyncSession,
        batch_public_id: uuid.UUID,
    ) -> PublicBatchResponse:
        """Resolve public batch information with strict availability enforcement.

        Availability Rule:
            Must exist, batch.status == 'ACTIVE', AND parent course.status == 'ACTIVE'.
            Otherwise, raises PublicBatchUnavailableError (404).
        """
        batch = await self.batch_repo.get_by_public_id_with_course(db, batch_public_id)

        if not batch or batch.status != "ACTIVE":
            logger.info(f"PUBLIC_BATCH_LOOKUP_FAILED: Batch [{batch_public_id}] not found or inactive.")
            raise PublicBatchUnavailableError("This registration link is no longer available.")

        if not batch.course or batch.course.status != "ACTIVE":
            logger.info(
                f"PUBLIC_BATCH_LOOKUP_FAILED: Parent course for batch [{batch_public_id}] "
                f"is missing or inactive/archived."
            )
            raise PublicBatchUnavailableError("This registration link is no longer available.")

        return PublicBatchResponse(
            public_id=batch.public_id,
            course_name=batch.course.name,
            batch_name=batch.name,
            amount_inr=batch.amount_inr,
            starts_at=batch.starts_at,
            ends_at=batch.ends_at,
        )

    async def validate_registration_context(
        self,
        db: AsyncSession,
        payload: PublicRegistrationValidateRequest,
    ) -> PublicRegistrationValidateResponse:
        """Validate participant submission against the authoritative batch state.

        Strict Phase Boundary:
            Derives authoritative course and amount from the database.
            Validates participant contact info.
            Does NOT create a payment session or generate UPI/QR references.
        """
        active_batch = await self.get_active_batch_by_public_id(db, payload.batch_public_id)

        return PublicRegistrationValidateResponse(
            batch_public_id=active_batch.public_id,
            course_name=active_batch.course_name,
            batch_name=active_batch.batch_name,
            amount_inr=active_batch.amount_inr,
            full_name=payload.full_name,
            phone=payload.phone,
            email=payload.email,
        )
