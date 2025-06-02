"""
Comprehensive tests for MCP metrics tools module.

Tests all functions, classes, and edge cases to achieve 100% coverage.
"""

from dataclasses import dataclass
from datetime import date
from typing import List, Optional
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastmcp import Context

from garmy.mcp.tools.metrics import DatedMetricData, MetricTools


# Test data classes for mocking
@dataclass
class MockMetricData:
    """Mock metric data class for testing."""

    value: float = 0.0
    quality: str = "good"
    timestamp: Optional[str] = None


@dataclass
class MockActivityData:
    """Mock activity data class for testing."""

    activity_name: str = "Running"
    activity_type_name: str = "running"
    duration_minutes: float = 30.0
    average_hr: Optional[float] = 150.0
    start_date: str = "2023-12-01"


class TestDatedMetricData:
    """Test suite for DatedMetricData class."""

    def test_init(self):
        """Test DatedMetricData initialization."""
        test_date = date(2023, 12, 1)
        test_data = {"value": 123}

        dated_data = DatedMetricData(date=test_date, data=test_data)

        assert dated_data.date == test_date
        assert dated_data.data == test_data

    def test_str_with_none_data(self):
        """Test string representation with None data."""
        test_date = date(2023, 12, 1)
        dated_data = DatedMetricData(date=test_date, data=None)

        result = str(dated_data)

        assert result == "**2023-12-01**: No data"

    def test_str_with_activities_data(self):
        """Test string representation with activities data."""
        test_date = date(2023, 12, 1)
        activities_data = {"activities": [MockActivityData()], "count": 1}
        dated_data = DatedMetricData(date=test_date, data=activities_data)

        with patch.object(
            dated_data, "_format_activities_data", return_value="formatted activities"
        ):
            result = str(dated_data)

        assert result == "formatted activities"

    def test_str_with_standard_data(self):
        """Test string representation with standard metric data."""
        test_date = date(2023, 12, 1)
        test_data = MockMetricData(value=123.45, quality="excellent")
        dated_data = DatedMetricData(date=test_date, data=test_data)

        result = str(dated_data)

        expected = f"**{test_date}**:\n{test_data!s}"
        assert result == expected

    def test_format_activities_data_no_activities(self):
        """Test activities formatting with no activities."""
        test_date = date(2023, 12, 1)
        activities_data = {"activities": [], "count": 0}
        dated_data = DatedMetricData(date=test_date, data=activities_data)

        result = dated_data._format_activities_data()

        assert result == "**2023-12-01**: No activities"

    def test_format_activities_data_single_activity(self):
        """Test activities formatting with single activity."""
        test_date = date(2023, 12, 1)
        activity = MockActivityData(
            activity_name="Morning Run",
            activity_type_name="running",
            duration_minutes=45.0,
            average_hr=160.0,
        )
        activities_data = {"activities": [activity], "count": 1}
        dated_data = DatedMetricData(date=test_date, data=activities_data)

        result = dated_data._format_activities_data()

        expected_parts = [
            "**2023-12-01**: 1 activity",
            "1. Morning Run (running) - 45 min - 160 bpm avg",
        ]
        for part in expected_parts:
            assert part in result

    def test_format_activities_data_multiple_activities(self):
        """Test activities formatting with multiple activities."""
        test_date = date(2023, 12, 1)
        activities = [
            MockActivityData(activity_name="Morning Run", duration_minutes=30.0),
            MockActivityData(
                activity_name="Evening Walk", duration_minutes=15.0, average_hr=None
            ),
        ]
        activities_data = {"activities": activities, "count": 2}
        dated_data = DatedMetricData(date=test_date, data=activities_data)

        result = dated_data._format_activities_data()

        assert "**2023-12-01**: 2 activities" in result
        assert "1. Morning Run" in result
        assert "2. Evening Walk" in result

    def test_format_activities_data_unnamed_activity(self):
        """Test activities formatting with unnamed activity."""
        test_date = date(2023, 12, 1)
        activity = MockActivityData(activity_name=None)
        activities_data = {"activities": [activity], "count": 1}
        dated_data = DatedMetricData(date=test_date, data=activities_data)

        result = dated_data._format_activities_data()

        assert "Unnamed Activity" in result

    def test_format_activities_data_missing_attributes(self):
        """Test activities formatting with missing attributes."""
        test_date = date(2023, 12, 1)
        # Create activity with minimal attributes
        activity = Mock()
        activity.activity_name = "Test"
        # Missing duration_minutes and average_hr attributes
        activities_data = {"activities": [activity], "count": 1}
        dated_data = DatedMetricData(date=test_date, data=activities_data)

        result = dated_data._format_activities_data()

        assert "Test (Unknown)" in result


