"""
Self-contained authentication client for Garmin Connect.

This module handles all authentication concerns:
- Token management
- Login/logout flows
- Session persistence
- HTTP authentication headers
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, Literal, Optional, Tuple, Union

if TYPE_CHECKING:
    import requests

from ..core.config import get_user_agent
from ..core.http_client import BaseHTTPClient
from . import sso
from .exceptions import AuthError
from .tokens import OAuth1Token, OAuth2Token


class TokenManager:
    """Manages OAuth1 and OAuth2 token state and validation.

    This class is responsible solely for token-related operations:
    - Token storage and retrieval
    - Token validation and expiration checking
    - Token refresh logic
    """

    def __init__(self) -> None:
        """Initialize the token manager."""
        self.oauth1_token: Optional[OAuth1Token] = None
        self.oauth2_token: Optional[OAuth2Token] = None

    def set_tokens(self, oauth1_token: OAuth1Token, oauth2_token: OAuth2Token) -> None:
        """Set both OAuth1 and OAuth2 tokens.

        Args:
            oauth1_token: OAuth1 token to store.
            oauth2_token: OAuth2 token to store.
        """
        self.oauth1_token = oauth1_token
        self.oauth2_token = oauth2_token

    def clear_tokens(self) -> None:
        """Clear all stored tokens."""
        self.oauth1_token = None
        self.oauth2_token = None

    def is_authenticated(self) -> bool:
        """Check if client is authenticated with valid tokens.

        Returns:
            True if both OAuth1 and OAuth2 tokens are present and OAuth2 token is not expired.
        """
        return (
            self.oauth1_token is not None
            and self.oauth2_token is not None
            and not self.oauth2_token.expired
        )

    def needs_refresh(self) -> bool:
        """Check if tokens need to be refreshed.

        Returns:
            True if OAuth2 token is expired but refresh token is still valid.
        """
        return (
            self.oauth1_token is not None
            and self.oauth2_token is not None
            and self.oauth2_token.expired
            and not self.oauth2_token.refresh_expired
        )

    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for API requests.

        Returns:
            Dictionary containing Authorization header with OAuth2 bearer token.

        Raises:
            AuthError: If not authenticated.
        """
        if not self.is_authenticated():
            raise AuthError("Not authenticated. Tokens are invalid or expired.")

        return {"Authorization": str(self.oauth2_token)}


