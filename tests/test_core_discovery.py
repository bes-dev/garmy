"""Comprehensive tests for garmy.core.discovery module.

This module provides 100% test coverage for metric discovery functionality.
"""

from dataclasses import dataclass
from typing import Any, Dict
from unittest.mock import Mock, patch

import pytest

from garmy.core.base import MetricConfig
from garmy.core.discovery import MetricDiscovery
from garmy.core.exceptions import DiscoveryError


# Test dataclasses for testing
@dataclass
class SampleMetric:
    """Test metric class for discovery testing."""

    value: int
    name: str


@dataclass
class AnotherSampleMetric:
    """Another test metric class."""

    data: str
    count: int


def parser_func(data: Dict[str, Any]) -> SampleMetric:
    """Test parser function."""
    return SampleMetric(data.get("value", 0), data.get("name", ""))


def endpoint_builder_func(date_input=None, api_client=None, **kwargs):
    """Test endpoint builder function."""
    result = f"/test/{date_input or 'default'}"
    return result


class SampleMetricDiscovery:
    """Test cases for MetricDiscovery class."""

    def test_metric_discovery_is_static(self):
        """Test MetricDiscovery is designed as static class."""
        # Should not be instantiated
        assert not hasattr(MetricDiscovery, "__init__")

        # All methods should be static/classmethod
        assert callable(MetricDiscovery.discover_metrics)
        assert callable(MetricDiscovery.validate_metrics)

    @patch("garmy.core.discovery.importlib.import_module")
    @patch("garmy.core.discovery.pkgutil.iter_modules")
    def test_discover_metrics_basic(self, mock_iter_modules, mock_import_module):
        """Test basic metric discovery functionality."""
        # Mock module iteration
        mock_module_info = Mock()
        mock_module_info.name = "test_metric"
        mock_iter_modules.return_value = [mock_module_info]

        # Mock module import
        mock_module = Mock()
        mock_module.__metric_config__ = MetricConfig(
            metric_class=SampleMetric, endpoint="/test/endpoint"
        )
        mock_import_module.return_value = mock_module

        # Mock metrics package path
        with patch("garmy.metrics.__path__", ["/fake/path"]):
            configs = MetricDiscovery.discover_metrics()

        assert "test_metric" in configs
        assert configs["test_metric"].metric_class == SampleMetric
        assert configs["test_metric"].endpoint == "/test/endpoint"

    @patch("garmy.core.discovery.importlib.import_module")
    @patch("garmy.core.discovery.pkgutil.iter_modules")
    def test_discover_metrics_with_parser_and_builder(
        self, mock_iter_modules, mock_import_module
    ):
        """Test metric discovery with parser and endpoint builder."""
        # Mock module iteration
        mock_module_info = Mock()
        mock_module_info.name = "advanced_metric"
        mock_iter_modules.return_value = [mock_module_info]

        # Mock module import with full config
        mock_module = Mock()
        mock_module.__metric_config__ = MetricConfig(
            metric_class=SampleMetric,
            endpoint="/advanced/endpoint",
            parser=parser_func,
            endpoint_builder=endpoint_builder_func,
        )
        mock_import_module.return_value = mock_module

        # Mock metrics package path
        with patch("garmy.metrics.__path__", ["/fake/path"]):
            configs = MetricDiscovery.discover_metrics()

        assert "advanced_metric" in configs
        config = configs["advanced_metric"]
        assert config.metric_class == SampleMetric
        assert config.endpoint == "/advanced/endpoint"
        assert config.parser == parser_func
        assert config.endpoint_builder == endpoint_builder_func

    @patch("garmy.core.discovery.importlib.import_module")
    @patch("garmy.core.discovery.pkgutil.iter_modules")
    def test_discover_metrics_multiple_modules(
        self, mock_iter_modules, mock_import_module
    ):
        """Test discovery of multiple metric modules."""
        # Mock multiple modules
        mock_module_info1 = Mock()
        mock_module_info1.name = "metric1"
        mock_module_info2 = Mock()
        mock_module_info2.name = "metric2"
        mock_iter_modules.return_value = [mock_module_info1, mock_module_info2]

        # Mock module imports
        mock_module1 = Mock()
        mock_module1.__metric_config__ = MetricConfig(
            metric_class=SampleMetric, endpoint="/metric1/endpoint"
        )

        mock_module2 = Mock()
        mock_module2.__metric_config__ = MetricConfig(
            metric_class=AnotherSampleMetric, endpoint="/metric2/endpoint"
        )

        def side_effect(module_name):
            if "metric1" in module_name:
                return mock_module1
            elif "metric2" in module_name:
                return mock_module2
            return Mock()

        mock_import_module.side_effect = side_effect

        # Mock metrics package path
        with patch("garmy.metrics.__path__", ["/fake/path"]):
            configs = MetricDiscovery.discover_metrics()

        assert len(configs) == 2
        assert "metric1" in configs
        assert "metric2" in configs
        assert configs["metric1"].metric_class == SampleMetric
        assert configs["metric2"].metric_class == AnotherSampleMetric

    @patch("garmy.core.discovery.importlib.import_module")
    @patch("garmy.core.discovery.pkgutil.iter_modules")
    def test_discover_metrics_skip_modules_without_config(
        self, mock_iter_modules, mock_import_module
    ):
        """Test discovery skips modules without __metric_config__."""
        # Mock module iteration
        mock_module_info1 = Mock()
        mock_module_info1.name = "valid_metric"
        mock_module_info2 = Mock()
        mock_module_info2.name = "invalid_metric"
        mock_iter_modules.return_value = [mock_module_info1, mock_module_info2]

        # Mock module imports - one with config, one without
        mock_valid_module = Mock()
        mock_valid_module.__metric_config__ = MetricConfig(
            metric_class=SampleMetric, endpoint="/valid/endpoint"
        )

        mock_invalid_module = Mock()
        # No __metric_config__ attribute
        del mock_invalid_module.__metric_config__

        def side_effect(module_name):
            if "valid_metric" in module_name:
                return mock_valid_module
            elif "invalid_metric" in module_name:
                return mock_invalid_module
            return Mock()

        mock_import_module.side_effect = side_effect

        # Mock metrics package path
        with patch("garmy.metrics.__path__", ["/fake/path"]):
            configs = MetricDiscovery.discover_metrics()

        # Should only include the valid metric
        assert len(configs) == 1
        assert "valid_metric" in configs
        assert "invalid_metric" not in configs

    @patch("garmy.core.discovery.importlib.import_module")
    @patch("garmy.core.discovery.pkgutil.iter_modules")
    def test_discover_metrics_handle_import_errors(
        self, mock_iter_modules, mock_import_module
    ):
        """Test discovery handles import errors gracefully."""
        # Mock module iteration
        mock_module_info1 = Mock()
        mock_module_info1.name = "good_metric"
        mock_module_info2 = Mock()
        mock_module_info2.name = "bad_metric"
        mock_iter_modules.return_value = [mock_module_info1, mock_module_info2]

        # Mock module imports - one successful, one failing
        mock_good_module = Mock()
        mock_good_module.__metric_config__ = MetricConfig(
            metric_class=SampleMetric, endpoint="/good/endpoint"
        )

        def side_effect(module_name):
            if "good_metric" in module_name:
                return mock_good_module
            elif "bad_metric" in module_name:
                raise ImportError("Failed to import bad_metric")
            return Mock()

        mock_import_module.side_effect = side_effect

        # Mock metrics package path
        with patch("garmy.metrics.__path__", ["/fake/path"]):
            configs = MetricDiscovery.discover_metrics()

        # Should include only the successfully imported metric
        assert len(configs) == 1
        assert "good_metric" in configs
        assert "bad_metric" not in configs

    @patch("garmy.core.discovery.importlib.import_module")
    @patch("garmy.core.discovery.pkgutil.iter_modules")
    def test_discover_metrics_handle_attribute_errors(
        self, mock_iter_modules, mock_import_module
    ):
        """Test discovery handles attribute errors gracefully."""
        # Mock module iteration
        mock_module_info = Mock()
        mock_module_info.name = "broken_metric"
        mock_iter_modules.return_value = [mock_module_info]

        # Mock module with attribute error
        mock_module = Mock()
        type(mock_module).__metric_config__ = Mock(
            side_effect=AttributeError("No config")
        )
        mock_import_module.return_value = mock_module

        # Mock metrics package path
        with patch("garmy.metrics.__path__", ["/fake/path"]):
            configs = MetricDiscovery.discover_metrics()

        # Should return empty dict
        assert len(configs) == 0

    @patch("garmy.core.discovery.importlib.import_module")
    @patch("garmy.core.discovery.pkgutil.iter_modules")
    def test_discover_metrics_skip_dunder_modules(
        self, mock_iter_modules, mock_import_module
    ):
        """Test discovery skips dunder modules like __init__."""
        # Mock module iteration with dunder modules
        mock_module_info1 = Mock()
        mock_module_info1.name = "__init__"
        mock_module_info2 = Mock()
        mock_module_info2.name = "__pycache__"
        mock_module_info3 = Mock()
        mock_module_info3.name = "valid_metric"
        mock_iter_modules.return_value = [
            mock_module_info1,
            mock_module_info2,
            mock_module_info3,
        ]

        # Mock valid module
        mock_valid_module = Mock()
        mock_valid_module.__metric_config__ = MetricConfig(
            metric_class=SampleMetric, endpoint="/valid/endpoint"
        )
        mock_import_module.return_value = mock_valid_module

        # Mock metrics package path
        with patch("garmy.metrics.__path__", ["/fake/path"]):
            configs = MetricDiscovery.discover_metrics()

        # Should only process the valid metric, skip dunder modules
        assert len(configs) == 1
        assert "valid_metric" in configs
        assert "__init__" not in configs
        assert "__pycache__" not in configs

        # Should only call import_module once (for valid_metric)
        mock_import_module.assert_called_once()

    def test_validate_metrics_valid_configs(self):
        """Test validation passes for valid metric configurations."""
        configs = {
            "test_metric": MetricConfig(
                metric_class=SampleMetric, endpoint="/test/endpoint"
            ),
            "another_metric": MetricConfig(
                metric_class=AnotherSampleMetric,
                endpoint="/another/endpoint",
                parser=parser_func,
            ),
        }

        # Should not raise any exceptions
        MetricDiscovery.validate_metrics(configs)

    def test_validate_metrics_empty_configs(self):
        """Test validation passes for empty configurations."""
        configs = {}

        # Should not raise any exceptions
        MetricDiscovery.validate_metrics(configs)

    def test_validate_metrics_invalid_config_type(self):
        """Test validation fails for invalid configuration type."""
        configs = {"invalid_metric": "not a MetricConfig object"}

        with pytest.raises(DiscoveryError, match="Invalid metric configuration"):
            MetricDiscovery.validate_metrics(configs)

    def test_validate_metrics_missing_metric_class(self):
        """Test validation fails for missing metric class."""
        configs = {
            "invalid_metric": MetricConfig(
                metric_class=None,
                endpoint="/test/endpoint",  # Invalid
            )
        }

        with pytest.raises(DiscoveryError, match="Invalid metric configuration"):
            MetricDiscovery.validate_metrics(configs)

    def test_validate_metrics_missing_endpoint(self):
        """Test validation fails for missing endpoint."""
        configs = {
            "invalid_metric": MetricConfig(
                metric_class=SampleMetric,
                endpoint="",  # Invalid empty endpoint
            )
        }

        with pytest.raises(DiscoveryError, match="Invalid metric configuration"):
            MetricDiscovery.validate_metrics(configs)

    def test_validate_metrics_none_endpoint(self):
        """Test validation fails for None endpoint."""
        configs = {
            "invalid_metric": MetricConfig(
                metric_class=SampleMetric,
                endpoint=None,  # Invalid None endpoint
            )
        }

        with pytest.raises(DiscoveryError, match="Invalid metric configuration"):
            MetricDiscovery.validate_metrics(configs)

    def test_validate_metrics_invalid_parser(self):
        """Test validation fails for invalid parser."""
        configs = {
            "invalid_metric": MetricConfig(
                metric_class=SampleMetric,
                endpoint="/test/endpoint",
                parser="not a callable",  # Invalid parser
            )
        }

        with pytest.raises(DiscoveryError, match="Invalid metric configuration"):
            MetricDiscovery.validate_metrics(configs)

    def test_validate_metrics_invalid_endpoint_builder(self):
        """Test validation fails for invalid endpoint builder."""
        configs = {
            "invalid_metric": MetricConfig(
                metric_class=SampleMetric,
                endpoint="/test/endpoint",
                endpoint_builder=123,  # Invalid endpoint builder
            )
        }

        with pytest.raises(DiscoveryError, match="Invalid metric configuration"):
            MetricDiscovery.validate_metrics(configs)

    def test_validate_metrics_multiple_invalid_configs(self):
        """Test validation reports first invalid configuration."""
        configs = {
            "valid_metric": MetricConfig(
                metric_class=SampleMetric, endpoint="/test/endpoint"
            ),
            "invalid_metric1": MetricConfig(
                metric_class=None,
                endpoint="/test/endpoint",  # Invalid
            ),
            "invalid_metric2": MetricConfig(
                metric_class=SampleMetric,
                endpoint="",  # Also invalid
            ),
        }

        with pytest.raises(DiscoveryError, match="Invalid metric configuration"):
            MetricDiscovery.validate_metrics(configs)

    def test_validate_metrics_with_valid_optional_fields(self):
        """Test validation passes with valid optional fields."""
        configs = {
            "full_metric": MetricConfig(
                metric_class=SampleMetric,
                endpoint="/test/endpoint",
                parser=parser_func,
                endpoint_builder=endpoint_builder_func,
            )
        }

        # Should not raise any exceptions
        MetricDiscovery.validate_metrics(configs)

    def test_validate_metrics_with_none_optional_fields(self):
        """Test validation passes with None optional fields."""
        configs = {
            "minimal_metric": MetricConfig(
                metric_class=SampleMetric,
                endpoint="/test/endpoint",
                parser=None,
                endpoint_builder=None,
            )
        }

        # Should not raise any exceptions
        MetricDiscovery.validate_metrics(configs)


