"""Comprehensive tests for garmy.auth.tokens module.

This module provides 100% test coverage for OAuth1Token and OAuth2Token classes.
"""

import time
from datetime import datetime
from unittest.mock import patch

from garmy.auth.tokens import OAuth1Token, OAuth2Token


class TestOAuth1Token:
    """Test cases for OAuth1Token class."""

    def test_oauth1_token_creation_minimal(self):
        """Test OAuth1Token creation with minimal required fields."""
        token = OAuth1Token(oauth_token="test_token", oauth_token_secret="test_secret")

        assert token.oauth_token == "test_token"
        assert token.oauth_token_secret == "test_secret"
        assert token.mfa_token is None
        assert token.mfa_expiration_timestamp is None
        assert token.domain is None

    def test_oauth1_token_creation_full(self):
        """Test OAuth1Token creation with all fields."""
        mfa_expiry = datetime.now()

        token = OAuth1Token(
            oauth_token="test_token",
            oauth_token_secret="test_secret",
            mfa_token="mfa_token_123",
            mfa_expiration_timestamp=mfa_expiry,
            domain="garmin.com",
        )

        assert token.oauth_token == "test_token"
        assert token.oauth_token_secret == "test_secret"
        assert token.mfa_token == "mfa_token_123"
        assert token.mfa_expiration_timestamp == mfa_expiry
        assert token.domain == "garmin.com"

    def test_oauth1_token_dataclass_equality(self):
        """Test OAuth1Token equality comparison."""
        mfa_expiry = datetime.now()

        token1 = OAuth1Token(
            oauth_token="test_token",
            oauth_token_secret="test_secret",
            mfa_token="mfa_token_123",
            mfa_expiration_timestamp=mfa_expiry,
            domain="garmin.com",
        )

        token2 = OAuth1Token(
            oauth_token="test_token",
            oauth_token_secret="test_secret",
            mfa_token="mfa_token_123",
            mfa_expiration_timestamp=mfa_expiry,
            domain="garmin.com",
        )

        token3 = OAuth1Token(
            oauth_token="different_token", oauth_token_secret="test_secret"
        )

        assert token1 == token2
        assert token1 != token3

    def test_oauth1_token_repr(self):
        """Test OAuth1Token string representation."""
        token = OAuth1Token(oauth_token="test_token", oauth_token_secret="test_secret")

        repr_str = repr(token)
        assert "OAuth1Token" in repr_str
        assert "oauth_token='test_token'" in repr_str
        assert "oauth_token_secret='test_secret'" in repr_str

    def test_oauth1_token_optional_fields_none(self):
        """Test OAuth1Token with explicitly None optional fields."""
        token = OAuth1Token(
            oauth_token="test_token",
            oauth_token_secret="test_secret",
            mfa_token=None,
            mfa_expiration_timestamp=None,
            domain=None,
        )

        assert token.mfa_token is None
        assert token.mfa_expiration_timestamp is None
        assert token.domain is None


