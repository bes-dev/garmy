"""
Core module - Common functionality and base classes.

This module provides the core functionality for the garmy library, including
HTTP client for API requests, metric framework with decorators, utility functions,
and custom exception classes.

Components:
    - APIClient: HTTP client for authenticated API requests
    - Metric framework: Decorator-based system for defining data metrics
    - Utility functions: Date formatting, string conversion, etc.
    - Custom exceptions: Structured error handling

Example:
    >>> from garmy.core import APIClient, metric
    >>> from dataclasses import dataclass
    >>>
    >>> @metric("/endpoint/{date}")
    ... @dataclass
    ... class MyMetric:
    ...     value: int
    ...
    >>> client = APIClient()
    >>> data = client.my_metric.get("2023-12-01")
"""

from typing import List as _List

from .client import APIClient

# Import safe components first (no circular dependencies)
from .exceptions import APIError, GarmyError
from .http_client import BaseHTTPClient
from .metrics import MetricAccessor
from .utils import (
    camel_to_snake,
    camel_to_snake_dict,
    date_range,
    format_date,
    handle_api_exception,
)

# Direct imports for all core components


__all__: _List[str] = [
    "APIClient",
    "APIError",
    "BaseHTTPClient",
    "GarmyError",
    "MetricAccessor",
    "camel_to_snake",
    "camel_to_snake_dict",
    "date_range",
    "format_date",
    "handle_api_exception",
]
