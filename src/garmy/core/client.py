"""
API Client for Garmin Connect API requests.

This module provides the main HTTP client for making authenticated requests
to the Garmin Connect API. It handles authentication, retries, and response
parsing while being separate from the authentication logic itself.

Classes:
    APIClient: Main HTTP client for API requests with authentication support.

Example:
    >>> from garmy.auth import AuthClient
    >>> from garmy.core import APIClient
    >>>
    >>> auth = AuthClient()
    >>> client = APIClient(auth_client=auth)
    >>> client.login("email@example.com", "password")
    >>> profile = client.get_user_profile()
"""

import json
from typing import TYPE_CHECKING, Any, Dict, Optional, Union

if TYPE_CHECKING:
    from ..auth.client import AuthClient
    from .registry import MetricRegistry

from urllib.parse import urljoin

from requests import HTTPError, Response

from .config import HTTPStatus, get_user_agent
from .exceptions import APIError
from .http_client import BaseHTTPClient


class HttpClientCore(BaseHTTPClient):
    """Core HTTP client handling requests, retries, and session management.

    This class extends BaseHTTPClient with API-specific configuration:
    - iOS app user agent for better API compatibility
    - URL building utilities for Garmin subdomains
    - API request execution with error handling
    """

    def __init__(
        self,
        domain: str = "garmin.com",
        timeout: Optional[int] = None,
        retries: Optional[int] = None,
    ):
        """Initialize the HTTP client core.

        Args:
            domain: Base domain for requests.
            timeout: Request timeout in seconds.
            retries: Number of retry attempts.
        """
        # Use BaseHTTPClient with iOS app user agent
        super().__init__(
            domain=domain,
            timeout=timeout,
            retries=retries,
            user_agent=get_user_agent("ios"),
        )

    def build_url(self, subdomain: str, path: str) -> str:
        """Build full URL from subdomain and path.

        Args:
            subdomain: Garmin subdomain (e.g., 'connectapi', 'connect').
            path: API endpoint path.

        Returns:
            Complete URL string.
        """
        base_url = f"https://{subdomain}.{self.domain}"
        return urljoin(base_url, path)

    def execute_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> Response:
        """Execute HTTP request with configured session.

        Args:
            method: HTTP method (GET, POST, etc.).
            url: Complete URL to request.
            headers: Optional headers to include.
            **kwargs: Additional arguments for requests.

        Returns:
            HTTP response object.

        Raises:
            APIError: If the HTTP request fails.
        """
        # Merge headers
        request_headers = headers or {}

        # Set default timeout
        kwargs.setdefault("timeout", self.timeout)

        try:
            resp = self.session.request(method, url, headers=request_headers, **kwargs)
            resp.raise_for_status()
            return resp
        except HTTPError as e:
            raise APIError(msg="HTTP request failed", error=e) from e


