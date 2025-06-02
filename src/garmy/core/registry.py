"""
Simplified metric registry for APIClient integration.

This module provides a lightweight metric registry that automatically discovers
and creates metric accessors. Designed for internal use within APIClient.
"""

import logging
from typing import TYPE_CHECKING, Any, Dict, KeysView

if TYPE_CHECKING:
    from .base import MetricConfig
    from .client import APIClient
from .discovery import MetricDiscovery
from .exceptions import FactoryError
from .metrics import MetricAccessor

logger = logging.getLogger(__name__)


class MetricRegistry:
    """
    Lightweight metric registry with automatic discovery and lazy loading.

    This class is designed for internal use within APIClient to provide
    seamless access to all available metrics through a simple interface.
    """

    def __init__(self, api_client: "APIClient"):
        """
        Initialize registry and discover all metrics immediately.

        Args:
            api_client: The API client for making requests
        """
        self.api_client = api_client
        self._accessors: Dict[str, Any] = {}
        self._discover_and_create_all()

    def _discover_and_create_all(self) -> None:
        """Discover all metrics and create accessors (internal method)."""
        logger.debug("Discovering and creating metric accessors")

        # Discover and validate all metrics
        configs = MetricDiscovery.discover_metrics()
        MetricDiscovery.validate_metrics(configs)

        # Create all accessors
        for name, config in configs.items():
            try:
                self._accessors[name] = self._create_accessor(name, config)
            except Exception as e:
                logger.error(f"Failed to create accessor for {name}: {e}")
                raise FactoryError(f"Failed to create accessor for {name}: {e}") from e

        logger.debug(f"Created {len(self._accessors)} metric accessors")

    def _create_accessor(self, name: str, config: "MetricConfig") -> Any:
        """Create a single metric accessor (internal method)."""
        # Check for custom accessor pattern
        try:
            module = __import__(f"garmy.metrics.{name}", fromlist=[""])
            if hasattr(module, "__custom_accessor_factory__"):
                return module.__custom_accessor_factory__(self.api_client)
        except ImportError:
            pass

        # Standard MetricAccessor
        return MetricAccessor(
            api_client=self.api_client,
            metric_class=config.metric_class,
            endpoint=config.endpoint,
            parse_func=config.parser,
            endpoint_builder=config.endpoint_builder,
        )

    def get(self, name: str) -> Any:
        """
        Get a metric accessor by name.

        Args:
            name: Name of the metric

        Returns:
            Metric accessor instance

        Raises:
            KeyError: If metric not found
        """
        if name not in self._accessors:
            available = list(self._accessors.keys())
            raise KeyError(f"Metric '{name}' not found. Available: {available}")
        return self._accessors[name]

    def __getitem__(self, name: str) -> Any:
        """Allow dict-style access: metrics['sleep']."""
        return self.get(name)

    def __contains__(self, name: str) -> bool:
        """Allow 'in' operator: 'sleep' in metrics."""
        return name in self._accessors

    def keys(self) -> KeysView[str]:
        """Get all available metric names."""
        return self._accessors.keys()

    def __len__(self) -> int:
        """Get number of available metrics."""
        return len(self._accessors)

    def __repr__(self) -> str:
        """Return string representation for debugging."""
        metrics_list = list(self._accessors.keys())
        return f"MetricRegistry({len(metrics_list)} metrics: {metrics_list})"
