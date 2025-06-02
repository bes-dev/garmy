"""Garmin Connect SSO authentication module.

This module provides self-contained authentication logic for Garmin Connect's
Single Sign-On (SSO) system. It handles the complete OAuth1/OAuth2 flow including:
- Initial login with email/password
- Multi-factor authentication (MFA) support
- Token exchange and management
- Session management for authentication requests

The module implements Garmin's specific SSO protocol which involves:
1. Initial SSO embed page request
2. CSRF token extraction
3. Login form submission
4. Optional MFA handling
5. OAuth1 token retrieval
6. OAuth2 token exchange
"""

import re
import time
from typing import TYPE_CHECKING, Any, Callable, Dict, Literal, Optional, Tuple, Union
from urllib.parse import parse_qs, urljoin

if TYPE_CHECKING:
    from requests import Session

    from .client import AuthClient

import requests
from requests_oauthlib import OAuth1Session

from ..core.config import get_user_agent
from .exceptions import AuthError, LoginError
from .tokens import OAuth1Token, OAuth2Token

# Regex patterns for parsing HTML responses
CSRF_RE = re.compile(r'name="_csrf"\s+value="(.+?)"')
TITLE_RE = re.compile(r"<title>(.+?)</title>")

# User agent for mobile app impersonation - use from config
USER_AGENT = {"User-Agent": get_user_agent("android")}


class GarminOAuth1Session(OAuth1Session):
    """OAuth1 session for Garmin Connect authentication.

    Extends requests-oauthlib's OAuth1Session with Garmin-specific configuration.
    Automatically loads OAuth consumer credentials and inherits session settings
    from a parent session if provided.

    Attributes:
        All attributes from OAuth1Session plus Garmin consumer key/secret
    """

    def __init__(self, parent: Optional["Session"] = None, **kwargs: Any) -> None:
        """Initialize OAuth1 session with Garmin consumer credentials.

        Args:
            parent: Optional parent Session to inherit settings from
            **kwargs: Additional arguments passed to OAuth1Session
        """
        oauth_consumer = self._get_oauth_consumer_safe()

        super().__init__(
            oauth_consumer["consumer_key"],
            oauth_consumer["consumer_secret"],
            **kwargs,
        )

        if parent is not None:
            self.mount("https://", parent.adapters["https://"])
            self.proxies = parent.proxies
            self.verify = parent.verify

    def _get_oauth_consumer_safe(self) -> Dict[str, str]:
        """Get OAuth consumer credentials safely with fallback chain.

        Returns:
            Dictionary containing consumer_key and consumer_secret

        Fallback order:
        1. Environment variables (if set)
        2. S3 fallback URL (if embedded credentials fail)
        3. Embedded credentials (default)
        """
        if not hasattr(self, "_oauth_consumer_cache"):
            self._oauth_consumer_cache = self._fetch_consumer_credentials()
        return dict(self._oauth_consumer_cache)

    def _fetch_consumer_credentials(self) -> Dict[str, str]:
        """Get OAuth consumer credentials with environment variable override support."""
        import os

        from ..core.config import OAuthCredentials

        # Check for environment variable override
        env_key = os.getenv("GARMY_OAUTH_CONSUMER_KEY")
        env_secret = os.getenv("GARMY_OAUTH_CONSUMER_SECRET")

        if env_key and env_secret:
            return {"consumer_key": env_key, "consumer_secret": env_secret}

        # Use embedded credentials (consumer key from mitmproxy + secret from S3)
        return {
            "consumer_key": OAuthCredentials.DEFAULT_CONSUMER_KEY,
            "consumer_secret": OAuthCredentials.DEFAULT_CONSUMER_SECRET,
        }


def get_csrf_token(html: str) -> str:
    """Extract CSRF token from HTML response.

    Args:
        html: HTML content containing CSRF token

    Returns:
        CSRF token string

    Raises:
        AuthError: If CSRF token cannot be found in HTML
    """
    match = CSRF_RE.search(html)
    if not match:
        raise AuthError("Could not find CSRF token in response")
    return match.group(1)