class TestMetricTools:
    """Test suite for MetricTools class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_server = Mock()
        self.mock_server.config.max_history_days = 90
        self.metric_tools = MetricTools(self.mock_server)
        self.mock_ctx = AsyncMock(spec=Context)

    def test_init(self):
        """Test MetricTools initialization."""
        server = Mock()
        metric_tools = MetricTools(server)
        assert metric_tools.server is server

    def test_export_to_csv_empty_data(self):
        """Test CSV export with empty data."""
        result = self.metric_tools._export_to_csv([], "test_metric")
        assert result == "No data to export"

    def test_export_to_csv_with_dataclass_objects(self):
        """Test CSV export with dataclass objects."""
        data_list = [
            MockMetricData(value=123.45, quality="good"),
            MockMetricData(value=234.56, quality="excellent"),
        ]

        result = self.metric_tools._export_to_csv(data_list, "test_metric")

        assert "value,quality,timestamp" in result
        assert "123.45,good," in result
        assert "234.56,excellent," in result

    def test_export_to_csv_with_complex_objects(self):
        """Test CSV export with complex nested objects."""

        @dataclass
        class ComplexData:
            simple_value: str
            list_value: List[str]
            dict_value: dict
            none_value: Optional[str]

        data_list = [
            ComplexData(
                simple_value="test",
                list_value=["a", "b"],
                dict_value={"key": "value"},
                none_value=None,
            )
        ]

        result = self.metric_tools._export_to_csv(data_list, "complex_metric")

        assert '"[""a"", ""b""]"' in result or '["a", "b"]' in result
        assert '{"key": "value"}' in result or '"{\\"key\\": \\"value\\"}"' in result
        assert "test" in result

    def test_export_to_csv_fallback_simple_objects(self):
        """Test CSV export fallback for simple objects."""
        data_list = ["simple_string", 123, {"not": "dataclass"}]

        result = self.metric_tools._export_to_csv(data_list, "simple_metric")

        assert "Simple Metric" in result
        assert "simple_string" in result
        assert "123" in result

    def test_export_dated_to_csv_empty_data(self):
        """Test dated CSV export with empty data."""
        result = self.metric_tools._export_dated_to_csv([], "test_metric")
        assert result == "No data to export"

    def test_export_dated_to_csv_activities_special_case(self):
        """Test dated CSV export with activities (special case)."""
        dated_data = [DatedMetricData(date=date.today(), data={"activities": []})]

        with patch.object(
            self.metric_tools,
            "_export_activities_to_csv",
            return_value="activities csv",
        ):
            result = self.metric_tools._export_dated_to_csv(dated_data, "activities")

        assert result == "activities csv"

    def test_export_dated_to_csv_no_valid_data(self):
        """Test dated CSV export with no valid data."""
        dated_data = [
            DatedMetricData(date=date(2023, 12, 1), data=None),
            DatedMetricData(date=date(2023, 12, 2), data=None),
        ]

        result = self.metric_tools._export_dated_to_csv(dated_data, "test_metric")

        assert "date,Test Metric" in result
        assert "No data available" in result

    def test_export_dated_to_csv_with_valid_data(self):
        """Test dated CSV export with valid dataclass data."""
        dated_data = [
            DatedMetricData(date=date(2023, 12, 1), data=MockMetricData(value=100.0)),
            DatedMetricData(date=date(2023, 12, 2), data=None),
            DatedMetricData(date=date(2023, 12, 3), data=MockMetricData(value=200.0)),
        ]

        result = self.metric_tools._export_dated_to_csv(dated_data, "test_metric")

        assert "date,value,quality,timestamp" in result
        assert "2023-12-03,100.0,good," in result  # Most recent first (reversed)
        assert "2023-12-02,," in result  # Empty data row
        assert "2023-12-01,200.0,good," in result

    def test_export_dated_to_csv_fallback_simple_objects(self):
        """Test dated CSV export fallback for simple objects."""
        dated_data = [
            DatedMetricData(date=date(2023, 12, 1), data="simple_data"),
            DatedMetricData(date=date(2023, 12, 2), data=None),
        ]

        result = self.metric_tools._export_dated_to_csv(dated_data, "simple_metric")

        assert "date,Simple Metric" in result
        assert "2023-12-02,No data" in result  # Most recent first (reversed)
        assert "2023-12-01,simple_data" in result

    def test_export_activities_to_csv_no_activities(self):
        """Test activities CSV export with no activities."""
        dated_data = []

        result = self.metric_tools._export_activities_to_csv(dated_data)

        assert "date,activity_name,activity_type,duration_minutes" in result
        assert "No activities found" in result

    def test_export_activities_to_csv_with_activities(self):
        """Test activities CSV export with activities."""
        activities = [
            MockActivityData(activity_name="Run", duration_minutes=30.0),
            MockActivityData(activity_name="Walk", duration_minutes=15.0),
        ]
        dated_data = [
            DatedMetricData(
                date=date(2023, 12, 1), data={"activities": activities, "count": 2}
            )
        ]

        result = self.metric_tools._export_activities_to_csv(dated_data)

        assert (
            "date,activity_name,activity_type_name,duration_minutes,average_hr,start_date"
            in result
        )
        assert "2023-12-01,Run,running,30.0,150.0,2023-12-01" in result
        assert "2023-12-01,Walk,running,15.0,150.0,2023-12-01" in result

    def test_export_activities_to_csv_sorted_by_date(self):
        """Test activities CSV export sorting by date."""
        activity1 = MockActivityData(activity_name="Activity1")
        activity2 = MockActivityData(activity_name="Activity2")

        dated_data = [
            DatedMetricData(
                date=date(2023, 12, 2), data={"activities": [activity2], "count": 1}
            ),
            DatedMetricData(
                date=date(2023, 12, 1), data={"activities": [activity1], "count": 1}
            ),
        ]

        result = self.metric_tools._export_activities_to_csv(dated_data)

        lines = result.strip().split("\n")
        # Should be sorted chronologically (date ascending)
        assert "2023-12-01,Activity1" in lines[1]  # After header
        assert "2023-12-02,Activity2" in lines[2]

    def test_export_activities_to_csv_complex_data(self):
        """Test activities CSV export with complex data types."""

        @dataclass
        class ComplexActivity:
            activity_name: str
            list_data: List[str]
            dict_data: dict
            none_data: Optional[str] = None

        activity = ComplexActivity(
            activity_name="Complex",
            list_data=["a", "b"],
            dict_data={"key": "value"},
            none_data=None,
        )

        dated_data = [
            DatedMetricData(
                date=date(2023, 12, 1), data={"activities": [activity], "count": 1}
            )
        ]

        result = self.metric_tools._export_activities_to_csv(dated_data)

        assert "Complex" in result
        assert '["a", "b"]' in result or '"[""a"", ""b""]"' in result

    def test_get_metric_history_with_dates_standard_metric(self):
        """Test getting metric history with dates for standard metrics."""
        self.mock_server.get_metric_data.side_effect = [
            MockMetricData(value=100.0),
            MockMetricData(value=200.0),
            None,  # No data for one day
        ]

        result = self.metric_tools._get_metric_history_with_dates(
            "sleep", 3, date(2023, 12, 3)
        )

        assert len(result) == 3
        assert result[0].date == date(2023, 12, 3)  # Most recent first
        assert result[0].data.value == 100.0
        assert result[1].date == date(2023, 12, 2)
        assert result[1].data.value == 200.0
        assert result[2].date == date(2023, 12, 1)
        assert result[2].data is None

    def test_get_metric_history_with_dates_activities_special_case(self):
        """Test getting metric history with dates for activities (special case)."""
        with patch.object(
            self.metric_tools,
            "_get_activities_history_with_dates",
            return_value="activities_result",
        ):
            result = self.metric_tools._get_metric_history_with_dates(
                "activities", 7, date.today()
            )

        assert result == "activities_result"

    def test_get_metric_history_with_dates_default_end_date(self):
        """Test getting metric history with default end date."""
        self.mock_server.get_metric_data.return_value = MockMetricData(value=123.0)

        with patch("garmy.mcp.tools.metrics.date") as mock_date:
            mock_date.today.return_value = date(2023, 12, 10)
            mock_date.side_effect = lambda *args: date(
                *args
            )  # Allow date() constructor

            result = self.metric_tools._get_metric_history_with_dates("steps", 2)

        assert len(result) == 2
        assert result[0].date == date(2023, 12, 10)
        assert result[1].date == date(2023, 12, 9)

    def test_get_metric_history_with_dates_api_exception(self):
        """Test getting metric history with API exceptions."""
        self.mock_server.get_metric_data.side_effect = [
            MockMetricData(value=100.0),
            Exception("API Error"),
            MockMetricData(value=300.0),
        ]

        with patch("garmy.mcp.tools.metrics.logger") as mock_logger:
            result = self.metric_tools._get_metric_history_with_dates(
                "heart_rate", 3, date(2023, 12, 3)
            )

        assert len(result) == 3
        assert result[0].data.value == 100.0
        assert result[1].data is None  # Exception handled
        assert result[2].data.value == 300.0
        mock_logger.warning.assert_called_once()

    def test_get_activities_history_with_dates_success(self):
        """Test getting activities history with successful API call."""
        mock_activity1 = Mock()
        mock_activity1.start_date = "2023-12-01"
        mock_activity2 = Mock()
        mock_activity2.start_date = "2023-12-02"
        mock_activity3 = Mock()
        mock_activity3.start_date = "2023-11-30"  # Outside range

        mock_activities_accessor = Mock()
        mock_activities_accessor.list.return_value = [
            mock_activity1,
            mock_activity2,
            mock_activity3,
        ]

        self.mock_server.api_client.metrics.get.return_value = mock_activities_accessor

        result = self.metric_tools._get_activities_history_with_dates(
            3, date(2023, 12, 2)
        )

        assert len(result) == 3
        # Check that activities are grouped by date
        assert result[0].date == date(2023, 12, 2)  # Most recent first
        assert result[0].data["count"] == 1
        assert result[0].data["activities"] == [mock_activity2]

        assert result[1].date == date(2023, 12, 1)
        assert result[1].data["count"] == 1
        assert result[1].data["activities"] == [mock_activity1]

        assert result[2].date == date(2023, 11, 30)
        assert result[2].data is None  # No activities this day (outside range)

    def test_get_activities_history_with_dates_no_accessor(self):
        """Test getting activities history when accessor is not available."""
        self.mock_server.api_client.metrics.get.return_value = None

        result = self.metric_tools._get_activities_history_with_dates(
            3, date(2023, 12, 2)
        )

        assert result == []

    def test_get_activities_history_with_dates_invalid_date_format(self):
        """Test getting activities history with invalid activity date format."""
        mock_activity = Mock()
        mock_activity.start_date = "invalid-date"

        mock_activities_accessor = Mock()
        mock_activities_accessor.list.return_value = [mock_activity]

        self.mock_server.api_client.metrics.get.return_value = mock_activities_accessor

        with patch("garmy.mcp.tools.metrics.logger") as mock_logger:
            result = self.metric_tools._get_activities_history_with_dates(
                1, date(2023, 12, 1)
            )

        assert len(result) == 1
        assert result[0].data is None  # No valid activities
        mock_logger.warning.assert_called()

    def test_get_activities_history_with_dates_api_exception(self):
        """Test getting activities history with API exception."""
        self.mock_server.api_client.metrics.get.side_effect = Exception("API Error")

        with patch("garmy.mcp.tools.metrics.logger") as mock_logger:
            result = self.metric_tools._get_activities_history_with_dates(
                2, date(2023, 12, 1)
            )

        assert len(result) == 2
        assert all(item.data is None for item in result)
        mock_logger.error.assert_called_once()

    def test_get_activities_history_with_dates_default_end_date(self):
        """Test getting activities history with default end date."""
        mock_activities_accessor = Mock()
        mock_activities_accessor.list.return_value = []
        self.mock_server.api_client.metrics.get.return_value = mock_activities_accessor

        with patch("garmy.mcp.tools.metrics.date") as mock_date:
            mock_date.today.return_value = date(2023, 12, 10)
            mock_date.side_effect = lambda *args: date(*args)

            result = self.metric_tools._get_activities_history_with_dates(1)

        assert len(result) == 1
        assert result[0].date == date(2023, 12, 10)

    @pytest.mark.asyncio
    async def test_list_available_metrics_no_metrics(self):
        """Test listing available metrics when none are discovered."""
        self.mock_server.discovered_metrics = {}

        # Create mock MCP and register tools
        mock_mcp = Mock()
        tool_functions = {}

        def mock_tool(func=None):
            def decorator(f):
                tool_functions[f.__name__] = f
                return f

            return decorator(func) if func else decorator

        mock_mcp.tool = mock_tool
        self.metric_tools.register_tools(mock_mcp)

        result = await tool_functions["list_available_metrics"](self.mock_ctx)

        assert "No metrics discovered" in result

    @pytest.mark.asyncio
    async def test_list_available_metrics_with_metrics(self):
        """Test listing available metrics with discovered metrics."""
        mock_config1 = Mock()
        mock_config1.description = "Sleep data"
        mock_config1.deprecated = False

        mock_config2 = Mock()
        mock_config2.description = None
        mock_config2.deprecated = True

        self.mock_server.discovered_metrics = {
            "sleep": mock_config1,
            "old_metric": mock_config2,
        }

        # Create mock MCP and register tools
        mock_mcp = Mock()
        tool_functions = {}

        def mock_tool(func=None):
            def decorator(f):
                tool_functions[f.__name__] = f
                return f

            return decorator(func) if func else decorator

        mock_mcp.tool = mock_tool
        self.metric_tools.register_tools(mock_mcp)

        result = await tool_functions["list_available_metrics"](self.mock_ctx)

        assert "**Sleep** (DEPRECATED)" not in result  # Sleep is not deprecated
        assert "**Old Metric** (DEPRECATED)" in result
        assert "Sleep data" in result
        assert "No description available" in result
        self.mock_ctx.info.assert_called_once_with("Discovered 2 metrics")

    @pytest.mark.asyncio
    async def test_get_metric_data_not_authenticated(self):
        """Test getting metric data when not authenticated."""
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
        self.metric_tools.register_tools(mock_mcp)

        result = await tool_functions["get_metric_data"](
            "sleep", "2023-12-01", self.mock_ctx
        )

        assert "Authentication required" in result

    @pytest.mark.asyncio
    async def test_get_metric_data_success(self):
        """Test successful metric data retrieval."""
        self.mock_server.is_authenticated.return_value = True
        self.mock_server.get_metric_data.return_value = MockMetricData(value=123.45)
        self.mock_server.format_metric_data.return_value = "Formatted data"

        # Create mock MCP and register tools
        mock_mcp = Mock()
        tool_functions = {}

        def mock_tool(func=None):
            def decorator(f):
                tool_functions[f.__name__] = f
                return f

            return decorator(func) if func else decorator

        mock_mcp.tool = mock_tool
        self.metric_tools.register_tools(mock_mcp)

        result = await tool_functions["get_metric_data"](
            "sleep", "2023-12-01", self.mock_ctx
        )

        assert "**Sleep** for 2023-12-01" in result
        assert "Formatted data" in result
        self.mock_ctx.info.assert_any_call("Getting sleep data for 2023-12-01")
        self.mock_ctx.info.assert_any_call("Successfully retrieved sleep data")

    @pytest.mark.asyncio
    async def test_get_metric_data_no_data(self):
        """Test metric data retrieval with no data."""
        self.mock_server.is_authenticated.return_value = True
        self.mock_server.get_metric_data.return_value = None

        # Create mock MCP and register tools
        mock_mcp = Mock()
        tool_functions = {}

        def mock_tool(func=None):
            def decorator(f):
                tool_functions[f.__name__] = f
                return f

            return decorator(func) if func else decorator

        mock_mcp.tool = mock_tool
        self.metric_tools.register_tools(mock_mcp)

        result = await tool_functions["get_metric_data"](
            "sleep", "2023-12-01", self.mock_ctx
        )

        assert "No sleep data for 2023-12-01" in result

    @pytest.mark.asyncio
    async def test_get_metric_data_default_date(self):
        """Test metric data retrieval with default date."""
        self.mock_server.is_authenticated.return_value = True
        self.mock_server.get_metric_data.return_value = MockMetricData()
        self.mock_server.format_metric_data.return_value = "Data"

        # Create mock MCP and register tools
        mock_mcp = Mock()
        tool_functions = {}

        def mock_tool(func=None):
            def decorator(f):
                tool_functions[f.__name__] = f
                return f

            return decorator(func) if func else decorator

        mock_mcp.tool = mock_tool
        self.metric_tools.register_tools(mock_mcp)

        with patch("garmy.mcp.tools.metrics.date") as mock_date:
            mock_date.today.return_value = date(2023, 12, 15)
            mock_date.side_effect = lambda *args: date(*args)

            result = await tool_functions["get_metric_data"](
                "steps", None, self.mock_ctx
            )

        assert "2023-12-15" in result

    @pytest.mark.asyncio
    async def test_get_metric_data_unknown_metric(self):
        """Test metric data retrieval with unknown metric."""
        self.mock_server.is_authenticated.return_value = True
        self.mock_server.get_metric_data.side_effect = ValueError(
            "Unknown metric 'unknown'"
        )
        self.mock_server.api_client.metrics.keys.return_value = ["sleep", "steps"]

        # Create mock MCP and register tools
        mock_mcp = Mock()
        tool_functions = {}

        def mock_tool(func=None):
            def decorator(f):
                tool_functions[f.__name__] = f
                return f

            return decorator(func) if func else decorator

        mock_mcp.tool = mock_tool
        self.metric_tools.register_tools(mock_mcp)

        result = await tool_functions["get_metric_data"](
            "unknown", "2023-12-01", self.mock_ctx
        )

        assert "Unknown metric 'unknown'" in result
        assert "Available: sleep, steps" in result

    @pytest.mark.asyncio
    async def test_get_metric_data_other_value_error(self):
        """Test metric data retrieval with other ValueError."""
        self.mock_server.is_authenticated.return_value = True
        self.mock_server.get_metric_data.side_effect = ValueError("Invalid date format")

        # Create mock MCP and register tools
        mock_mcp = Mock()
        tool_functions = {}

        def mock_tool(func=None):
            def decorator(f):
                tool_functions[f.__name__] = f
                return f

            return decorator(func) if func else decorator

        mock_mcp.tool = mock_tool
        self.metric_tools.register_tools(mock_mcp)

        result = await tool_functions["get_metric_data"](
            "sleep", "invalid-date", self.mock_ctx
        )

        assert "Error: Invalid date format" in result

    @pytest.mark.asyncio
    async def test_get_metric_data_general_exception(self):
        """Test metric data retrieval with general exception."""
        self.mock_server.is_authenticated.return_value = True
        self.mock_server.get_metric_data.side_effect = Exception("API Error")

        # Create mock MCP and register tools
        mock_mcp = Mock()
        tool_functions = {}

        def mock_tool(func=None):
            def decorator(f):
                tool_functions[f.__name__] = f
                return f

            return decorator(func) if func else decorator

        mock_mcp.tool = mock_tool
        self.metric_tools.register_tools(mock_mcp)

        result = await tool_functions["get_metric_data"](
            "sleep", "2023-12-01", self.mock_ctx
        )

        assert "Error: API Error" in result
        self.mock_ctx.error.assert_called_once_with("Error getting data: API Error")

    @pytest.mark.asyncio
    async def test_get_metric_history_success(self):
        """Test successful metric history retrieval."""
        self.mock_server.is_authenticated.return_value = True

        mock_dated_data = [
            DatedMetricData(date=date(2023, 12, 3), data=MockMetricData(value=100.0)),
            DatedMetricData(date=date(2023, 12, 2), data=MockMetricData(value=200.0)),
            DatedMetricData(date=date(2023, 12, 1), data=None),
        ]

        with patch.object(
            self.metric_tools,
            "_get_metric_history_with_dates",
            return_value=mock_dated_data,
        ):
            # Create mock MCP and register tools
            mock_mcp = Mock()
            tool_functions = {}

            def mock_tool(func=None):
                def decorator(f):
                    tool_functions[f.__name__] = f
                    return f

                return decorator(func) if func else decorator

            mock_mcp.tool = mock_tool
            self.metric_tools.register_tools(mock_mcp)

            result = await tool_functions["get_metric_history"](
                "sleep", 3, "2023-12-03", self.mock_ctx
            )

        assert "**Sleep History** (3 days until 2023-12-03)" in result
        assert "Found records: 2 out of 3 days" in result
        assert "**2023-12-03**" in result
        assert "**2023-12-02**" in result
        assert "**2023-12-01**: No data" in result

    @pytest.mark.asyncio
    async def test_get_metric_history_no_data(self):
        """Test metric history retrieval with no data."""
        self.mock_server.is_authenticated.return_value = True

        mock_dated_data = [DatedMetricData(date=date(2023, 12, 1), data=None)]

        with patch.object(
            self.metric_tools,
            "_get_metric_history_with_dates",
            return_value=mock_dated_data,
        ):
            # Create mock MCP and register tools
            mock_mcp = Mock()
            tool_functions = {}

            def mock_tool(func=None):
                def decorator(f):
                    tool_functions[f.__name__] = f
                    return f

                return decorator(func) if func else decorator

            mock_mcp.tool = mock_tool
            self.metric_tools.register_tools(mock_mcp)

            result = await tool_functions["get_metric_history"](
                "sleep", 1, None, self.mock_ctx
            )

        assert "No historical sleep data" in result

    @pytest.mark.asyncio
    async def test_get_metric_history_large_dataset(self):
        """Test metric history retrieval with large dataset (>10 records)."""
        self.mock_server.is_authenticated.return_value = True

        # Create 15 records
        mock_dated_data = [
            DatedMetricData(date=date(2023, 12, i), data=MockMetricData(value=i * 10.0))
            for i in range(1, 16)
        ]

        with patch.object(
            self.metric_tools,
            "_get_metric_history_with_dates",
            return_value=mock_dated_data,
        ):
            # Create mock MCP and register tools
            mock_mcp = Mock()
            tool_functions = {}

            def mock_tool(func=None):
                def decorator(f):
                    tool_functions[f.__name__] = f
                    return f

                return decorator(func) if func else decorator

            mock_mcp.tool = mock_tool
            self.metric_tools.register_tools(mock_mcp)

            result = await tool_functions["get_metric_history"](
                "sleep", 15, None, self.mock_ctx
            )

        assert "Found records: 15 out of 15 days" in result
        assert "... and 5 more days" in result  # Should truncate to first 10

    @pytest.mark.asyncio
    async def test_get_metric_range_success(self):
        """Test successful metric range retrieval."""
        self.mock_server.is_authenticated.return_value = True

        mock_dated_data = [
            DatedMetricData(date=date(2023, 12, 1), data=MockMetricData(value=100.0)),
            DatedMetricData(date=date(2023, 12, 2), data=MockMetricData(value=200.0)),
        ]

        with patch.object(
            self.metric_tools,
            "_get_metric_history_with_dates",
            return_value=mock_dated_data,
        ):
            # Create mock MCP and register tools
            mock_mcp = Mock()
            tool_functions = {}

            def mock_tool(func=None):
                def decorator(f):
                    tool_functions[f.__name__] = f
                    return f

                return decorator(func) if func else decorator

            mock_mcp.tool = mock_tool
            self.metric_tools.register_tools(mock_mcp)

            result = await tool_functions["get_metric_range"](
                "sleep", "2023-12-01", "2023-12-02", self.mock_ctx
            )

        assert "**Sleep** from 2023-12-01 to 2023-12-02" in result
        assert "Found records: 2 out of 2 days" in result

    @pytest.mark.asyncio
    async def test_get_metric_range_invalid_date_order(self):
        """Test metric range retrieval with invalid date order."""
        self.mock_server.is_authenticated.return_value = True

        # Create mock MCP and register tools
        mock_mcp = Mock()
        tool_functions = {}

        def mock_tool(func=None):
            def decorator(f):
                tool_functions[f.__name__] = f
                return f

            return decorator(func) if func else decorator

        mock_mcp.tool = mock_tool
        self.metric_tools.register_tools(mock_mcp)

        result = await tool_functions["get_metric_range"](
            "sleep", "2023-12-02", "2023-12-01", self.mock_ctx
        )

        assert "Error: Start date cannot be after end date" in result

    @pytest.mark.asyncio
    async def test_get_metric_range_exceeds_max_days(self):
        """Test metric range retrieval exceeding maximum days."""
        self.mock_server.is_authenticated.return_value = True
        self.mock_server.config.max_history_days = 30

        # Create mock MCP and register tools
        mock_mcp = Mock()
        tool_functions = {}

        def mock_tool(func=None):
            def decorator(f):
                tool_functions[f.__name__] = f
                return f

            return decorator(func) if func else decorator

        mock_mcp.tool = mock_tool
        self.metric_tools.register_tools(mock_mcp)

        result = await tool_functions["get_metric_range"](
            "sleep", "2023-01-01", "2023-12-31", self.mock_ctx
        )

        assert "exceeds maximum allowed (30 days)" in result

    @pytest.mark.asyncio
    async def test_get_metric_range_large_dataset(self):
        """Test metric range retrieval with large dataset (>15 records)."""
        self.mock_server.is_authenticated.return_value = True

        # Create 20 records
        mock_dated_data = [
            DatedMetricData(date=date(2023, 12, i), data=MockMetricData(value=i * 10.0))
            for i in range(1, 21)
        ]

        with patch.object(
            self.metric_tools,
            "_get_metric_history_with_dates",
            return_value=mock_dated_data,
        ):
            # Create mock MCP and register tools
            mock_mcp = Mock()
            tool_functions = {}

            def mock_tool(func=None):
                def decorator(f):
                    tool_functions[f.__name__] = f
                    return f

                return decorator(func) if func else decorator

            mock_mcp.tool = mock_tool
            self.metric_tools.register_tools(mock_mcp)

            result = await tool_functions["get_metric_range"](
                "sleep", "2023-12-01", "2023-12-20", self.mock_ctx
            )

        assert "**First 5 days:**" in result
        assert "**Last 5 days:**" in result
        assert "10 more days" in result

    @pytest.mark.asyncio
    async def test_get_metric_range_invalid_date_format(self):
        """Test metric range retrieval with invalid date format."""
        self.mock_server.is_authenticated.return_value = True

        # Create mock MCP and register tools
        mock_mcp = Mock()
        tool_functions = {}

        def mock_tool(func=None):
            def decorator(f):
                tool_functions[f.__name__] = f
                return f

            return decorator(func) if func else decorator

        mock_mcp.tool = mock_tool
        self.metric_tools.register_tools(mock_mcp)

        result = await tool_functions["get_metric_range"](
            "sleep", "invalid-date", None, self.mock_ctx
        )

        assert "Error: Invalid date format. Use YYYY-MM-DD format." in result

    @pytest.mark.asyncio
    async def test_export_metric_csv_success(self):
        """Test successful metric CSV export."""
        self.mock_server.is_authenticated.return_value = True

        mock_dated_data = [
            DatedMetricData(date=date(2023, 12, 1), data=MockMetricData(value=100.0)),
            DatedMetricData(date=date(2023, 12, 2), data=None),
        ]

        with patch.object(
            self.metric_tools,
            "_get_metric_history_with_dates",
            return_value=mock_dated_data,
        ):
            with patch.object(
                self.metric_tools, "_export_dated_to_csv", return_value="CSV content"
            ):
                # Create mock MCP and register tools
                mock_mcp = Mock()
                tool_functions = {}

                def mock_tool(func=None):
                    def decorator(f):
                        tool_functions[f.__name__] = f
                        return f

                    return decorator(func) if func else decorator

                mock_mcp.tool = mock_tool
                self.metric_tools.register_tools(mock_mcp)

                result = await tool_functions["export_metric_csv"](
                    "sleep", 2, "2023-12-02", self.mock_ctx
                )

        assert "**Sleep CSV Export**" in result
        assert "1 valid records out of 2 days" in result
        assert "```csv" in result
        assert "CSV content" in result

    @pytest.mark.asyncio
    async def test_export_metric_csv_no_data(self):
        """Test metric CSV export with no data."""
        self.mock_server.is_authenticated.return_value = True

        mock_dated_data = [DatedMetricData(date=date(2023, 12, 1), data=None)]

        with patch.object(
            self.metric_tools,
            "_get_metric_history_with_dates",
            return_value=mock_dated_data,
        ):
            # Create mock MCP and register tools
            mock_mcp = Mock()
            tool_functions = {}

            def mock_tool(func=None):
                def decorator(f):
                    tool_functions[f.__name__] = f
                    return f

                return decorator(func) if func else decorator

            mock_mcp.tool = mock_tool
            self.metric_tools.register_tools(mock_mcp)

            result = await tool_functions["export_metric_csv"](
                "sleep", 1, None, self.mock_ctx
            )

        assert "No sleep data to export" in result

    @pytest.mark.asyncio
    async def test_export_metric_csv_exception(self):
        """Test metric CSV export with exception."""
        self.mock_server.is_authenticated.return_value = True

        with patch.object(
            self.metric_tools,
            "_get_metric_history_with_dates",
            side_effect=Exception("Export error"),
        ):
            # Create mock MCP and register tools
            mock_mcp = Mock()
            tool_functions = {}

            def mock_tool(func=None):
                def decorator(f):
                    tool_functions[f.__name__] = f
                    return f

                return decorator(func) if func else decorator

            mock_mcp.tool = mock_tool
            self.metric_tools.register_tools(mock_mcp)

            result = await tool_functions["export_metric_csv"](
                "sleep", 1, None, self.mock_ctx
            )

        assert "Error: Export error" in result
        self.mock_ctx.error.assert_called_once_with("Error exporting CSV: Export error")

    @pytest.mark.asyncio
    async def test_get_metric_schema_success(self):
        """Test successful metric schema retrieval."""
        mock_config = Mock()
        mock_config.metric_class = MockMetricData
        mock_config.description = "Test metric description"
        mock_config.version = "2.0"
        mock_config.requires_user_id = True
        mock_config.deprecated = False

        self.mock_server.discovered_metrics = {"test_metric": mock_config}

        # Create mock MCP and register tools
        mock_mcp = Mock()
        tool_functions = {}

        def mock_tool(func=None):
            def decorator(f):
                tool_functions[f.__name__] = f
                return f

            return decorator(func) if func else decorator

        mock_mcp.tool = mock_tool
        self.metric_tools.register_tools(mock_mcp)

        result = await tool_functions["get_metric_schema"]("test_metric", self.mock_ctx)

        assert "**Test Metric Schema**" in result
        assert "**Class**: MockMetricData" in result
        assert "**Description**: Test metric description" in result
        assert "**Version**: 2.0" in result
        assert "**Requires User ID**: True" in result
        assert "**Deprecated**: False" in result
        assert "**Available Fields**:" in result
        assert "`value`:" in result
        assert "`quality`:" in result

    @pytest.mark.asyncio
    async def test_get_metric_schema_unknown_metric(self):
        """Test metric schema retrieval for unknown metric."""
        self.mock_server.discovered_metrics = {"known_metric": Mock()}

        # Create mock MCP and register tools
        mock_mcp = Mock()
        tool_functions = {}

        def mock_tool(func=None):
            def decorator(f):
                tool_functions[f.__name__] = f
                return f

            return decorator(func) if func else decorator

        mock_mcp.tool = mock_tool
        self.metric_tools.register_tools(mock_mcp)

        result = await tool_functions["get_metric_schema"](
            "unknown_metric", self.mock_ctx
        )

        assert "Unknown metric 'unknown_metric'" in result
        assert "Available: known_metric" in result

    @pytest.mark.asyncio
    async def test_get_metric_schema_with_properties(self):
        """Test metric schema retrieval with computed properties."""

        @dataclass
        class MetricWithProperties:
            value: float

            @property
            def computed_value(self) -> float:
                return self.value * 2

        mock_config = Mock()
        mock_config.metric_class = MetricWithProperties
        mock_config.description = "Metric with properties"
        mock_config.version = "1.0"
        mock_config.requires_user_id = False
        mock_config.deprecated = False

        self.mock_server.discovered_metrics = {"prop_metric": mock_config}

        # Create mock MCP and register tools
        mock_mcp = Mock()
        tool_functions = {}

        def mock_tool(func=None):
            def decorator(f):
                tool_functions[f.__name__] = f
                return f

            return decorator(func) if func else decorator

        mock_mcp.tool = mock_tool
        self.metric_tools.register_tools(mock_mcp)

        result = await tool_functions["get_metric_schema"]("prop_metric", self.mock_ctx)

        assert "**Computed Properties**:" in result
        assert "`computed_value`" in result

    @pytest.mark.asyncio
    async def test_get_metric_schema_introspection_error(self):
        """Test metric schema retrieval with introspection error."""
        mock_config = Mock()
        # Create a class that will cause introspection to fail
        mock_config.metric_class = Mock()
        mock_config.metric_class.__name__ = "BadClass"
        mock_config.metric_class.__dataclass_fields__ = (
            None  # This will cause AttributeError
        )
        mock_config.description = "Bad class"
        mock_config.version = "1.0"
        mock_config.requires_user_id = False
        mock_config.deprecated = False

        self.mock_server.discovered_metrics = {"bad_metric": mock_config}

        # Create mock MCP and register tools
        mock_mcp = Mock()
        tool_functions = {}

        def mock_tool(func=None):
            def decorator(f):
                tool_functions[f.__name__] = f
                return f

            return decorator(func) if func else decorator

        mock_mcp.tool = mock_tool
        self.metric_tools.register_tools(mock_mcp)

        result = await tool_functions["get_metric_schema"]("bad_metric", self.mock_ctx)

        assert "Schema introspection error:" in result

    @pytest.mark.asyncio
    async def test_get_metric_schema_general_exception(self):
        """Test metric schema retrieval with general exception."""
        self.mock_server.discovered_metrics = {"test_metric": Mock()}

        # Create mock MCP and register tools
        mock_mcp = Mock()
        tool_functions = {}

        def mock_tool(func=None):
            def decorator(f):
                tool_functions[f.__name__] = f
                return f

            return decorator(func) if func else decorator

        mock_mcp.tool = mock_tool
        self.metric_tools.register_tools(mock_mcp)

        # Make discovered_metrics access fail
        with patch.object(
            self.mock_server,
            "discovered_metrics",
            side_effect=Exception("Schema error"),
        ):
            result = await tool_functions["get_metric_schema"](
                "test_metric", self.mock_ctx
            )

        assert "Error: Schema error" in result
        self.mock_ctx.error.assert_called_once_with(
            "Error getting schema: Schema error"
        )


if __name__ == "__main__":
    pytest.main([__file__])
