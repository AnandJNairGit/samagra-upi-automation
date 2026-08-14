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

    def __init__(self, current_status: str, action: str):
        super().__init__(
            f"Cannot perform action '{action}' on payment session with status '{current_status}'."
        )
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