class SampleMetricDiscoveryIntegration:
    """Test cases for metric discovery integration scenarios."""

    @patch("garmy.core.discovery.importlib.import_module")
    @patch("garmy.core.discovery.pkgutil.iter_modules")
    def test_discover_and_validate_integration(
        self, mock_iter_modules, mock_import_module
    ):
        """Test integration of discovery and validation."""
        # Mock module iteration
        mock_module_info = Mock()
        mock_module_info.name = "integration_metric"
        mock_iter_modules.return_value = [mock_module_info]

        # Mock module with valid config
        mock_module = Mock()
        mock_module.__metric_config__ = MetricConfig(
            metric_class=SampleMetric,
            endpoint="/integration/endpoint",
            parser=parser_func,
        )
        mock_import_module.return_value = mock_module

        # Mock metrics package path
        with patch("garmy.metrics.__path__", ["/fake/path"]):
            # Discover metrics
            configs = MetricDiscovery.discover_metrics()

            # Validate discovered metrics
            MetricDiscovery.validate_metrics(configs)

        # Should complete without errors
        assert "integration_metric" in configs

    @patch("garmy.core.discovery.importlib.import_module")
    @patch("garmy.core.discovery.pkgutil.iter_modules")
    def test_discover_with_mixed_valid_invalid_modules(
        self, mock_iter_modules, mock_import_module
    ):
        """Test discovery with mix of valid and invalid modules."""
        # Mock multiple modules
        mock_module_info1 = Mock()
        mock_module_info1.name = "valid_metric"
        mock_module_info2 = Mock()
        mock_module_info2.name = "import_error_metric"
        mock_module_info3 = Mock()
        mock_module_info3.name = "no_config_metric"
        mock_iter_modules.return_value = [
            mock_module_info1,
            mock_module_info2,
            mock_module_info3,
        ]

        # Mock different module scenarios
        mock_valid_module = Mock()
        mock_valid_module.__metric_config__ = MetricConfig(
            metric_class=SampleMetric, endpoint="/valid/endpoint"
        )

        mock_no_config_module = Mock()
        del mock_no_config_module.__metric_config__

        def side_effect(module_name):
            if "valid_metric" in module_name:
                return mock_valid_module
            elif "import_error_metric" in module_name:
                raise ImportError("Import failed")
            elif "no_config_metric" in module_name:
                return mock_no_config_module
            return Mock()

        mock_import_module.side_effect = side_effect

        # Mock metrics package path
        with patch("garmy.metrics.__path__", ["/fake/path"]):
            configs = MetricDiscovery.discover_metrics()

        # Should only include valid metrics
        assert len(configs) == 1
        assert "valid_metric" in configs

    @patch("garmy.metrics.__path__", [])
    def test_discover_metrics_no_metrics_package_path(self):
        """Test discovery when metrics package has no path."""
        configs = MetricDiscovery.discover_metrics()

        # Should return empty dict when no path is available
        assert configs == {}


