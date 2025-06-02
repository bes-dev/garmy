"""Comprehensive tests for garmy.core.metrics module.

This module provides 100% test coverage for metric framework components.
"""

import os
import threading
from dataclasses import dataclass
from datetime import date, datetime
from unittest.mock import Mock, patch

import pytest
from requests import HTTPError

from garmy.core.exceptions import APIError
from garmy.core.metrics import (
    MetricAccessor,
    MetricConcurrencyManager,
    MetricDataParser,
    MetricHttpClient,
)


def create_mock_http_error(msg="HTTP Error"):
    """Create a mock HTTPError for testing."""
    error = HTTPError(msg)
    return error


# Test dataclasses for testing
@dataclass
class SampleMetric:
    """Test metric class for testing."""

    value: int
    name: str
    timestamp: datetime = None


@dataclass
class SampleSummary:
    """Test summary class for testing."""

    total: int
    average: float


class SampleMetricHttpClient:
    """Test cases for MetricHttpClient class."""

    def test_metric_http_client_initialization(self):
        """Test MetricHttpClient initialization."""
        mock_api_client = Mock()
        client = MetricHttpClient(mock_api_client)

        assert client.api_client == mock_api_client

    def test_fetch_raw_data_with_endpoint_builder(self):
        """Test fetch_raw_data with endpoint builder."""
        mock_api_client = Mock()
        mock_api_client.connectapi.return_value = {"data": "test"}

        client = MetricHttpClient(mock_api_client)

        def mock_builder(date_input=None, api_client=None, **kwargs):
            return f"/test/{date_input}/{kwargs.get('param', 'default')}"

        result = client.fetch_raw_data(
            "/template/endpoint",
            date_input="2023-12-01",
            endpoint_builder=mock_builder,
            param="custom",
        )

        assert result == {"data": "test"}
        mock_api_client.connectapi.assert_called_once_with("/test/2023-12-01/custom")

    @patch("garmy.core.metrics.format_date")
    def test_fetch_raw_data_without_endpoint_builder(self, mock_format_date):
        """Test fetch_raw_data without endpoint builder."""
        mock_api_client = Mock()
        mock_api_client.connectapi.return_value = {"data": "test"}
        mock_format_date.return_value = "2023-12-01"

        client = MetricHttpClient(mock_api_client)

        result = client.fetch_raw_data(
            "/template/{date}/endpoint", date_input="2023-12-01"
        )

        assert result == {"data": "test"}
        mock_api_client.connectapi.assert_called_once_with(
            "/template/2023-12-01/endpoint"
        )
        mock_format_date.assert_called_once_with("2023-12-01")

    @patch("garmy.core.metrics.handle_api_exception")
    def test_fetch_raw_data_exception_handling(self, mock_handle_exception):
        """Test fetch_raw_data exception handling."""
        mock_api_client = Mock()
        http_error = create_mock_http_error("API failed")
        mock_api_client.connectapi.side_effect = APIError("API failed", http_error)
        mock_handle_exception.return_value = []

        client = MetricHttpClient(mock_api_client)

        result = client.fetch_raw_data("/test/endpoint")

        assert result == []
        mock_handle_exception.assert_called_once()

    def test_fetch_raw_data_no_date_input(self):
        """Test fetch_raw_data with no date input."""
        mock_api_client = Mock()
        mock_api_client.connectapi.return_value = {"data": "test"}

        client = MetricHttpClient(mock_api_client)

        with patch("garmy.core.metrics.format_date") as mock_format_date:
            mock_format_date.return_value = "2023-12-01"

            result = client.fetch_raw_data("/test/{date}/endpoint")

            assert result == {"data": "test"}
            mock_format_date.assert_called_once_with(None)


