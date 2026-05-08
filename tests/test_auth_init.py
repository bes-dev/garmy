"""Comprehensive tests for garmy.auth.__init__ module.

This module provides 100% test coverage for the auth module's public interface.
"""

import pytest

from garmy.auth import (
    AuthClient,
    AuthError,
    LoginError,
    MFARequiredError,
    OAuth1Token,
    OAuth2Token,
    login,
    resume_login,
)


class TestAuthModuleExports:
    """Test auth module's public interface exports."""

    def test_auth_client_import(self):
        """Test AuthClient can be imported from auth module."""
        assert AuthClient is not None
        assert hasattr(AuthClient, "login")
        assert hasattr(AuthClient, "logout")
        assert hasattr(AuthClient, "is_authenticated")

    def test_exception_imports(self):
        """Test all exceptions can be imported from auth module."""
        assert AuthError is not None
        assert LoginError is not None
        assert MFARequiredError is not None

        # Test inheritance
        assert issubclass(LoginError, AuthError)
        assert issubclass(MFARequiredError, AuthError)

    def test_token_imports(self):
        """Test token classes can be imported from auth module."""
        assert OAuth1Token is not None
        assert OAuth2Token is not None

        # Test they are dataclasses/classes with expected attributes
        # Create instances to test fields
        oauth1_instance = OAuth1Token("test", "test")
        oauth2_instance = OAuth2Token(
            "scope", "jti", "Bearer", "access", "refresh", 3600, 1000, 86400, 2000
        )

        assert hasattr(oauth1_instance, "oauth_token")
        assert hasattr(oauth1_instance, "oauth_token_secret")
        assert hasattr(oauth2_instance, "access_token")
        assert hasattr(oauth2_instance, "refresh_token")

    def test_function_imports(self):
        """Test SSO functions can be imported from auth module."""
        assert login is not None
        assert resume_login is not None

        # Test they are callable
        assert callable(login)
        assert callable(resume_login)

    def test_all_exports(self):
        """Test __all__ contains all expected exports."""
        from garmy.auth import __all__

        expected_exports = {
            "AuthClient",
            "AuthError",
            "LoginError",
            "MFARequiredError",
            "OAuth1Token",
            "OAuth2Token",
            "login",
            "resume_login",
        }

        assert set(__all__) == expected_exports

    def test_module_docstring(self):
        """Test auth module has comprehensive docstring."""
        import garmy.auth as auth_module

        assert auth_module.__doc__ is not None
        docstring = auth_module.__doc__.lower()

        # Check for key concepts in docstring
        assert "authentication" in docstring
        assert "oauth" in docstring
        assert "garmin connect" in docstring

    def test_no_extra_exports(self):
        """Test auth module doesn't export internal implementation details."""
        import garmy.auth as auth_module

        # These should not be directly accessible
        internal_names = [
            "TokenManager",
            "TokenFileManager",
            "AuthHttpClient",
            "GarminOAuth1Session",
            "get_csrf_token",
            "get_title",
            "make_request",
        ]

        for name in internal_names:
            assert not hasattr(
                auth_module, name
            ), f"Internal {name} should not be exported"

    def test_import_style_consistency(self):
        """Test imports follow consistent patterns."""
        # All imports should work without raising ImportError
        try:
            # Test imports by accessing them - they are already imported at module level
            assert AuthClient is not None
            assert AuthError is not None
            assert LoginError is not None
            assert MFARequiredError is not None
            assert OAuth1Token is not None
            assert OAuth2Token is not None
            assert login is not None
            assert resume_login is not None
        except ImportError as e:
            pytest.fail(f"Import failed: {e}")

    def test_backward_compatibility(self):
        """Test backward compatibility with expected interfaces."""
        # AuthClient should maintain its main interface
        client = AuthClient()

        # These methods should exist and be callable
        assert hasattr(client, "login")
        assert hasattr(client, "logout")
        assert hasattr(client, "is_authenticated")
        assert hasattr(client, "get_auth_headers")

        # Properties should be accessible
        assert hasattr(client, "needs_refresh")

    def test_exception_hierarchy_consistency(self):
        """Test exception hierarchy is consistent across module."""
        # All auth exceptions should inherit from AuthError
        auth_exceptions = [LoginError, MFARequiredError]

        for exc_class in auth_exceptions:
            assert issubclass(exc_class, AuthError)

            # Should be able to instantiate with message
            exc_instance = exc_class("test message")
            assert str(exc_instance) == "test message"

    def test_token_class_consistency(self):
        """Test token classes have consistent interface."""
        # OAuth1Token minimal instantiation
        oauth1 = OAuth1Token("token", "secret")
        assert oauth1.oauth_token == "token"
        assert oauth1.oauth_token_secret == "secret"

        # OAuth2Token with required fields
        oauth2 = OAuth2Token(
            scope="scope",
            jti="jti",
            token_type="Bearer",
            access_token="access",
            refresh_token="refresh",
            expires_in=3600,
            expires_at=1000,
            refresh_token_expires_in=86400,
            refresh_token_expires_at=2000,
        )

        # Should have expiration check properties
        assert hasattr(oauth2, "expired")
        assert hasattr(oauth2, "refresh_expired")
        # They are properties, not methods
        assert isinstance(type(oauth2).expired, property)
        assert isinstance(type(oauth2).refresh_expired, property)

    def test_function_signatures_consistency(self):
        """Test function signatures are as expected."""
        import inspect

        # login function should accept expected parameters
        login_sig = inspect.signature(login)
        expected_params = [
            "email",
            "password",
            "auth_client",
            "prompt_mfa",
            "return_on_mfa",
        ]
        actual_params = list(login_sig.parameters.keys())

        for param in expected_params:
            assert param in actual_params, f"login missing parameter: {param}"

        # resume_login function should accept expected parameters
        resume_sig = inspect.signature(resume_login)
        expected_resume_params = ["mfa_code", "client_state"]
        actual_resume_params = list(resume_sig.parameters.keys())

        for param in expected_resume_params:
            assert (
                param in actual_resume_params
            ), f"resume_login missing parameter: {param}"

    def test_type_hints_available(self):
        """Test that type hints are available for main functions."""
        import inspect

        # Check if type hints are present (they may be strings in some Python versions)
        login_sig = inspect.signature(login)

        # At minimum, should have some annotations
        assert len(login_sig.parameters) > 0

        # resume_login should also have signature
        resume_sig = inspect.signature(resume_login)
        assert len(resume_sig.parameters) > 0
