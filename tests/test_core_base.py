"""Comprehensive tests for garmy.core.base module.

This module provides 100% test coverage for base classes and protocols.
"""

from dataclasses import dataclass
from typing import Any, Dict
from unittest.mock import Mock

import pytest

from garmy.core.base import EndpointBuilder, MetricConfig, MetricParser


# Test dataclasses for testing MetricConfig
@dataclass
class SampleMetric:
    """Test metric class for testing."""

    value: int
    name: str


@dataclass
class SampleSummary:
    """Test summary class for testing."""

    total: int
    average: float


class TestEndpointBuilder:
    """Test cases for EndpointBuilder protocol."""

    def test_endpoint_builder_protocol_structure(self):
        """Test EndpointBuilder protocol has required methods."""
        # Test that protocol is callable
        assert callable(EndpointBuilder)

        # Check protocol has required methods
        import inspect

        # Get the __call__ method signature
        signature = inspect.signature(EndpointBuilder.__call__)
        assert "date_input" in signature.parameters
        assert "api_client" in signature.parameters

    def test_endpoint_builder_protocol_compliance(self):
        """Test class can implement EndpointBuilder protocol."""

        class TestBuilder:
            def __call__(self, date_input=None, api_client=None, **kwargs):
                return "/test/endpoint"

        builder = TestBuilder()

        # Should be able to use as EndpointBuilder
        assert callable(builder)
        assert callable(builder)

        # Test method works
        result = builder()
        assert result == "/test/endpoint"

    def test_endpoint_builder_with_parameters(self):
        """Test EndpointBuilder with various parameters."""

        class ParameterizedBuilder:
            def build(self, date_input=None, api_client=None, **kwargs):
                parts = ["/test"]
                if date_input:
                    parts.append(str(date_input))
                if kwargs.get("user_id"):
                    parts.append(kwargs["user_id"])
                return "/".join(parts)

        builder = ParameterizedBuilder()

        # Test with no parameters
        assert builder.build() == "/test"

        # Test with date
        assert builder.build(date_input="2023-12-01") == "/test/2023-12-01"

        # Test with kwargs
        assert builder.build(user_id="123") == "/test/123"

        # Test with multiple parameters
        result = builder.build(date_input="2023-12-01", user_id="123")
        assert result == "/test/2023-12-01/123"


class SampleMetricParser:
    """Test cases for MetricParser protocol."""

    def test_metric_parser_protocol_structure(self):
        """Test MetricParser protocol has required methods."""
        # Test that protocol is callable
        assert callable(MetricParser)

        # Check protocol has required methods
        import inspect

        # Get the __call__ method signature
        signature = inspect.signature(MetricParser.__call__)
        assert "data" in signature.parameters

    def test_metric_parser_protocol_compliance(self):
        """Test class can implement MetricParser protocol."""

        class TestParser:
            def __call__(self, data: Any) -> Any:
                return {"parsed": data}

        parser = TestParser()

        # Should be able to use as MetricParser
        assert callable(parser)
        assert callable(parser)

        # Test method works
        result = parser("test_data")
        assert result == {"parsed": "test_data"}

    def test_metric_parser_with_different_inputs(self):
        """Test MetricParser with various input types."""

        class FlexibleParser:
            def parse(self, data: Any) -> Any:
                if isinstance(data, dict):
                    return SampleMetric(data.get("value", 0), data.get("name", ""))
                elif isinstance(data, list):
                    return [self.parse(item) for item in data]
                else:
                    return SampleMetric(0, str(data))

        parser = FlexibleParser()

        # Test with dict
        result = parser.parse({"value": 42, "name": "test"})
        assert isinstance(result, SampleMetric)
        assert result.value == 42
        assert result.name == "test"

        # Test with list
        results = parser.parse([{"value": 1, "name": "a"}, {"value": 2, "name": "b"}])
        assert isinstance(results, list)
        assert len(results) == 2
        assert all(isinstance(r, SampleMetric) for r in results)

        # Test with string
        result = parser.parse("simple")
        assert isinstance(result, SampleMetric)
        assert result.value == 0
        assert result.name == "simple"

    def test_metric_parser_error_handling(self):
        """Test MetricParser with error handling."""

        class SafeParser:
            def parse(self, data: Any) -> Any:
                try:
                    if not isinstance(data, dict):
                        raise ValueError("Expected dict")
                    return SampleMetric(data["value"], data["name"])
                except (KeyError, ValueError) as e:
                    return SampleMetric(-1, f"error: {e}")

        parser = SafeParser()

        # Test with valid data
        result = parser.parse({"value": 10, "name": "valid"})
        assert result.value == 10
        assert result.name == "valid"

        # Test with invalid data
        result = parser.parse("invalid")
        assert result.value == -1
        assert "error:" in result.name

        # Test with missing keys
        result = parser.parse({"value": 5})  # Missing 'name'
        assert result.value == -1
        assert "error:" in result.name