class TestOAuth2Token:
    """Test cases for OAuth2Token class."""

    def test_oauth2_token_creation(self):
        """Test OAuth2Token creation with all required fields."""
        current_time = int(time.time())

        token = OAuth2Token(
            scope="connect:all",
            jti="unique_token_id",
            token_type="Bearer",
            access_token="access_token_123",
            refresh_token="refresh_token_456",
            expires_in=3600,
            expires_at=current_time + 3600,
            refresh_token_expires_in=86400,
            refresh_token_expires_at=current_time + 86400,
        )

        assert token.scope == "connect:all"
        assert token.jti == "unique_token_id"
        assert token.token_type == "Bearer"
        assert token.access_token == "access_token_123"
        assert token.refresh_token == "refresh_token_456"
        assert token.expires_in == 3600
        assert token.expires_at == current_time + 3600
        assert token.refresh_token_expires_in == 86400
        assert token.refresh_token_expires_at == current_time + 86400

    def test_oauth2_token_expired_property_false(self):
        """Test OAuth2Token.expired property when token is not expired."""
        current_time = int(time.time())
        future_time = current_time + 3600  # 1 hour in future

        token = OAuth2Token(
            scope="connect:all",
            jti="unique_token_id",
            token_type="Bearer",
            access_token="access_token_123",
            refresh_token="refresh_token_456",
            expires_in=3600,
            expires_at=future_time,
            refresh_token_expires_in=86400,
            refresh_token_expires_at=current_time + 86400,
        )

        assert not token.expired

    def test_oauth2_token_expired_property_true(self):
        """Test OAuth2Token.expired property when token is expired."""
        current_time = int(time.time())
        past_time = current_time - 3600  # 1 hour in past

        token = OAuth2Token(
            scope="connect:all",
            jti="unique_token_id",
            token_type="Bearer",
            access_token="access_token_123",
            refresh_token="refresh_token_456",
            expires_in=3600,
            expires_at=past_time,
            refresh_token_expires_in=86400,
            refresh_token_expires_at=current_time + 86400,
        )

        assert token.expired

    def test_oauth2_token_refresh_expired_property_false(self):
        """Test OAuth2Token.refresh_expired when refresh token is not expired."""
        current_time = int(time.time())
        future_time = current_time + 86400  # 1 day in future

        token = OAuth2Token(
            scope="connect:all",
            jti="unique_token_id",
            token_type="Bearer",
            access_token="access_token_123",
            refresh_token="refresh_token_456",
            expires_in=3600,
            expires_at=current_time + 3600,
            refresh_token_expires_in=86400,
            refresh_token_expires_at=future_time,
        )

        assert not token.refresh_expired

    def test_oauth2_token_refresh_expired_property_true(self):
        """Test OAuth2Token.refresh_expired property when refresh token is expired."""
        current_time = int(time.time())
        past_time = current_time - 86400  # 1 day in past

        token = OAuth2Token(
            scope="connect:all",
            jti="unique_token_id",
            token_type="Bearer",
            access_token="access_token_123",
            refresh_token="refresh_token_456",
            expires_in=3600,
            expires_at=current_time + 3600,
            refresh_token_expires_in=86400,
            refresh_token_expires_at=past_time,
        )

        assert token.refresh_expired

    @patch("time.time")
    def test_oauth2_token_expired_edge_case(self, mock_time):
        """Test OAuth2Token.expired property at exact expiration time."""
        mock_time.return_value = 1000

        token = OAuth2Token(
            scope="connect:all",
            jti="unique_token_id",
            token_type="Bearer",
            access_token="access_token_123",
            refresh_token="refresh_token_456",
            expires_in=3600,
            expires_at=1000,  # Exact current time
            refresh_token_expires_in=86400,
            refresh_token_expires_at=2000,
        )

        # At exact expiration time, should be considered expired
        # Since 1000 < 1000 is False, token should not be expired yet
        assert not token.expired

    @patch("time.time")
    def test_oauth2_token_refresh_expired_edge_case(self, mock_time):
        """Test OAuth2Token.refresh_expired property at exact expiration time."""
        mock_time.return_value = 2000

        token = OAuth2Token(
            scope="connect:all",
            jti="unique_token_id",
            token_type="Bearer",
            access_token="access_token_123",
            refresh_token="refresh_token_456",
            expires_in=3600,
            expires_at=1000,
            refresh_token_expires_in=86400,
            refresh_token_expires_at=2000,  # Exact current time
        )

        # At exact expiration time, should not be considered expired yet
        assert not token.refresh_expired

    def test_oauth2_token_str_bearer_default(self):
        """Test OAuth2Token.__str__ method with Bearer token type."""
        token = OAuth2Token(
            scope="connect:all",
            jti="unique_token_id",
            token_type="Bearer",
            access_token="access_token_123",
            refresh_token="refresh_token_456",
            expires_in=3600,
            expires_at=int(time.time()) + 3600,
            refresh_token_expires_in=86400,
            refresh_token_expires_at=int(time.time()) + 86400,
        )

        assert str(token) == "Bearer access_token_123"

    def test_oauth2_token_str_lowercase_token_type(self):
        """Test OAuth2Token.__str__ method with lowercase token type."""
        token = OAuth2Token(
            scope="connect:all",
            jti="unique_token_id",
            token_type="bearer",
            access_token="access_token_123",
            refresh_token="refresh_token_456",
            expires_in=3600,
            expires_at=int(time.time()) + 3600,
            refresh_token_expires_in=86400,
            refresh_token_expires_at=int(time.time()) + 86400,
        )

        # Should be title-cased
        assert str(token) == "Bearer access_token_123"

    def test_oauth2_token_str_custom_token_type(self):
        """Test OAuth2Token.__str__ method with custom token type."""
        token = OAuth2Token(
            scope="connect:all",
            jti="unique_token_id",
            token_type="custom",
            access_token="access_token_123",
            refresh_token="refresh_token_456",
            expires_in=3600,
            expires_at=int(time.time()) + 3600,
            refresh_token_expires_in=86400,
            refresh_token_expires_at=int(time.time()) + 86400,
        )

        assert str(token) == "Custom access_token_123"

    def test_oauth2_token_dataclass_equality(self):
        """Test OAuth2Token equality comparison."""
        current_time = int(time.time())

        token1 = OAuth2Token(
            scope="connect:all",
            jti="unique_token_id",
            token_type="Bearer",
            access_token="access_token_123",
            refresh_token="refresh_token_456",
            expires_in=3600,
            expires_at=current_time + 3600,
            refresh_token_expires_in=86400,
            refresh_token_expires_at=current_time + 86400,
        )

        token2 = OAuth2Token(
            scope="connect:all",
            jti="unique_token_id",
            token_type="Bearer",
            access_token="access_token_123",
            refresh_token="refresh_token_456",
            expires_in=3600,
            expires_at=current_time + 3600,
            refresh_token_expires_in=86400,
            refresh_token_expires_at=current_time + 86400,
        )

        token3 = OAuth2Token(
            scope="connect:all",
            jti="different_id",
            token_type="Bearer",
            access_token="access_token_123",
            refresh_token="refresh_token_456",
            expires_in=3600,
            expires_at=current_time + 3600,
            refresh_token_expires_in=86400,
            refresh_token_expires_at=current_time + 86400,
        )

        assert token1 == token2
        assert token1 != token3

    def test_oauth2_token_repr(self):
        """Test OAuth2Token string representation."""
        current_time = int(time.time())

        token = OAuth2Token(
            scope="connect:all",
            jti="unique_token_id",
            token_type="Bearer",
            access_token="access_token_123",
            refresh_token="refresh_token_456",
            expires_in=3600,
            expires_at=current_time + 3600,
            refresh_token_expires_in=86400,
            refresh_token_expires_at=current_time + 86400,
        )

        repr_str = repr(token)
        assert "OAuth2Token" in repr_str
        assert "scope='connect:all'" in repr_str
        assert "jti='unique_token_id'" in repr_str
        assert "token_type='Bearer'" in repr_str

    def test_oauth2_token_with_zero_expiry_times(self):
        """Test OAuth2Token with zero expiry times (edge case)."""
        token = OAuth2Token(
            scope="connect:all",
            jti="unique_token_id",
            token_type="Bearer",
            access_token="access_token_123",
            refresh_token="refresh_token_456",
            expires_in=0,
            expires_at=0,
            refresh_token_expires_in=0,
            refresh_token_expires_at=0,
        )

        # Both should be expired since current time > 0
        assert token.expired
        assert token.refresh_expired

    def test_oauth2_token_with_negative_expiry_times(self):
        """Test OAuth2Token with negative expiry times (edge case)."""
        token = OAuth2Token(
            scope="connect:all",
            jti="unique_token_id",
            token_type="Bearer",
            access_token="access_token_123",
            refresh_token="refresh_token_456",
            expires_in=-1,
            expires_at=-1,
            refresh_token_expires_in=-1,
            refresh_token_expires_at=-1,
        )

        # Both should be expired
        assert token.expired
        assert token.refresh_expired