class SampleMetricDiscoveryErrorHandling:
    """Test cases for error handling in metric discovery."""

    def test_discovery_error_creation(self):
        """Test DiscoveryError can be created."""
        error = DiscoveryError("Test error message")

        assert isinstance(error, Exception)
        assert str(error) == "Test error message"

    def test_discovery_error_inheritance(self):
        """Test DiscoveryError inherits from appropriate base."""
        error = DiscoveryError("Test error")

        assert isinstance(error, Exception)

    @patch("garmy.core.discovery.importlib.import_module")
    @patch("garmy.core.discovery.pkgutil.iter_modules")
    def test_discovery_handles_unexpected_errors(
        self, mock_iter_modules, mock_import_module
    ):
        """Test discovery handles unexpected errors during module processing."""
        # Mock module iteration
        mock_module_info = Mock()
        mock_module_info.name = "problematic_metric"
        mock_iter_modules.return_value = [mock_module_info]

        # Mock module that raises unexpected error
        mock_import_module.side_effect = ValueError("Unexpected error")

        # Mock metrics package path
        with patch("garmy.metrics.__path__", ["/fake/path"]):
            configs = MetricDiscovery.discover_metrics()

        # Should handle error gracefully and return empty dict
        assert len(configs) == 0

    def test_validate_metrics_detailed_error_messages(self):
        """Test validation provides detailed error messages."""
        configs = {
            "problematic_metric": MetricConfig(
                metric_class=SampleMetric,
                endpoint="",  # Invalid empty endpoint
            )
        }

        with pytest.raises(DiscoveryError) as exc_info:
            MetricDiscovery.validate_metrics(configs)

        error_message = str(exc_info.value)
        assert "problematic_metric" in error_message
        assert "Invalid metric configuration" in error_message
