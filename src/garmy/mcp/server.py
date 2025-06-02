#!/usr/bin/env python3
"""Garmy MCP Server implementation.

This module provides the main MCP server class for Garmy, enabling AI assistants
to access Garmin Connect health and fitness data through the standardized MCP protocol.
"""

import logging
from typing import Any, Dict, List, Optional, Union

import anyio
from fastmcp import FastMCP

try:
    from builtins import BaseExceptionGroup  # Python 3.11+
except ImportError:
    # Python < 3.11 compatibility
    BaseExceptionGroup = Exception

from .. import APIClient, AuthClient
from ..core.discovery import MetricDiscovery
from .config import MCPConfig
from .prompts import PromptTemplates
from .resources import ResourceProviders
from .tools import AnalysisTools, AuthTools, MetricTools

logger = logging.getLogger(__name__)


class GarmyMCPServer:
    """MCP server for Garmy with authentication state management.

    Provides AI assistants access to Garmin Connect data through
    the standardized MCP protocol.

    Attributes:
        config: Server configuration.
        mcp: FastMCP server instance.
        auth_client: Garmin authentication client.
        api_client: Garmin API client.
        discovered_metrics: Discovered health metrics.
    """

    def __init__(self, config: Optional[MCPConfig] = None):
        """Initialize MCP server.

        Args:
            config: Server configuration. Uses defaults if not provided.
        """
        self.config = config or MCPConfig()
        self.mcp = FastMCP(self.config.server_name)

        # Authentication state
        self.auth_client: Optional[AuthClient] = None
        self.api_client: Optional[APIClient] = None

        # Discovered metrics
        self.discovered_metrics: Dict[str, Any] = {}

        # Setup logging
        if self.config.debug_mode:
            logging.basicConfig(level=logging.DEBUG)

        # Initialize components
        self._initialize_components()

    def _initialize_components(self):
        """Initialize all server components."""
        # Discover metrics
        self._discover_metrics()

        # Register components according to configuration
        if self.config.enable_auth_tools:
            self._register_auth_tools()

        if self.config.enable_metric_tools:
            self._register_metric_tools()

        if self.config.enable_analysis_tools:
            self._register_analysis_tools()

        if self.config.enable_resources:
            self._register_resources()

        if self.config.enable_prompts:
            self._register_prompts()

    def _discover_metrics(self):
        """Discover all available metrics."""
        try:
            self.discovered_metrics = MetricDiscovery.discover_metrics()
            MetricDiscovery.validate_metrics(self.discovered_metrics)
            logger.info(f"Discovered {len(self.discovered_metrics)} metrics")
        except Exception as e:
            logger.error(f"Error discovering metrics: {e}")
            self.discovered_metrics = {}

    def _register_auth_tools(self):
        """Register authentication tools."""
        auth_tools = AuthTools(self)
        auth_tools.register_tools(self.mcp)

    def _register_metric_tools(self):
        """Register metric access tools."""
        metric_tools = MetricTools(self)
        metric_tools.register_tools(self.mcp)

    def _register_analysis_tools(self):
        """Register data analysis tools."""
        analysis_tools = AnalysisTools(self)
        analysis_tools.register_tools(self.mcp)

    def _register_resources(self):
        """Register data reading resources."""
        resource_providers = ResourceProviders(self)
        resource_providers.register_resources(self.mcp)

    def _register_prompts(self):
        """Register prompt templates."""
        prompt_templates = PromptTemplates(self)
        prompt_templates.register_prompts(self.mcp)

    def authenticate(self, email: str, password: str) -> bool:
        """Perform authentication with Garmin Connect.

        Args:
            email: Email address.
            password: Password.

        Returns:
            True if authentication successful, False otherwise.
        """
        try:
            self.auth_client = AuthClient()
            self.api_client = APIClient(auth_client=self.auth_client)
            self.auth_client.login(email, password)
            return True
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            self.auth_client = None
            self.api_client = None
            return False

    def logout(self):
        """Perform logout from system."""
        self.auth_client = None
        self.api_client = None
        logger.info("Logged out from Garmin Connect")

    def is_authenticated(self) -> bool:
        """Check if user is authenticated.

        Returns:
            True if user is authenticated.
        """
        return bool(self.auth_client and self.api_client)

    def _validate_authentication(self) -> None:
        """Validate that user is authenticated.

        Raises:
            ValueError: If user is not authenticated.
        """
        if not self.is_authenticated():
            raise ValueError("Authentication required")

    def _validate_metric_name(self, metric_name: str) -> None:
        """Validate that metric name exists.

        Args:
            metric_name: Name of the metric to validate.

        Raises:
            ValueError: If metric name is not found.
        """
        if metric_name not in self.api_client.metrics:
            available = list(self.api_client.metrics.keys())
            raise ValueError(f"Unknown metric '{metric_name}'. Available: {available}")

    def get_metric_data(
        self, metric_name: str, date_input: Optional[Union[str]] = None
    ) -> Any:
        """Get metric data for specified date.

        Args:
            metric_name: Name of the metric.
            date_input: Date (defaults to today).

        Returns:
            Metric data or None.

        Raises:
            ValueError: If user not authenticated or metric not found.
        """
        self._validate_authentication()
        self._validate_metric_name(metric_name)
        return self.api_client.metrics[metric_name].get(date_input)

    def get_metric_history(
        self, metric_name: str, days: int = 7, end_date: Optional[str] = None
    ) -> List[Any]:
        """Get historical metric data.

        Args:
            metric_name: Name of the metric.
            days: Number of days.
            end_date: End date (defaults to today).

        Returns:
            List of metric data.

        Raises:
            ValueError: If user not authenticated or metric not found.
        """
        self._validate_authentication()
        self._validate_metric_name(metric_name)

        # Limit days according to configuration
        days = min(days, self.config.max_history_days)

        return self.api_client.metrics[metric_name].list(end=end_date, days=days)

    def format_metric_data(
        self, data: Any, metric_name: str, compact: bool = False
    ) -> str:
        """Format metric data for display using generic approach.

        Args:
            data: Metric data object.
            metric_name: Name of the metric.
            compact: Compact display mode (currently unused, kept for compatibility).

        Returns:
            Formatted string using object's __str__ method or fallback.
        """
        if not data:
            return "No data"

        try:
            # Use object's __str__ method if available and meaningful
            if hasattr(data, "__str__") and not isinstance(
                data, (str, int, float, bool)
            ):
                formatted = str(data)
                # Check if __str__ was overridden (not default object.__str__)
                if formatted and formatted != object.__str__(data):
                    return formatted

            # Fallback for objects with useful attributes
            return self._format_object_attributes(data, compact)

        except Exception as e:
            logger.error(f"Error formatting {metric_name} data: {e}")
            return f"Formatting error: {e!s}"

    def _format_object_attributes(self, data: Any, compact: bool) -> str:
        """Generic object attribute formatting as fallback.

        Args:
            data: Object to format.
            compact: Whether to use compact formatting.

        Returns:
            Formatted string showing object attributes.
        """
        if hasattr(data, "__dict__"):
            fields = data.__dict__
            result = []
            max_fields = 3 if compact else 8

            for key, value in list(fields.items())[:max_fields]:
                if value is not None and not key.startswith("_"):
                    # Format value appropriately
                    if isinstance(value, float):
                        formatted_value = f"{value:.1f}"
                    elif isinstance(value, int) and value > 1000:
                        formatted_value = f"{value:,}"
                    else:
                        formatted_value = str(value)

                    result.append(
                        f"• {key.replace('_', ' ').title()}: {formatted_value}"
                    )

            return "\n".join(result) if result else "Data available"
        else:
            return str(data)

    def run(self, transport: str = "stdio", **kwargs):
        """Start MCP server.

        Args:
            transport: Transport type ("stdio" or "streamable-http").
            **kwargs: Additional transport parameters.
        """
        # Only print debug info if explicitly in debug mode to avoid MCP protocol interference
        if self.config.debug_mode:
            self._log_debug("Starting Garmy MCP Server...")
            self._log_debug(f"Transport: {transport}")
            self._log_debug(f"Discovered metrics: {len(self.discovered_metrics)}")
            self._log_debug("Server ready!")

        try:
            self.mcp.run(transport=transport, **kwargs)
        except BaseExceptionGroup as eg:
            # Handle exception groups from anyio TaskGroup
            has_broken_resource = any(
                isinstance(exc, anyio.BrokenResourceError) for exc in eg.exceptions
            )
            if has_broken_resource and self.config.debug_mode:
                self._log_debug("MCP client disconnected (normal)")
            if not has_broken_resource:
                # Only re-raise if there are serious errors, not just disconnections
                self._log_error(
                    f"Error in MCP server: {eg}", eg if self.config.debug_mode else None
                )
                raise
        except anyio.BrokenResourceError:
            # Normal client disconnection
            if self.config.debug_mode:
                self._log_debug("MCP client disconnected (normal)")
        except Exception as e:
            self._log_error(
                f"Error running MCP server: {e}", e if self.config.debug_mode else None
            )
            raise

    def _log_error(self, message: str, exception: Optional[Exception] = None) -> None:
        """Log error message with optional traceback.

        Args:
            message: Error message to log.
            exception: Optional exception for traceback.
        """
        # Use stderr for logging to avoid MCP protocol interference
        import sys

        sys.stderr.write(f"{message}\n")
        sys.stderr.flush()
        if exception and self.config.debug_mode:
            import traceback

            traceback.print_exception(
                type(exception), exception, exception.__traceback__, file=sys.stderr
            )

    def _log_debug(self, message: str) -> None:
        """Log debug message to stderr if debug mode is enabled."""
        if self.config.debug_mode:
            import sys

            sys.stderr.write(f"DEBUG: {message}\n")
            sys.stderr.flush()
