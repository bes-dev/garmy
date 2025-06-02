"""Comprehensive tests for garmy.auth.exceptions module.

This module provides 100% test coverage for authentication exceptions.
"""

from unittest.mock import Mock

from requests import HTTPError

from garmy.auth.exceptions import (
    AuthError,
    AuthHTTPError,
    LoginError,
    MFARequiredError,
    TokenExpiredError,
)


class TestAuthError:
    """Test cases for AuthError class."""

    def test_auth_error_creation_with_message(self):
        """Test AuthError creation with error message."""
        error = AuthError("Authentication failed")

        assert str(error) == "Authentication failed"
        assert error.msg == "Authentication failed"

    def test_auth_error_inheritance(self):
        """Test AuthError inheritance hierarchy."""
        error = AuthError("Authentication failed")

        # AuthError should inherit from the core exception hierarchy
        assert isinstance(error, Exception)

    def test_auth_error_empty_message(self):
        """Test AuthError with empty message."""
        error = AuthError("")

        assert str(error) == ""
        assert error.msg == ""

    def test_auth_error_none_message(self):
        """Test AuthError with None message (edge case)."""
        error = AuthError(None)

        assert error.msg is None


class TestLoginError:
    """Test cases for LoginError class."""

    def test_login_error_creation(self):
        """Test LoginError creation with error message."""
        error = LoginError("Invalid credentials")

        assert str(error) == "Invalid credentials"
        assert error.msg == "Invalid credentials"

    def test_login_error_inheritance(self):
        """Test LoginError inheritance from AuthError."""
        error = LoginError("Invalid credentials")

        assert isinstance(error, AuthError)
        assert isinstance(error, Exception)

    def test_login_error_with_detailed_message(self):
        """Test LoginError with detailed error message."""
        detailed_msg = "Login failed. Title: MFA Required"
        error = LoginError(detailed_msg)

        assert str(error) == detailed_msg
        assert error.msg == detailed_msg


class TestMFARequiredError:
    """Test cases for MFARequiredError class."""

    def test_mfa_required_error_creation(self):
        """Test MFARequiredError creation with error message."""
        error = MFARequiredError("Multi-factor authentication required")

        assert str(error) == "Multi-factor authentication required"
        assert error.msg == "Multi-factor authentication required"

    def test_mfa_required_error_inheritance(self):
        """Test MFARequiredError inheritance from AuthError."""
        error = MFARequiredError("MFA required")

        assert isinstance(error, AuthError)
        assert isinstance(error, Exception)

    def test_mfa_required_error_typical_message(self):
        """Test MFARequiredError with typical MFA message."""
        error = MFARequiredError("MFA code required but no prompt function provided")

        assert "MFA code required" in str(error)


class TestTokenExpiredError:
    """Test cases for TokenExpiredError class."""

    def test_token_expired_error_creation(self):
        """Test TokenExpiredError creation with error message."""
        error = TokenExpiredError("Access token has expired")

        assert str(error) == "Access token has expired"
        assert error.msg == "Access token has expired"

    def test_token_expired_error_inheritance(self):
        """Test TokenExpiredError inheritance from AuthError."""
        error = TokenExpiredError("Token expired")

        assert isinstance(error, AuthError)
        assert isinstance(error, Exception)

    def test_token_expired_error_refresh_scenario(self):
        """Test TokenExpiredError for refresh token scenario."""
        error = TokenExpiredError("Refresh token has expired, please login again")

        assert "Refresh token has expired" in str(error)


