"""Domain and business logic exception definitions."""


class DomainError(Exception):
    """Base class for all domain errors."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class DuplicateUTRError(DomainError):
    """Raised when a submitted UTR already exists in the system."""

    def __init__(self, utr: str):
        super().__init__(f"UTR '{utr}' has already been submitted and must be unique.")
        self.utr = utr


class InvalidSessionStateError(DomainError):
    """Raised when a state transition is not allowed for the payment session."""

    def __init__(self, current_status: str, action: str, message: str = ""):
        msg = message or f"Cannot perform action '{action}' on payment session with status '{current_status}'."
        super().__init__(msg)
        self.current_status = current_status
        self.action = action


class SessionNotFoundError(DomainError):
    """Raised when a payment session is not found."""

    def __init__(self, identifier: str):
        super().__init__(f"Payment session '{identifier}' was not found.")
        self.identifier = identifier


class SubmissionNotFoundError(DomainError):
    """Raised when a payment submission is not found."""

    def __init__(self, identifier: str):
        super().__init__(f"Payment submission '{identifier}' was not found.")
        self.identifier = identifier


class AuthenticationError(DomainError):
    """Raised when admin authentication fails (generic message to avoid enumeration)."""

    def __init__(self, message: str = "Invalid email or password."):
        super().__init__(message)


class InactiveAdminError(DomainError):
    """Raised when an admin account is deactivated."""

    def __init__(self, message: str = "Administrator account is deactivated."):
        super().__init__(message)


class InvalidRefreshTokenError(DomainError):
    """Raised when a refresh token is missing, expired, revoked, or malformed."""

    def __init__(self, message: str = "Invalid or expired session."):
        super().__init__(message)


class RefreshTokenReplayError(DomainError):
    """Raised when an already rotated refresh token is re-submitted."""

    def __init__(self, message: str = "Session has been invalidated due to token reuse."):
        super().__init__(message)


class CourseNotFoundError(DomainError):
    """Raised when a course is not found."""

    def __init__(self, identifier: str):
        super().__init__(f"Course '{identifier}' was not found.")
        self.identifier = identifier


class BatchNotFoundError(DomainError):
    """Raised when a batch is not found."""

    def __init__(self, identifier: str):
        super().__init__(f"Batch '{identifier}' was not found.")
        self.identifier = identifier


class CourseArchivedError(DomainError):
    """Raised when an action is forbidden because the target or parent course is archived."""

    def __init__(self, message: str = "Course is archived and cannot be modified or receive new batches."):
        super().__init__(message)


class BatchArchivedError(DomainError):
    """Raised when an action is forbidden because the batch is archived."""

    def __init__(self, message: str = "Batch is archived and cannot be modified."):
        super().__init__(message)


class InvalidStateTransitionError(DomainError):
    """Raised when an entity lifecycle transition is invalid or forbidden."""

    def __init__(self, entity_type: str, current_status: str, target_status: str):
        super().__init__(
            f"Cannot transition {entity_type} from '{current_status}' to '{target_status}'."
        )
        self.entity_type = entity_type
        self.current_status = current_status
        self.target_status = target_status


class BatchCourseImmutableError(DomainError):
    """Raised when attempting to reassign a batch's course after payment sessions have been created."""

    def __init__(self, message: str = "Cannot reassign course for a batch with existing payment sessions."):
        super().__init__(message)


class InvalidDateRangeError(DomainError):
    """Raised when batch ends_at is before starts_at."""

    def __init__(self, message: str = "Batch end date (ends_at) must be on or after start date (starts_at)."):
        super().__init__(message)


class InvalidAmountError(DomainError):
    """Raised when an invalid monetary amount is provided."""

    def __init__(self, message: str = "Amount must be a positive integer in whole INR (amount_inr > 0)."):
        super().__init__(message)


class PublicBatchUnavailableError(DomainError):
    """Raised when a public registration batch is not found, inactive, archived, or parent course is inactive/archived."""

    def __init__(self, message: str = "This registration link is no longer available."):
        super().__init__(message)


class ParticipantValidationError(DomainError):
    """Raised when public participant registration details fail domain validation."""

    def __init__(self, message: str):
        super().__init__(message)


class PaymentSessionUnavailableError(DomainError):
    """Raised when a public payment session is not found or not available."""

    def __init__(self, message: str = "This payment session is no longer available."):
        super().__init__(message)


class PaymentSessionExpiredError(DomainError):
    """Raised when an operation is attempted on an expired payment session."""

    def __init__(self, message: str = "This payment session has expired."):
        super().__init__(message)


class ReconciliationRunNotFoundError(DomainError):
    """Raised when a reconciliation run is not found."""

    def __init__(self, identifier: str):
        super().__init__(f"Reconciliation run '{identifier}' was not found.")
        self.identifier = identifier


class ReconciliationResultNotFoundError(DomainError):
    """Raised when a reconciliation result is not found."""

    def __init__(self, identifier: str):
        super().__init__(f"Reconciliation result '{identifier}' was not found.")
        self.identifier = identifier


class StatementImportNotReadyError(DomainError):
    """Raised when a statement import is not found or not ready for reconciliation."""

    def __init__(self, message: str = "Statement import is not ready for reconciliation."):
        super().__init__(message)


class StatementImportInUseError(DomainError):
    """Raised when attempting to delete a statement import that has active reconciliation records."""

    def __init__(self, message: str = "Cannot delete statement import that has active reconciliation records."):
        super().__init__(message)


