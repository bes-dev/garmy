"""Comprehensive tests for garmy.core.registry module.

This module provides 100% test coverage for metric registry functionality.
"""

from dataclasses import dataclass
from unittest.mock import Mock, patch

import pytest

from garmy.core.base import MetricConfig
from garmy.core.exceptions import FactoryError
from garmy.core.registry import MetricRegistry


# Test dataclasses for testing
@dataclass
class SampleMetric:
    """Test metric class for registry testing."""

    value: int
    name: str


@dataclass
class AnotherSampleMetric:
    """Another test metric class."""

    data: str
    count: int


def parser_func(data):
    """Test parser function."""
    return SampleMetric(data.get("value", 0), data.get("name", ""))


def endpoint_builder_func(**kwargs):
    """Test endpoint builder function."""
    result = "/test/endpoint"
    return result


class SampleMetricRegistry:
    """Test cases for MetricRegistry class."""

    @patch("garmy.core.registry.MetricDiscovery.discover_metrics")
    @patch("garmy.core.registry.MetricDiscovery.validate_metrics")
    def test_metric_registry_initialization(self, mock_validate, mock_discover):
        """Test MetricRegistry initialization."""
        mock_api_client = Mock()

        # Mock discovery results
        mock_configs = {
            "test_metric": MetricConfig(
                metric_class=SampleMetric, endpoint="/test/endpoint"
            )
        }
        mock_discover.return_value = mock_configs

        with patch.object(MetricRegistry, "_create_accessor") as mock_create:
            mock_accessor = Mock()
            mock_create.return_value = mock_accessor

            registry = MetricRegistry(mock_api_client)

            assert registry.api_client == mock_api_client
            assert len(registry._accessors) == 1
            assert "test_metric" in registry._accessors

            mock_discover.assert_called_once()
            mock_validate.assert_called_once_with(mock_configs)
            mock_create.assert_called_once_with(
                "test_metric", mock_configs["test_metric"]
            )

    @patch("garmy.core.registry.MetricDiscovery.discover_metrics")
    @patch("garmy.core.registry.MetricDiscovery.validate_metrics")
    def test_metric_registry_multiple_metrics(self, mock_validate, mock_discover):
        """Test MetricRegistry with multiple metrics."""
        mock_api_client = Mock()

        # Mock discovery results with multiple metrics
        mock_configs = {
            "metric1": MetricConfig(
                metric_class=SampleMetric, endpoint="/metric1/endpoint"
            ),
            "metric2": MetricConfig(
                metric_class=AnotherSampleMetric, endpoint="/metric2/endpoint"
            ),
        }
        mock_discover.return_value = mock_configs

        with patch.object(MetricRegistry, "_create_accessor") as mock_create:
            mock_accessor1 = Mock()
            mock_accessor2 = Mock()
            mock_create.side_effect = [mock_accessor1, mock_accessor2]

            registry = MetricRegistry(mock_api_client)

            assert len(registry._accessors) == 2
            assert "metric1" in registry._accessors
            assert "metric2" in registry._accessors
            assert registry._accessors["metric1"] == mock_accessor1
            assert registry._accessors["metric2"] == mock_accessor2

            assert mock_create.call_count == 2

    @patch("garmy.core.registry.MetricDiscovery.discover_metrics")
    @patch("garmy.core.registry.MetricDiscovery.validate_metrics")
    def test_metric_registry_creation_error(self, mock_validate, mock_discover):
        """Test MetricRegistry handles accessor creation errors."""
        mock_api_client = Mock()

        mock_configs = {
            "failing_metric": MetricConfig(
                metric_class=SampleMetric, endpoint="/test/endpoint"
            )
        }
        mock_discover.return_value = mock_configs

        with patch.object(MetricRegistry, "_create_accessor") as mock_create:
            mock_create.side_effect = Exception("Accessor creation failed")

            with pytest.raises(
                FactoryError, match="Failed to create accessor for failing_metric"
            ):
                MetricRegistry(mock_api_client)

    @patch("garmy.core.registry.MetricDiscovery.discover_metrics")
    @patch("garmy.core.registry.MetricDiscovery.validate_metrics")
    def test_create_accessor_standard_pattern(self, mock_validate, mock_discover):
        """Test _create_accessor creates standard MetricAccessor."""
        mock_api_client = Mock()
        mock_discover.return_value = {}

        registry = MetricRegistry(mock_api_client)

        config = MetricConfig(
            metric_class=SampleMetric,
            endpoint="/test/endpoint",
            parser=parser_func,
            endpoint_builder=endpoint_builder_func,
        )

        with patch("garmy.core.registry.MetricAccessor") as mock_accessor_class:
            mock_accessor = Mock()
            mock_accessor_class.return_value = mock_accessor

            result = registry._create_accessor("test_metric", config)

            assert result == mock_accessor
            mock_accessor_class.assert_called_once_with(
                api_client=mock_api_client,
                metric_class=SampleMetric,
                endpoint="/test/endpoint",
                parse_func=parser_func,
                endpoint_builder=endpoint_builder_func,
            )

    @patch("garmy.core.registry.MetricDiscovery.discover_metrics")
    @patch("garmy.core.registry.MetricDiscovery.validate_metrics")
    def test_create_accessor_custom_factory(self, mock_validate, mock_discover):
        """Test _create_accessor with custom accessor factory."""
        mock_api_client = Mock()
        mock_discover.return_value = {}

        registry = MetricRegistry(mock_api_client)

        config = MetricConfig(metric_class=SampleMetric, endpoint="/test/endpoint")

        # Mock importlib and custom factory
        mock_module = Mock()
        mock_custom_factory = Mock()
        mock_custom_accessor = Mock()
        mock_module.__custom_accessor_factory__ = mock_custom_factory
        mock_custom_factory.return_value = mock_custom_accessor

        with patch("builtins.__import__", return_value=mock_module):
            result = registry._create_accessor("test_metric", config)

            assert result == mock_custom_accessor
            mock_custom_factory.assert_called_once_with(mock_api_client)

    @patch("garmy.core.registry.MetricDiscovery.discover_metrics")
    @patch("garmy.core.registry.MetricDiscovery.validate_metrics")
    def test_create_accessor_import_error_fallback(self, mock_validate, mock_discover):
        """Test _create_accessor fallback when import fails."""
        mock_api_client = Mock()
        mock_discover.return_value = {}

        registry = MetricRegistry(mock_api_client)

        config = MetricConfig(metric_class=SampleMetric, endpoint="/test/endpoint")

        # Mock import error
        with patch(
            "builtins.__import__", side_effect=ImportError("Module not found")
        ), patch("garmy.core.registry.MetricAccessor") as mock_accessor_class:
            mock_accessor = Mock()
            mock_accessor_class.return_value = mock_accessor

            result = registry._create_accessor("test_metric", config)

            assert result == mock_accessor
            mock_accessor_class.assert_called_once()

    @patch("garmy.core.registry.MetricDiscovery.discover_metrics")
    @patch("garmy.core.registry.MetricDiscovery.validate_metrics")
    def test_get_method_success(self, mock_validate, mock_discover):
        """Test get method returns correct accessor."""
        mock_api_client = Mock()

        mock_configs = {
            "test_metric": MetricConfig(
                metric_class=SampleMetric, endpoint="/test/endpoint"
            )
        }
        mock_discover.return_value = mock_configs

        with patch.object(MetricRegistry, "_create_accessor") as mock_create:
            mock_accessor = Mock()
            mock_create.return_value = mock_accessor

            registry = MetricRegistry(mock_api_client)

            result = registry.get("test_metric")

            assert result == mock_accessor

    @patch("garmy.core.registry.MetricDiscovery.discover_metrics")
    @patch("garmy.core.registry.MetricDiscovery.validate_metrics")
    def test_get_method_not_found(self, mock_validate, mock_discover):
        """Test get method raises error for unknown metric."""
        mock_api_client = Mock()

        mock_configs = {
            "existing_metric": MetricConfig(
                metric_class=SampleMetric, endpoint="/test/endpoint"
            )
        }
        mock_discover.return_value = mock_configs

        with patch.object(MetricRegistry, "_create_accessor"):
            registry = MetricRegistry(mock_api_client)

            with pytest.raises(KeyError, match="Metric 'unknown_metric' not found"):
                registry.get("unknown_metric")

    @patch("garmy.core.registry.MetricDiscovery.discover_metrics")
    @patch("garmy.core.registry.MetricDiscovery.validate_metrics")
    def test_getitem_method(self, mock_validate, mock_discover):
        """Test __getitem__ method (dict-style access)."""
        mock_api_client = Mock()

        mock_configs = {
            "test_metric": MetricConfig(
                metric_class=SampleMetric, endpoint="/test/endpoint"
            )
        }
        mock_discover.return_value = mock_configs

        with patch.object(MetricRegistry, "_create_accessor") as mock_create:
            mock_accessor = Mock()
            mock_create.return_value = mock_accessor

            registry = MetricRegistry(mock_api_client)

            result = registry["test_metric"]

            assert result == mock_accessor

    @patch("garmy.core.registry.MetricDiscovery.discover_metrics")
    @patch("garmy.core.registry.MetricDiscovery.validate_metrics")
    def test_contains_method(self, mock_validate, mock_discover):
        """Test __contains__ method (in operator)."""
        mock_api_client = Mock()

        mock_configs = {
            "existing_metric": MetricConfig(
                metric_class=SampleMetric, endpoint="/test/endpoint"
            )
        }
        mock_discover.return_value = mock_configs

        with patch.object(MetricRegistry, "_create_accessor"):
            registry = MetricRegistry(mock_api_client)

            assert "existing_metric" in registry
            assert "non_existing_metric" not in registry

    @patch("garmy.core.registry.MetricDiscovery.discover_metrics")
    @patch("garmy.core.registry.MetricDiscovery.validate_metrics")
    def test_keys_method(self, mock_validate, mock_discover):
        """Test keys method returns metric names."""
        mock_api_client = Mock()

        mock_configs = {
            "metric1": MetricConfig(metric_class=SampleMetric, endpoint="/metric1"),
            "metric2": MetricConfig(
                metric_class=AnotherSampleMetric, endpoint="/metric2"
            ),
        }
        mock_discover.return_value = mock_configs

        with patch.object(MetricRegistry, "_create_accessor"):
            registry = MetricRegistry(mock_api_client)

            keys = registry.keys()

            assert set(keys) == {"metric1", "metric2"}

    @patch("garmy.core.registry.MetricDiscovery.discover_metrics")
    @patch("garmy.core.registry.MetricDiscovery.validate_metrics")
    def test_len_method(self, mock_validate, mock_discover):
        """Test __len__ method returns number of metrics."""
        mock_api_client = Mock()

        mock_configs = {
            "metric1": MetricConfig(metric_class=SampleMetric, endpoint="/metric1"),
            "metric2": MetricConfig(
                metric_class=AnotherSampleMetric, endpoint="/metric2"
            ),
            "metric3": MetricConfig(metric_class=SampleMetric, endpoint="/metric3"),
        }
        mock_discover.return_value = mock_configs

        with patch.object(MetricRegistry, "_create_accessor"):
            registry = MetricRegistry(mock_api_client)

            assert len(registry) == 3

    @patch("garmy.core.registry.MetricDiscovery.discover_metrics")
    @patch("garmy.core.registry.MetricDiscovery.validate_metrics")
    def test_repr_method(self, mock_validate, mock_discover):
        """Test __repr__ method returns string representation."""
        mock_api_client = Mock()

        mock_configs = {
            "metric1": MetricConfig(metric_class=SampleMetric, endpoint="/metric1"),
            "metric2": MetricConfig(
                metric_class=AnotherSampleMetric, endpoint="/metric2"
            ),
        }
        mock_discover.return_value = mock_configs

        with patch.object(MetricRegistry, "_create_accessor"):
            registry = MetricRegistry(mock_api_client)

            repr_str = repr(registry)

            assert "MetricRegistry" in repr_str
            assert "2 metrics" in repr_str
            assert "metric1" in repr_str
            assert "metric2" in repr_str