class TokenFileManager:
    """Handles persistent storage and retrieval of authentication tokens.

    This class is responsible solely for file I/O operations:
    - Loading tokens from disk
    - Saving tokens to disk
    - Managing token file locations
    """

    def __init__(self, token_dir: Optional[str] = None):
        """Initialize the token file manager.

        Token directory resolution priority:
        1. Explicit token_dir parameter
        2. GARMY_PROFILE_PATH environment variable
        3. Default: ~/.garmy/

        Args:
            token_dir: Directory path for storing tokens.
        """
        if token_dir:
            self.token_dir = token_dir
        else:
            # Check environment variable for profile path
            profile_path = os.getenv("GARMY_PROFILE_PATH")
            if profile_path:
                self.token_dir = str(Path(profile_path).expanduser())
            else:
                # Default fallback
                self.token_dir = str(Path.home() / ".garmy")

    def load_tokens(self) -> Tuple[Optional[OAuth1Token], Optional[OAuth2Token]]:
        """Load authentication tokens from persistent storage.

        Returns:
            Tuple of (OAuth1Token, OAuth2Token) or (None, None) if not found.
        """
        Path(self.token_dir).mkdir(parents=True, exist_ok=True)

        oauth1_token = self._load_oauth1_token()
        oauth2_token = self._load_oauth2_token()

        return oauth1_token, oauth2_token

    def save_tokens(
        self, oauth1_token: Optional[OAuth1Token], oauth2_token: Optional[OAuth2Token]
    ) -> None:
        """Save authentication tokens to persistent storage.

        Args:
            oauth1_token: OAuth1 token to save.
            oauth2_token: OAuth2 token to save.
        """
        Path(self.token_dir).mkdir(parents=True, exist_ok=True)

        if oauth1_token:
            self._save_oauth1_token(oauth1_token)

        if oauth2_token:
            self._save_oauth2_token(oauth2_token)

    def clear_stored_tokens(self) -> None:
        """Remove stored token files from disk."""
        for filename in ["oauth1_token.json", "oauth2_token.json"]:
            filepath = Path(self.token_dir) / filename
            if filepath.exists():
                filepath.unlink()

    def _load_oauth1_token(self) -> Optional[OAuth1Token]:
        """Load OAuth1 token from file."""
        oauth1_path = Path(self.token_dir) / "oauth1_token.json"

        if not oauth1_path.exists():
            return None

        return self._safe_load_token_file(oauth1_path, self._parse_oauth1_data)

    def _load_oauth2_token(self) -> Optional[OAuth2Token]:
        """Load OAuth2 token from file."""
        oauth2_path = Path(self.token_dir) / "oauth2_token.json"

        if not oauth2_path.exists():
            return None

        return self._safe_load_token_file(oauth2_path, self._parse_oauth2_data)

    def _safe_load_token_file(
        self, file_path: Path, parser_func: Callable
    ) -> Optional[Any]:
        """Safely load and parse a token file with differentiated error handling.

        Args:
            file_path: Path to the token file
            parser_func: Function to parse the loaded data

        Returns:
            Parsed token or None if loading fails

        Raises:
            PermissionError: If file permissions prevent access
            OSError: If there are critical filesystem issues
        """
        import logging

        logger = logging.getLogger(__name__)

        try:
            with file_path.open() as token_file:
                data = json.load(token_file)
                return parser_func(data)

        except PermissionError:
            logger.error(f"Permission denied accessing token file: {file_path}")
            raise

        except OSError as e:
            # Critical filesystem issues should not be silently ignored
            if e.errno in (28, 30):  # No space left, Read-only filesystem
                logger.error(f"Critical filesystem error loading token: {e}")
                raise
            logger.warning(f"Filesystem error loading token from {file_path}: {e}")
            return None

        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in token file {file_path}: {e}")
            return None

        except (KeyError, ValueError, TypeError) as e:
            logger.warning(f"Invalid token data structure in {file_path}: {e}")
            return None

        except (SystemExit, KeyboardInterrupt, GeneratorExit):
            # Don't catch system control exceptions
            raise

        except Exception as e:
            # Log unexpected errors with full traceback for debugging
            logger.error(
                f"Unexpected error loading token from {file_path}: {e}", exc_info=True
            )
            return None

    def _parse_oauth1_data(self, data: Dict[str, Any]) -> OAuth1Token:
        """Parse OAuth1 token data with datetime handling."""
        if data.get("mfa_expiration_timestamp"):
            data["mfa_expiration_timestamp"] = datetime.fromisoformat(
                data["mfa_expiration_timestamp"]
            )
        return OAuth1Token(**data)

    def _parse_oauth2_data(self, data: Dict[str, Any]) -> OAuth2Token:
        """Parse OAuth2 token data."""
        return OAuth2Token(**data)

    def _save_oauth1_token(self, token: OAuth1Token) -> None:
        """Save OAuth1 token to file."""
        oauth1_path = Path(self.token_dir) / "oauth1_token.json"
        with oauth1_path.open("w") as oauth1_file:
            data = {
                "oauth_token": token.oauth_token,
                "oauth_token_secret": token.oauth_token_secret,
                "mfa_token": token.mfa_token,
                "mfa_expiration_timestamp": (
                    token.mfa_expiration_timestamp.isoformat()
                    if token.mfa_expiration_timestamp
                    else None
                ),
                "domain": token.domain,
            }
            json.dump(data, oauth1_file)

    def _save_oauth2_token(self, token: OAuth2Token) -> None:
        """Save OAuth2 token to file."""
        oauth2_path = Path(self.token_dir) / "oauth2_token.json"
        with oauth2_path.open("w") as oauth2_file:
            data = {
                "scope": token.scope,
                "jti": token.jti,
                "token_type": token.token_type,
                "access_token": token.access_token,
                "refresh_token": token.refresh_token,
                "expires_in": token.expires_in,
                "expires_at": token.expires_at,
                "refresh_token_expires_in": token.refresh_token_expires_in,
                "refresh_token_expires_at": token.refresh_token_expires_at,
            }
            json.dump(data, oauth2_file)