def get_title(html: str) -> str:
    """Extract page title from HTML response.

    Args:
        html: HTML content containing title tag

    Returns:
        Page title string, empty string if no title found
    """
    match = TITLE_RE.search(html)
    return match.group(1) if match else ""


def set_expirations(token: dict) -> dict:
    """Set token expiration times based on expires_in values.

    Args:
        token: Token dictionary with expires_in and refresh_token_expires_in

    Returns:
        Updated token dictionary with expires_at and refresh_token_expires_at timestamps
    """
    token["expires_at"] = int(time.time() + token["expires_in"])
    token["refresh_token_expires_at"] = int(
        time.time() + token["refresh_token_expires_in"]
    )
    return token


def make_request(
    auth_client: "AuthClient",
    method: str,
    subdomain: str,
    path: str,
    referrer: bool = False,  # Currently unused but kept for API compatibility
    **kwargs: Any,
) -> requests.Response:
    """Make HTTP request using auth client session.

    Args:
        auth_client: AuthClient instance with session and domain
        method: HTTP method (GET, POST, etc.)
        subdomain: Garmin subdomain (sso, connectapi, etc.)
        path: URL path
        referrer: Whether to include referer header from last response
        **kwargs: Additional arguments passed to request method

    Returns:
        HTTP Response object

    Raises:
        HTTPError: If request fails with non-2xx status code
    """
    url = f"https://{subdomain}.{auth_client.domain}"
    url = urljoin(url, path)

    # Add referer if requested
    if referrer and auth_client.last_resp:
        kwargs.setdefault("headers", {})["referer"] = auth_client.last_resp.url

    kwargs.setdefault("timeout", auth_client.http_client.timeout)

    resp = auth_client.http_client.session.request(method, url, **kwargs)
    resp.raise_for_status()

    # Store last response for SSO flow state management
    auth_client.last_resp = resp
    return resp


def get_oauth1_token(ticket: str, auth_client: "AuthClient") -> OAuth1Token:
    """Exchange login ticket for OAuth1 token.

    Args:
        ticket: Login ticket obtained from successful SSO authentication
        auth_client: AuthClient instance with session and domain

    Returns:
        OAuth1Token with token and secret for API access

    Raises:
        HTTPError: If token exchange request fails
    """
    sess = GarminOAuth1Session(parent=auth_client.http_client.session)

    base_url = f"https://connectapi.{auth_client.domain}/oauth-service/oauth/"
    login_url = f"https://sso.{auth_client.domain}/sso/embed"
    url = (
        f"{base_url}preauthorized?ticket={ticket}&login-url={login_url}"
        "&accepts-mfa-tokens=true"
    )

    resp = sess.get(url, headers=USER_AGENT, timeout=auth_client.http_client.timeout)
    resp.raise_for_status()

    parsed = parse_qs(resp.text)
    token = {k: v[0] for k, v in parsed.items()}

    return OAuth1Token(
        domain=auth_client.domain,
        oauth_token=token.get("oauth_token", ""),
        oauth_token_secret=token.get("oauth_token_secret", ""),
    )


def exchange(oauth1: OAuth1Token, auth_client: "AuthClient") -> OAuth2Token:
    """Exchange OAuth1 token for OAuth2 token.

    Args:
        oauth1: Valid OAuth1Token to exchange
        auth_client: AuthClient instance with session and domain

    Returns:
        OAuth2Token with access token and refresh token

    Raises:
        HTTPError: If token exchange request fails
    """
    sess = GarminOAuth1Session(
        resource_owner_key=oauth1.oauth_token,
        resource_owner_secret=oauth1.oauth_token_secret,
        parent=auth_client.http_client.session,
    )

    data = {"mfa_token": oauth1.mfa_token} if oauth1.mfa_token else {}
    base_url = f"https://connectapi.{auth_client.domain}/oauth-service/oauth/"
    url = f"{base_url}exchange/user/2.0"
    headers = {
        **USER_AGENT,
        **{"Content-Type": "application/x-www-form-urlencoded"},
    }

    resp = sess.post(
        url, headers=headers, data=data, timeout=auth_client.http_client.timeout
    )
    resp.raise_for_status()

    token = resp.json()
    return OAuth2Token(**set_expirations(token))


