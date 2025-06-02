"""
Unified exception hierarchy for the Garmin Connect API client.

This module defines a comprehensive exception hierarchy used throughout the garmy library
to handle various error conditions consistently. All custom exceptions inherit from GarmyError.

Exception Hierarchy:
    GarmyError (base)
    ├── AuthError (authentication-related)
    │   ├── LoginError
    │   ├── MFARequiredError
    │   └── TokenExpiredError
    ├── APIError (HTTP request failures)
    ├── DiscoveryError (metric discovery)
    ├── FactoryError (accessor creation)
    ├── EndpointBuilderError (endpoint building)
    ├── MetricDataError (data parsing)
    └── ValidationError (data validation)

Example:
    >>> try:
    ...     client.connectapi("/invalid-endpoint")
    ... except APIError as e:
    ...     print(f"API request failed: {e}")
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from requests import HTTPError


@dataclass
class GarmyError(Exception):
    """Base exception for all Garmy exceptions.

    This is the base class for all custom exceptions in the garmy library.
    All other custom exceptions should inherit from this class.

    Args:
        msg: Descriptive error message explaining what went wrong.

    Attributes:
        msg: The error message string.
    """

    msg: str

    def __str__(self) -> str:
        """Return the error message as the string representation.

        Returns:
            The error message string.
        """
        return self.msg


@dataclass
class APIError(GarmyError):
    """Exception raised for HTTP API request failures.

    This exception is raised when HTTP requests to the Garmin Connect API
    fail due to network issues, authentication problems, or server errors.

    Args:
        msg: Descriptive error message.
        error: The underlying HTTPError that caused this exception.

    Attributes:
        msg: The error message string.
        error: The original HTTPError instance.
    """

    error: "HTTPError"

    def __str__(self) -> str:
        """Return a formatted error message including the HTTP error.

        Returns:
            Formatted string combining the error message and HTTP error details.
        """
        return f"{self.msg}: {self.error}"


# Authentication-related exceptions
class AuthError(GarmyError):
    """Base class for authentication-related errors."""

    pass


class LoginError(AuthError):
    """Error during login process."""

    pass


class MFARequiredError(AuthError):
    """Multi-factor authentication is required."""

    pass


class TokenExpiredError(AuthError):
    """Authentication token has expired."""

    pass


class DiscoveryError(GarmyError):
    """Metric discovery and validation errors."""

    pass


class FactoryError(GarmyError):
    """Metric accessor factory errors."""

    pass


class EndpointBuilderError(GarmyError):
    """Endpoint building errors."""

    pass


# Data processing exceptions
class MetricDataError(GarmyError):
    """Metric data parsing or processing errors."""

    pass


class ValidationError(GarmyError):
    """Data validation errors."""

    pass
