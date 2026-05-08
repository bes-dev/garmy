"""
Garmy Configuration Constants.

This module contains all configuration constants and magic numbers used throughout
the garmy library. This centralizes configuration and makes values easily adjustable.

Configuration categories:
- HTTP settings (status codes, timeouts, retries)
- Concurrency settings (worker limits, thread pool sizes)
- Cache settings (size limits, TTL values)
- User agent strings and API compatibility
- Error handling constants
- Data parsing configuration
"""

import os
from dataclasses import dataclass
from typing import ClassVar, List, Optional

# =============================================================================
# HTTP Configuration
# =============================================================================


class HTTPStatus:
    """HTTP status codes used throughout the library."""

    # Success codes
    OK = 200
    NO_CONTENT = 204

    # Client error codes
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    REQUEST_TIMEOUT = 408
    TOO_MANY_REQUESTS = 429

    # Server error codes
    INTERNAL_SERVER_ERROR = 500
    BAD_GATEWAY = 502
    SERVICE_UNAVAILABLE = 503
    GATEWAY_TIMEOUT = 504

    # Retry-able status codes
    RETRYABLE_CODES: ClassVar[List[int]] = [
        REQUEST_TIMEOUT,
        TOO_MANY_REQUESTS,
        INTERNAL_SERVER_ERROR,
        BAD_GATEWAY,
        SERVICE_UNAVAILABLE,
        GATEWAY_TIMEOUT,
    ]


class Timeouts:
    """Timeout configuration for different operations."""

    # HTTP request timeouts (seconds)
    DEFAULT_REQUEST = 10
    AUTH_REQUEST = 15
    LONG_REQUEST = 30

    # Concurrent operation timeouts (seconds)
    THREAD_POOL_SHUTDOWN = 300  # 5 minutes
    INDIVIDUAL_TASK = 30

    # Retry configuration
    DEFAULT_RETRIES = 3
    AUTH_RETRIES = 2
    BACKOFF_FACTOR = 0.5


class Concurrency:
    """Concurrency and threading configuration."""

    # Worker limits
    MIN_WORKERS = 1
    MAX_WORKERS = 50
    OPTIMAL_MIN_WORKERS = 4
    OPTIMAL_MAX_WORKERS = 20
    CPU_MULTIPLIER = 3

    # Thread pool configuration
    DEFAULT_POOL_SIZE = 10


class CacheConfig:
    """Cache size limits and configuration."""

    # Memory cache limits
    DATETIME_CACHE_SIZE = 512
    STRESS_READINGS_CACHE_SIZE = 256
    KEY_MEMO_CACHE_SIZE = 1000
    METRIC_DATA_CACHE_SIZE = 100

    # Cache management
    CACHE_CLEAR_THRESHOLD = 1000


# =============================================================================
# User Agent Configuration
# =============================================================================


class UserAgents:
    """User agent strings for API compatibility."""

    # Default garmy user agent
    DEFAULT = "garmy/1.0"

    # iOS app user agent for API compatibility
    IOS_APP = "GCM-iOS-5.12.24"

    # Android app user agent for authentication
    ANDROID_APP = "com.garmin.android.apps.connectmobile"


class AppHeaders:
    """Additional headers for mobile app compatibility."""

    # iOS app version and platform info
    IOS_APP_VERSION = "5.12"
    IOS_BUILD_VERSION = "5.12.24"
    IOS_PLATFORM = "iOS"
    IOS_PLATFORM_VERSION = "18.4.1"

    # Garmin-specific headers
    GARMIN_CLIENT_PLATFORM = "iOS"
    GARMIN_USER_AGENT_PREFIX = "com.garmin.connect.mobile"

    @classmethod
    def get_ios_headers(cls) -> dict:
        """Get complete set of iOS app headers for maximum compatibility."""
        return {
            "User-Agent": UserAgents.IOS_APP,
            "x-app-ver": cls.IOS_APP_VERSION,
            "x-garmin-user-agent": f"{cls.GARMIN_USER_AGENT_PREFIX}/{cls.IOS_BUILD_VERSION};;Apple/iPhone13,4/;{cls.IOS_PLATFORM}/{cls.IOS_PLATFORM_VERSION};CFNetwork/1.0(Darwin/24.4.0)",
            "garmin-client-platform": cls.GARMIN_CLIENT_PLATFORM,
            "garmin-client-platform-version": cls.IOS_PLATFORM_VERSION,
            "accept": "*/*",
            "accept-language": "en-GB,en;q=0.9",
            "accept-encoding": "gzip, deflate, br",
        }


