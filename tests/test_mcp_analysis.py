"""
Comprehensive tests for MCP analysis tools module.

Tests all analysis functionality to achieve 100% coverage.
"""

from datetime import date
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastmcp import Context

from garmy.mcp.tools.analysis import AnalysisTools


class TestAnalysisTools:
    """Test suite for AnalysisTools class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_server = Mock()
        self.mock_server.config.default_analysis_period = 30
        self.analysis_tools = AnalysisTools(self.mock_server)
        self.mock_ctx = AsyncMock(spec=Context)

    def test_init(self):
        """Test AnalysisTools initialization."""
        server = Mock()
        analysis_tools = AnalysisTools(server)
        assert analysis_tools.server is server

    @pytest.mark.asyncio
    async def test_analyze_metric_trends_not_authenticated(self):
        """Test metric trend analysis when not authenticated."""
        self.mock_server.is_authenticated.return_value = False

        # Create mock MCP and register tools
        mock_mcp = Mock()
        tool_functions = {}

        def mock_tool(func=None):
            def decorator(f):
                tool_functions[f.__name__] = f
                return f

            return decorator(func) if func else decorator

        mock_mcp.tool = mock_tool
        self.analysis_tools.register_tools(mock_mcp)

        result = await tool_functions["analyze_metric_trends"](
            "sleep", 7, None, self.mock_ctx
        )

        assert "Authentication required" in result

    @pytest.mark.asyncio
    async def test_analyze_metric_trends_success(self):
        """Test successful metric trend analysis."""
        self.mock_server.is_authenticated.return_value = True

        # Mock metric history data
        mock_history = [
            Mock(value=8.5),  # Sleep hours for different days
            Mock(value=7.2),
            Mock(value=8.8),
            Mock(value=6.5),
            Mock(value=9.1),
        ]
        self.mock_server.get_metric_history.return_value = mock_history

        # Create mock MCP and register tools
        mock_mcp = Mock()
        tool_functions = {}

        def mock_tool(func=None):
            def decorator(f):
                tool_functions[f.__name__] = f
                return f

            return decorator(func) if func else decorator

        mock_mcp.tool = mock_tool
        self.analysis_tools.register_tools(mock_mcp)

        result = await tool_functions["analyze_metric_trends"](
            "sleep", 5, "2023-12-01", self.mock_ctx
        )

        assert "**Sleep Trend Analysis**" in result
        assert "Period: 5 days until 2023-12-01" in result
        assert "Data Points: 5" in result
        assert "Average:" in result
        assert "Min:" in result
        assert "Max:" in result
        assert "Trend:" in result

        self.mock_server.get_metric_history.assert_called_once_with(
            "sleep", 5, "2023-12-01"
        )
        self.mock_ctx.info.assert_any_call(
            "Analyzing sleep trends for 5 days until 2023-12-01"
        )

    @pytest.mark.asyncio
    async def test_analyze_metric_trends_no_data(self):
        """Test metric trend analysis with no data."""
        self.mock_server.is_authenticated.return_value = True
        self.mock_server.get_metric_history.return_value = []

        # Create mock MCP and register tools
        mock_mcp = Mock()
        tool_functions = {}

        def mock_tool(func=None):
            def decorator(f):
                tool_functions[f.__name__] = f
                return f

            return decorator(func) if func else decorator

        mock_mcp.tool = mock_tool
        self.analysis_tools.register_tools(mock_mcp)

        result = await tool_functions["analyze_metric_trends"](
            "sleep", 7, None, self.mock_ctx
        )

        assert "No sleep data available for trend analysis" in result

    @pytest.mark.asyncio
    async def test_analyze_metric_trends_default_period(self):
        """Test metric trend analysis with default period."""
        self.mock_server.is_authenticated.return_value = True
        self.mock_server.get_metric_history.return_value = [Mock(value=123)]

        # Create mock MCP and register tools
        mock_mcp = Mock()
        tool_functions = {}

        def mock_tool(func=None):
            def decorator(f):
                tool_functions[f.__name__] = f
                return f

            return decorator(func) if func else decorator

        mock_mcp.tool = mock_tool
        self.analysis_tools.register_tools(mock_mcp)

        await tool_functions["analyze_metric_trends"](
            "steps", None, None, self.mock_ctx
        )

        # Should use default analysis period from config
        self.mock_server.get_metric_history.assert_called_once_with("steps", 30, None)

    @pytest.mark.asyncio
    async def test_analyze_metric_trends_exception(self):
        """Test metric trend analysis with exception."""
        self.mock_server.is_authenticated.return_value = True
        self.mock_server.get_metric_history.side_effect = Exception("API Error")

        # Create mock MCP and register tools
        mock_mcp = Mock()
        tool_functions = {}

        def mock_tool(func=None):
            def decorator(f):
                tool_functions[f.__name__] = f
                return f

            return decorator(func) if func else decorator

        mock_mcp.tool = mock_tool
        self.analysis_tools.register_tools(mock_mcp)

        result = await tool_functions["analyze_metric_trends"](
            "sleep", 7, None, self.mock_ctx
        )

        assert "Error analyzing trends: API Error" in result
        self.mock_ctx.error.assert_called_once_with("Error analyzing trends: API Error")

    @pytest.mark.asyncio
    async def test_compare_time_periods_not_authenticated(self):
        """Test time period comparison when not authenticated."""
        self.mock_server.is_authenticated.return_value = False

        # Create mock MCP and register tools
        mock_mcp = Mock()
        tool_functions = {}

        def mock_tool(func=None):
            def decorator(f):
                tool_functions[f.__name__] = f
                return f

            return decorator(func) if func else decorator

        mock_mcp.tool = mock_tool
        self.analysis_tools.register_tools(mock_mcp)

        result = await tool_functions["compare_time_periods"](
            "steps", 7, 7, self.mock_ctx
        )

        assert "Authentication required" in result

    @pytest.mark.asyncio
    async def test_compare_time_periods_success(self):
        """Test successful time period comparison."""
        self.mock_server.is_authenticated.return_value = True

        # Mock data for two periods
        current_data = [Mock(value=8000), Mock(value=9000), Mock(value=7500)]
        previous_data = [Mock(value=7000), Mock(value=8500), Mock(value=6500)]

        self.mock_server.get_metric_history.side_effect = [current_data, previous_data]

        # Create mock MCP and register tools
        mock_mcp = Mock()
        tool_functions = {}

        def mock_tool(func=None):
            def decorator(f):
                tool_functions[f.__name__] = f
                return f

            return decorator(func) if func else decorator

        mock_mcp.tool = mock_tool
        self.analysis_tools.register_tools(mock_mcp)

        with patch("garmy.mcp.tools.analysis.date") as mock_date:
            mock_date.today.return_value = date(2023, 12, 15)
            mock_date.side_effect = lambda *args: date(*args)

            result = await tool_functions["compare_time_periods"](
                "steps", 3, 3, self.mock_ctx
            )

        assert "**Steps Period Comparison**" in result
        assert "Current Period:" in result
        assert "Previous Period:" in result
        assert "Current Average:" in result
        assert "Previous Average:" in result
        assert "Change:" in result
        assert "Current Data Points: 3" in result
        assert "Previous Data Points: 3" in result

    @pytest.mark.asyncio
    async def test_compare_time_periods_no_current_data(self):
        """Test time period comparison with no current data."""
        self.mock_server.is_authenticated.return_value = True
        self.mock_server.get_metric_history.side_effect = [[], [Mock(value=100)]]

        # Create mock MCP and register tools
        mock_mcp = Mock()
        tool_functions = {}

        def mock_tool(func=None):
            def decorator(f):
                tool_functions[f.__name__] = f
                return f

            return decorator(func) if func else decorator

        mock_mcp.tool = mock_tool
        self.analysis_tools.register_tools(mock_mcp)

        result = await tool_functions["compare_time_periods"](
            "steps", 7, 7, self.mock_ctx
        )

        assert "No current period data available" in result

    @pytest.mark.asyncio
    async def test_compare_time_periods_no_previous_data(self):
        """Test time period comparison with no previous data."""
        self.mock_server.is_authenticated.return_value = True
        self.mock_server.get_metric_history.side_effect = [[Mock(value=100)], []]

        # Create mock MCP and register tools
        mock_mcp = Mock()
        tool_functions = {}

        def mock_tool(func=None):
            def decorator(f):
                tool_functions[f.__name__] = f
                return f

            return decorator(func) if func else decorator

        mock_mcp.tool = mock_tool
        self.analysis_tools.register_tools(mock_mcp)

        result = await tool_functions["compare_time_periods"](
            "steps", 7, 7, self.mock_ctx
        )

        assert "No previous period data available for comparison" in result

    @pytest.mark.asyncio
    async def test_compare_time_periods_exception(self):
        """Test time period comparison with exception."""
        self.mock_server.is_authenticated.return_value = True
        self.mock_server.get_metric_history.side_effect = Exception("API Error")

        # Create mock MCP and register tools
        mock_mcp = Mock()
        tool_functions = {}

        def mock_tool(func=None):
            def decorator(f):
                tool_functions[f.__name__] = f
                return f

            return decorator(func) if func else decorator

        mock_mcp.tool = mock_tool
        self.analysis_tools.register_tools(mock_mcp)

        result = await tool_functions["compare_time_periods"](
            "steps", 7, 7, self.mock_ctx
        )

        assert "Error comparing periods: API Error" in result
        self.mock_ctx.error.assert_called_once_with(
            "Error comparing periods: API Error"
        )


if __name__ == "__main__":
    pytest.main([__file__])