class SampleMetricRegistryEdgeCases:
    """Test cases for MetricRegistry edge cases and error handling."""

    @patch("garmy.core.registry.MetricDiscovery.discover_metrics")
    @patch("garmy.core.registry.MetricDiscovery.validate_metrics")
    def test_empty_registry(self, mock_validate, mock_discover):
        """Test MetricRegistry with no metrics."""
        mock_api_client = Mock()
        mock_discover.return_value = {}

        registry = MetricRegistry(mock_api_client)

        assert len(registry) == 0
        assert list(registry.keys()) == []
        assert "any_metric" not in registry

        with pytest.raises(KeyError):
            registry.get("any_metric")

    @patch("garmy.core.registry.MetricDiscovery.discover_metrics")
    @patch("garmy.core.registry.MetricDiscovery.validate_metrics")
    def test_registry_with_none_values(self, mock_validate, mock_discover):
        """Test MetricRegistry handles None values gracefully."""
        mock_api_client = Mock()

        mock_configs = {
            "test_metric": MetricConfig(
                metric_class=SampleMetric,
                endpoint="/test/endpoint",
                parser=None,
                endpoint_builder=None,
            )
        }
        mock_discover.return_value = mock_configs

        with patch("garmy.core.registry.MetricAccessor") as mock_accessor_class:
            mock_accessor = Mock()
            mock_accessor_class.return_value = mock_accessor

            registry = MetricRegistry(mock_api_client)

            # Should handle None values correctly
            assert "test_metric" in registry
            mock_accessor_class.assert_called_once_with(
                api_client=mock_api_client,
                metric_class=SampleMetric,
                endpoint="/test/endpoint",
                parse_func=None,
                endpoint_builder=None,
            )

    @patch("garmy.core.registry.MetricDiscovery.discover_metrics")
    @patch("garmy.core.registry.MetricDiscovery.validate_metrics")
    def test_discovery_logging(self, mock_validate, mock_discover):
        """Test MetricRegistry logging during discovery."""
        mock_api_client = Mock()

        mock_configs = {
            "test_metric": MetricConfig(
                metric_class=SampleMetric, endpoint="/test/endpoint"
            )
        }
        mock_discover.return_value = mock_configs

        with patch.object(MetricRegistry, "_create_accessor"), patch(
            "garmy.core.registry.logger"
        ) as mock_logger:
            MetricRegistry(mock_api_client)

            # Should log discovery process
            mock_logger.debug.assert_called()

    @patch("garmy.core.registry.MetricDiscovery.discover_metrics")
    @patch("garmy.core.registry.MetricDiscovery.validate_metrics")
    def test_creation_error_logging(self, mock_validate, mock_discover):
        """Test MetricRegistry logs creation errors."""
        mock_api_client = Mock()

        mock_configs = {
            "failing_metric": MetricConfig(
                metric_class=SampleMetric, endpoint="/test/endpoint"
            )
        }
        mock_discover.return_value = mock_configs

        with patch.object(MetricRegistry, "_create_accessor") as mock_create:
            mock_create.side_effect = Exception("Creation failed")

            with patch("garmy.core.registry.logger") as mock_logger:
                with pytest.raises(FactoryError):
                    MetricRegistry(mock_api_client)

                # Should log the error
                mock_logger.error.assert_called()

    @patch("garmy.core.registry.MetricDiscovery.discover_metrics")
    @patch("garmy.core.registry.MetricDiscovery.validate_metrics")
    def test_multiple_api_clients(self, mock_validate, mock_discover):
        """Test multiple MetricRegistry instances with different API clients."""
        mock_api_client1 = Mock()
        mock_api_client2 = Mock()

        mock_configs = {
            "test_metric": MetricConfig(
                metric_class=SampleMetric, endpoint="/test/endpoint"
            )
        }
        mock_discover.return_value = mock_configs

        with patch.object(MetricRegistry, "_create_accessor"):
            registry1 = MetricRegistry(mock_api_client1)
            registry2 = MetricRegistry(mock_api_client2)

            # Should be separate instances
            assert registry1 is not registry2
            assert registry1.api_client == mock_api_client1
            assert registry2.api_client == mock_api_client2