def handle_mfa(
    auth_client: "AuthClient", signin_params: dict, prompt_mfa: Callable[[], str]
) -> None:
    """Handle multi-factor authentication flow.

    Args:
        auth_client: AuthClient instance with session and last response
        signin_params: SSO signin parameters for the MFA request
        prompt_mfa: Callable that prompts user for MFA code and returns it

    Raises:
        AuthError: If CSRF token cannot be extracted
        HTTPError: If MFA verification request fails
    """
    if auth_client.last_resp:
        csrf_token = get_csrf_token(auth_client.last_resp.text)
    else:
        csrf_token = None
    mfa_code = prompt_mfa()

    make_request(
        auth_client,
        "POST",
        "sso",
        "/sso/verifyMFA/loginEnterMfaCode",
        params=signin_params,
        referrer=True,
        data={
            "mfa-code": mfa_code,
            "embed": "true",
            "_csrf": csrf_token,
            "fromPage": "setupEnterMfaCode",
        },
    )


def _complete_login(
    auth_client: "AuthClient", html: str
) -> Tuple[OAuth1Token, OAuth2Token]:
    """Complete the login process after successful authentication.

    Args:
        auth_client: AuthClient instance with session and domain
        html: HTML response containing the login ticket

    Returns:
        Tuple of (OAuth1Token, OAuth2Token) for authenticated access

    Raises:
        LoginError: If login ticket cannot be found in response
        HTTPError: If token exchange requests fail
    """
    match = re.search(r'embed\?ticket=([^"]+)"', html)
    if not match:
        raise LoginError("Could not find ticket in response")

    ticket = match.group(1)

    oauth1 = get_oauth1_token(ticket, auth_client)
    oauth2 = exchange(oauth1, auth_client)

    return oauth1, oauth2