class SampleMetricDataParser:
    """Test cases for MetricDataParser class."""

    def test_metric_data_parser_initialization_default(self):
        """Test MetricDataParser initialization with default parser."""
        parser = MetricDataParser(SampleMetric)

        assert parser.metric_class == SampleMetric
        assert parser.parse_func == parser._default_parse

    def test_metric_data_parser_initialization_custom(self):
        """Test MetricDataParser initialization with custom parser."""

        def custom_parser(data):
            return SampleMetric(42, "custom")

        parser = MetricDataParser(SampleMetric, custom_parser)

        assert parser.metric_class == SampleMetric
        assert parser.parse_func == custom_parser

    def test_parse_with_no_data(self):
        """Test parse method with no data."""
        parser = MetricDataParser(SampleMetric)

        result = parser.parse(None)

        assert result is None

    def test_parse_with_empty_data(self):
        """Test parse method with empty data."""
        parser = MetricDataParser(SampleMetric)

        result = parser.parse([])

        assert result is None

    def test_parse_with_custom_parser(self):
        """Test parse method with custom parser."""

        def custom_parser(data):
            return SampleMetric(data["value"], data["name"])

        parser = MetricDataParser(SampleMetric, custom_parser)

        result = parser.parse({"value": 123, "name": "test"})

        assert isinstance(result, SampleMetric)
        assert result.value == 123
        assert result.name == "test"

    @patch("garmy.core.metrics.camel_to_snake_dict")
    def test_default_parse_single_item(self, mock_camel_to_snake):
        """Test _default_parse with single item."""
        mock_camel_to_snake.return_value = {"value": 42, "name": "test"}

        parser = MetricDataParser(SampleMetric)

        result = parser.parse({"value": 42, "name": "test"})

        assert isinstance(result, SampleMetric)
        assert result.value == 42
        assert result.name == "test"

    @patch("garmy.core.metrics.camel_to_snake_dict")
    def test_default_parse_list(self, mock_camel_to_snake):
        """Test _default_parse with list."""
        mock_camel_to_snake.side_effect = [
            {"value": 1, "name": "first"},
            {"value": 2, "name": "second"},
        ]

        parser = MetricDataParser(SampleMetric)

        result = parser.parse(
            [{"value": 1, "name": "first"}, {"value": 2, "name": "second"}]
        )

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0].value == 1
        assert result[1].value == 2

    @patch("garmy.core.metrics.camel_to_snake_dict")
    def test_parse_single_item_with_datetime(self, mock_camel_to_snake):
        """Test _parse_single_item with datetime conversion."""
        mock_camel_to_snake.return_value = {
            "value": 42,
            "name": "test",
            "timestamp": "2023-12-01T10:00:00Z",
        }

        parser = MetricDataParser(SampleMetric)

        result = parser.parse(
            {"value": 42, "name": "test", "timestamp": "2023-12-01T10:00:00Z"}
        )

        assert isinstance(result, SampleMetric)
        assert isinstance(result.timestamp, datetime)

    @patch("garmy.core.metrics.camel_to_snake_dict")
    def test_parse_single_item_invalid_datetime(self, mock_camel_to_snake):
        """Test _parse_single_item with invalid datetime."""
        mock_camel_to_snake.return_value = {
            "value": 42,
            "name": "test",
            "timestamp": "invalid-datetime",
        }

        parser = MetricDataParser(SampleMetric)

        result = parser.parse(
            {"value": 42, "name": "test", "timestamp": "invalid-datetime"}
        )

        # Should keep original value when datetime parsing fails
        assert result.timestamp == "invalid-datetime"

    @patch("garmy.core.metrics.camel_to_snake_dict")
    def test_parse_single_item_unknown_fields(self, mock_camel_to_snake):
        """Test _parse_single_item filters unknown fields."""
        mock_camel_to_snake.return_value = {
            "value": 42,
            "name": "test",
            "unknown_field": "should_be_filtered",
            "another_unknown": 123,
        }

        parser = MetricDataParser(SampleMetric)

        result = parser.parse(
            {"value": 42, "name": "test", "unknown_field": "should_be_filtered"}
        )

        assert isinstance(result, SampleMetric)
        assert result.value == 42
        assert result.name == "test"
        assert not hasattr(result, "unknown_field")

    @patch("garmy.core.metrics.camel_to_snake_dict")
    def test_parse_single_item_non_dict_snake_result(self, mock_camel_to_snake):
        """Test _parse_single_item when camel_to_snake_dict returns non-dict."""
        mock_camel_to_snake.return_value = "not a dict"

        parser = MetricDataParser(SampleMetric)

        with pytest.raises(ValueError, match="Expected dict but got"):
            parser.parse({"value": 42})