class AuthenticationDelegate:
    """Handles authentication-related operations and state.

    This class is responsible solely for authentication concerns:
    - Authentication state checking
    - Auth header generation
    - Authentication delegation to auth client
    """

    def __init__(
        self, auth_client: Optional["AuthClient"] = None, domain: str = "garmin.com"
    ):
        """Initialize the authentication delegate.

        Args:
            auth_client: Optional authentication client.
            domain: Domain for creating auth client if none provided.
        """
        if auth_client is None:
            from ..auth.client import AuthClient

            self.auth_client = AuthClient(domain=domain)
        else:
            self.auth_client = auth_client

    def is_authenticated(self) -> bool:
        """Check if currently authenticated.

        Returns:
            True if authenticated, False otherwise.
        """
        return self.auth_client.is_authenticated

    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for API requests.

        Returns:
            Dictionary of authentication headers.
        """
        return self.auth_client.get_auth_headers()

    def login(self, email: str, password: str, **kwargs: Any) -> Any:
        """Delegate login to the authentication client.

        Args:
            email: User email address.
            password: User password.
            **kwargs: Additional arguments for auth client.

        Returns:
            Login response from auth client.
        """
        return self.auth_client.login(email, password, **kwargs)

    def logout(self) -> Any:
        """Delegate logout to the authentication client.

        Returns:
            Logout response from auth client.
        """
        return self.auth_client.logout()


class APIClient:
    """Orchestrates API requests using composition of specialized components.

    This class uses the Single Responsibility Principle by delegating specific
    tasks to specialized components:
    - HttpClientCore: Handles HTTP mechanics (sessions, retries, requests)
    - AuthenticationDelegate: Handles authentication concerns (auth state, headers)

    The APIClient now acts as an orchestrator providing a clean interface for
    Garmin Connect API operations while maintaining separation of concerns.

    Args:
        auth_client: Optional authentication client instance.
        domain: Base domain for Garmin services. Defaults to "garmin.com".
        timeout: Request timeout in seconds. Defaults to 10.
        retries: Number of retry attempts for failed requests. Defaults to 3.

    Attributes:
        http_client: Component handling HTTP requests and session management.
        auth_delegate: Component handling authentication concerns.
        domain: The base domain for API requests.

    Example:
        >>> client = APIClient(timeout=30, retries=5)
        >>> client.login("email@example.com", "password")
        >>> data = client.connectapi("/userprofile-service/userprofile")
    """

    def __init__(
        self,
        auth_client: Optional["AuthClient"] = None,
        domain: str = "garmin.com",
        timeout: Optional[int] = None,
        retries: Optional[int] = None,
    ) -> None:
        """Initialize the API client with composed components.

        Args:
            auth_client: Optional authentication client. If None, creates new AuthClient.
            domain: Base domain for Garmin services.
            timeout: Request timeout in seconds.
            retries: Number of retry attempts for failed requests.
        """
        self.domain = domain

        # Compose with specialized components following SRP
        self.http_client = HttpClientCore(domain, timeout, retries)
        self.auth_delegate = AuthenticationDelegate(auth_client, domain)

    @property
    def is_authenticated(self) -> bool:
        """Check if the client is authenticated.

        Delegates to the authentication component.

        Returns:
            True if the client has valid authentication credentials, False otherwise.
        """
        return self.auth_delegate.is_authenticated()

    @property
    def username(self) -> str:
        """Get the username from the user profile.

        Returns:
            The username string, or "Unknown" if unable to retrieve.

        Raises:
            APIError: If the user profile request fails.
        """
        profile = self.get_user_profile()
        username = profile.get("userName", "Unknown")
        return str(username) if username is not None else "Unknown"

    @property
    def profile(self) -> Dict[str, Any]:
        """Get the complete user profile.

        Returns:
            Dictionary containing user profile information.

        Raises:
            APIError: If the user profile request fails.
        """
        return self.get_user_profile()

    @property
    def metrics(self) -> "MetricRegistry":
        """
        Get the metric registry with all available metrics.

        Provides lazy-loaded access to all Garmin Connect metrics through
        a simple, unified interface. Metrics are discovered and created
        automatically on first access.

        Returns:
            MetricRegistry instance with access to all metrics

        Example:
            >>> client = APIClient(auth_client=auth)
            >>> sleep_data = client.metrics.get("sleep").get()
            >>> steps_data = client.metrics["steps"].get()
            >>> print("Available:", list(client.metrics.keys()))
        """
        if not hasattr(self, "_metrics"):
            from .registry import MetricRegistry

            self._metrics = MetricRegistry(self)
        return self._metrics

    def get_user_profile(self) -> Dict[str, Any]:
        """Get user profile information from the API.

        Returns:
            Dictionary containing user profile data including username,
            display name, locale, and other profile information.
            Returns empty dict if the API request fails.
        """
        try:
            result = self.connectapi("/userprofile-service/socialProfile")
            if isinstance(result, dict):
                return result
            else:
                # Return empty dict for non-dict responses
                return {}
        except APIError:
            # Return empty dict on API errors
            return {}

    def request(
        self, method: str, subdomain: str, path: str, api: bool = False, **kwargs: Any
    ) -> Response:
        """Make HTTP request to a Garmin API endpoint.

        Coordinates between HTTP client and authentication components.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.).
            subdomain: Garmin subdomain (e.g., 'connectapi', 'connect').
            path: API endpoint path.
            api: Whether to include authentication headers.
            **kwargs: Additional arguments passed to requests.Session.request().

        Returns:
            HTTP response object.

        Raises:
            APIError: If the HTTP request fails or returns an error status.
        """
        # Use HTTP client to build URL
        url = self.http_client.build_url(subdomain, path)

        # Get authentication headers if needed
        headers = kwargs.get("headers", {})
        if api:
            auth_headers = self.auth_delegate.get_auth_headers()
            headers.update(auth_headers)

        # Delegate to HTTP client for execution
        return self.http_client.execute_request(method, url, headers, **kwargs)

    def connectapi(
        self, path: str, method: str = "GET", **kwargs: Any
    ) -> Union[Dict[str, Any], str, None]:
        """Make request to the connectapi subdomain and return parsed JSON.

        Args:
            path: API endpoint path.
            method: HTTP method. Defaults to "GET".
            **kwargs: Additional arguments passed to the request method.

        Returns:
            Parsed JSON response as a dictionary, response text for non-JSON
            responses, or None for 204 No Content responses.

        Raises:
            APIError: If the API request fails.
        """
        resp = self.request(method, "connectapi", path, api=True, **kwargs)

        if resp.status_code == HTTPStatus.NO_CONTENT:
            return None

        try:
            json_result: Union[Dict[str, Any], str, None] = resp.json()
            return json_result
        except json.JSONDecodeError:
            text_result: str = resp.text
            return text_result

    def graphql(
        self, query: str, variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a GraphQL query against Garmin Connect.

        Args:
            query: GraphQL query string.
            variables: Optional variables for the GraphQL query.

        Returns:
            Dictionary containing the GraphQL response data.

        Raises:
            APIError: If the GraphQL request fails.
        """
        payload = {"query": query, "variables": variables or {}}

        resp = self.request(
            "POST", "connect", "/graphql-gateway/graphql", api=True, json=payload
        )
        result = resp.json()
        if isinstance(result, dict):
            return result
        else:
            # Create a mock HTTPError for the APIError
            from requests import HTTPError

            mock_error = HTTPError("Invalid response type from GraphQL API")
            raise APIError(
                msg="Expected dict from GraphQL API but got: " + str(type(result)),
                error=mock_error,
            )

    def login(self, email: str, password: str, **kwargs: Any) -> Any:
        """Login using the authentication delegate.

        Delegates authentication operations to the authentication component.

        Args:
            email: User email address.
            password: User password.
            **kwargs: Additional arguments passed to the auth client login method.

        Returns:
            Login response from the authentication client.

        Raises:
            GarmyError: If login fails.
        """
        return self.auth_delegate.login(email, password, **kwargs)

    def logout(self) -> Any:
        """Logout using the authentication delegate.

        Delegates authentication operations to the authentication component.

        Returns:
            Logout response from the authentication client.
        """
        return self.auth_delegate.logout()