# =============================================================================
# API Endpoints and URLs
# =============================================================================


class OAuthCredentials:
    """OAuth consumer credentials for Garmin Connect API.

    These credentials are extracted from the official Garmin Connect mobile app
    and are required for OAuth 1.0a authentication flow.

    To extract fresh credentials if these become invalid:
    1. See docs/oauth-credentials-extraction.md for detailed instructions
    2. Use mitmproxy to intercept mobile app traffic
    3. Look for GET /oauth-service/oauth/tokens/consumer endpoint
    4. Override using environment variables if needed
    """

    # Consumer key from Authorization header, secret from S3 (both public)
    DEFAULT_CONSUMER_KEY = "fc3e99d2-118c-44b8-8ae3-03370dde24c0"
    DEFAULT_CONSUMER_SECRET = "E08WAR897WEy2knn7aFBrvegVAf0AFdWBBF"  # nosec B105

    # Dynamic endpoint for fresh credentials (requires authentication)
    DYNAMIC_CONSUMER_ENDPOINT = "/oauth-service/oauth/tokens/consumer"


class Endpoints:
    """External URLs and API endpoints."""

    # Garmin Connect API base URLs
    CONNECT_API_BASE = "https://connectapi.garmin.com"
    SSO_BASE = "https://sso.garmin.com"


# =============================================================================
# Data Processing Configuration
# =============================================================================


class DataLimits:
    """Limits for data processing operations."""

    # Text and content limits
    MAX_LINE_LENGTH = 2000
    MAX_LOG_MESSAGE_LENGTH = 1000

    # Array processing
    MIN_ARRAY_LENGTH = 2
    BODY_BATTERY_ARRAY_LENGTH = 4

    # Timestamp conversion
    MILLISECOND_DIVISOR = 1000


class ErrorCodes:
    """System error codes used in error handling."""

    # Filesystem errno codes
    NO_SPACE_LEFT = 28
    READ_ONLY_FILESYSTEM = 30
    FILESYSTEM_ERRORS: ClassVar[List[int]] = [NO_SPACE_LEFT, READ_ONLY_FILESYSTEM]


# =============================================================================
# Configuration Management
# =============================================================================


@dataclass
class GarmyConfig:
    """Main configuration class that can be customized."""

    # HTTP settings
    request_timeout: int = Timeouts.DEFAULT_REQUEST
    auth_timeout: int = Timeouts.AUTH_REQUEST
    retries: int = Timeouts.DEFAULT_RETRIES
    backoff_factor: float = Timeouts.BACKOFF_FACTOR

    # Concurrency settings
    max_workers: int = Concurrency.MAX_WORKERS
    optimal_min_workers: int = Concurrency.OPTIMAL_MIN_WORKERS
    optimal_max_workers: int = Concurrency.OPTIMAL_MAX_WORKERS

    # Cache settings
    datetime_cache_size: int = CacheConfig.DATETIME_CACHE_SIZE
    key_cache_size: int = CacheConfig.KEY_MEMO_CACHE_SIZE
    metric_cache_size: int = CacheConfig.METRIC_DATA_CACHE_SIZE

    # User agents
    default_user_agent: str = UserAgents.DEFAULT
    ios_user_agent: str = UserAgents.IOS_APP
    android_user_agent: str = UserAgents.ANDROID_APP

    # OAuth credentials with environment override support
    oauth_consumer_key: str = ""
    oauth_consumer_secret: str = ""

    # Profile path for multi-user support
    # When set, tokens and database are stored/loaded from this directory
    profile_path: Optional[str] = None

    @classmethod
    def from_environment(cls) -> "GarmyConfig":
        """Create configuration from environment variables."""

        def safe_int(env_var: str, default: int) -> int:
            """Safely convert environment variable to int, using default on error."""
            try:
                return int(os.getenv(env_var, default))
            except (ValueError, TypeError):
                return default

        return cls(
            request_timeout=safe_int("GARMY_REQUEST_TIMEOUT", cls.request_timeout),
            auth_timeout=safe_int("GARMY_AUTH_TIMEOUT", cls.auth_timeout),
            retries=safe_int("GARMY_RETRIES", cls.retries),
            max_workers=safe_int("GARMY_MAX_WORKERS", cls.max_workers),
            datetime_cache_size=safe_int(
                "GARMY_DATETIME_CACHE_SIZE", cls.datetime_cache_size
            ),
            key_cache_size=safe_int("GARMY_KEY_CACHE_SIZE", cls.key_cache_size),
            metric_cache_size=safe_int(
                "GARMY_METRIC_CACHE_SIZE", cls.metric_cache_size
            ),
            oauth_consumer_key=os.getenv(
                "GARMY_OAUTH_CONSUMER_KEY", OAuthCredentials.DEFAULT_CONSUMER_KEY
            ),
            oauth_consumer_secret=os.getenv(
                "GARMY_OAUTH_CONSUMER_SECRET", OAuthCredentials.DEFAULT_CONSUMER_SECRET
            ),
            profile_path=os.getenv("GARMY_PROFILE_PATH"),
        )