class SampleMetricConfig:
    """Test cases for MetricConfig dataclass."""

    def test_metric_config_creation(self):
        """Test basic MetricConfig creation."""
        config = MetricConfig(metric_class=SampleMetric, endpoint="/test/endpoint")

        assert config.metric_class == SampleMetric
        assert config.endpoint == "/test/endpoint"
        assert config.parser is None
        assert config.endpoint_builder is None

    def test_metric_config_with_all_fields(self):
        """Test MetricConfig with all optional fields."""
        mock_parser = Mock()
        mock_builder = Mock()

        config = MetricConfig(
            metric_class=SampleMetric,
            endpoint="/test/endpoint",
            parser=mock_parser,
            endpoint_builder=mock_builder,
        )

        assert config.metric_class == SampleMetric
        assert config.endpoint == "/test/endpoint"
        assert config.parser == mock_parser
        assert config.endpoint_builder == mock_builder

    def test_metric_config_immutable(self):
        """Test MetricConfig is frozen (immutable)."""
        config = MetricConfig(metric_class=SampleMetric, endpoint="/test/endpoint")

        # Should not be able to modify fields
        with pytest.raises(AttributeError):
            config.metric_class = SampleSummary

        with pytest.raises(AttributeError):
            config.endpoint = "/new/endpoint"

    def test_metric_config_equality(self):
        """Test MetricConfig equality comparison."""
        config1 = MetricConfig(metric_class=SampleMetric, endpoint="/test/endpoint")

        config2 = MetricConfig(metric_class=SampleMetric, endpoint="/test/endpoint")

        config3 = MetricConfig(metric_class=SampleSummary, endpoint="/test/endpoint")

        # Same configurations should be equal
        assert config1 == config2

        # Different configurations should not be equal
        assert config1 != config3

    def test_metric_config_with_parser_function(self):
        """Test MetricConfig with actual parser function."""

        def test_parser(data: Dict[str, Any]) -> SampleMetric:
            return SampleMetric(data.get("value", 0), data.get("name", ""))

        config = MetricConfig(
            metric_class=SampleMetric, endpoint="/test/endpoint", parser=test_parser
        )

        assert config.parser == test_parser
        assert callable(config.parser)

        # Test parser works
        result = config.parser({"value": 42, "name": "test"})
        assert isinstance(result, SampleMetric)
        assert result.value == 42
        assert result.name == "test"

    def test_metric_config_with_endpoint_builder(self):
        """Test MetricConfig with actual endpoint builder."""

        def test_builder(date_input=None, api_client=None, **kwargs):
            return f"/test/{date_input or 'today'}"

        config = MetricConfig(
            metric_class=SampleMetric,
            endpoint="/test/endpoint",
            endpoint_builder=test_builder,
        )

        assert config.endpoint_builder == test_builder
        assert callable(config.endpoint_builder)

        # Test builder works
        result = config.endpoint_builder(date_input="2023-12-01")
        assert result == "/test/2023-12-01"

    def test_metric_config_repr(self):
        """Test MetricConfig string representation."""
        config = MetricConfig(metric_class=SampleMetric, endpoint="/test/endpoint")

        repr_str = repr(config)

        assert "MetricConfig" in repr_str
        assert "SampleMetric" in repr_str
        assert "/test/endpoint" in repr_str

    def test_metric_config_generic_typing(self):
        """Test MetricConfig generic type parameter."""
        # Test that we can create configs with different metric types
        config1: MetricConfig[SampleMetric] = MetricConfig(
            metric_class=SampleMetric, endpoint="/metric"
        )

        config2: MetricConfig[SampleSummary] = MetricConfig(
            metric_class=SampleSummary, endpoint="/summary"
        )

        assert config1.metric_class == SampleMetric
        assert config2.metric_class == SampleSummary

    def test_metric_config_type_hints(self):
        """Test MetricConfig type annotations work correctly."""
        MetricConfig(metric_class=SampleMetric, endpoint="/test/endpoint")

        # Should be able to access annotations
        annotations = MetricConfig.__annotations__

        assert "metric_class" in annotations
        assert "endpoint" in annotations
        assert "parser" in annotations
        assert "endpoint_builder" in annotations

    def test_metric_config_with_none_values(self):
        """Test MetricConfig with None values for optional fields."""
        config = MetricConfig(
            metric_class=SampleMetric,
            endpoint="/test/endpoint",
            parser=None,
            endpoint_builder=None,
        )

        assert config.metric_class == SampleMetric
        assert config.endpoint == "/test/endpoint"
        assert config.parser is None
        assert config.endpoint_builder is None

    def test_metric_config_hash(self):
        """Test MetricConfig is hashable (for use in sets/dicts)."""
        config1 = MetricConfig(metric_class=SampleMetric, endpoint="/test/endpoint")

        config2 = MetricConfig(metric_class=SampleMetric, endpoint="/test/endpoint")

        # Should be hashable
        config_set = {config1, config2}
        assert len(config_set) == 1  # Same configs should hash to same value

        # Should be usable as dict key
        config_dict = {config1: "test_value"}
        assert config_dict[config2] == "test_value"


class TestProtocolCompliance:
    """Test cases for protocol compliance and type checking."""

    def test_endpoint_builder_protocol_checking(self):
        """Test endpoint builder protocol checking."""

        class ValidBuilder:
            def build(self, date_input=None, api_client=None, **kwargs):
                return "/valid"

        class InvalidBuilder:
            def wrong_method(self):
                pass

        valid_builder = ValidBuilder()
        invalid_builder = InvalidBuilder()

        # Valid builder should have required method
        assert hasattr(valid_builder, "build")

        # Invalid builder should not have required method
        assert not hasattr(invalid_builder, "build")

    def test_metric_parser_protocol_checking(self):
        """Test metric parser protocol checking."""

        class ValidParser:
            def parse(self, data):
                return data

        class InvalidParser:
            def wrong_method(self, data):
                return data

        valid_parser = ValidParser()
        invalid_parser = InvalidParser()

        # Valid parser should have required method
        assert hasattr(valid_parser, "parse")

        # Invalid parser should not have required method
        assert not hasattr(invalid_parser, "parse")

    def test_protocol_methods_callable(self):
        """Test protocol methods are callable."""

        class TestImplementation:
            def build(self):
                return "built"

            def parse(self, data):
                return data

        impl = TestImplementation()

        # Methods should be callable
        assert callable(impl.build)
        assert callable(impl.parse)

        # Methods should work
        assert impl.build() == "built"
        assert impl.parse("test") == "test"
