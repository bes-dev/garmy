"""Configuration for Garmy MCP server.

This module provides configuration classes and utilities for customizing
the behavior of the Garmy MCP server.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class MCPConfig:
    """Configuration for Garmy MCP server.

    Attributes:
        server_name: Name of the MCP server.
        server_version: Version of the MCP server.
        enable_auth_tools: Whether to enable authentication tools.
        enable_metric_tools: Whether to enable metric access tools.
        enable_analysis_tools: Whether to enable data analysis tools.
        enable_resources: Whether to enable MCP resources.
        enable_prompts: Whether to enable MCP prompts.
        cache_enabled: Whether to enable data caching.
        cache_size: Maximum number of cached items.
        max_history_days: Maximum days for historical data requests.
        default_analysis_period: Default period for analysis tools (days).
        custom_tool_config: Custom configuration for tools.
        debug_mode: Whether to enable debug logging.
    """

    # Server identification
    server_name: str = "Garmy Health & Fitness Server"
    server_version: str = "1.0.0"

    # Feature toggles
    enable_auth_tools: bool = True
    enable_metric_tools: bool = True
    enable_analysis_tools: bool = True
    enable_resources: bool = True
    enable_prompts: bool = True

    # Performance settings
    cache_enabled: bool = False
    cache_size: int = 100

    # Data limits
    max_history_days: int = 365
    default_analysis_period: int = 30

    # Custom configuration
    custom_tool_config: Dict[str, Any] = field(default_factory=dict)

    # Development settings
    debug_mode: bool = False

    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.max_history_days <= 0:
            raise ValueError("max_history_days must be positive")

        if self.default_analysis_period <= 0:
            raise ValueError("default_analysis_period must be positive")

        if self.cache_size <= 0:
            raise ValueError("cache_size must be positive")

    @classmethod
    def for_development(cls) -> "MCPConfig":
        """Create a configuration optimized for development.

        Returns:
            MCPConfig with development-friendly settings.
        """
        return cls(
            debug_mode=True, cache_enabled=True, cache_size=50, max_history_days=90
        )

    @classmethod
    def for_production(cls) -> "MCPConfig":
        """Create a configuration optimized for production.

        Returns:
            MCPConfig with production-ready settings.
        """
        return cls(
            debug_mode=False, cache_enabled=True, cache_size=200, max_history_days=365
        )

    @classmethod
    def minimal(cls) -> "MCPConfig":
        """Create a minimal configuration with only basic features.

        Returns:
            MCPConfig with minimal feature set.
        """
        return cls(
            enable_analysis_tools=False,
            enable_resources=False,
            enable_prompts=False,
            cache_enabled=False,
            max_history_days=30,
        )


@dataclass
class ToolConfig:
    """Configuration for individual MCP tools.

    Attributes:
        enabled: Whether the tool is enabled.
        rate_limit: Maximum calls per minute (0 = no limit).
        timeout_seconds: Timeout for tool execution.
        custom_params: Custom parameters for the tool.
    """

    enabled: bool = True
    rate_limit: int = 0  # 0 = no limit
    timeout_seconds: int = 30
    custom_params: Dict[str, Any] = field(default_factory=dict)


class ConfigManager:
    """Manager for MCP server configuration.

    Provides utilities for loading, validating, and updating configuration.
    """

    @staticmethod
    def load_from_env() -> MCPConfig:
        """Load configuration from environment variables.

        Environment variables:
            GARMY_MCP_DEBUG: Enable debug mode (true/false).
            GARMY_MCP_CACHE_ENABLED: Enable caching (true/false).
            GARMY_MCP_CACHE_SIZE: Cache size (integer).
            GARMY_MCP_MAX_HISTORY_DAYS: Max history days (integer).
            GARMIN_EMAIL: Garmin Connect email (for auto-authentication).
            GARMIN_PASSWORD: Garmin Connect password (for auto-authentication).

        Returns:
            MCPConfig loaded from environment.
        """
        import os

        def get_bool(key: str, default: bool) -> bool:
            value = os.getenv(key, "").lower()
            if value in ("true", "1", "yes", "on"):
                return True
            elif value in ("false", "0", "no", "off"):
                return False
            return default

        def get_int(key: str, default: int) -> int:
            try:
                return int(os.getenv(key, str(default)))
            except ValueError:
                return default

        return MCPConfig(
            debug_mode=get_bool("GARMY_MCP_DEBUG", False),
            cache_enabled=get_bool("GARMY_MCP_CACHE_ENABLED", False),
            cache_size=get_int("GARMY_MCP_CACHE_SIZE", 100),
            max_history_days=get_int("GARMY_MCP_MAX_HISTORY_DAYS", 365),
            default_analysis_period=get_int("GARMY_MCP_DEFAULT_ANALYSIS_PERIOD", 30),
        )

    @staticmethod
    def validate_config(config: MCPConfig) -> None:
        """Validate MCP configuration.

        Args:
            config: Configuration to validate.

        Raises:
            ValueError: If configuration is invalid.
        """
        if not config.server_name.strip():
            raise ValueError("server_name cannot be empty")

        if not config.server_version.strip():
            raise ValueError("server_version cannot be empty")

        # Additional validation happens in MCPConfig.__post_init__

    @staticmethod
    def get_garmin_credentials() -> tuple[Optional[str], Optional[str]]:
        """Get Garmin Connect credentials from environment variables.

        Returns:
            Tuple of (email, password) from environment variables.
            Both may be None if not set in environment.
        """
        import os

        return os.getenv("GARMIN_EMAIL"), os.getenv("GARMIN_PASSWORD")

    @staticmethod
    def has_garmin_credentials() -> bool:
        """Check if Garmin Connect credentials are available in environment.

        Returns:
            True if both email and password are set in environment.
        """
        email, password = ConfigManager.get_garmin_credentials()
        return bool(email and password)
