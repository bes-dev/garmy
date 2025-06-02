"""Resource providers for Garmy MCP server.

Provides structured data resources for AI assistants.
"""

import json
import logging
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP

    from ..server import GarmyMCPServer

logger = logging.getLogger(__name__)


class ResourceProviders:
    """Resource providers for MCP server."""

    def __init__(self, server: "GarmyMCPServer"):
        """Initialize resource providers.

        Args:
            server: The parent MCP server instance.
        """
        self.server = server

    def register_resources(self, mcp: "FastMCP"):
        """Register resources with the MCP server.

        Args:
            mcp: FastMCP server instance to register resources with.
        """

        @mcp.resource("garmy://metrics/available")
        async def available_metrics_resource():
            """List of all available metrics."""
            metrics_info = []
            for name, config in self.server.discovered_metrics.items():
                metrics_info.append(
                    {
                        "name": name,
                        "description": config.description,
                        "endpoint": config.endpoint,
                        "deprecated": config.deprecated,
                        "class": config.metric_class.__name__,
                    }
                )

            return json.dumps(metrics_info, indent=2, ensure_ascii=False)

        @mcp.resource("garmy://status/auth")
        async def auth_status_resource():
            """Authentication status information."""
            status = {
                "authenticated": self.server.is_authenticated(),
                "timestamp": datetime.now().isoformat(),
                "available_metrics": len(self.server.discovered_metrics),
            }

            if self.server.api_client:
                try:
                    status["api_metrics_count"] = len(
                        list(self.server.api_client.metrics.keys())
                    )
                except Exception:
                    status["api_metrics_count"] = 0

            return json.dumps(status, indent=2, ensure_ascii=False)

        @mcp.resource("garmy://config/server")
        async def server_config_resource():
            """Server configuration information."""
            config_info = {
                "server_name": self.server.config.server_name,
                "server_version": self.server.config.server_version,
                "features": {
                    "auth_tools": self.server.config.enable_auth_tools,
                    "metric_tools": self.server.config.enable_metric_tools,
                    "analysis_tools": self.server.config.enable_analysis_tools,
                    "resources": self.server.config.enable_resources,
                    "prompts": self.server.config.enable_prompts,
                },
                "limits": {
                    "max_history_days": self.server.config.max_history_days,
                    "default_analysis_period": self.server.config.default_analysis_period,
                    "cache_enabled": self.server.config.cache_enabled,
                    "cache_size": self.server.config.cache_size,
                },
                "debug_mode": self.server.config.debug_mode,
            }

            return json.dumps(config_info, indent=2, ensure_ascii=False)