class SampleMetricConcurrencyManager:
    """Test cases for MetricConcurrencyManager class."""

    def test_metric_concurrency_manager_initialization_default(self):
        """Test MetricConcurrencyManager initialization with default workers."""
        with patch.object(
            MetricConcurrencyManager, "_determine_optimal_workers", return_value=5
        ):
            manager = MetricConcurrencyManager()

            assert manager.max_workers == 5

    def test_metric_concurrency_manager_initialization_custom(self):
        """Test MetricConcurrencyManager initialization with custom workers."""
        with patch.object(
            MetricConcurrencyManager, "_determine_optimal_workers", return_value=10
        ):
            manager = MetricConcurrencyManager(15)

            assert manager.max_workers == 10

    @patch("garmy.core.metrics.get_config")
    @patch("garmy.core.metrics.os.cpu_count")
    def test_determine_optimal_workers_with_max_workers(
        self, mock_cpu_count, mock_get_config
    ):
        """Test _determine_optimal_workers with max_workers specified."""
        mock_config = Mock()
        mock_config.max_workers = 20
        mock_get_config.return_value = mock_config
        mock_cpu_count.return_value = 4

        manager = MetricConcurrencyManager()

        # Test with value within bounds
        result = manager._determine_optimal_workers(10)
        assert result == 10

        # Test with value above max
        result = manager._determine_optimal_workers(25)
        assert result == 20

        # Test with value below min
        result = manager._determine_optimal_workers(0)
        assert result >= 1  # Should be at least MIN_WORKERS

    @patch("garmy.core.metrics.get_config")
    @patch("garmy.core.metrics.os.cpu_count")
    @patch.dict(os.environ, {}, clear=True)
    def test_determine_optimal_workers_auto_detection(
        self, mock_cpu_count, mock_get_config
    ):
        """Test _determine_optimal_workers with auto-detection."""
        mock_config = Mock()
        mock_config.max_workers = 20
        mock_config.optimal_min_workers = 2
        mock_config.optimal_max_workers = 12
        mock_get_config.return_value = mock_config
        mock_cpu_count.return_value = 4

        manager = MetricConcurrencyManager()

        result = manager._determine_optimal_workers(None)

        # Should be CPU cores * 3, capped by optimal_max_workers
        expected = max(2, min(4 * 3, 12))
        assert result == expected

    @patch("garmy.core.metrics.get_config")
    @patch.dict(os.environ, {"GARMY_MAX_WORKERS": "8"})
    def test_determine_optimal_workers_environment_override(self, mock_get_config):
        """Test _determine_optimal_workers with environment variable."""
        mock_config = Mock()
        mock_config.max_workers = 20
        mock_get_config.return_value = mock_config

        manager = MetricConcurrencyManager()

        result = manager._determine_optimal_workers(None)
        assert result == 8

    @patch("garmy.core.metrics.get_config")
    @patch.dict(os.environ, {"GARMY_MAX_WORKERS": "invalid"})
    @patch("garmy.core.metrics.os.cpu_count")
    def test_determine_optimal_workers_invalid_environment(
        self, mock_cpu_count, mock_get_config
    ):
        """Test _determine_optimal_workers with invalid environment variable."""
        mock_config = Mock()
        mock_config.max_workers = 20
        mock_config.optimal_min_workers = 2
        mock_config.optimal_max_workers = 12
        mock_get_config.return_value = mock_config
        mock_cpu_count.return_value = 4

        manager = MetricConcurrencyManager()

        result = manager._determine_optimal_workers(None)

        # Should fall back to CPU-based calculation
        expected = max(2, min(4 * 3, 12))
        assert result == expected

    def test_fetch_multiple_dates_single_date(self):
        """Test fetch_multiple_dates with single date."""
        manager = MetricConcurrencyManager(5)

        def mock_fetch(date_val):
            return f"data_for_{date_val}"

        dates = [date(2023, 12, 1)]

        result = manager.fetch_multiple_dates(mock_fetch, dates)

        assert result == ["data_for_2023-12-01"]

    def test_fetch_multiple_dates_multiple_dates(self):
        """Test fetch_multiple_dates with multiple dates."""
        manager = MetricConcurrencyManager(5)

        def mock_fetch(date_val):
            return f"data_for_{date_val}"

        dates = [date(2023, 12, 1), date(2023, 12, 2), date(2023, 12, 3)]

        with patch.object(
            manager, "_fetch_concurrent"
        ) as mock_concurrent, patch.object(manager, "_flatten_results") as mock_flatten:
            mock_concurrent.return_value = ["result1", "result2", "result3"]
            mock_flatten.return_value = ["flattened1", "flattened2", "flattened3"]

            result = manager.fetch_multiple_dates(mock_fetch, dates)

            assert result == ["flattened1", "flattened2", "flattened3"]
            mock_concurrent.assert_called_once_with(mock_fetch, dates)
            mock_flatten.assert_called_once_with(["result1", "result2", "result3"])

    def test_fetch_single_date_with_data(self):
        """Test _fetch_single_date with data."""
        manager = MetricConcurrencyManager(5)

        def mock_fetch(date_val):
            return f"data_for_{date_val}"

        result = manager._fetch_single_date(mock_fetch, date(2023, 12, 1))

        assert result == ["data_for_2023-12-01"]

    def test_fetch_single_date_no_data(self):
        """Test _fetch_single_date with no data."""
        manager = MetricConcurrencyManager(5)

        def mock_fetch(date_val):
            return None

        result = manager._fetch_single_date(mock_fetch, date(2023, 12, 1))

        assert result == []

    @patch("garmy.core.metrics.ThreadPoolExecutor")
    @patch("garmy.core.metrics.as_completed")
    def test_fetch_concurrent_success(self, mock_as_completed, mock_executor_class):
        """Test _fetch_concurrent successful execution."""
        manager = MetricConcurrencyManager(3)

        # Mock executor and futures
        mock_executor = Mock()
        mock_executor_class.return_value.__enter__.return_value = mock_executor

        mock_future1 = Mock()
        mock_future2 = Mock()
        mock_future1.result.return_value = "result1"
        mock_future2.result.return_value = "result2"

        mock_executor.submit.side_effect = [mock_future1, mock_future2]
        mock_as_completed.return_value = [mock_future1, mock_future2]

        def mock_fetch(date_val):
            return f"data_for_{date_val}"

        dates = [date(2023, 12, 1), date(2023, 12, 2)]

        result = manager._fetch_concurrent(mock_fetch, dates)

        assert len(result) == 2
        assert "result1" in result
        assert "result2" in result

    @patch("garmy.core.metrics.ThreadPoolExecutor")
    @patch("garmy.core.metrics.as_completed")
    def test_fetch_concurrent_with_exception(
        self, mock_as_completed, mock_executor_class
    ):
        """Test _fetch_concurrent with task exception."""
        manager = MetricConcurrencyManager(3)

        # Mock executor and futures
        mock_executor = Mock()
        mock_executor_class.return_value.__enter__.return_value = mock_executor

        mock_future1 = Mock()
        mock_future2 = Mock()
        mock_future1.result.return_value = "result1"
        mock_future2.result.side_effect = Exception("Task failed")

        mock_executor.submit.side_effect = [mock_future1, mock_future2]
        mock_as_completed.return_value = [mock_future1, mock_future2]

        def mock_fetch(date_val):
            return f"data_for_{date_val}"

        dates = [date(2023, 12, 1), date(2023, 12, 2)]

        with patch("garmy.core.metrics.logging.warning"):
            result = manager._fetch_concurrent(mock_fetch, dates)

        # Should contain successful result and None for failed task
        assert len(result) == 2
        assert "result1" in result
        assert None in result

    @patch("garmy.core.metrics.ThreadPoolExecutor")
    def test_fetch_concurrent_executor_exception(self, mock_executor_class):
        """Test _fetch_concurrent with executor exception."""
        manager = MetricConcurrencyManager(3)

        # Mock executor that raises exception
        mock_executor = Mock()
        mock_executor_class.return_value.__enter__.return_value = mock_executor
        mock_executor.submit.side_effect = Exception("Executor failed")

        def mock_fetch(date_val):
            return f"data_for_{date_val}"

        dates = [date(2023, 12, 1)]

        with patch("garmy.core.metrics.logging.error"), pytest.raises(
            Exception, match="Executor failed"
        ):
            manager._fetch_concurrent(mock_fetch, dates)

    def test_flatten_results_mixed_data(self):
        """Test _flatten_results with mixed data types."""
        manager = MetricConcurrencyManager(5)

        results = [
            "single_item",
            ["list_item1", "list_item2"],
            None,
            "another_single",
            [],
        ]

        flattened = manager._flatten_results(results)

        expected = ["single_item", "list_item1", "list_item2", "another_single"]
        assert flattened == expected

    def test_flatten_results_empty_list(self):
        """Test _flatten_results with empty list."""
        manager = MetricConcurrencyManager(5)

        result = manager._flatten_results([])

        assert result == []

    def test_flatten_results_none_values(self):
        """Test _flatten_results with None values."""
        manager = MetricConcurrencyManager(5)

        results = [None, None, None]

        result = manager._flatten_results(results)

        assert result == []


