"""
Base HTTP client with common session configuration.

This module provides the BaseHTTPClient class that encapsulates common HTTP
session setup, retry configuration, and request handling logic used by both
AuthClient and APIClient to eliminate code duplication.

Classes:
    BaseHTTPClient: Base class with common HTTP session configuration.

Example:
    >>> class MyClient(BaseHTTPClient):
    ...     def __init__(self):
    ...         super().__init__(domain="garmin.com", timeout=10)
    ...         self.session.headers.update({"Custom-Header": "value"})
"""

from typing import Dict, Optional

from requests import Session
from requests.adapters import HTTPAdapter, Retry

from .config import get_config, get_retryable_status_codes


class BaseHTTPClient:
    """Base HTTP client with common session configuration.

    This class provides the foundation for HTTP clients by encapsulating:
    - Session creation and configuration
    - Retry strategy setup
    - Common headers management
    - Base timeout handling

    Attributes:
        domain: Base domain for requests.
        timeout: Request timeout in seconds.
        session: Configured requests Session.
    """

    def __init__(
        self,
        domain: str = "garmin.com",
        timeout: Optional[int] = None,
        retries: Optional[int] = None,
        user_agent: Optional[str] = None,
    ):
        """Initialize the base HTTP client.

        Args:
            domain: Base domain for requests.
            timeout: Request timeout in seconds.
            retries: Number of retry attempts.
            user_agent: Custom user agent string. Uses default if None.
        """
        config = get_config()
        self.domain = domain
        self.timeout = timeout or config.request_timeout
        self.session = self._create_session(
            retries if retries is not None else config.retries, user_agent
        )

    def _create_session(self, retries: int, user_agent: Optional[str]) -> Session:
        """Create and configure HTTP session with standard settings.

        Args:
            retries: Number of retry attempts.
            user_agent: Custom user agent string.

        Returns:
            Configured requests Session.
        """
        session = Session()

        # Set default headers
        default_headers = self._get_default_headers(user_agent)
        session.headers.update(default_headers)

        # Configure retry strategy
        retry_strategy = self._create_retry_strategy(retries)
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def _get_default_headers(self, user_agent: Optional[str]) -> Dict[str, str]:
        """Get default headers for all requests.

        Args:
            user_agent: Custom user agent string.

        Returns:
            Dictionary of default headers.
        """
        from .config import get_user_agent

        return {
            "User-Agent": user_agent or get_user_agent("default"),
            "Accept": "application/json",
        }

    def _create_retry_strategy(self, retries: int) -> Retry:
        """Create retry strategy with standard configuration.

        Args:
            retries: Number of retry attempts.

        Returns:
            Configured Retry strategy.
        """
        config = get_config()
        return Retry(
            total=retries,
            status_forcelist=get_retryable_status_codes(),
            backoff_factor=config.backoff_factor,
        )

    def get_session(self) -> Session:
        """Get the configured HTTP session.

        Returns:
            Configured requests Session.
        """
        return self.session