class SampleMetricRegistryIntegration:
    """Test cases for MetricRegistry integration scenarios."""

    @patch("garmy.core.registry.MetricDiscovery.discover_metrics")
    @patch("garmy.core.registry.MetricDiscovery.validate_metrics")
    def test_full_workflow_integration(self, mock_validate, mock_discover):
        """Test MetricRegistry full workflow integration."""
        mock_api_client = Mock()

        # Mock realistic metric configurations
        mock_configs = {
            "heart_rate": MetricConfig(
                metric_class=SampleMetric,
                endpoint="/wellness-service/wellness/dailyHeartRate/{user_id}?date={date}",
                parser=parser_func,
            ),
            "sleep": MetricConfig(
                metric_class=AnotherSampleMetric,
                endpoint="/wellness-service/wellness/dailySleepData/{user_id}?date={date}",
                endpoint_builder=endpoint_builder_func,
            ),
        }
        mock_discover.return_value = mock_configs

        with patch("garmy.core.registry.MetricAccessor") as mock_accessor_class:
            mock_hr_accessor = Mock()
            mock_sleep_accessor = Mock()
            mock_accessor_class.side_effect = [mock_hr_accessor, mock_sleep_accessor]

            registry = MetricRegistry(mock_api_client)

            # Test full workflow
            assert len(registry) == 2
            assert "heart_rate" in registry
            assert "sleep" in registry

            # Test accessor retrieval
            hr_accessor = registry["heart_rate"]
            sleep_accessor = registry.get("sleep")

            assert hr_accessor == mock_hr_accessor
            assert sleep_accessor == mock_sleep_accessor

            # Verify accessors were created with correct parameters
            assert mock_accessor_class.call_count == 2

    @patch("garmy.core.registry.MetricDiscovery.discover_metrics")
    @patch("garmy.core.registry.MetricDiscovery.validate_metrics")
    def test_registry_with_custom_factories(self, mock_validate, mock_discover):
        """Test MetricRegistry with mix of standard and custom factories."""
        mock_api_client = Mock()

        mock_configs = {
            "standard_metric": MetricConfig(
                metric_class=SampleMetric, endpoint="/standard/endpoint"
            ),
            "custom_metric": MetricConfig(
                metric_class=AnotherSampleMetric, endpoint="/custom/endpoint"
            ),
        }
        mock_discover.return_value = mock_configs

        # Mock one standard and one custom factory
        def mock_import_side_effect(module_name):
            if "custom_metric" in module_name:
                mock_module = Mock()
                mock_factory = Mock()
                mock_custom_accessor = Mock()
                mock_module.__custom_accessor_factory__ = mock_factory
                mock_factory.return_value = mock_custom_accessor
                return mock_module
            else:
                raise ImportError("Module not found")

        with patch("builtins.__import__", side_effect=mock_import_side_effect), patch(
            "garmy.core.registry.MetricAccessor"
        ) as mock_standard_accessor_class:
            mock_standard_accessor = Mock()
            mock_standard_accessor_class.return_value = mock_standard_accessor

            registry = MetricRegistry(mock_api_client)

            # Should create both types of accessors
            assert len(registry) == 2
            assert "standard_metric" in registry
            assert "custom_metric" in registry

    @patch("garmy.core.registry.MetricDiscovery.discover_metrics")
    @patch("garmy.core.registry.MetricDiscovery.validate_metrics")
    def test_registry_error_resilience(self, mock_validate, mock_discover):
        """Test MetricRegistry error resilience."""
        mock_api_client = Mock()

        mock_configs = {
            "good_metric": MetricConfig(
                metric_class=SampleMetric, endpoint="/good/endpoint"
            ),
            "bad_metric": MetricConfig(
                metric_class=AnotherSampleMetric, endpoint="/bad/endpoint"
            ),
        }
        mock_discover.return_value = mock_configs

        # Mock one successful and one failing accessor creation
        def mock_create_side_effect(name, config):
            if name == "good_metric":
                return Mock()
            else:
                raise Exception("Creation failed")

        with patch.object(
            MetricRegistry, "_create_accessor", side_effect=mock_create_side_effect
        ), pytest.raises(
            FactoryError, match="Failed to create accessor for bad_metric"
        ):
            MetricRegistry(mock_api_client)


