"""Python SDK for the Verdikta Bounties API."""

from .client import VerdiktaClient
from .errors import (
    APIError,
    AuthenticationError,
    NetworkError,
    NotFoundError,
    RateLimitError,
    ValidationError,
    VerdiktaError,
)

__all__ = [
    "VerdiktaClient",
    "VerdiktaError",
    "APIError",
    "AuthenticationError",
    "NetworkError",
    "NotFoundError",
    "RateLimitError",
    "ValidationError",
]

__version__ = "0.1.0"