class AuthHttpClient(BaseHTTPClient):
    """Handles HTTP requests for authentication operations.

    This class extends BaseHTTPClient with authentication-specific configuration:
    - Mobile app user agent for Garmin compatibility
    - Standard retry and timeout configuration from base class
    """

    def __init__(self, domain: str = "garmin.com", timeout: int = 10, retries: int = 3):
        """Initialize the authentication HTTP client.

        Args:
            domain: Garmin domain for requests.
            timeout: Request timeout in seconds.
            retries: Number of retry attempts.
        """
        # Use BaseHTTPClient with mobile app user agent
        super().__init__(
            domain=domain,
            timeout=timeout,
            retries=retries,
            user_agent=get_user_agent("android"),
        )


class AuthClient:
    """Orchestrates authentication operations using composition of specialized components.

    This class uses the Single Responsibility Principle by delegating specific
    tasks to specialized components:
    - TokenManager: Handles token state and validation
    - TokenFileManager: Handles persistent token storage
    - AuthHttpClient: Handles HTTP requests for authentication

    The AuthClient now acts as an orchestrator providing a clean interface for
    Garmin Connect authentication while maintaining separation of concerns.

    Attributes:
        domain: Garmin domain (default: "garmin.com")
        token_manager: Component handling token state and validation
        file_manager: Component handling token file I/O
        http_client: Component handling HTTP requests
    """

    def __init__(
        self,
        domain: str = "garmin.com",
        timeout: int = 10,
        retries: int = 3,
        token_dir: Optional[str] = None,
    ) -> None:
        """Initialize the authentication client with composed components.

        Args:
            domain: Garmin domain to authenticate with
            timeout: Request timeout in seconds
            retries: Number of retry attempts for failed requests
            token_dir: Directory path for storing tokens.
                       Resolution priority:
                       1. This parameter if provided
                       2. GARMY_PROFILE_PATH environment variable
                       3. Default: ~/.garmy/
        """
        self.domain = domain

        # Compose with specialized components following SRP
        self.token_manager = TokenManager()
        self.file_manager = TokenFileManager(token_dir)
        self.http_client = AuthHttpClient(domain, timeout, retries)
        # Add last_resp for SSO flow state management
        self.last_resp: Optional[requests.Response] = None

        # Load existing tokens
        self.load_tokens()

    @property
    def is_authenticated(self) -> bool:
        """Check if client is authenticated with valid tokens.

        Delegates to the token manager component.

        Returns:
            True if both OAuth1 and OAuth2 tokens are present and OAuth2 token is not expired
        """
        return self.token_manager.is_authenticated()

    @property
    def needs_refresh(self) -> bool:
        """Check if tokens need to be refreshed.

        Delegates to the token manager component.

        Returns:
            True if OAuth2 token is expired but refresh token is still valid
        """
        return self.token_manager.needs_refresh()

    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for API requests.

        Delegates to the token manager with automatic refresh if needed.

        Returns:
            Dictionary containing Authorization header with OAuth2 bearer token

        Raises:
            AuthError: If not authenticated and cannot refresh tokens
        """
        if not self.is_authenticated:
            if self.needs_refresh:
                self.refresh_tokens()
            else:
                raise AuthError("Not authenticated. Please login first.")

        return self.token_manager.get_auth_headers()

    def login(
        self,
        email: str,
        password: str,
        prompt_mfa: Optional[Callable[[], str]] = None,
        return_on_mfa: bool = False,
    ) -> Union[
        Tuple[OAuth1Token, OAuth2Token], Tuple[Literal["needs_mfa"], Dict[str, Any]]
    ]:
        """Login to Garmin Connect with email and password.

        Coordinates between SSO module and token/file components.

        Args:
            email: Garmin account email address
            password: Garmin account password
            prompt_mfa: Optional callable that prompts user for MFA code and returns it
            return_on_mfa: If True, return MFA state instead of prompting for code

        Returns:
            Either a tuple of (OAuth1Token, OAuth2Token) on successful login,
            or ("needs_mfa", client_state_dict) if MFA is required and return_on_mfa=True

        Raises:
            LoginError: If login credentials are invalid
            AuthError: If authentication process fails
        """
        # Use SSO module for login
        result = sso.login(
            email,
            password,
            auth_client=self,
            prompt_mfa=prompt_mfa,
            return_on_mfa=return_on_mfa,
        )

        # Handle MFA case
        if isinstance(result, tuple) and result[0] == "needs_mfa":
            return result

        # Store tokens using components
        oauth1_token, oauth2_token = result
        self.token_manager.set_tokens(oauth1_token, oauth2_token)
        self.file_manager.save_tokens(oauth1_token, oauth2_token)

        return result

    def resume_login(
        self, mfa_code: str, client_state: Dict[str, Any]
    ) -> Tuple[OAuth1Token, OAuth2Token]:
        """Resume login process after providing MFA code.

        Coordinates between SSO module and token/file components.

        Args:
            mfa_code: Multi-factor authentication code from user's device
            client_state: State dictionary returned from login() when MFA was required

        Returns:
            Tuple of (OAuth1Token, OAuth2Token) on successful authentication

        Raises:
            LoginError: If MFA code is invalid or verification fails
            AuthError: If authentication process fails
        """
        result = sso.resume_login(mfa_code, client_state)

        # Store tokens using components
        oauth1_token, oauth2_token = result
        self.token_manager.set_tokens(oauth1_token, oauth2_token)
        self.file_manager.save_tokens(oauth1_token, oauth2_token)

        return result

    def refresh_tokens(self) -> OAuth2Token:
        """Refresh OAuth2 token using existing OAuth1 token.

        Coordinates between SSO module and token/file components.

        Returns:
            New OAuth2Token with updated access token and expiration

        Raises:
            AuthError: If OAuth1 token is not available for refresh
        """
        if not self.token_manager.oauth1_token:
            raise AuthError("OAuth1 token required for refresh")

        # Exchange OAuth1 for new OAuth2 token
        new_oauth2_token = sso.exchange(self.token_manager.oauth1_token, self)
        self.token_manager.oauth2_token = new_oauth2_token
        self.file_manager.save_tokens(self.token_manager.oauth1_token, new_oauth2_token)

        return new_oauth2_token

    def logout(self) -> None:
        """Clear authentication tokens and remove stored token files.

        Delegates to token manager and file manager components.

        This method invalidates the current session by clearing both OAuth1 and OAuth2
        tokens from memory and removing the stored token files from disk.
        """
        self.token_manager.clear_tokens()
        self.file_manager.clear_stored_tokens()

    def load_tokens(self) -> None:
        """Load authentication tokens from persistent storage.

        Delegates to the file manager component to load tokens.

        Raises:
            PermissionError: If token files cannot be accessed due to permissions
            OSError: If critical filesystem errors occur
        """
        import logging

        logger = logging.getLogger(__name__)

        try:
            oauth1_token, oauth2_token = self.file_manager.load_tokens()

            # Track loading success for better debugging
            tokens_loaded = []
            if oauth1_token:
                self.token_manager.oauth1_token = oauth1_token
                tokens_loaded.append("OAuth1")
            if oauth2_token:
                self.token_manager.oauth2_token = oauth2_token
                tokens_loaded.append("OAuth2")

            if tokens_loaded:
                logger.debug(f"Successfully loaded tokens: {', '.join(tokens_loaded)}")
            else:
                logger.debug("No valid tokens found in storage")

        except OSError as e:
            logger.error(f"Failed to load tokens due to filesystem error: {e}")
            # Re-raise critical errors so they don't get silently ignored
            raise
        except (SystemExit, KeyboardInterrupt, GeneratorExit):
            # Don't catch system control exceptions
            raise

        except Exception as e:
            logger.error(f"Unexpected error loading tokens: {e}", exc_info=True)
            # Clear any partially loaded state before re-raising
            self.token_manager.clear_tokens()
            # Re-raise to maintain the original exception context
            raise AuthError(f"Failed to load tokens: {e}") from e

    def save_tokens(self) -> None:
        """Save current authentication tokens to persistent storage.

        Delegates to the file manager component to save tokens.
        """
        self.file_manager.save_tokens(
            self.token_manager.oauth1_token, self.token_manager.oauth2_token
        )

    def clear_stored_tokens(self) -> None:
        """Remove stored token files from disk.

        Delegates to the file manager component to clear stored tokens.
        """
        self.file_manager.clear_stored_tokens()
