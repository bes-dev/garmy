"""
Comprehensive tests for MCP authentication tools module.

Tests all functions and edge cases to achieve 100% coverage.
"""

import os
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastmcp import Context

from garmy.mcp.tools.auth import AuthTools


class TestAuthTools:
    """Test suite for AuthTools class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_server = Mock()
        self.auth_tools = AuthTools(self.mock_server)
        self.mock_ctx = AsyncMock(spec=Context)

    def test_init(self):
        """Test AuthTools initialization."""
        server = Mock()
        auth_tools = AuthTools(server)
        assert auth_tools.server is server

    def test_resolve_credentials_with_provided_credentials(self):
        """Test resolving credentials when both email and password are provided."""
        email = "test@example.com"
        password = "test123"

        result_email, result_password, is_manual = self.auth_tools._resolve_credentials(
            email, password
        )

        assert result_email == email
        assert result_password == password
        assert is_manual is True

    def test_resolve_credentials_with_partial_credentials(self):
        """Test resolving credentials with only email provided."""
        with (
            patch.dict(
                os.environ,
                {"GARMIN_EMAIL": "env@example.com", "GARMIN_PASSWORD": "envpass"},
            ),
            patch("garmy.mcp.tools.auth.ConfigManager") as mock_config,
        ):
            mock_config.get_garmin_credentials.return_value = (
                "env@example.com",
                "envpass",
            )

            result_email, result_password, is_manual = (
                self.auth_tools._resolve_credentials("test@example.com", "")
            )

            assert result_email == "test@example.com"
            assert result_password == "envpass"
            assert is_manual is False

    def test_resolve_credentials_from_environment(self):
        """Test resolving credentials from environment variables."""
        with patch("garmy.mcp.tools.auth.ConfigManager") as mock_config:
            mock_config.get_garmin_credentials.return_value = (
                "env@example.com",
                "envpass",
            )

            result_email, result_password, is_manual = (
                self.auth_tools._resolve_credentials("", "")
            )

            assert result_email == "env@example.com"
            assert result_password == "envpass"
            assert is_manual is False

    def test_resolve_credentials_no_credentials_available(self):
        """Test resolving credentials when none are available."""
        with patch("garmy.mcp.tools.auth.ConfigManager") as mock_config:
            mock_config.get_garmin_credentials.return_value = (None, None)

            with pytest.raises(ValueError, match="No credentials provided"):
                self.auth_tools._resolve_credentials("", "")

    def test_resolve_credentials_missing_email(self):
        """Test resolving credentials when email is missing."""
        with patch("garmy.mcp.tools.auth.ConfigManager") as mock_config:
            mock_config.get_garmin_credentials.return_value = (None, "password")

            with pytest.raises(ValueError, match="No credentials provided"):
                self.auth_tools._resolve_credentials("", "test123")

    def test_resolve_credentials_missing_password(self):
        """Test resolving credentials when password is missing."""
        with patch("garmy.mcp.tools.auth.ConfigManager") as mock_config:
            mock_config.get_garmin_credentials.return_value = ("email@test.com", None)

            with pytest.raises(ValueError, match="No credentials provided"):
                self.auth_tools._resolve_credentials("test@example.com", "")

    def test_mask_email_valid_email(self):
        """Test email masking for valid email addresses."""
        assert self.auth_tools._mask_email("test@example.com") == "tes***@example.com"
        assert self.auth_tools._mask_email("a@b.com") == "a***@b.com"
        assert (
            self.auth_tools._mask_email("verylongemail@domain.org")
            == "ver***@domain.org"
        )

    def test_mask_email_invalid_email(self):
        """Test email masking for invalid email format."""
        assert self.auth_tools._mask_email("notanemail") == "***"
        assert self.auth_tools._mask_email("") == "***"
        assert self.auth_tools._mask_email("no_at_symbol") == "***"

    @pytest.mark.asyncio
    async def test_garmin_login_success_with_manual_credentials(self):
        """Test successful login with manually provided credentials."""
        # Setup mocks
        self.mock_server.authenticate.return_value = True

        # Create mock MCP and register tools
        mock_mcp = Mock()
        tool_functions = {}

        def mock_tool(func=None):
            def decorator(f):
                tool_functions[f.__name__] = f
                return f

            return decorator(func) if func else decorator

        mock_mcp.tool = mock_tool
        self.auth_tools.register_tools(mock_mcp)

        # Call the registered function
        result = await tool_functions["garmin_login"](
            self.mock_ctx, "test@example.com", "password123"
        )

        # Verify results
        assert "Successfully logged into Garmin Connect using manual input" in result
        self.mock_server.authenticate.assert_called_once_with(
            "test@example.com", "password123"
        )
        self.mock_ctx.info.assert_any_call(
            "Attempting login for user: tes***@example.com"
        )
        self.mock_ctx.info.assert_any_call(
            "WARNING: Credentials passed manually may be visible to Anthropic servers"
        )
        self.mock_ctx.info.assert_any_call("Successfully logged into Garmin Connect")

    @pytest.mark.asyncio
    async def test_garmin_login_success_with_env_credentials(self):
        """Test successful login with environment credentials."""
        # Setup mocks
        self.mock_server.authenticate.return_value = True

        with patch("garmy.mcp.tools.auth.ConfigManager") as mock_config:
            mock_config.get_garmin_credentials.return_value = (
                "env@example.com",
                "envpass",
            )

            # Create mock MCP and register tools
            mock_mcp = Mock()
            tool_functions = {}

            def mock_tool(func=None):
                def decorator(f):
                    tool_functions[f.__name__] = f
                    return f

                return decorator(func) if func else decorator

            mock_mcp.tool = mock_tool
            self.auth_tools.register_tools(mock_mcp)

            # Call the registered function with empty credentials
            result = await tool_functions["garmin_login"](self.mock_ctx, "", "")

            # Verify results
            assert (
                "Successfully logged into Garmin Connect using environment variables"
                in result
            )
            self.mock_server.authenticate.assert_called_once_with(
                "env@example.com", "envpass"
            )
            self.mock_ctx.info.assert_any_call(
                "Using credentials from environment variables (secure)"
            )

    @pytest.mark.asyncio
    async def test_garmin_login_failure(self):
        """Test failed login attempt."""
        # Setup mocks
        self.mock_server.authenticate.return_value = False

        # Create mock MCP and register tools
        mock_mcp = Mock()
        tool_functions = {}

        def mock_tool(func=None):
            def decorator(f):
                tool_functions[f.__name__] = f
                return f

            return decorator(func) if func else decorator

        mock_mcp.tool = mock_tool
        self.auth_tools.register_tools(mock_mcp)

        # Call the registered function
        result = await tool_functions["garmin_login"](
            self.mock_ctx, "test@example.com", "wrongpass"
        )

        # Verify results
        assert "Login failed. Please check your credentials." in result
        self.mock_ctx.error.assert_called_once_with("Login failed")

    @pytest.mark.asyncio
    async def test_garmin_login_no_credentials_error(self):
        """Test login with no credentials available."""
        with patch("garmy.mcp.tools.auth.ConfigManager") as mock_config:
            mock_config.get_garmin_credentials.return_value = (None, None)

            # Create mock MCP and register tools
            mock_mcp = Mock()
            tool_functions = {}

            def mock_tool(func=None):
                def decorator(f):
                    tool_functions[f.__name__] = f
                    return f

                return decorator(func) if func else decorator

            mock_mcp.tool = mock_tool
            self.auth_tools.register_tools(mock_mcp)

            # Call the registered function
            result = await tool_functions["garmin_login"](self.mock_ctx, "", "")

            # Verify results
            assert "Authentication failed: No credentials provided" in result
            self.mock_ctx.error.assert_called_once_with("No credentials provided")

    @pytest.mark.asyncio
    async def test_garmin_login_exception(self):
        """Test login with unexpected exception."""
        # Setup mocks
        self.mock_server.authenticate.side_effect = Exception("Connection error")

        # Create mock MCP and register tools
        mock_mcp = Mock()
        tool_functions = {}

        def mock_tool(func=None):
            def decorator(f):
                tool_functions[f.__name__] = f
                return f

            return decorator(func) if func else decorator

        mock_mcp.tool = mock_tool
        self.auth_tools.register_tools(mock_mcp)

        # Call the registered function
        result = await tool_functions["garmin_login"](
            self.mock_ctx, "test@example.com", "password123"
        )

        # Verify results
        assert "Login error: Connection error" in result
        self.mock_ctx.error.assert_called_once_with("Login error: Connection error")

    @pytest.mark.asyncio
    async def test_garmin_auto_login(self):
        """Test automatic login using environment variables."""
        with patch("garmy.mcp.tools.auth.ConfigManager") as mock_config:
            mock_config.get_garmin_credentials.return_value = (
                "auto@example.com",
                "autopass",
            )
            self.mock_server.authenticate.return_value = True

            # Create mock MCP and register tools
            mock_mcp = Mock()
            tool_functions = {}

            def mock_tool(func=None):
                def decorator(f):
                    tool_functions[f.__name__] = f
                    return f

                return decorator(func) if func else decorator

            mock_mcp.tool = mock_tool
            self.auth_tools.register_tools(mock_mcp)

            # Call the registered function
            result = await tool_functions["garmin_auto_login"](self.mock_ctx)

            # Verify results
            assert (
                "Successfully logged into Garmin Connect using environment variables"
                in result
            )
            self.mock_server.authenticate.assert_called_once_with(
                "auto@example.com", "autopass"
            )

    @pytest.mark.asyncio
    async def test_garmin_logout_when_authenticated(self):
        """Test logout when user is authenticated."""
        # Setup mocks
        self.mock_server.is_authenticated.return_value = True

        # Create mock MCP and register tools
        mock_mcp = Mock()
        tool_functions = {}

        def mock_tool(func=None):
            def decorator(f):
                tool_functions[f.__name__] = f
                return f

            return decorator(func) if func else decorator

        mock_mcp.tool = mock_tool
        self.auth_tools.register_tools(mock_mcp)

        # Call the registered function
        result = await tool_functions["garmin_logout"](self.mock_ctx)

        # Verify results
        assert "Successfully logged out." in result
        self.mock_server.logout.assert_called_once()
        self.mock_ctx.info.assert_called_once_with("Logged out of Garmin Connect")

    @pytest.mark.asyncio
    async def test_garmin_logout_when_not_authenticated(self):
        """Test logout when user is not authenticated."""
        # Setup mocks
        self.mock_server.is_authenticated.return_value = False

        # Create mock MCP and register tools
        mock_mcp = Mock()
        tool_functions = {}

        def mock_tool(func=None):
            def decorator(f):
                tool_functions[f.__name__] = f
                return f

            return decorator(func) if func else decorator

        mock_mcp.tool = mock_tool
        self.auth_tools.register_tools(mock_mcp)

        # Call the registered function
        result = await tool_functions["garmin_logout"](self.mock_ctx)

        # Verify results
        assert "User was not authenticated." in result
        self.mock_server.logout.assert_not_called()

    @pytest.mark.asyncio
    async def test_garmin_logout_exception(self):
        """Test logout with exception."""
        # Setup mocks
        self.mock_server.is_authenticated.return_value = True
        self.mock_server.logout.side_effect = Exception("Logout error")

        # Create mock MCP and register tools
        mock_mcp = Mock()
        tool_functions = {}

        def mock_tool(func=None):
            def decorator(f):
                tool_functions[f.__name__] = f
                return f

            return decorator(func) if func else decorator

        mock_mcp.tool = mock_tool
        self.auth_tools.register_tools(mock_mcp)

        # Call the registered function
        result = await tool_functions["garmin_logout"](self.mock_ctx)

        # Verify results
        assert "Logout error: Logout error" in result
        self.mock_ctx.error.assert_called_once_with("Logout error: Logout error")

    @pytest.mark.asyncio
    async def test_check_auth_status_authenticated(self):
        """Test auth status check when authenticated."""
        # Setup mocks
        self.mock_server.is_authenticated.return_value = True
        self.mock_server.api_client.metrics.keys.return_value = [
            "sleep",
            "steps",
            "heart_rate",
        ]

        # Create mock MCP and register tools
        mock_mcp = Mock()
        tool_functions = {}

        def mock_tool(func=None):
            def decorator(f):
                tool_functions[f.__name__] = f
                return f

            return decorator(func) if func else decorator

        mock_mcp.tool = mock_tool
        self.auth_tools.register_tools(mock_mcp)

        # Call the registered function
        result = await tool_functions["check_auth_status"](self.mock_ctx)

        # Verify results
        assert "Authenticated with Garmin Connect. 3 metrics available." in result
        self.mock_ctx.info.assert_called_once_with(
            "Authenticated. Available metrics: 3"
        )

    @pytest.mark.asyncio
    async def test_check_auth_status_authenticated_with_api_error(self):
        """Test auth status check when authenticated but API has issues."""
        # Setup mocks
        self.mock_server.is_authenticated.return_value = True
        self.mock_server.api_client.metrics.keys.side_effect = Exception("API Error")

        # Create mock MCP and register tools
        mock_mcp = Mock()
        tool_functions = {}

        def mock_tool(func=None):
            def decorator(f):
                tool_functions[f.__name__] = f
                return f

            return decorator(func) if func else decorator

        mock_mcp.tool = mock_tool
        self.auth_tools.register_tools(mock_mcp)

        # Call the registered function
        result = await tool_functions["check_auth_status"](self.mock_ctx)

        # Verify results
        assert "Possible authentication issues: API Error" in result
        self.mock_ctx.warning.assert_called_once_with(
            "Authentication issues: API Error"
        )

    @pytest.mark.asyncio
    async def test_check_auth_status_not_authenticated(self):
        """Test auth status check when not authenticated."""
        # Setup mocks
        self.mock_server.is_authenticated.return_value = False

        # Create mock MCP and register tools
        mock_mcp = Mock()
        tool_functions = {}

        def mock_tool(func=None):
            def decorator(f):
                tool_functions[f.__name__] = f
                return f

            return decorator(func) if func else decorator

        mock_mcp.tool = mock_tool
        self.auth_tools.register_tools(mock_mcp)

        # Call the registered function
        result = await tool_functions["check_auth_status"](self.mock_ctx)

        # Verify results
        assert "Not authenticated. Use garmin_login to log in." in result


if __name__ == "__main__":
    pytest.main([__file__])
