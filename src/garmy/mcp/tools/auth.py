"""Authentication tools for Garmy MCP server.

Provides tools for logging in/out of Garmin Connect and checking authentication status.
"""

import logging
from typing import TYPE_CHECKING

from fastmcp import Context

if TYPE_CHECKING:
    from fastmcp import FastMCP

    from ..server import GarmyMCPServer

logger = logging.getLogger(__name__)


class AuthTools:
    """Authentication tools for MCP server."""

    def __init__(self, server: "GarmyMCPServer"):
        """
        Initialize authentication tools.

        Args:
            server: The parent MCP server instance
        """
        self.server = server

    def _resolve_credentials(self, email: str, password: str) -> tuple[str, str, bool]:
        """Resolve final credentials and determine source.

        Args:
            email: Provided email (may be empty).
            password: Provided password (may be empty).

        Returns:
            Tuple of (final_email, final_password, is_manual).

        Raises:
            ValueError: If no credentials are available.
        """
        from ..config import ConfigManager

        # Use provided credentials or fall back to environment variables
        final_email = email or None
        final_password = password or None

        if not final_email or not final_password:
            env_email, env_password = ConfigManager.get_garmin_credentials()
            final_email = final_email or env_email
            final_password = final_password or env_password

        if not final_email or not final_password:
            raise ValueError(
                "No credentials provided. Either provide email and password manually or set GARMIN_EMAIL and GARMIN_PASSWORD environment variables."
            )

        is_manual = bool(email and password)
        return final_email, final_password, is_manual

    def _mask_email(self, email: str) -> str:
        """Mask email for secure logging."""
        if "@" not in email:
            return "***"
        parts = email.split("@")
        return f"{parts[0][:3]}***@{parts[1]}"

    def register_tools(self, mcp: "FastMCP"):
        """
        Register authentication tools with the MCP server.

        Args:
            mcp: FastMCP server instance to register tools with
        """

        @mcp.tool()
        async def garmin_login(
            ctx: Context, email: str = "", password: str = ""
        ) -> str:
            """Log into Garmin Connect with credentials.

            Will automatically use environment variables GARMIN_EMAIL and GARMIN_PASSWORD
            if no credentials are provided manually.

            Args:
                email: Garmin Connect email address (optional if set in environment).
                password: Garmin Connect password (optional if set in environment).
            """
            try:
                final_email, final_password, is_manual = self._resolve_credentials(
                    email, password
                )
                masked_email = self._mask_email(final_email)

                # Log attempt with security warning
                await ctx.info(f"Attempting login for user: {masked_email}")
                if is_manual:
                    await ctx.info(
                        "WARNING: Credentials passed manually may be visible to Anthropic servers"
                    )
                else:
                    await ctx.info(
                        "Using credentials from environment variables (secure)"
                    )

                success = self.server.authenticate(final_email, final_password)

                if success:
                    await ctx.info("Successfully logged into Garmin Connect")
                    source = "manual input" if is_manual else "environment variables"
                    return f"Successfully logged into Garmin Connect using {source}. All health metrics are now available."
                else:
                    await ctx.error("Login failed")
                    return "Login failed. Please check your credentials."

            except ValueError as e:
                await ctx.error("No credentials provided")
                return f"Authentication failed: {e!s}"
            except Exception as e:
                await ctx.error(f"Login error: {e!s}")
                return f"Login error: {e!s}"

        @mcp.tool()
        async def garmin_auto_login(ctx: Context) -> str:
            """Automatically log into Garmin Connect using environment variables.

            Uses GARMIN_EMAIL and GARMIN_PASSWORD environment variables.
            This is the most secure way to authenticate as credentials never
            pass through Claude/Anthropic servers.
            """
            # Delegate to garmin_login with empty credentials (will use env vars)
            return await garmin_login(ctx, "", "")

        @mcp.tool()
        async def garmin_logout(ctx: Context) -> str:
            """Log out of Garmin Connect."""
            try:
                if self.server.is_authenticated():
                    self.server.logout()
                    await ctx.info("Logged out of Garmin Connect")
                    return "Successfully logged out."
                else:
                    return "User was not authenticated."
            except Exception as e:
                await ctx.error(f"Logout error: {e!s}")
                return f"Logout error: {e!s}"

        @mcp.tool()
        async def check_auth_status(ctx: Context) -> str:
            """Check authentication status."""
            if self.server.is_authenticated():
                try:
                    # Check API availability by getting metrics list
                    available_metrics = list(self.server.api_client.metrics.keys())
                    await ctx.info(
                        f"Authenticated. Available metrics: {len(available_metrics)}"
                    )
                    return f"Authenticated with Garmin Connect. {len(available_metrics)} metrics available."
                except Exception as e:
                    await ctx.warning(f"Authentication issues: {e}")
                    return f"Possible authentication issues: {e}"
            else:
                return "Not authenticated. Use garmin_login to log in."
