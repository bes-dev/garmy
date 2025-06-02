"""Authentication tokens for Garmin Connect OAuth1/OAuth2 flow.

This module defines the data structures for OAuth1 and OAuth2 tokens used
in Garmin Connect authentication. These tokens are used to authorize API
requests and maintain authenticated sessions.

OAuth1 tokens are obtained during the initial login process and can be
exchanged for OAuth2 tokens. OAuth2 tokens contain the actual access token
used for API authentication, along with refresh capabilities.
"""

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from datetime import datetime


@dataclass
class OAuth1Token:
    """OAuth1 token for Garmin Connect API authentication.

    This token is obtained during the initial SSO login flow and can be
    exchanged for OAuth2 tokens. It may also contain MFA tokens for
    multi-factor authentication scenarios.

    Attributes:
        oauth_token: OAuth1 token string
        oauth_token_secret: OAuth1 token secret string
        mfa_token: Optional MFA token for enhanced security
        mfa_expiration_timestamp: Optional MFA token expiration time
        domain: Garmin domain this token is valid for
    """

    oauth_token: str
    oauth_token_secret: str
    mfa_token: Optional[str] = None
    mfa_expiration_timestamp: Optional["datetime"] = None
    domain: Optional[str] = None


@dataclass
class OAuth2Token:
    """OAuth2 token for Garmin Connect API authentication.

    This is the primary token used for API authentication. It contains
    an access token for immediate use and a refresh token for obtaining
    new access tokens when the current one expires.

    Attributes:
        scope: OAuth2 scope permissions
        jti: JSON Token Identifier (unique token ID)
        token_type: Token type (typically "Bearer")
        access_token: The actual access token for API requests
        refresh_token: Token used to refresh the access token
        expires_in: Access token lifetime in seconds
        expires_at: Access token expiration timestamp
        refresh_token_expires_in: Refresh token lifetime in seconds
        refresh_token_expires_at: Refresh token expiration timestamp
    """

    scope: str
    jti: str
    token_type: str
    access_token: str
    refresh_token: str
    expires_in: int
    expires_at: int
    refresh_token_expires_in: int
    refresh_token_expires_at: int

    @property
    def expired(self) -> bool:
        """Check if the access token has expired.

        Returns:
            True if the access token expiration time has passed
        """
        return self.expires_at < time.time()

    @property
    def refresh_expired(self) -> bool:
        """Check if the refresh token has expired.

        Returns:
            True if the refresh token expiration time has passed
        """
        return self.refresh_token_expires_at < time.time()

    def __str__(self) -> str:
        """Return the token in Authorization header format.

        Returns:
            String formatted as "Bearer {access_token}" for HTTP Authorization headers
        """
        return f"{self.token_type.title()} {self.access_token}"