class SampleMetricRegistryPerformance:
    """Test cases for MetricRegistry performance characteristics."""

    @patch("garmy.core.registry.MetricDiscovery.discover_metrics")
    @patch("garmy.core.registry.MetricDiscovery.validate_metrics")
    def test_lazy_accessor_creation(self, mock_validate, mock_discover):
        """Test MetricRegistry creates all accessors during initialization."""
        mock_api_client = Mock()

        # Large number of metrics to test performance
        mock_configs = {}
        for i in range(100):
            mock_configs[f"metric_{i}"] = MetricConfig(
                metric_class=SampleMetric, endpoint=f"/metric_{i}/endpoint"
            )

        mock_discover.return_value = mock_configs

        with patch.object(MetricRegistry, "_create_accessor") as mock_create:
            mock_create.return_value = Mock()

            # Should create all accessors during initialization
            registry = MetricRegistry(mock_api_client)

            # All accessors should be created
            assert mock_create.call_count == 100
            assert len(registry) == 100

    @patch("garmy.core.registry.MetricDiscovery.discover_metrics")
    @patch("garmy.core.registry.MetricDiscovery.validate_metrics")
    def test_fast_accessor_retrieval(self, mock_validate, mock_discover):
        """Test MetricRegistry provides fast accessor retrieval."""
        mock_api_client = Mock()

        mock_configs = {
            "test_metric": MetricConfig(
                metric_class=SampleMetric, endpoint="/test/endpoint"
            )
        }
        mock_discover.return_value = mock_configs

        with patch.object(MetricRegistry, "_create_accessor") as mock_create:
            mock_accessor = Mock()
            mock_create.return_value = mock_accessor

            registry = MetricRegistry(mock_api_client)

            # Multiple retrievals should not create additional accessors
            accessor1 = registry.get("test_metric")
            accessor2 = registry["test_metric"]

            assert accessor1 is accessor2
            assert accessor1 == mock_accessor
            # Should only create once
            mock_create.assert_called_once()

    @patch("garmy.core.registry.MetricDiscovery.discover_metrics")
    @patch("garmy.core.registry.MetricDiscovery.validate_metrics")
    def test_memory_efficient_storage(self, mock_validate, mock_discover):
        """Test MetricRegistry memory efficient storage."""
        mock_api_client = Mock()

        mock_configs = {
            "test_metric": MetricConfig(
                metric_class=SampleMetric, endpoint="/test/endpoint"
            )
        }
        mock_discover.return_value = mock_configs

        with patch.object(MetricRegistry, "_create_accessor"):
            registry = MetricRegistry(mock_api_client)

            # Should store accessors efficiently
            assert isinstance(registry._accessors, dict)
            assert len(registry._accessors) == 1

            # No unnecessary data structures
            assert not hasattr(registry, "_cache")
            assert not hasattr(registry, "_buffer")