def _setup_sso_urls(domain: str) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Set up SSO URLs and parameters for authentication.

    Args:
        domain: Garmin domain for authentication

    Returns:
        Tuple of (SSO_EMBED_PARAMS, SIGNIN_PARAMS)
    """
    SSO = f"https://sso.{domain}/sso"
    SSO_EMBED = f"{SSO}/embed"

    SSO_EMBED_PARAMS = {
        "id": "gauth-widget",
        "embedWidget": "true",
        "gauthHost": SSO,
    }

    SIGNIN_PARAMS = {
        **SSO_EMBED_PARAMS,
        "gauthHost": SSO_EMBED,
        "service": SSO_EMBED,
        "source": SSO_EMBED,
        "redirectAfterAccountLoginUrl": SSO_EMBED,
        "redirectAfterAccountCreationUrl": SSO_EMBED,
    }

    return SSO_EMBED_PARAMS, SIGNIN_PARAMS


def _perform_initial_login(
    auth_client: "AuthClient",
    email: str,
    password: str,
    csrf_token: str,
    signin_params: Dict[str, str],
) -> str:
    """Perform initial login form submission.

    Args:
        auth_client: AuthClient instance
        email: User email
        password: User password
        csrf_token: CSRF token for form submission
        signin_params: SSO signin parameters

    Returns:
        Page title from response
    """
    resp = make_request(
        auth_client,
        "POST",
        "sso",
        "/sso/signin",
        params=signin_params,
        referrer=True,
        data={
            "username": email,
            "password": password,
            "embed": "true",
            "_csrf": csrf_token,
        },
    )
    return get_title(resp.text)


def _handle_mfa_response(
    auth_client: "AuthClient",
    signin_params: Dict[str, str],
    prompt_mfa: Optional[Callable[[], str]],
    return_on_mfa: bool,
    csrf_token: str,
) -> Tuple[bool, str, Optional[Tuple[Literal["needs_mfa"], Dict[str, Any]]]]:
    """Handle MFA response and return appropriate action.

    Args:
        auth_client: AuthClient instance
        signin_params: SSO signin parameters
        prompt_mfa: MFA prompt function
        return_on_mfa: Whether to return on MFA requirement
        csrf_token: CSRF token

    Returns:
        Tuple of (should_return_mfa_state, title, mfa_return_value)
    """
    if return_on_mfa or prompt_mfa is None:
        mfa_state = {
            "csrf_token": csrf_token,
            "signin_params": signin_params,
            "auth_client": auth_client,
        }
        return True, "", ("needs_mfa", mfa_state)

    handle_mfa(auth_client, signin_params, prompt_mfa)
    title = get_title(auth_client.last_resp.text) if auth_client.last_resp else ""
    return False, title, None


def login(
    email: str,
    password: str,
    auth_client: Optional["AuthClient"] = None,
    prompt_mfa: Optional[Callable[[], str]] = lambda: input("MFA code: "),
    return_on_mfa: bool = False,
) -> Union[
    Tuple[OAuth1Token, OAuth2Token], Tuple[Literal["needs_mfa"], Dict[str, Any]]
]:
    """Login to Garmin Connect using email and password.

    Performs the complete SSO authentication flow including CSRF token handling,
    login form submission, optional MFA, and token retrieval.

    Args:
        email: Garmin account email address
        password: Garmin account password
        auth_client: Optional AuthClient instance (creates new one if None)
        prompt_mfa: Optional callable that prompts user for MFA code
        return_on_mfa: If True, return MFA state instead of prompting

    Returns:
        Either a tuple of (OAuth1Token, OAuth2Token) on successful login,
        or ("needs_mfa", client_state_dict) if MFA is required and return_on_mfa=True

    Raises:
        LoginError: If login credentials are invalid or authentication fails
        AuthError: If CSRF token extraction fails
        HTTPError: If any HTTP requests fail
    """
    if auth_client is None:
        from .client import AuthClient

        auth_client = AuthClient()

    # Setup SSO URLs and parameters
    sso_embed_params, signin_params = _setup_sso_urls(auth_client.domain)

    # Initialize SSO session
    make_request(auth_client, "GET", "sso", "/sso/embed", params=sso_embed_params)

    # Get CSRF token
    resp = make_request(
        auth_client, "GET", "sso", "/sso/signin", params=signin_params, referrer=True
    )
    csrf_token = get_csrf_token(resp.text)

    # Perform login
    title = _perform_initial_login(
        auth_client, email, password, csrf_token, signin_params
    )

    # Handle MFA if required
    if "MFA" in title:
        should_return, updated_title, mfa_result = _handle_mfa_response(
            auth_client, signin_params, prompt_mfa, return_on_mfa, csrf_token
        )
        if should_return and mfa_result is not None:
            return mfa_result
        title = updated_title

    # Validate successful login
    if title != "Success":
        raise LoginError(f"Login failed. Title: {title}")

    # Complete login and get tokens
    if auth_client.last_resp:
        return _complete_login(auth_client, auth_client.last_resp.text)
    else:
        raise LoginError("No response available to complete login")


def resume_login(
    mfa_code: str,
    client_state: Dict[str, Any],
) -> Tuple[OAuth1Token, OAuth2Token]:
    """Resume login process after MFA code entry.

    Args:
        mfa_code: Multi-factor authentication code from user's device
        client_state: State dictionary containing auth_client, csrf_token, and signin_params

    Returns:
        Tuple of (OAuth1Token, OAuth2Token) on successful authentication

    Raises:
        LoginError: If MFA code is invalid or verification fails
        HTTPError: If MFA verification request fails
    """
    auth_client = client_state["auth_client"]
    csrf_token = client_state["csrf_token"]
    signin_params = client_state["signin_params"]

    # Submit MFA code
    make_request(
        auth_client,
        "POST",
        "sso",
        "/sso/verifyMFA/loginEnterMfaCode",
        params=signin_params,
        referrer=True,
        data={
            "mfa-code": mfa_code,
            "embed": "true",
            "_csrf": csrf_token,
            "fromPage": "setupEnterMfaCode",
        },
    )

    title = get_title(auth_client.last_resp.text) if auth_client.last_resp else ""

    if title != "Success":
        raise LoginError(f"MFA verification failed. Title: {title}")

    if auth_client.last_resp:
        return _complete_login(auth_client, auth_client.last_resp.text)
    else:
        raise LoginError("No response available to complete MFA login")
