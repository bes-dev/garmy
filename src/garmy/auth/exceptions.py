"""Authentication exceptions for Garmin Connect authentication.

This module provides backward compatibility for authentication exceptions
while using the unified exception hierarchy from core.exceptions.

All exceptions now inherit from the unified GarmyError hierarchy for consistency.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from requests import HTTPError

from ..core.exceptions import AuthError, LoginError, MFARequiredError, TokenExpiredError


@dataclass
class AuthHTTPError(AuthError):
    """HTTP related authentication errors.

    Raised when HTTP requests during authentication fail.

    Attributes:
        msg: Error message describing the failure
        error: The underlying HTTPError that caused this exception
    """

    error: "HTTPError"

    def __str__(self) -> str:
        """Return formatted error message with HTTP error details.

        Returns:
            Formatted string combining message and HTTP error
        """
        return f"{self.msg}: {self.error}"


# Re-export unified exceptions for backward compatibility
__all__ = [
    "AuthError",
    "AuthHTTPError",
    "LoginError",
    "MFARequiredError",
    "TokenExpiredError",
]
