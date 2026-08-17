"""Services package exports."""

from app.services.exceptions import (
    AuthenticationError,
    BatchArchivedError,
    BatchCourseImmutableError,
    BatchNotFoundError,
    CourseArchivedError,
    CourseNotFoundError,
    DomainError,
    DuplicateUTRError,
    InactiveAdminError,
    InvalidAmountError,
    InvalidDateRangeError,
    InvalidRefreshTokenError,
    InvalidSessionStateError,
    InvalidStateTransitionError,
    ParticipantValidationError,
    PaymentSessionExpiredError,
    PaymentSessionUnavailableError,
    PublicBatchUnavailableError,
    RefreshTokenReplayError,
    SessionNotFoundError,
    SubmissionNotFoundError,
)
from app.services.admin_payment_service import AdminPaymentService
from app.services.auth_service import AuthService
from app.services.batch_service import BatchService
from app.services.course_service import CourseService
from app.services.payment_session_service import PaymentSessionService
from app.services.payment_submission_service import PaymentSubmissionService
from app.services.public_registration_service import PublicRegistrationService
from app.services.upi_service import build_upi_uri, generate_reference_id
from app.services.whatsapp_service import (
    build_whatsapp_admin_url,
    format_whatsapp_admin_message,
    mask_utr,
)

__all__ = [
    "DomainError",
    "DuplicateUTRError",
    "InvalidSessionStateError",
    "SessionNotFoundError",
    "SubmissionNotFoundError",
    "AuthenticationError",
    "InactiveAdminError",
    "InvalidRefreshTokenError",
    "RefreshTokenReplayError",
    "CourseNotFoundError",
    "BatchNotFoundError",
    "CourseArchivedError",
    "BatchArchivedError",
    "InvalidStateTransitionError",
    "BatchCourseImmutableError",
    "InvalidDateRangeError",
    "InvalidAmountError",
    "PublicBatchUnavailableError",
    "ParticipantValidationError",
    "PaymentSessionUnavailableError",
    "PaymentSessionExpiredError",
    "AuthService",
    "AdminPaymentService",
    "PaymentSubmissionService",
    "PaymentSessionService",
    "CourseService",
    "BatchService",
    "PublicRegistrationService",
    "generate_reference_id",
    "build_upi_uri",
    "build_whatsapp_admin_url",
    "format_whatsapp_admin_message",
    "mask_utr",
]

