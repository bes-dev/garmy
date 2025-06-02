"""
Comprehensive tests for MCP resource providers module.

Tests all resource provider functionality to achieve 100% coverage.
"""

from unittest.mock import Mock

import pytest

from garmy.mcp.resources.providers import ResourceProviders


class TestResourceProviders:
    """Test suite for ResourceProviders class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_server = Mock()
        self.resource_providers = ResourceProviders(self.mock_server)

    def test_init(self):
        """Test ResourceProviders initialization."""
        server = Mock()
        providers = ResourceProviders(server)
        assert providers.server is server

    def test_register_resources(self):
        """Test resource registration with MCP server."""
        mock_mcp = Mock()
        resource_functions = {}

        def mock_resource(func=None):
            def decorator(f):
                resource_functions[f.__name__] = f
                return f

            return decorator(func) if func else decorator

        mock_mcp.resource = mock_resource

        self.resource_providers.register_resources(mock_mcp)

        # Verify that resources were registered
        expected_resources = [
            "garmin_health_data_schema",
            "garmin_metric_definitions",
            "garmin_api_endpoints",
        ]

        for resource_name in expected_resources:
            assert resource_name in resource_functions

    @pytest.mark.asyncio
    async def test_garmin_health_data_schema(self):
        """Test Garmin health data schema resource."""
        mock_mcp = Mock()
        resource_functions = {}

        def mock_resource(func=None):
            def decorator(f):
                resource_functions[f.__name__] = f
                return f

            return decorator(func) if func else decorator

        mock_mcp.resource = mock_resource

        self.resource_providers.register_resources(mock_mcp)

        result = await resource_functions["garmin_health_data_schema"]()

        assert isinstance(result, str)
        assert "Garmin Connect Health Data Schema" in result
        assert "sleep" in result.lower()
        assert "steps" in result.lower()
        assert "heart_rate" in result.lower()

    @pytest.mark.asyncio
    async def test_garmin_metric_definitions(self):
        """Test Garmin metric definitions resource."""
        # Mock discovered metrics
        mock_config1 = Mock()
        mock_config1.description = "Sleep data tracking"
        mock_config1.version = "1.0"
        mock_config1.deprecated = False

        mock_config2 = Mock()
        mock_config2.description = "Daily step count"
        mock_config2.version = "2.0"
        mock_config2.deprecated = True

        self.mock_server.discovered_metrics = {
            "sleep": mock_config1,
            "steps": mock_config2,
        }

        mock_mcp = Mock()
        resource_functions = {}

        def mock_resource(func=None):
            def decorator(f):
                resource_functions[f.__name__] = f
                return f

            return decorator(func) if func else decorator

        mock_mcp.resource = mock_resource

        self.resource_providers.register_resources(mock_mcp)

        result = await resource_functions["garmin_metric_definitions"]()

        assert isinstance(result, str)
        assert "Available Garmin Health Metrics" in result
        assert "Sleep" in result
        assert "Steps" in result
        assert "Sleep data tracking" in result
        assert "Daily step count" in result
        assert "Version: 1.0" in result
        assert "Version: 2.0" in result
        assert "DEPRECATED" in result  # Should show deprecated status

    @pytest.mark.asyncio
    async def test_garmin_metric_definitions_no_metrics(self):
        """Test Garmin metric definitions resource with no discovered metrics."""
        self.mock_server.discovered_metrics = {}

        mock_mcp = Mock()
        resource_functions = {}

        def mock_resource(func=None):
            def decorator(f):
                resource_functions[f.__name__] = f
                return f

            return decorator(func) if func else decorator

        mock_mcp.resource = mock_resource

        self.resource_providers.register_resources(mock_mcp)

        result = await resource_functions["garmin_metric_definitions"]()

        assert isinstance(result, str)
        assert "No metrics discovered" in result

    @pytest.mark.asyncio
    async def test_garmin_api_endpoints(self):
        """Test Garmin API endpoints resource."""
        mock_mcp = Mock()
        resource_functions = {}

        def mock_resource(func=None):
            def decorator(f):
                resource_functions[f.__name__] = f
                return f

            return decorator(func) if func else decorator

        mock_mcp.resource = mock_resource

        self.resource_providers.register_resources(mock_mcp)

        result = await resource_functions["garmin_api_endpoints"]()

        assert isinstance(result, str)
        assert "Garmin Connect API Endpoints" in result
        assert "Base URL:" in result
        assert "connect.garmin.com" in result
        assert "Authentication:" in result
        assert "OAuth" in result
        assert "Rate Limiting:" in result


if __name__ == "__main__":
    pytest.main([__file__])