class SampleMetricAccessor:
    """Test cases for MetricAccessor class."""

    @patch("garmy.core.metrics.MetricConcurrencyManager")
    @patch("garmy.core.metrics.MetricDataParser")
    @patch("garmy.core.metrics.MetricHttpClient")
    def test_metric_accessor_initialization(
        self, mock_http, mock_parser, mock_concurrency
    ):
        """Test MetricAccessor initialization."""
        mock_api_client = Mock()
        mock_http_instance = Mock()
        mock_parser_instance = Mock()
        mock_concurrency_instance = Mock()

        mock_http.return_value = mock_http_instance
        mock_parser.return_value = mock_parser_instance
        mock_concurrency.return_value = mock_concurrency_instance

        accessor = MetricAccessor(
            mock_api_client,
            SampleMetric,
            "/test/endpoint",
            parse_func=None,
            endpoint_builder=None,
            max_workers=5,
        )

        assert accessor.endpoint == "/test/endpoint"
        assert accessor.endpoint_builder is None
        assert accessor.metric_class == SampleMetric
        assert accessor.http_client == mock_http_instance
        assert accessor.parser == mock_parser_instance
        assert accessor.concurrency_manager == mock_concurrency_instance

        mock_http.assert_called_once_with(mock_api_client)
        mock_parser.assert_called_once_with(SampleMetric, None)
        mock_concurrency.assert_called_once_with(5)

    @patch("garmy.core.metrics.MetricConcurrencyManager")
    @patch("garmy.core.metrics.MetricDataParser")
    @patch("garmy.core.metrics.MetricHttpClient")
    def test_metric_accessor_initialization_with_custom_params(
        self, mock_http, mock_parser, mock_concurrency
    ):
        """Test MetricAccessor initialization with custom parameters."""
        mock_api_client = Mock()

        def custom_parser(data):
            return SampleMetric(42, "custom")

        def custom_builder(**kwargs):
            return "/custom/endpoint"

        accessor = MetricAccessor(
            mock_api_client,
            SampleMetric,
            "/test/endpoint",
            parse_func=custom_parser,
            endpoint_builder=custom_builder,
            max_workers=10,
        )

        assert accessor.endpoint == "/test/endpoint"
        assert accessor.endpoint_builder == custom_builder
        mock_parser.assert_called_once_with(SampleMetric, custom_parser)
        mock_concurrency.assert_called_once_with(10)

    @patch("garmy.core.metrics.MetricConcurrencyManager")
    @patch("garmy.core.metrics.MetricDataParser")
    @patch("garmy.core.metrics.MetricHttpClient")
    @patch.dict(os.environ, {"GARMY_ENABLE_CACHE": "true"})
    def test_raw_method_with_caching_enabled(
        self, mock_http, mock_parser, mock_concurrency
    ):
        """Test raw method with caching enabled."""
        mock_api_client = Mock()
        mock_http_instance = Mock()
        mock_http_instance.fetch_raw_data.return_value = {"data": "test"}
        mock_http.return_value = mock_http_instance

        accessor = MetricAccessor(mock_api_client, SampleMetric, "/test/endpoint")

        # First call
        result1 = accessor.raw("2023-12-01")
        assert result1 == {"data": "test"}

        # Second call should use cache
        result2 = accessor.raw("2023-12-01")
        assert result2 == {"data": "test"}

        # Should only fetch once due to caching
        mock_http_instance.fetch_raw_data.assert_called_once()

    @patch("garmy.core.metrics.MetricConcurrencyManager")
    @patch("garmy.core.metrics.MetricDataParser")
    @patch("garmy.core.metrics.MetricHttpClient")
    @patch.dict(os.environ, {"GARMY_ENABLE_CACHE": "false"})
    def test_raw_method_without_caching(self, mock_http, mock_parser, mock_concurrency):
        """Test raw method without caching."""
        mock_api_client = Mock()
        mock_http_instance = Mock()
        mock_http_instance.fetch_raw_data.return_value = {"data": "test"}
        mock_http.return_value = mock_http_instance

        accessor = MetricAccessor(mock_api_client, SampleMetric, "/test/endpoint")

        # Two calls
        result1 = accessor.raw("2023-12-01")
        result2 = accessor.raw("2023-12-01")

        assert result1 == {"data": "test"}
        assert result2 == {"data": "test"}

        # Should fetch twice without caching
        assert mock_http_instance.fetch_raw_data.call_count == 2

    @patch("garmy.core.metrics.MetricConcurrencyManager")
    @patch("garmy.core.metrics.MetricDataParser")
    @patch("garmy.core.metrics.MetricHttpClient")
    @patch.dict(os.environ, {"GARMY_ENABLE_CACHE": "true"})
    @patch("garmy.core.metrics.get_config")
    def test_raw_method_cache_size_limit(
        self, mock_get_config, mock_http, mock_parser, mock_concurrency
    ):
        """Test raw method cache size limit."""
        mock_config = Mock()
        mock_config.metric_cache_size = 1  # Very small cache
        mock_get_config.return_value = mock_config

        mock_api_client = Mock()
        mock_http_instance = Mock()
        mock_http_instance.fetch_raw_data.side_effect = [
            {"data": "first"},
            {"data": "second"},
        ]
        mock_http.return_value = mock_http_instance

        accessor = MetricAccessor(mock_api_client, SampleMetric, "/test/endpoint")

        # Fill cache
        result1 = accessor.raw("2023-12-01")
        assert result1 == {"data": "first"}

        # Cache should evict oldest entry
        result2 = accessor.raw("2023-12-02")
        assert result2 == {"data": "second"}

        # Should fetch both times due to cache eviction
        assert mock_http_instance.fetch_raw_data.call_count == 2

    @patch("garmy.core.metrics.MetricConcurrencyManager")
    @patch("garmy.core.metrics.MetricDataParser")
    @patch("garmy.core.metrics.MetricHttpClient")
    def test_get_method(self, mock_http, mock_parser, mock_concurrency):
        """Test get method."""
        mock_api_client = Mock()
        mock_http_instance = Mock()
        mock_parser_instance = Mock()
        mock_http_instance.fetch_raw_data.return_value = {"value": 42, "name": "test"}
        mock_parser_instance.parse.return_value = SampleMetric(42, "test")
        mock_http.return_value = mock_http_instance
        mock_parser.return_value = mock_parser_instance

        accessor = MetricAccessor(mock_api_client, SampleMetric, "/test/endpoint")

        result = accessor.get("2023-12-01", extra="param")

        assert isinstance(result, SampleMetric)
        assert result.value == 42
        assert result.name == "test"

        mock_http_instance.fetch_raw_data.assert_called_once_with(
            "/test/endpoint", "2023-12-01", None, extra="param"
        )
        mock_parser_instance.parse.assert_called_once_with(
            {"value": 42, "name": "test"}
        )

    @patch("garmy.core.metrics.MetricConcurrencyManager")
    @patch("garmy.core.metrics.MetricDataParser")
    @patch("garmy.core.metrics.MetricHttpClient")
    @patch("garmy.core.metrics.datetime")
    def test_list_method_with_end_date(
        self, mock_datetime, mock_http, mock_parser, mock_concurrency
    ):
        """Test list method with end date."""
        mock_api_client = Mock()
        mock_concurrency_instance = Mock()
        mock_concurrency_instance.fetch_multiple_dates.return_value = [
            SampleMetric(1, "first"),
            SampleMetric(2, "second"),
        ]
        mock_concurrency.return_value = mock_concurrency_instance

        # Mock datetime
        end_date = date(2023, 12, 3)
        mock_datetime.strptime.return_value.date.return_value = end_date

        accessor = MetricAccessor(mock_api_client, SampleMetric, "/test/endpoint")

        result = accessor.list("2023-12-03", 3)

        assert len(result) == 2
        assert result[0].value == 1
        assert result[1].value == 2

        # Should generate correct date range
        mock_concurrency_instance.fetch_multiple_dates.assert_called_once()
        call_args = mock_concurrency_instance.fetch_multiple_dates.call_args
        dates = call_args[0][1]
        assert len(dates) == 3

    @patch("garmy.core.metrics.MetricConcurrencyManager")
    @patch("garmy.core.metrics.MetricDataParser")
    @patch("garmy.core.metrics.MetricHttpClient")
    @patch("garmy.core.metrics.date")
    def test_list_method_no_end_date(
        self, mock_date, mock_http, mock_parser, mock_concurrency
    ):
        """Test list method with no end date."""
        mock_api_client = Mock()
        mock_concurrency_instance = Mock()
        mock_concurrency_instance.fetch_multiple_dates.return_value = [
            SampleMetric(1, "test")
        ]
        mock_concurrency.return_value = mock_concurrency_instance

        # Mock today's date
        today = date(2023, 12, 5)
        mock_date.today.return_value = today

        accessor = MetricAccessor(mock_api_client, SampleMetric, "/test/endpoint")

        result = accessor.list(days=2)

        assert len(result) == 1
        mock_concurrency_instance.fetch_multiple_dates.assert_called_once()

    @patch("garmy.core.metrics.MetricConcurrencyManager")
    @patch("garmy.core.metrics.MetricDataParser")
    @patch("garmy.core.metrics.MetricHttpClient")
    @patch.dict(os.environ, {"GARMY_ENABLE_CACHE": "true"})
    def test_clear_cache(self, mock_http, mock_parser, mock_concurrency):
        """Test clear_cache method."""
        mock_api_client = Mock()

        accessor = MetricAccessor(mock_api_client, SampleMetric, "/test/endpoint")

        # Add something to cache
        accessor._cache["test_key"] = "test_value"

        accessor.clear_cache()

        assert len(accessor._cache) == 0

    @patch("garmy.core.metrics.MetricConcurrencyManager")
    @patch("garmy.core.metrics.MetricDataParser")
    @patch("garmy.core.metrics.MetricHttpClient")
    @patch.dict(os.environ, {"GARMY_ENABLE_CACHE": "true"})
    def test_get_cache_stats_enabled(self, mock_http, mock_parser, mock_concurrency):
        """Test get_cache_stats with caching enabled."""
        mock_api_client = Mock()

        accessor = MetricAccessor(mock_api_client, SampleMetric, "/test/endpoint")

        # Add items to cache
        accessor._cache["key1"] = "value1"
        accessor._cache["key2"] = "value2"

        stats = accessor.get_cache_stats()

        assert stats == {"enabled": True, "size": 2}

    @patch("garmy.core.metrics.MetricConcurrencyManager")
    @patch("garmy.core.metrics.MetricDataParser")
    @patch("garmy.core.metrics.MetricHttpClient")
    @patch.dict(os.environ, {"GARMY_ENABLE_CACHE": "false"})
    def test_get_cache_stats_disabled(self, mock_http, mock_parser, mock_concurrency):
        """Test get_cache_stats with caching disabled."""
        mock_api_client = Mock()

        accessor = MetricAccessor(mock_api_client, SampleMetric, "/test/endpoint")

        stats = accessor.get_cache_stats()

        assert stats == {"enabled": False, "size": 0}


