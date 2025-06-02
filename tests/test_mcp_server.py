"""
Comprehensive tests for MCP server module.

Tests the main GarmyMCPServer class and all its functionality to achieve 100% coverage.
"""

import logging
from dataclasses import dataclass
from io import StringIO
from unittest.mock import Mock, patch

import anyio
import pytest

try:
    from builtins import BaseExceptionGroup  # Python 3.11+
except ImportError:
    # Python < 3.11 compatibility
    BaseExceptionGroup = Exception

from garmy.mcp.config import MCPConfig
from garmy.mcp.server import GarmyMCPServer


@dataclass
class MockMetricData:
    """Mock metric data for testing."""

    value: float = 123.45
    quality: str = "good"

    def __str__(self):
        return f"MockMetricData(value={self.value}, quality='{self.quality}')"


class TestGarmyMCPServer:
    """Test suite for GarmyMCPServer class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_config = MCPConfig()
        self.mock_config.debug_mode = False  # Disable debug output for clean tests

    @patch("garmy.mcp.server.MetricDiscovery")
    @patch("garmy.mcp.server.FastMCP")
    def test_init_with_default_config(self, mock_fastmcp, mock_discovery):
        """Test server initialization with default configuration."""
        mock_discovery.discover_metrics.return_value = {}
        mock_discovery.validate_metrics.return_value = None

        server = GarmyMCPServer()

        assert server.config is not None
        assert server.mcp is not None
        assert server.auth_client is None
        assert server.api_client is None
        assert server.discovered_metrics == {}
        mock_fastmcp.assert_called_once()

    @patch("garmy.mcp.server.MetricDiscovery")
    @patch("garmy.mcp.server.FastMCP")
    def test_init_with_custom_config(self, mock_fastmcp, mock_discovery):
        """Test server initialization with custom configuration."""
        mock_discovery.discover_metrics.return_value = {}
        mock_discovery.validate_metrics.return_value = None

        config = MCPConfig(server_name="Test Server", debug_mode=True)
        server = GarmyMCPServer(config)

        assert server.config == config
        mock_fastmcp.assert_called_once_with("Test Server")

    @patch("garmy.mcp.server.MetricDiscovery")
    @patch("garmy.mcp.server.FastMCP")
    @patch("garmy.mcp.server.logging.basicConfig")
    def test_init_with_debug_mode(
        self, mock_logging_config, mock_fastmcp, mock_discovery
    ):
        """Test server initialization with debug mode enabled."""
        mock_discovery.discover_metrics.return_value = {}
        mock_discovery.validate_metrics.return_value = None

        config = MCPConfig(debug_mode=True)
        GarmyMCPServer(config)

        mock_logging_config.assert_called_once_with(level=logging.DEBUG)

    @patch("garmy.mcp.server.MetricDiscovery")
    @patch("garmy.mcp.server.FastMCP")
    def test_discover_metrics_success(self, mock_fastmcp, mock_discovery):
        """Test successful metric discovery."""
        mock_metrics = {"sleep": Mock(), "steps": Mock()}
        mock_discovery.discover_metrics.return_value = mock_metrics
        mock_discovery.validate_metrics.return_value = None

        with patch("garmy.mcp.server.logger") as mock_logger:
            server = GarmyMCPServer(self.mock_config)

        assert server.discovered_metrics == mock_metrics
        mock_discovery.discover_metrics.assert_called_once()
        mock_discovery.validate_metrics.assert_called_once_with(mock_metrics)
        mock_logger.info.assert_called_once_with("Discovered 2 metrics")

    @patch("garmy.mcp.server.MetricDiscovery")
    @patch("garmy.mcp.server.FastMCP")
    def test_discover_metrics_failure(self, mock_fastmcp, mock_discovery):
        """Test metric discovery failure."""
        mock_discovery.discover_metrics.side_effect = Exception("Discovery failed")

        with patch("garmy.mcp.server.logger") as mock_logger:
            server = GarmyMCPServer(self.mock_config)

        assert server.discovered_metrics == {}
        mock_logger.error.assert_called_once_with(
            "Error discovering metrics: Discovery failed"
        )

    @patch("garmy.mcp.server.MetricDiscovery")
    @patch("garmy.mcp.server.FastMCP")
    @patch("garmy.mcp.server.AuthTools")
    def test_register_auth_tools(
        self, mock_auth_tools_class, mock_fastmcp, mock_discovery
    ):
        """Test authentication tools registration."""
        mock_discovery.discover_metrics.return_value = {}
        mock_discovery.validate_metrics.return_value = None
        mock_auth_tools = Mock()
        mock_auth_tools_class.return_value = mock_auth_tools

        config = MCPConfig(enable_auth_tools=True)
        server = GarmyMCPServer(config)

        mock_auth_tools_class.assert_called_once_with(server)
        mock_auth_tools.register_tools.assert_called_once_with(server.mcp)

    @patch("garmy.mcp.server.MetricDiscovery")
    @patch("garmy.mcp.server.FastMCP")
    @patch("garmy.mcp.server.MetricTools")
    def test_register_metric_tools(
        self, mock_metric_tools_class, mock_fastmcp, mock_discovery
    ):
        """Test metric tools registration."""
        mock_discovery.discover_metrics.return_value = {}
        mock_discovery.validate_metrics.return_value = None
        mock_metric_tools = Mock()
        mock_metric_tools_class.return_value = mock_metric_tools

        config = MCPConfig(enable_metric_tools=True)
        server = GarmyMCPServer(config)

        mock_metric_tools_class.assert_called_once_with(server)
        mock_metric_tools.register_tools.assert_called_once_with(server.mcp)

    @patch("garmy.mcp.server.MetricDiscovery")
    @patch("garmy.mcp.server.FastMCP")
    @patch("garmy.mcp.server.AnalysisTools")
    def test_register_analysis_tools(
        self, mock_analysis_tools_class, mock_fastmcp, mock_discovery
    ):
        """Test analysis tools registration."""
        mock_discovery.discover_metrics.return_value = {}
        mock_discovery.validate_metrics.return_value = None
        mock_analysis_tools = Mock()
        mock_analysis_tools_class.return_value = mock_analysis_tools

        config = MCPConfig(enable_analysis_tools=True)
        server = GarmyMCPServer(config)

        mock_analysis_tools_class.assert_called_once_with(server)
        mock_analysis_tools.register_tools.assert_called_once_with(server.mcp)

    @patch("garmy.mcp.server.MetricDiscovery")
    @patch("garmy.mcp.server.FastMCP")
    @patch("garmy.mcp.server.ResourceProviders")
    def test_register_resources(
        self, mock_resource_providers_class, mock_fastmcp, mock_discovery
    ):
        """Test resource providers registration."""
        mock_discovery.discover_metrics.return_value = {}
        mock_discovery.validate_metrics.return_value = None
        mock_resource_providers = Mock()
        mock_resource_providers_class.return_value = mock_resource_providers

        config = MCPConfig(enable_resources=True)
        server = GarmyMCPServer(config)

        mock_resource_providers_class.assert_called_once_with(server)
        mock_resource_providers.register_resources.assert_called_once_with(server.mcp)

    @patch("garmy.mcp.server.MetricDiscovery")
    @patch("garmy.mcp.server.FastMCP")
    @patch("garmy.mcp.server.PromptTemplates")
    def test_register_prompts(
        self, mock_prompt_templates_class, mock_fastmcp, mock_discovery
    ):
        """Test prompt templates registration."""
        mock_discovery.discover_metrics.return_value = {}
        mock_discovery.validate_metrics.return_value = None
        mock_prompt_templates = Mock()
        mock_prompt_templates_class.return_value = mock_prompt_templates

        config = MCPConfig(enable_prompts=True)
        server = GarmyMCPServer(config)

        mock_prompt_templates_class.assert_called_once_with(server)
        mock_prompt_templates.register_prompts.assert_called_once_with(server.mcp)

    @patch("garmy.mcp.server.MetricDiscovery")
    @patch("garmy.mcp.server.FastMCP")
    def test_initialize_components_all_disabled(self, mock_fastmcp, mock_discovery):
        """Test component initialization with all features disabled."""
        mock_discovery.discover_metrics.return_value = {}
        mock_discovery.validate_metrics.return_value = None

        config = MCPConfig(
            enable_auth_tools=False,
            enable_metric_tools=False,
            enable_analysis_tools=False,
            enable_resources=False,
            enable_prompts=False,
        )

        # Should not raise any errors
        server = GarmyMCPServer(config)
        assert server is not None

    @patch("garmy.mcp.server.MetricDiscovery")
    @patch("garmy.mcp.server.FastMCP")
    @patch("garmy.mcp.server.AuthClient")
    @patch("garmy.mcp.server.APIClient")
    def test_authenticate_success(
        self,
        mock_api_client_class,
        mock_auth_client_class,
        mock_fastmcp,
        mock_discovery,
    ):
        """Test successful authentication."""
        mock_discovery.discover_metrics.return_value = {}
        mock_discovery.validate_metrics.return_value = None

        mock_auth_client = Mock()
        mock_api_client = Mock()
        mock_auth_client_class.return_value = mock_auth_client
        mock_api_client_class.return_value = mock_api_client

        server = GarmyMCPServer(self.mock_config)
        result = server.authenticate("test@example.com", "password123")

        assert result is True
        assert server.auth_client == mock_auth_client
        assert server.api_client == mock_api_client
        mock_auth_client.login.assert_called_once_with(
            "test@example.com", "password123"
        )
        mock_api_client_class.assert_called_once_with(auth_client=mock_auth_client)

    @patch("garmy.mcp.server.MetricDiscovery")
    @patch("garmy.mcp.server.FastMCP")
    @patch("garmy.mcp.server.AuthClient")
    def test_authenticate_failure(
        self, mock_auth_client_class, mock_fastmcp, mock_discovery
    ):
        """Test authentication failure."""
        mock_discovery.discover_metrics.return_value = {}
        mock_discovery.validate_metrics.return_value = None

        mock_auth_client = Mock()
        mock_auth_client.login.side_effect = Exception("Login failed")
        mock_auth_client_class.return_value = mock_auth_client

        with patch("garmy.mcp.server.logger") as mock_logger:
            server = GarmyMCPServer(self.mock_config)
            result = server.authenticate("test@example.com", "wrongpass")

        assert result is False
        assert server.auth_client is None
        assert server.api_client is None
        mock_logger.error.assert_called_once_with("Authentication failed: Login failed")

    @patch("garmy.mcp.server.MetricDiscovery")
    @patch("garmy.mcp.server.FastMCP")
    def test_logout(self, mock_fastmcp, mock_discovery):
        """Test logout functionality."""
        mock_discovery.discover_metrics.return_value = {}
        mock_discovery.validate_metrics.return_value = None

        server = GarmyMCPServer(self.mock_config)
        server.auth_client = Mock()
        server.api_client = Mock()

        with patch("garmy.mcp.server.logger") as mock_logger:
            server.logout()

        assert server.auth_client is None
        assert server.api_client is None
        mock_logger.info.assert_called_once_with("Logged out from Garmin Connect")

    @patch("garmy.mcp.server.MetricDiscovery")
    @patch("garmy.mcp.server.FastMCP")
    def test_is_authenticated_true(self, mock_fastmcp, mock_discovery):
        """Test authentication status when authenticated."""
        mock_discovery.discover_metrics.return_value = {}
        mock_discovery.validate_metrics.return_value = None

        server = GarmyMCPServer(self.mock_config)
        server.auth_client = Mock()
        server.api_client = Mock()

        assert server.is_authenticated() is True

    @patch("garmy.mcp.server.MetricDiscovery")
    @patch("garmy.mcp.server.FastMCP")
    def test_is_authenticated_false_no_auth_client(self, mock_fastmcp, mock_discovery):
        """Test authentication status with no auth client."""
        mock_discovery.discover_metrics.return_value = {}
        mock_discovery.validate_metrics.return_value = None

        server = GarmyMCPServer(self.mock_config)
        server.auth_client = None
        server.api_client = Mock()

        assert server.is_authenticated() is False

    @patch("garmy.mcp.server.MetricDiscovery")
    @patch("garmy.mcp.server.FastMCP")
    def test_is_authenticated_false_no_api_client(self, mock_fastmcp, mock_discovery):
        """Test authentication status with no API client."""
        mock_discovery.discover_metrics.return_value = {}
        mock_discovery.validate_metrics.return_value = None

        server = GarmyMCPServer(self.mock_config)
        server.auth_client = Mock()
        server.api_client = None

        assert server.is_authenticated() is False

    @patch("garmy.mcp.server.MetricDiscovery")
    @patch("garmy.mcp.server.FastMCP")
    def test_validate_authentication_success(self, mock_fastmcp, mock_discovery):
        """Test authentication validation when authenticated."""
        mock_discovery.discover_metrics.return_value = {}
        mock_discovery.validate_metrics.return_value = None

        server = GarmyMCPServer(self.mock_config)
        server.auth_client = Mock()
        server.api_client = Mock()

        # Should not raise an exception
        server._validate_authentication()

    @patch("garmy.mcp.server.MetricDiscovery")
    @patch("garmy.mcp.server.FastMCP")
    def test_validate_authentication_failure(self, mock_fastmcp, mock_discovery):
        """Test authentication validation when not authenticated."""
        mock_discovery.discover_metrics.return_value = {}
        mock_discovery.validate_metrics.return_value = None

        server = GarmyMCPServer(self.mock_config)
        server.auth_client = None
        server.api_client = None

        with pytest.raises(ValueError, match="Authentication required"):
            server._validate_authentication()

    @patch("garmy.mcp.server.MetricDiscovery")
    @patch("garmy.mcp.server.FastMCP")
    def test_validate_metric_name_success(self, mock_fastmcp, mock_discovery):
        """Test metric name validation with valid metric."""
        mock_discovery.discover_metrics.return_value = {}
        mock_discovery.validate_metrics.return_value = None

        server = GarmyMCPServer(self.mock_config)
        server.api_client = Mock()
        server.api_client.metrics.keys.return_value = ["sleep", "steps", "heart_rate"]

        # Should not raise an exception
        server._validate_metric_name("sleep")

    @patch("garmy.mcp.server.MetricDiscovery")
    @patch("garmy.mcp.server.FastMCP")
    def test_validate_metric_name_failure(self, mock_fastmcp, mock_discovery):
        """Test metric name validation with invalid metric."""
        mock_discovery.discover_metrics.return_value = {}
        mock_discovery.validate_metrics.return_value = None

        server = GarmyMCPServer(self.mock_config)
        server.api_client = Mock()
        server.api_client.metrics.keys.return_value = ["sleep", "steps"]

        with pytest.raises(ValueError, match="Unknown metric 'invalid'"):
            server._validate_metric_name("invalid")

    @patch("garmy.mcp.server.MetricDiscovery")
    @patch("garmy.mcp.server.FastMCP")
    def test_get_metric_data_success(self, mock_fastmcp, mock_discovery):
        """Test successful metric data retrieval."""
        mock_discovery.discover_metrics.return_value = {}
        mock_discovery.validate_metrics.return_value = None

        server = GarmyMCPServer(self.mock_config)
        server.auth_client = Mock()
        server.api_client = Mock()

        mock_metric_accessor = Mock()
        mock_metric_data = MockMetricData(value=123.45)
        mock_metric_accessor.get.return_value = mock_metric_data
        server.api_client.metrics = {"sleep": mock_metric_accessor}
        server.api_client.metrics.keys.return_value = ["sleep"]

        result = server.get_metric_data("sleep", "2023-12-01")

        assert result == mock_metric_data
        mock_metric_accessor.get.assert_called_once_with("2023-12-01")

    @patch("garmy.mcp.server.MetricDiscovery")
    @patch("garmy.mcp.server.FastMCP")
    def test_get_metric_data_not_authenticated(self, mock_fastmcp, mock_discovery):
        """Test metric data retrieval when not authenticated."""
        mock_discovery.discover_metrics.return_value = {}
        mock_discovery.validate_metrics.return_value = None

        server = GarmyMCPServer(self.mock_config)
        server.auth_client = None
        server.api_client = None

        with pytest.raises(ValueError, match="Authentication required"):
            server.get_metric_data("sleep", "2023-12-01")

    @patch("garmy.mcp.server.MetricDiscovery")
    @patch("garmy.mcp.server.FastMCP")
    def test_get_metric_data_invalid_metric(self, mock_fastmcp, mock_discovery):
        """Test metric data retrieval with invalid metric name."""
        mock_discovery.discover_metrics.return_value = {}
        mock_discovery.validate_metrics.return_value = None

        server = GarmyMCPServer(self.mock_config)
        server.auth_client = Mock()
        server.api_client = Mock()
        server.api_client.metrics.keys.return_value = ["sleep"]

        with pytest.raises(ValueError, match="Unknown metric 'invalid'"):
            server.get_metric_data("invalid", "2023-12-01")

    @patch("garmy.mcp.server.MetricDiscovery")
    @patch("garmy.mcp.server.FastMCP")
    def test_get_metric_history_success(self, mock_fastmcp, mock_discovery):
        """Test successful metric history retrieval."""
        mock_discovery.discover_metrics.return_value = {}
        mock_discovery.validate_metrics.return_value = None

        server = GarmyMCPServer(self.mock_config)
        server.auth_client = Mock()
        server.api_client = Mock()

        mock_metric_accessor = Mock()
        mock_history_data = [MockMetricData(value=100.0), MockMetricData(value=200.0)]
        mock_metric_accessor.list.return_value = mock_history_data
        server.api_client.metrics = {"sleep": mock_metric_accessor}
        server.api_client.metrics.keys.return_value = ["sleep"]

        result = server.get_metric_history("sleep", 7, "2023-12-01")

        assert result == mock_history_data
        mock_metric_accessor.list.assert_called_once_with(end="2023-12-01", days=7)

    @patch("garmy.mcp.server.MetricDiscovery")
    @patch("garmy.mcp.server.FastMCP")
    def test_get_metric_history_limit_days(self, mock_fastmcp, mock_discovery):
        """Test metric history retrieval with days limit."""
        mock_discovery.discover_metrics.return_value = {}
        mock_discovery.validate_metrics.return_value = None

        config = MCPConfig(max_history_days=30)
        server = GarmyMCPServer(config)
        server.auth_client = Mock()
        server.api_client = Mock()

        mock_metric_accessor = Mock()
        mock_metric_accessor.list.return_value = []
        server.api_client.metrics = {"sleep": mock_metric_accessor}
        server.api_client.metrics.keys.return_value = ["sleep"]

        server.get_metric_history(
            "sleep", 100
        )  # Request 100 days, should be limited to 30

        mock_metric_accessor.list.assert_called_once_with(end=None, days=30)

    @patch("garmy.mcp.server.MetricDiscovery")
    @patch("garmy.mcp.server.FastMCP")
    def test_format_metric_data_none(self, mock_fastmcp, mock_discovery):
        """Test formatting None metric data."""
        mock_discovery.discover_metrics.return_value = {}
        mock_discovery.validate_metrics.return_value = None

        server = GarmyMCPServer(self.mock_config)

        result = server.format_metric_data(None, "sleep")
        assert result == "No data"

    @patch("garmy.mcp.server.MetricDiscovery")
    @patch("garmy.mcp.server.FastMCP")
    def test_format_metric_data_with_str_method(self, mock_fastmcp, mock_discovery):
        """Test formatting metric data with custom __str__ method."""
        mock_discovery.discover_metrics.return_value = {}
        mock_discovery.validate_metrics.return_value = None

        server = GarmyMCPServer(self.mock_config)
        data = MockMetricData(value=123.45, quality="excellent")

        result = server.format_metric_data(data, "sleep")
        assert "MockMetricData(value=123.45, quality='excellent')" in result

    @patch("garmy.mcp.server.MetricDiscovery")
    @patch("garmy.mcp.server.FastMCP")
    def test_format_metric_data_fallback_to_attributes(
        self, mock_fastmcp, mock_discovery
    ):
        """Test formatting metric data falling back to attributes."""
        mock_discovery.discover_metrics.return_value = {}
        mock_discovery.validate_metrics.return_value = None

        server = GarmyMCPServer(self.mock_config)

        # Create object without meaningful __str__ method
        class SimpleData:
            def __init__(self):
                self.temperature = 98.6
                self.humidity = 65
                self.pressure = 1013.25

        data = SimpleData()

        result = server.format_metric_data(data, "weather")
        assert "Temperature: 98.6" in result
        assert "Humidity: 65" in result
        assert "Pressure: 1013.3" in result  # Float formatting

    @patch("garmy.mcp.server.MetricDiscovery")
    @patch("garmy.mcp.server.FastMCP")
    def test_format_metric_data_string_type(self, mock_fastmcp, mock_discovery):
        """Test formatting string metric data."""
        mock_discovery.discover_metrics.return_value = {}
        mock_discovery.validate_metrics.return_value = None

        server = GarmyMCPServer(self.mock_config)

        # String data should use object attributes fallback
        result = server.format_metric_data("simple string", "test")
        assert result == "simple string"

    @patch("garmy.mcp.server.MetricDiscovery")
    @patch("garmy.mcp.server.FastMCP")
    def test_format_metric_data_exception(self, mock_fastmcp, mock_discovery):
        """Test formatting metric data with exception."""
        mock_discovery.discover_metrics.return_value = {}
        mock_discovery.validate_metrics.return_value = None

        server = GarmyMCPServer(self.mock_config)

        # Create object that will cause exception during formatting
        class BadData:
            def __str__(self):
                raise ValueError("Formatting error")

            def __dict__(self):
                raise ValueError("Dict access error")

        data = BadData()

        with patch("garmy.mcp.server.logger") as mock_logger:
            result = server.format_metric_data(data, "bad_metric")

        assert "Formatting error:" in result
        mock_logger.error.assert_called_once()

    @patch("garmy.mcp.server.MetricDiscovery")
    @patch("garmy.mcp.server.FastMCP")
    def test_format_object_attributes_compact(self, mock_fastmcp, mock_discovery):
        """Test formatting object attributes in compact mode."""
        mock_discovery.discover_metrics.return_value = {}
        mock_discovery.validate_metrics.return_value = None

        server = GarmyMCPServer(self.mock_config)

        class TestData:
            def __init__(self):
                self.field1 = "value1"
                self.field2 = "value2"
                self.field3 = "value3"
                self.field4 = "value4"  # Should be excluded in compact mode

        data = TestData()

        result = server._format_object_attributes(data, compact=True)
        lines = result.split("\n")
        assert len(lines) <= 3  # Compact mode should limit fields

    @patch("garmy.mcp.server.MetricDiscovery")
    @patch("garmy.mcp.server.FastMCP")
    def test_format_object_attributes_large_numbers(self, mock_fastmcp, mock_discovery):
        """Test formatting object attributes with large numbers."""
        mock_discovery.discover_metrics.return_value = {}
        mock_discovery.validate_metrics.return_value = None

        server = GarmyMCPServer(self.mock_config)

        class TestData:
            def __init__(self):
                self.large_int = 1234567
                self.float_val = 123.456789
                self.small_int = 42

        data = TestData()

        result = server._format_object_attributes(data, compact=False)
        assert "1,234,567" in result  # Large integer formatting
        assert "123.5" in result  # Float formatting
        assert "42" in result  # Small integer - no formatting change

    @patch("garmy.mcp.server.MetricDiscovery")
    @patch("garmy.mcp.server.FastMCP")
    def test_format_object_attributes_none_values(self, mock_fastmcp, mock_discovery):
        """Test formatting object attributes with None values."""
        mock_discovery.discover_metrics.return_value = {}
        mock_discovery.validate_metrics.return_value = None

        server = GarmyMCPServer(self.mock_config)

        class TestData:
            def __init__(self):
                self.valid_field = "value"
                self.none_field = None
                self._private_field = "private"

        data = TestData()

        result = server._format_object_attributes(data, compact=False)
        assert "Valid Field: value" in result
        assert "none_field" not in result  # None values should be excluded
        assert "_private_field" not in result  # Private fields should be excluded

    @patch("garmy.mcp.server.MetricDiscovery")
    @patch("garmy.mcp.server.FastMCP")
    def test_format_object_attributes_no_dict(self, mock_fastmcp, mock_discovery):
        """Test formatting object without __dict__ attribute."""
        mock_discovery.discover_metrics.return_value = {}
        mock_discovery.validate_metrics.return_value = None

        server = GarmyMCPServer(self.mock_config)

        # Use a simple type without __dict__
        data = 42

        result = server._format_object_attributes(data, compact=False)
        assert result == "42"

    @patch("garmy.mcp.server.MetricDiscovery")
    @patch("garmy.mcp.server.FastMCP")
    def test_format_object_attributes_empty_dict(self, mock_fastmcp, mock_discovery):
        """Test formatting object with empty attributes."""
        mock_discovery.discover_metrics.return_value = {}
        mock_discovery.validate_metrics.return_value = None

        server = GarmyMCPServer(self.mock_config)

        class EmptyData:
            pass

        data = EmptyData()

        result = server._format_object_attributes(data, compact=False)
        assert result == "Data available"  # Fallback for empty attributes

    @patch("garmy.mcp.server.MetricDiscovery")
    @patch("garmy.mcp.server.FastMCP")
    def test_run_stdio_transport(self, mock_fastmcp, mock_discovery):
        """Test running server with stdio transport."""
        mock_discovery.discover_metrics.return_value = {}
        mock_discovery.validate_metrics.return_value = None

        server = GarmyMCPServer(self.mock_config)

        server.run(transport="stdio")
        server.mcp.run.assert_called_once_with(transport="stdio")

    @patch("garmy.mcp.server.MetricDiscovery")
    @patch("garmy.mcp.server.FastMCP")
    def test_run_debug_mode(self, mock_fastmcp, mock_discovery):
        """Test running server in debug mode."""
        mock_discovery.discover_metrics.return_value = {"sleep": Mock()}
        mock_discovery.validate_metrics.return_value = None

        config = MCPConfig(debug_mode=True)
        server = GarmyMCPServer(config)

        # Capture stderr output
        with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
            server.run(transport="stdio")

        stderr_output = mock_stderr.getvalue()
        assert "Starting Garmy MCP Server..." in stderr_output
        assert "Transport: stdio" in stderr_output
        assert "Discovered metrics: 1" in stderr_output
        assert "Server ready!" in stderr_output

    @patch("garmy.mcp.server.MetricDiscovery")
    @patch("garmy.mcp.server.FastMCP")
    def test_run_broken_resource_error(self, mock_fastmcp, mock_discovery):
        """Test running server with BrokenResourceError (normal disconnection)."""
        mock_discovery.discover_metrics.return_value = {}
        mock_discovery.validate_metrics.return_value = None

        config = MCPConfig(debug_mode=True)
        server = GarmyMCPServer(config)
        server.mcp.run.side_effect = anyio.BrokenResourceError("Client disconnected")

        with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
            server.run(transport="stdio")  # Should not raise

        stderr_output = mock_stderr.getvalue()
        assert "MCP client disconnected (normal)" in stderr_output

    @patch("garmy.mcp.server.MetricDiscovery")
    @patch("garmy.mcp.server.FastMCP")
    def test_run_exception_group_with_broken_resource(
        self, mock_fastmcp, mock_discovery
    ):
        """Test running server with BaseExceptionGroup containing BrokenResourceError."""
        mock_discovery.discover_metrics.return_value = {}
        mock_discovery.validate_metrics.return_value = None

        config = MCPConfig(debug_mode=True)
        server = GarmyMCPServer(config)

        # Create exception group with BrokenResourceError
        broken_error = anyio.BrokenResourceError("Connection broken")
        exception_group = BaseExceptionGroup("Multiple errors", [broken_error])
        server.mcp.run.side_effect = exception_group

        with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
            server.run(transport="stdio")  # Should not raise

        stderr_output = mock_stderr.getvalue()
        assert "MCP client disconnected (normal)" in stderr_output

    @patch("garmy.mcp.server.MetricDiscovery")
    @patch("garmy.mcp.server.FastMCP")
    def test_run_exception_group_without_broken_resource(
        self, mock_fastmcp, mock_discovery
    ):
        """Test running server with BaseExceptionGroup without BrokenResourceError."""
        mock_discovery.discover_metrics.return_value = {}
        mock_discovery.validate_metrics.return_value = None

        server = GarmyMCPServer(self.mock_config)

        # Create exception group with other errors
        other_error = ValueError("Some other error")
        exception_group = BaseExceptionGroup("Multiple errors", [other_error])
        server.mcp.run.side_effect = exception_group

        with patch.object(server, "_log_error") as mock_log_error:
            with pytest.raises(BaseExceptionGroup):
                server.run(transport="stdio")

        mock_log_error.assert_called_once()

    @patch("garmy.mcp.server.MetricDiscovery")
    @patch("garmy.mcp.server.FastMCP")
    def test_run_general_exception(self, mock_fastmcp, mock_discovery):
        """Test running server with general exception."""
        mock_discovery.discover_metrics.return_value = {}
        mock_discovery.validate_metrics.return_value = None

        server = GarmyMCPServer(self.mock_config)
        server.mcp.run.side_effect = RuntimeError("Server error")

        with patch.object(server, "_log_error") as mock_log_error:
            with pytest.raises(RuntimeError):
                server.run(transport="stdio")

        mock_log_error.assert_called_once_with(
            "Error running MCP server: Server error", mock_log_error.call_args[0][1]
        )

    @patch("garmy.mcp.server.MetricDiscovery")
    @patch("garmy.mcp.server.FastMCP")
    def test_log_error_without_exception(self, mock_fastmcp, mock_discovery):
        """Test error logging without exception."""
        mock_discovery.discover_metrics.return_value = {}
        mock_discovery.validate_metrics.return_value = None

        server = GarmyMCPServer(self.mock_config)

        with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
            server._log_error("Test error message")

        stderr_output = mock_stderr.getvalue()
        assert "Test error message" in stderr_output

    @patch("garmy.mcp.server.MetricDiscovery")
    @patch("garmy.mcp.server.FastMCP")
    def test_log_error_with_exception_debug_mode(self, mock_fastmcp, mock_discovery):
        """Test error logging with exception in debug mode."""
        mock_discovery.discover_metrics.return_value = {}
        mock_discovery.validate_metrics.return_value = None

        config = MCPConfig(debug_mode=True)
        server = GarmyMCPServer(config)

        exception = ValueError("Test exception")

        with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
            with patch(
                "garmy.mcp.server.traceback.print_exception"
            ) as mock_print_exception:
                server._log_error("Test error message", exception)

        stderr_output = mock_stderr.getvalue()
        assert "Test error message" in stderr_output
        mock_print_exception.assert_called_once()

    @patch("garmy.mcp.server.MetricDiscovery")
    @patch("garmy.mcp.server.FastMCP")
    def test_log_error_with_exception_no_debug(self, mock_fastmcp, mock_discovery):
        """Test error logging with exception not in debug mode."""
        mock_discovery.discover_metrics.return_value = {}
        mock_discovery.validate_metrics.return_value = None

        server = GarmyMCPServer(self.mock_config)  # debug_mode=False

        exception = ValueError("Test exception")

        with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
            with patch(
                "garmy.mcp.server.traceback.print_exception"
            ) as mock_print_exception:
                server._log_error("Test error message", exception)

        stderr_output = mock_stderr.getvalue()
        assert "Test error message" in stderr_output
        mock_print_exception.assert_not_called()  # Should not print traceback


if __name__ == "__main__":
    pytest.main([__file__])
