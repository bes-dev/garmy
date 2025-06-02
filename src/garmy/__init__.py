"""
Garmy - Lightweight, modular library for Garmin Connect API.

Modern architecture with auto-discovery and type safety.

Modern Usage:
    >>> from garmy import AuthClient, APIClient
    >>>
    >>> # Create clients
    >>> auth_client = AuthClient()
    >>> api_client = APIClient(auth_client=auth_client)
    >>>
    >>> # Login
    >>> auth_client.login("email@example.com", "password")
    >>>
    >>> # Use metrics directly (auto-discovery happens automatically)
    >>> sleep_data = api_client.metrics.get('sleep').get('2023-12-01')
    >>> readiness = api_client.metrics.get('training_readiness').get()
    >>> weekly_steps = api_client.metrics['steps'].list(days=7)
    >>>
    >>> # See what's available
    >>> print("Available metrics:", list(api_client.metrics.keys()))
    >>>
    >>> # Direct metric class imports
    >>> from garmy import Sleep, TrainingReadiness
    >>> print(f"Available fields: {Sleep.__dataclass_fields__.keys()}")
"""

import os

# Core client exports - the main API surface
from .auth.client import AuthClient
from .core.client import APIClient
from .core.config import (
    GarmyConfig,
    get_app_headers,
    get_config,
    get_oauth_credentials,
    reset_config,
    set_config,
)
from .core.discovery import MetricDiscovery
from .core.exceptions import APIError, GarmyError
from .core.metrics import MetricAccessor
from .core.utils import camel_to_snake, format_date
from .metrics.activities import ActivitySummary
from .metrics.body_battery import BodyBattery
from .metrics.calories import Calories
from .metrics.daily_summary import DailySummary
from .metrics.heart_rate import HeartRate
from .metrics.hrv import HRV
from .metrics.respiration import Respiration
from .metrics.sleep import Sleep
from .metrics.steps import Steps
from .metrics.stress import Stress
from .metrics.training_readiness import TrainingReadiness

# Package metadata
__version__ = "1.0.0"
__author__ = "bes-dev"

# Environment setup
os.environ.setdefault("GARMY_NETWORK_VALIDATE_SSL", "false")

__all__ = [
    "HRV",
    "APIClient",
    "APIError",
    "ActivitySummary",
    "AuthClient",
    "BodyBattery",
    "Calories",
    "DailySummary",
    "GarmyConfig",
    "GarmyError",
    "HeartRate",
    "MetricAccessor",
    "MetricDiscovery",
    "Respiration",
    "Sleep",
    "Steps",
    "Stress",
    "TrainingReadiness",
    "__author__",
    "__version__",
    "camel_to_snake",
    "format_date",
    "get_app_headers",
    "get_config",
    "get_oauth_credentials",
    "reset_config",
    "set_config",
]
