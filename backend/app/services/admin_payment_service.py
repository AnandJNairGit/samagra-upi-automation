"""Admin payment dashboard and inspection service."""

import math
import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.batch_repository import BatchRepository
from app.repositories.course_repository import CourseRepository
from app.repositories.payment_session_repository import PaymentSessionRepository
from app.repositories.payment_submission_repository import PaymentSubmissionRepository
from app.schemas.admin_payment import (
    AdminDashboardSummaryResponse,
    AdminPaymentDetailParticipant,
    AdminPaymentDetailPayment,
    AdminPaymentDetailResponse,
    AdminPaymentDetailSubmission,
    AdminPaymentDetailTraining,
    AdminPaymentListItem,
    AdminPaymentListResponse,
)
from app.services.exceptions import PaymentSessionUnavailableError

ALLOWED_PAYMENT_STATUSES = {
    "PENDING",
    "SUBMITTED",
    "REVIEW_REQUIRED",
    "APPROVED",
    "REJECTED",
    "EXPIRED",
}


class AdminPaymentService:
    """Read-only administrative service for payment metrics, search, and detail inspection."""

    def __init__(
        self,
        session_repo: Optional[PaymentSessionRepository] = None,
        submission_repo: Optional[PaymentSubmissionRepository] = None,
        course_repo: Optional[CourseRepository] = None,
        batch_repo: Optional[BatchRepository] = None,
    ):
        self.session_repo = session_repo or PaymentSessionRepository()
        self.submission_repo = submission_repo or PaymentSubmissionRepository()
        self.course_repo = course_repo or CourseRepository()
        self.batch_repo = batch_repo or BatchRepository()

    async def get_dashboard_summary(
        self, db: AsyncSession
    ) -> AdminDashboardSummaryResponse:
        """Calculate aggregate payment metrics for the admin console."""
        summary_data = await self.session_repo.get_dashboard_summary(db)
        return AdminDashboardSummaryResponse(**summary_data)

    async def list_payments(
        self,
        db: AsyncSession,
        status: Optional[str] = None,
        course_public_id: Optional[uuid.UUID] = None,
        batch_public_id: Optional[uuid.UUID] = None,
        search: Optional[str] = None,
        reference_id: Optional[str] = None,
        utr: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> AdminPaymentListResponse:
        """Fetch paginated, filtered, and searchable payment sessions for administrative view."""
        # Sanitize & bound pagination
        page = max(1, page)
        page_size = max(1, min(100, page_size))

        # Validate status if supplied
        clean_status = status.strip().upper() if status and status.strip() else None
        if clean_status and clean_status not in ALLOWED_PAYMENT_STATUSES:
            raise ValueError(f"Invalid payment status filter: '{status}'")

        # Resolve public UUIDs to internal IDs
        course_id = None
        if course_public_id:
            course = await self.course_repo.get_by_public_id(db, course_public_id)
            if not course:
                return AdminPaymentListResponse(
                    items=[], page=page, page_size=page_size, total=0, total_pages=0
                )
            course_id = course.id

        batch_id = None
        if batch_public_id:
            batch = await self.batch_repo.get_by_public_id(db, batch_public_id)
            if not batch:
                return AdminPaymentListResponse(
                    items=[], page=page, page_size=page_size, total=0, total_pages=0
                )
            batch_id = batch.id

        items_tuples, total = await self.session_repo.list_admin_payments(
            session=db,
            status=clean_status,
            course_id=course_id,
            batch_id=batch_id,
            search=search,
            reference_id=reference_id,
            utr=utr,
            page=page,
            page_size=page_size,
        )

        list_items = []
        for ps, course_obj, batch_obj, current_sub in items_tuples:
            item = AdminPaymentListItem(
                payment_session_public_id=ps.public_id,
                participant_name=ps.full_name,
                phone=ps.phone,
                email=ps.email,
                course_public_id=course_obj.public_id,
                course_name=ps.course_name_snapshot,
                batch_public_id=batch_obj.public_id,
                batch_name=ps.batch_name_snapshot,
                amount_inr=ps.amount_inr,
                reference_id=ps.reference_id,
                payment_session_status=ps.status,
                utr=current_sub.utr if current_sub else None,
                submission_status=current_sub.status if current_sub else None,
                submitted_at=current_sub.submitted_at if current_sub else None,
                created_at=ps.created_at,
            )
            list_items.append(item)

        total_pages = math.ceil(total / page_size) if total > 0 else 0

        return AdminPaymentListResponse(
            items=list_items,
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
        )

    async def get_payment_detail(
        self, db: AsyncSession, payment_session_public_id: uuid.UUID
    ) -> AdminPaymentDetailResponse:
        """Fetch complete read-only payment detail including historical snapshots and submission history."""
        tuple_res = await self.session_repo.get_admin_payment_detail_by_public_id(
            db, payment_session_public_id
        )
        if not tuple_res:
            raise PaymentSessionUnavailableError("Payment record not found.")

        ps, course_obj, batch_obj = tuple_res

        # Fetch current submission and historical submission records
        current_sub = await self.submission_repo.get_current_for_session(db, ps.id)
        all_subs = await self.submission_repo.list_by_session_id(db, ps.id)

        current_sub_schema = (
            AdminPaymentDetailSubmission.model_validate(current_sub)
            if current_sub
            else None
        )
        history_schemas = [
            AdminPaymentDetailSubmission.model_validate(sub) for sub in all_subs
        ]

        return AdminPaymentDetailResponse(
            payment_session_public_id=ps.public_id,
            participant=AdminPaymentDetailParticipant(
                full_name=ps.full_name,
                phone=ps.phone,
                email=ps.email,
            ),
            training=AdminPaymentDetailTraining(
                course_public_id=course_obj.public_id,
                course_name=ps.course_name_snapshot,
                batch_public_id=batch_obj.public_id,
                batch_name=ps.batch_name_snapshot,
            ),
            payment=AdminPaymentDetailPayment(
                amount_inr=ps.amount_inr,
                reference_id=ps.reference_id,
                upi_id_snapshot=ps.upi_id_snapshot,
                payee_name_snapshot=ps.payee_name_snapshot,
                upi_uri=ps.upi_uri,
                status=ps.status,
                created_at=ps.created_at,
                expires_at=ps.expires_at,
            ),
            current_submission=current_sub_schema,
            submission_history=history_schemas,
        )
