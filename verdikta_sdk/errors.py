"""Exception hierarchy for the Verdikta SDK."""

from typing import Any, Mapping, Optional


class VerdiktaError(Exception):
    """Base class for all SDK-specific exceptions."""


class NetworkError(VerdiktaError):
    """Raised when the SDK cannot reach the Verdikta API."""


class APIError(VerdiktaError):
    """Raised for non-2xx responses from the Verdikta API."""

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        payload: Optional[Mapping[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.payload = payload

    def __str__(self) -> str:
        if self.status_code is None:
            return self.message
        return f"HTTP {self.status_code}: {self.message}"


class AuthenticationError(APIError):
    """Raised when an API key is missing, invalid, or unauthorized."""


class NotFoundError(APIError):
    """Raised when a requested Verdikta resource does not exist."""


class RateLimitError(APIError):
    """Raised when the Verdikta API rate-limits the request."""


class ValidationError(APIError):
    """Raised when the Verdikta API rejects request input."""