class TestAuthHTTPError:
    """Test cases for AuthHTTPError class."""

    def test_auth_http_error_creation(self):
        """Test AuthHTTPError creation with HTTPError."""
        # Create a mock HTTPError
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.reason = "Unauthorized"

        http_error = HTTPError("401 Client Error: Unauthorized")
        http_error.response = mock_response

        auth_error = AuthHTTPError("Authentication request failed", http_error)

        assert auth_error.msg == "Authentication request failed"
        assert auth_error.error == http_error

    def test_auth_http_error_str_method(self):
        """Test AuthHTTPError.__str__ method formatting."""
        # Create a mock HTTPError
        http_error = HTTPError("401 Client Error: Unauthorized")

        auth_error = AuthHTTPError("Authentication request failed", http_error)

        expected_str = "Authentication request failed: 401 Client Error: Unauthorized"
        assert str(auth_error) == expected_str

    def test_auth_http_error_inheritance(self):
        """Test AuthHTTPError inheritance from AuthError."""
        http_error = HTTPError("500 Server Error")
        auth_error = AuthHTTPError("Server error during auth", http_error)

        assert isinstance(auth_error, AuthError)
        assert isinstance(auth_error, Exception)

    def test_auth_http_error_dataclass_fields(self):
        """Test AuthHTTPError dataclass fields access."""
        http_error = HTTPError("403 Forbidden")
        auth_error = AuthHTTPError("Access denied", http_error)

        # Test direct field access
        assert auth_error.msg == "Access denied"
        assert auth_error.error == http_error

    def test_auth_http_error_with_different_http_errors(self):
        """Test AuthHTTPError with various HTTP error types."""
        # Test with 400 Bad Request
        http_400 = HTTPError("400 Bad Request")
        auth_400 = AuthHTTPError("Bad request", http_400)
        assert str(auth_400) == "Bad request: 400 Bad Request"

        # Test with 404 Not Found
        http_404 = HTTPError("404 Not Found")
        auth_404 = AuthHTTPError("Resource not found", http_404)
        assert str(auth_404) == "Resource not found: 404 Not Found"

        # Test with 500 Internal Server Error
        http_500 = HTTPError("500 Internal Server Error")
        auth_500 = AuthHTTPError("Server error", http_500)
        assert str(auth_500) == "Server error: 500 Internal Server Error"

    def test_auth_http_error_empty_message(self):
        """Test AuthHTTPError with empty message."""
        http_error = HTTPError("401 Unauthorized")
        auth_error = AuthHTTPError("", http_error)

        assert str(auth_error) == ": 401 Unauthorized"

    def test_auth_http_error_complex_http_error(self):
        """Test AuthHTTPError with complex HTTPError message."""
        complex_error = HTTPError(
            "401 Client Error: Unauthorized for url: https://sso.garmin.com/sso/signin"
        )
        auth_error = AuthHTTPError("SSO authentication failed", complex_error)

        expected = (
            "SSO authentication failed: 401 Client Error: Unauthorized for url: "
            "https://sso.garmin.com/sso/signin"
        )
        assert str(auth_error) == expected

    def test_auth_http_error_equality(self):
        """Test AuthHTTPError equality comparison."""
        http_error1 = HTTPError("401 Unauthorized")
        http_error3 = HTTPError("403 Forbidden")

        auth_error1 = AuthHTTPError("Auth failed", http_error1)
        auth_error2 = AuthHTTPError("Auth failed", http_error1)  # Use same object
        auth_error3 = AuthHTTPError("Auth failed", http_error3)
        auth_error4 = AuthHTTPError("Different message", http_error1)

        # Same message and same error object should be equal
        assert auth_error1 == auth_error2

        # Different error should not be equal
        assert auth_error1 != auth_error3

        # Different message should not be equal
        assert auth_error1 != auth_error4

    def test_auth_http_error_repr(self):
        """Test AuthHTTPError string representation."""
        http_error = HTTPError("401 Unauthorized")
        auth_error = AuthHTTPError("Auth failed", http_error)

        repr_str = repr(auth_error)
        assert "AuthHTTPError" in repr_str
        assert "msg='Auth failed'" in repr_str
        assert "error=" in repr_str


class TestExceptionModuleExports:
    """Test module-level exports and backward compatibility."""

    def test_module_exports_all_exceptions(self):
        """Test that all expected exceptions are exported."""
        from garmy.auth.exceptions import (
            AuthError,
            AuthHTTPError,
            LoginError,
            MFARequiredError,
            TokenExpiredError,
        )

        # Verify all exceptions can be imported
        assert AuthError is not None
        assert AuthHTTPError is not None
        assert LoginError is not None
        assert MFARequiredError is not None
        assert TokenExpiredError is not None

    def test_backward_compatibility_imports(self):
        """Test backward compatibility with core exceptions."""
        # These should be the same classes from core.exceptions
        from garmy.auth.exceptions import AuthError as AuthAuthError
        from garmy.core.exceptions import AuthError as CoreAuthError

        # Should be the same class
        assert AuthAuthError is CoreAuthError

    def test_exception_hierarchy_consistency(self):
        """Test that all auth exceptions follow consistent hierarchy."""
        from garmy.auth.exceptions import (
            AuthError,
            LoginError,
            MFARequiredError,
            TokenExpiredError,
        )

        # All should inherit from AuthError
        assert issubclass(LoginError, AuthError)
        assert issubclass(MFARequiredError, AuthError)
        assert issubclass(TokenExpiredError, AuthError)

        # AuthHTTPError should also inherit from AuthError
        from garmy.auth.exceptions import AuthHTTPError

        assert issubclass(AuthHTTPError, AuthError)

    def test_exception_module_docstring(self):
        """Test module has proper docstring."""
        import garmy.auth.exceptions as exceptions_module

        assert exceptions_module.__doc__ is not None
        assert "backward compatibility" in exceptions_module.__doc__.lower()

    def test_all_exports_list(self):
        """Test __all__ exports list contains expected exceptions."""
        from garmy.auth.exceptions import __all__

        expected_exports = {
            "AuthError",
            "AuthHTTPError",
            "LoginError",
            "MFARequiredError",
            "TokenExpiredError",
        }

        assert set(__all__) == expected_exports
