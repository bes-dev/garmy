"""
Auto-discovery system for metrics.

This module provides stateless auto-discovery functionality that automatically
finds and validates metric configurations without requiring manual registration.
"""

import importlib
import logging
import pkgutil
from pathlib import Path
from typing import Any, Dict, Optional

from .base import MetricConfig
from .exceptions import DiscoveryError

logger = logging.getLogger(__name__)


class MetricDiscovery:
    """
    Stateless metric discovery system.

    This class provides methods to automatically discover metric configurations
    from Python modules without maintaining global state.
    """

    @staticmethod
    def discover_metrics(
        package_path: str = "garmy.metrics",
    ) -> Dict[str, MetricConfig]:
        """
        Discover all metrics in the specified package.

        This method scans a Python package for modules containing metric
        configurations and returns a dictionary mapping metric names to
        their configurations.

        Args:
            package_path: Python package path to scan (e.g., "garmy.metrics")

        Returns:
            Dictionary mapping metric names to MetricConfig objects
        """
        metrics = {}

        try:
            # Import the metrics package
            package = importlib.import_module(package_path)
            package_dir = Path(package.__file__ or "").parent

            logger.debug(f"Discovering metrics in package: {package_path}")

            # Iterate through all modules in the package
            for module_info in pkgutil.iter_modules([str(package_dir)]):
                # Skip private modules and __init__.py
                if module_info.name.startswith("_"):
                    continue

                module_name = f"{package_path}.{module_info.name}"
                logger.debug(f"Checking module: {module_name}")

                # Import module safely
                module = MetricDiscovery._import_module_safe(module_name)
                if module is None:
                    continue

                # Look for metric configuration
                if hasattr(module, "__metric_config__"):
                    config = module.__metric_config__
                    if isinstance(config, MetricConfig):
                        metric_name = module_info.name
                        metrics[metric_name] = config
                        logger.debug(f"Found metric: {metric_name}")
                    else:
                        logger.warning(f"Invalid __metric_config__ in {module_name}")

        except ImportError as e:
            logger.error(f"Failed to import package {package_path}: {e}")
            raise
        except (SystemExit, KeyboardInterrupt, GeneratorExit):
            raise
        except (AttributeError, ModuleNotFoundError) as e:
            logger.error(f"Module structure error during discovery: {e}")
            raise DiscoveryError(
                f"Failed to discover metrics due to module structure: {e}"
            ) from e
        except Exception as e:
            logger.error(f"Unexpected error during discovery: {e}", exc_info=True)
            raise DiscoveryError(f"Failed to discover metrics: {e}") from e

        logger.info(f"Discovered {len(metrics)} metrics: {list(metrics.keys())}")
        return metrics

    @staticmethod
    def validate_metrics(metrics: Dict[str, MetricConfig]) -> None:
        """
        Validate all discovered metric configurations.

        Args:
            metrics: Dictionary of metric configurations to validate
        """
        logger.debug(f"Validating {len(metrics)} metric configurations")

        for name, config in metrics.items():
            try:
                # Validate the metric class is a dataclass
                if not hasattr(config.metric_class, "__dataclass_fields__"):
                    raise DiscoveryError(
                        f"Metric class {config.metric_class} is not a dataclass"
                    )

                # Validate parser if provided
                if config.parser and not callable(config.parser):
                    raise DiscoveryError(f"Parser for {name} is not callable")

                # Validate endpoint_builder if provided
                if config.endpoint_builder and not callable(config.endpoint_builder):
                    raise DiscoveryError(f"Endpoint builder for {name} is not callable")

                # Validate endpoint configuration
                if not config.endpoint and not config.endpoint_builder:
                    raise DiscoveryError(
                        f"Metric {name} has neither endpoint nor endpoint_builder"
                    )

                # Check for deprecated metrics
                if config.deprecated:
                    logger.warning(f"Metric {name} is deprecated: {config.description}")

                logger.debug(f"Validated metric: {name}")

            except Exception as e:
                error_msg = f"Invalid configuration for metric {name}: {e}"
                logger.error(error_msg)
                raise DiscoveryError(error_msg) from e

        # Check for endpoint conflicts (warning only)
        MetricDiscovery._check_endpoint_conflicts(metrics)

        logger.info(f"All {len(metrics)} metric configurations are valid")

    @staticmethod
    def print_metrics_info(metrics: Dict[str, MetricConfig]) -> None:
        """Print a summary of all discovered metrics."""
        print(f"\n=== Discovered Metrics ({len(metrics)}) ===")
        for name, config in metrics.items():
            status = " (DEPRECATED)" if config.deprecated else ""
            endpoint = config.endpoint or "dynamic"
            field_count = len(config.metric_class.__dataclass_fields__)

            print(f"\n{name}{status}:")
            print(f"  Class: {config.metric_class.__name__}")
            print(f"  Endpoint: {endpoint}")
            print(f"  Fields: {field_count}")
            if config.description:
                print(f"  Description: {config.description}")

    @staticmethod
    def _import_module_safe(module_path: str) -> Optional[Any]:
        """Safely import a module with error handling."""
        try:
            return importlib.import_module(module_path)
        except ImportError as e:
            logger.warning(f"Failed to import {module_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error importing {module_path}: {e}")
            return None

    @staticmethod
    def _check_endpoint_conflicts(metrics: Dict[str, MetricConfig]) -> None:
        """Check for endpoint conflicts (warning only)."""
        endpoints: Dict[str, str] = {}
        for name, config in metrics.items():
            if config.endpoint:
                if config.endpoint in endpoints:
                    existing_metric = endpoints[config.endpoint]
                    logger.warning(
                        f"Endpoint shared by multiple metrics: {config.endpoint} "
                        f"used by {name} and {existing_metric}"
                    )
                endpoints[config.endpoint] = name