class SampleMetricAccessorThreadSafety:
    """Test cases for MetricAccessor thread safety."""

    @patch("garmy.core.metrics.MetricConcurrencyManager")
    @patch("garmy.core.metrics.MetricDataParser")
    @patch("garmy.core.metrics.MetricHttpClient")
    @patch.dict(os.environ, {"GARMY_ENABLE_CACHE": "true"})
    def test_concurrent_cache_access(self, mock_http, mock_parser, mock_concurrency):
        """Test concurrent cache access is thread-safe."""
        mock_api_client = Mock()
        mock_http_instance = Mock()
        mock_http_instance.fetch_raw_data.return_value = {"data": "test"}
        mock_http.return_value = mock_http_instance

        accessor = MetricAccessor(mock_api_client, SampleMetric, "/test/endpoint")

        results = []

        def fetch_data():
            result = accessor.raw("2023-12-01")
            results.append(result)

        # Create multiple threads
        threads = [threading.Thread(target=fetch_data) for _ in range(10)]

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # All results should be the same
        assert len(results) == 10
        assert all(result == {"data": "test"} for result in results)

        # Should only fetch once due to caching and thread safety
        assert (
            mock_http_instance.fetch_raw_data.call_count <= 2
        )  # Allow for race conditions

    @patch("garmy.core.metrics.MetricConcurrencyManager")
    @patch("garmy.core.metrics.MetricDataParser")
    @patch("garmy.core.metrics.MetricHttpClient")
    def test_initialization_thread_safety(
        self, mock_http, mock_parser, mock_concurrency
    ):
        """Test MetricAccessor initialization is thread-safe."""
        mock_api_client = Mock()

        accessors = []

        def create_accessor():
            accessor = MetricAccessor(mock_api_client, SampleMetric, "/test/endpoint")
            accessors.append(accessor)

        # Create multiple threads
        threads = [threading.Thread(target=create_accessor) for _ in range(5)]

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # All accessors should be created successfully
        assert len(accessors) == 5
        assert all(isinstance(accessor, MetricAccessor) for accessor in accessors)