# =============================================================================
# Global Configuration Instance
# =============================================================================


class ConfigManager:
    """Thread-safe configuration manager using singleton pattern."""

    _instance: Optional["ConfigManager"] = None
    _config: Optional[GarmyConfig] = None

    def __new__(cls) -> "ConfigManager":
        """Create or return the singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_config(self) -> GarmyConfig:
        """Get the current configuration."""
        if self._config is None:
            self._config = GarmyConfig.from_environment()
        return self._config

    def set_config(self, config: GarmyConfig) -> None:
        """Set the configuration."""
        self._config = config

    def reset_config(self) -> None:
        """Reset configuration to defaults."""
        self._config = None


# Create global instance
_config_manager = ConfigManager()


def get_config() -> GarmyConfig:
    """Get the current global configuration."""
    return _config_manager.get_config()


def set_config(config: GarmyConfig) -> None:
    """Set the global configuration."""
    _config_manager.set_config(config)


def reset_config() -> None:
    """Reset configuration to defaults."""
    _config_manager.reset_config()


# =============================================================================
# Convenience Functions
# =============================================================================


def get_timeout(operation: str = "default") -> int:
    """Get timeout for specific operation type."""
    config = get_config()
    timeouts = {
        "default": config.request_timeout,
        "auth": config.auth_timeout,
        "long": Timeouts.LONG_REQUEST,
    }
    return timeouts.get(operation, config.request_timeout)


def get_retryable_status_codes() -> List[int]:
    """Get list of HTTP status codes that should trigger retries."""
    return HTTPStatus.RETRYABLE_CODES.copy()


def get_user_agent(client_type: str = "default") -> str:
    """Get user agent string for specific client type."""
    config = get_config()
    agents = {
        "default": config.default_user_agent,
        "ios": config.ios_user_agent,
        "android": config.android_user_agent,
    }
    return agents.get(client_type, config.default_user_agent)


def get_oauth_credentials() -> dict:
    """Get OAuth consumer credentials with environment variable override support.

    Returns:
        Dictionary with consumer_key and consumer_secret

    Environment Variables:
        GARMY_OAUTH_CONSUMER_KEY: Override consumer key
        GARMY_OAUTH_CONSUMER_SECRET: Override consumer secret

    Example:
        export GARMY_OAUTH_CONSUMER_KEY="your_new_key"
        export GARMY_OAUTH_CONSUMER_SECRET="your_new_secret"
    """
    config = get_config()
    return {
        "consumer_key": config.oauth_consumer_key,
        "consumer_secret": config.oauth_consumer_secret,
    }


def get_app_headers(platform: str = "ios") -> dict:
    """Get mobile app headers for maximum API compatibility.

    Args:
        platform: Platform type ("ios" or "android")

    Returns:
        Dictionary of headers matching the official mobile app

    Example:
        headers = get_app_headers("ios")
        response = requests.get(url, headers=headers)
    """
    if platform.lower() == "ios":
        return AppHeaders.get_ios_headers()
    else:
        # Fallback to basic headers for other platforms
        return {
            "User-Agent": get_user_agent("android"),
            "accept": "*/*",
            "accept-encoding": "gzip, deflate, br",
        }


def get_profile_path() -> Optional[str]:
    """Get the profile path from configuration.

    The profile path is a directory containing user-specific data:
    - OAuth tokens (oauth1_token.json, oauth2_token.json)
    - Health database (health.db)
    - Logs (logs/)

    Returns:
        Profile path string if set, None otherwise.
        When None, components should fall back to their defaults (e.g., ~/.garmy/).

    Environment Variables:
        GARMY_PROFILE_PATH: Path to profile directory

    Example:
        export GARMY_PROFILE_PATH="/path/to/profiles/user1"
    """
    config = get_config()
    return config.profile_path
