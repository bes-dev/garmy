"""Authentication module for Garmin Connect.

This module provides a complete, self-contained authentication solution for
Garmin Connect.
It handles all aspects of the OAuth1/OAuth2 authentication flow including:

- Initial login with email/password credentials
- Multi-factor authentication (MFA) support
- OAuth1 token acquisition and OAuth2 token exchange
- Automatic token refresh and expiration handling
- Persistent token storage and session management
- HTTP authentication header generation

The main entry point is the AuthClient class which provides a high-level
interface
for authentication operations. Lower-level functions are available in the sso
module
for custom implementations.

Example:
    Basic authentication:

    >>> from garmy.auth import AuthClient
    >>> auth_client = AuthClient()
    >>> tokens = auth_client.login("your_email@example.com", "your_password")
    >>> headers = auth_client.get_auth_headers()

    Handling MFA:

    >>> result = auth_client.login(
    ...     "email@example.com", "password", return_on_mfa=True
    ... )
    >>> if isinstance(result, tuple) and result[0] == "needs_mfa":
    ...     mfa_code = input("Enter MFA code: ")
    ...     tokens = auth_client.resume_login(mfa_code, result[1])

Classes:
    AuthClient: Main authentication client
    OAuth1Token: OAuth1 token data structure
    OAuth2Token: OAuth2 token data structure

Functions:
    login: Low-level SSO login function
    resume_login: Resume login after MFA

Exceptions:
    AuthError: Base authentication error
    LoginError: Login process failure
    MFARequiredError: MFA required but not handled
"""

from .client import AuthClient
from .exceptions import AuthError, LoginError, MFARequiredError
from .sso import login, resume_login
from .tokens import OAuth1Token, OAuth2Token

__all__ = [
    "AuthClient",
    "AuthError",
    "LoginError",
    "MFARequiredError",
    "OAuth1Token",
    "OAuth2Token",
    "login",
    "resume_login",
]