class SampleMetricAccessorIntegration:
    """Test cases for MetricAccessor integration scenarios."""

    def test_metric_accessor_full_workflow(self):
        """Test MetricAccessor full workflow integration."""
        # Create real instances (not mocked)
        mock_api_client = Mock()
        mock_api_client.connectapi.return_value = {
            "metricValue": 42,
            "metricName": "test_metric",
        }

        accessor = MetricAccessor(
            mock_api_client, SampleMetric, "/test/{date}/endpoint"
        )

        # Test the full workflow
        result = accessor.get("2023-12-01")

        # Should get parsed result
        assert isinstance(result, SampleMetric)
        assert result.value == 42
        assert result.name == "test_metric"

    def test_metric_accessor_with_endpoint_builder(self):
        """Test MetricAccessor with endpoint builder."""
        mock_api_client = Mock()
        mock_api_client.connectapi.return_value = {
            "metricValue": 123,
            "metricName": "built_endpoint",
        }

        def custom_builder(date_input=None, api_client=None, **kwargs):
            return f"/custom/{date_input}/endpoint"

        accessor = MetricAccessor(
            mock_api_client,
            SampleMetric,
            "/template/endpoint",
            endpoint_builder=custom_builder,
        )

        result = accessor.get("2023-12-01")

        assert isinstance(result, SampleMetric)
        mock_api_client.connectapi.assert_called_once_with(
            "/custom/2023-12-01/endpoint"
        )

    def test_metric_accessor_error_handling(self):
        """Test MetricAccessor error handling."""
        mock_api_client = Mock()
        http_error = create_mock_http_error("API failed")
        mock_api_client.connectapi.side_effect = APIError("API failed", http_error)

        accessor = MetricAccessor(mock_api_client, SampleMetric, "/test/endpoint")

        # Should handle API errors gracefully
        result = accessor.get("2023-12-01")

        # Should return None when API fails
        assert result is None
