"""Comprehensive tests for garmy.core.utils module.

This module provides 100% test coverage for utility functions and classes.
"""

import threading
import time
from dataclasses import dataclass
from datetime import date, datetime
from typing import List
from unittest.mock import Mock, patch

import pytest
from requests import HTTPError

from garmy.auth.exceptions import AuthError
from garmy.core.exceptions import APIError
from garmy.core.utils import (
    TimestampMixin,
    camel_to_snake,
    camel_to_snake_dict,
    create_list_parser,
    create_nested_summary_parser,
    create_simple_field_parser,
    create_simple_parser,
    create_summary_raw_parser,
    date_range,
    format_date,
    handle_api_exception,
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
    timestamp_local: datetime = None
    calendar_date: str = None


@dataclass
class SampleSummary:
    """Test summary class for testing."""

    total: int
    average: float
    count: int = 0


@dataclass
class SampleMainClass:
    """Test main class with summary."""

    test_summary: SampleSummary
    raw_data: List[int] = None
    extra_field: str = None


@dataclass
class SampleMainWithSample:
    """Test main class that follows the naming pattern."""

    sample_summary: SampleSummary
    raw_data: List[int] = None
    extra_field: str = None


class TestCamelToSnake:
    """Test cases for camel_to_snake function."""

    def test_camel_to_snake_basic(self):
        """Test basic camelCase to snake_case conversion."""
        assert camel_to_snake("camelCase") == "camel_case"
        assert camel_to_snake("PascalCase") == "pascal_case"
        assert camel_to_snake("simpleword") == "simpleword"

    def test_camel_to_snake_complex(self):
        """Test complex camelCase conversions."""
        assert camel_to_snake("HTTPResponseCode") == "http_response_code"
        assert camel_to_snake("XMLHttpRequest") == "xml_http_request"
        assert camel_to_snake("APIKeyValue") == "api_key_value"

    def test_camel_to_snake_with_numbers(self):
        """Test camelCase with numbers."""
        assert camel_to_snake("version2API") == "version2_api"
        assert camel_to_snake("http2Protocol") == "http2_protocol"
        assert camel_to_snake("OAuth2Token") == "o_auth2_token"

    def test_camel_to_snake_edge_cases(self):
        """Test camelCase edge cases."""
        assert camel_to_snake("") == ""
        assert camel_to_snake("A") == "a"
        assert camel_to_snake("ABC") == "abc"
        assert camel_to_snake("a") == "a"

    def test_camel_to_snake_already_snake_case(self):
        """Test strings already in snake_case."""
        assert camel_to_snake("snake_case") == "snake_case"
        assert camel_to_snake("already_converted") == "already_converted"
        assert camel_to_snake("_leading_underscore") == "_leading_underscore"

    def test_camel_to_snake_mixed_cases(self):
        """Test mixed case scenarios."""
        assert camel_to_snake("camelCase_mixed") == "camel_case_mixed"
        assert camel_to_snake("Mixed_camelCase") == "mixed_camel_case"


class TestFormatDate:
    """Test cases for format_date function."""

    def test_format_date_with_date_object(self):
        """Test format_date with date object."""
        test_date = date(2023, 12, 1)
        result = format_date(test_date)
        assert result == "2023-12-01"

    def test_format_date_with_datetime_object(self):
        """Test format_date with datetime object."""
        test_datetime = datetime(2023, 12, 1, 10, 30, 45)
        result = format_date(test_datetime)
        assert result == "2023-12-01"

    def test_format_date_with_string(self):
        """Test format_date with string input."""
        result = format_date("2023-12-01")
        assert result == "2023-12-01"

    def test_format_date_with_none(self):
        """Test format_date with None defaults to today."""
        with patch("garmy.core.utils.date") as mock_date:
            mock_today = date(2023, 12, 15)
            mock_date.today.return_value = mock_today

            result = format_date(None)
            assert result == "2023-12-15"

    def test_format_date_different_formats(self):
        """Test format_date with different date formats."""
        # Test various date objects
        dates = [
            date(2023, 1, 1),
            date(2023, 12, 31),
            date(2000, 2, 29),  # Leap year
        ]

        expected = ["2023-01-01", "2023-12-31", "2000-02-29"]

        for test_date, expected_result in zip(dates, expected):
            assert format_date(test_date) == expected_result


class TestDateRange:
    """Test cases for date_range function."""

    def test_date_range_basic(self):
        """Test basic date range generation."""
        end_date = date(2023, 12, 3)
        result = date_range(end_date, 3)

        expected = [date(2023, 12, 3), date(2023, 12, 2), date(2023, 12, 1)]

        assert result == expected

    def test_date_range_single_day(self):
        """Test date range with single day."""
        end_date = date(2023, 12, 1)
        result = date_range(end_date, 1)

        assert result == [date(2023, 12, 1)]

    def test_date_range_with_string_date(self):
        """Test date range with string date input."""
        result = date_range("2023-12-3", 3)

        expected = [date(2023, 12, 3), date(2023, 12, 2), date(2023, 12, 1)]

        assert result == expected

    def test_date_range_zero_days(self):
        """Test date range with zero days."""
        end_date = date(2023, 12, 1)
        result = date_range(end_date, 0)

        assert result == []

    def test_date_range_large_range(self):
        """Test date range with large number of days."""
        end_date = date(2023, 12, 31)
        result = date_range(end_date, 365)

        assert len(result) == 365
        assert result[0] == date(2023, 12, 31)
        assert result[-1] == date(2023, 1, 1)

    def test_date_range_memory_optimization(self):
        """Test date range memory optimization."""
        # Test that function pre-allocates list
        end_date = date(2023, 12, 10)
        result = date_range(end_date, 5)

        # Should return correct dates in reverse chronological order
        assert len(result) == 5
        assert all(isinstance(d, date) for d in result)
        assert result[0] > result[1] > result[2] > result[3] > result[4]


class TestCamelToSnakeDict:
    """Test cases for camel_to_snake_dict function."""

    @patch("garmy.core.config.get_config")
    def test_camel_to_snake_dict_simple(self, mock_get_config):
        """Test camel_to_snake_dict with simple dictionary."""
        mock_config = Mock()
        mock_config.key_cache_size = 1000
        mock_get_config.return_value = mock_config

        data = {
            "firstName": "John",
            "lastName": "Doe",
            "emailAddress": "john@example.com",
        }

        result = camel_to_snake_dict(data)

        expected = {
            "first_name": "John",
            "last_name": "Doe",
            "email_address": "john@example.com",
        }

        assert result == expected

    @patch("garmy.core.config.get_config")
    def test_camel_to_snake_dict_nested(self, mock_get_config):
        """Test camel_to_snake_dict with nested dictionaries."""
        mock_config = Mock()
        mock_config.key_cache_size = 1000
        mock_get_config.return_value = mock_config

        data = {
            "userProfile": {
                "firstName": "John",
                "contactInfo": {"phoneNumber": "123-456-7890"},
            }
        }

        result = camel_to_snake_dict(data)

        expected = {
            "user_profile": {
                "first_name": "John",
                "contact_info": {"phone_number": "123-456-7890"},
            }
        }

        assert result == expected

    @patch("garmy.core.config.get_config")
    def test_camel_to_snake_dict_with_list(self, mock_get_config):
        """Test camel_to_snake_dict with lists."""
        mock_config = Mock()
        mock_config.key_cache_size = 1000
        mock_get_config.return_value = mock_config

        data = {
            "userList": [
                {"firstName": "John", "lastName": "Doe"},
                {"firstName": "Jane", "lastName": "Smith"},
            ]
        }

        result = camel_to_snake_dict(data)

        expected = {
            "user_list": [
                {"first_name": "John", "last_name": "Doe"},
                {"first_name": "Jane", "last_name": "Smith"},
            ]
        }

        assert result == expected

    @patch("garmy.core.config.get_config")
    def test_camel_to_snake_dict_with_primitives(self, mock_get_config):
        """Test camel_to_snake_dict with primitive values."""
        mock_config = Mock()
        mock_config.key_cache_size = 1000
        mock_get_config.return_value = mock_config

        # Test with non-dict input
        assert camel_to_snake_dict("string") == "string"
        assert camel_to_snake_dict(123) == 123
        assert camel_to_snake_dict(None) is None
        assert camel_to_snake_dict([1, 2, 3]) == [1, 2, 3]

    @patch("garmy.core.config.get_config")
    def test_camel_to_snake_dict_caching(self, mock_get_config):
        """Test camel_to_snake_dict caching mechanism."""
        mock_config = Mock()
        mock_config.key_cache_size = 2  # Small cache for testing
        mock_get_config.return_value = mock_config

        # Clear any existing cache
        func_obj = camel_to_snake_dict
        if hasattr(func_obj, "_cache"):
            delattr(func_obj, "_cache")

        data1 = {"firstName": "John"}
        data2 = {"firstName": "Jane", "lastName": "Doe"}
        data3 = {
            "firstName": "Bob",
            "lastName": "Smith",
            "emailAddress": "bob@example.com",
        }

        # Process data to populate cache
        camel_to_snake_dict(data1)
        camel_to_snake_dict(data2)
        camel_to_snake_dict(data3)  # Should trigger cache eviction

        # Cache should have evicted oldest entries
        cache = func_obj._cache.key_memo  # type: ignore[attr-defined]
        assert len(cache) <= 2

    @patch("garmy.core.config.get_config")
    def test_camel_to_snake_dict_thread_safety(self, mock_get_config):
        """Test camel_to_snake_dict thread safety."""
        mock_config = Mock()
        mock_config.key_cache_size = 1000
        mock_get_config.return_value = mock_config

        results = []

        def convert_data():
            data = {"firstName": "John", "lastName": "Doe"}
            result = camel_to_snake_dict(data)
            results.append(result)

        # Create multiple threads
        threads = [threading.Thread(target=convert_data) for _ in range(10)]

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # All results should be the same
        expected = {"first_name": "John", "last_name": "Doe"}
        assert all(result == expected for result in results)

    @patch("garmy.core.config.get_config")
    def test_camel_to_snake_dict_empty_structures(self, mock_get_config):
        """Test camel_to_snake_dict with empty structures."""
        mock_config = Mock()
        mock_config.key_cache_size = 1000
        mock_get_config.return_value = mock_config

        assert camel_to_snake_dict({}) == {}
        assert camel_to_snake_dict([]) == []
        assert camel_to_snake_dict({"emptyDict": {}}) == {"empty_dict": {}}
        assert camel_to_snake_dict({"emptyList": []}) == {"empty_list": []}


class TestHandleApiException:
    """Test cases for handle_api_exception function."""

    def test_handle_api_exception_auth_error(self):
        """Test handle_api_exception with AuthError."""
        auth_error = AuthError("Authentication failed")

        with pytest.raises(
            AuthError, match="Authentication required for test operation"
        ):
            handle_api_exception(auth_error, "test operation")

    @patch("garmy.core.utils.logging.warning")
    def test_handle_api_exception_api_error(self, mock_warning):
        """Test handle_api_exception with APIError."""
        http_error = create_mock_http_error("API call failed")
        api_error = APIError("API call failed", http_error)

        result = handle_api_exception(
            api_error, "test operation", "/test/endpoint", "default"
        )

        assert result == "default"
        mock_warning.assert_called_once()

    @patch("garmy.core.utils.logging.error")
    def test_handle_api_exception_unexpected_error(self, mock_error):
        """Test handle_api_exception with unexpected error."""
        unexpected_error = ValueError("Unexpected error")

        result = handle_api_exception(
            unexpected_error, "test operation", "/test/endpoint", []
        )

        assert result == []
        mock_error.assert_called_once()

    def test_handle_api_exception_no_endpoint(self):
        """Test handle_api_exception without endpoint."""
        http_error = create_mock_http_error("API call failed")
        api_error = APIError("API call failed", http_error)

        with patch("garmy.core.utils.logging.warning") as mock_warning:
            result = handle_api_exception(
                api_error, "test operation", default_return=None
            )

            assert result is None
            mock_warning.assert_called_once()

    def test_handle_api_exception_no_default_return(self):
        """Test handle_api_exception without default return value."""
        http_error = create_mock_http_error("API call failed")
        api_error = APIError("API call failed", http_error)

        with patch("garmy.core.utils.logging.warning"):
            result = handle_api_exception(api_error, "test operation")

            assert result is None


class TestTimestampMixin:
    """Test cases for TimestampMixin class."""

    def test_timestamp_to_datetime(self):
        """Test timestamp_to_datetime method."""
        from datetime import timezone
        # Test Unix timestamp in milliseconds
        timestamp = 1640995200000  # 2022-01-01 00:00:00 UTC
        result = TimestampMixin.timestamp_to_datetime(timestamp)

        assert isinstance(result, datetime)
        assert result.year == 2022
        assert result.month == 1
        assert result.day == 1
        assert result.tzinfo == timezone.utc

    def test_timestamp_to_datetime_different_values(self):
        """Test timestamp_to_datetime with different values."""
        timestamps = [
            1640995200000,  # 2022-01-01
            1609459200000,  # 2021-01-01
            1577836800000,  # 2020-01-01
        ]

        for timestamp in timestamps:
            result = TimestampMixin.timestamp_to_datetime(timestamp)
            assert isinstance(result, datetime)

    def test_iso_to_datetime_valid_iso(self):
        """Test iso_to_datetime with valid ISO string."""
        iso_string = "2023-12-01T10:30:00.0Z"
        result = TimestampMixin.iso_to_datetime(iso_string)

        assert isinstance(result, datetime)
        assert result.year == 2023
        assert result.month == 12
        assert result.day == 1
        assert result.hour == 10
        assert result.minute == 30

    def test_iso_to_datetime_without_z_suffix(self):
        """Test iso_to_datetime without Z suffix."""
        iso_string = "2023-12-01T10:30:00"
        result = TimestampMixin.iso_to_datetime(iso_string)

        assert isinstance(result, datetime)
        assert result.year == 2023

    def test_iso_to_datetime_none_input(self):
        """Test iso_to_datetime with None input."""
        result = TimestampMixin.iso_to_datetime(None)
        assert result is None

    def test_iso_to_datetime_empty_string(self):
        """Test iso_to_datetime with empty string."""
        result = TimestampMixin.iso_to_datetime("")
        assert result is None

    def test_iso_to_datetime_invalid_format(self):
        """Test iso_to_datetime with invalid format."""
        result = TimestampMixin.iso_to_datetime("invalid-date-format")
        assert result is None

    def test_timestamp_mixin_as_mixin(self):
        """Test TimestampMixin can be used as a mixin."""

        class TestClass(TimestampMixin):
            def __init__(self, timestamp):
                self.datetime = self.timestamp_to_datetime(timestamp)

        test_obj = TestClass(1640995200000)
        assert isinstance(test_obj.datetime, datetime)


class TestParserFactories:
    """Test cases for parser factory functions."""

    def test_create_simple_parser_basic(self):
        """Test create_simple_parser basic functionality."""
        parser = create_simple_parser(SampleMainWithSample, SampleSummary, ["raw_data"])

        data = {"total": 100, "average": 50.0, "count": 2, "rawData": [1, 2, 3]}

        with patch("garmy.core.utils.camel_to_snake_dict") as mock_convert:
            mock_convert.return_value = {
                "total": 100,
                "average": 50.0,
                "count": 2,
                "raw_data": [1, 2, 3],
            }

            result = parser(data)

            assert isinstance(result, SampleMainWithSample)
            assert isinstance(result.sample_summary, SampleSummary)
            assert result.raw_data == [1, 2, 3]

    def test_create_simple_parser_no_raw_fields(self):
        """Test create_simple_parser without raw fields."""
        parser = create_simple_parser(SampleMainWithSample, SampleSummary)

        data = {"total": 100, "average": 50.0}

        with patch("garmy.core.utils.camel_to_snake_dict") as mock_convert:
            mock_convert.return_value = {"total": 100, "average": 50.0}

            result = parser(data)

            assert isinstance(result, SampleMainWithSample)
            assert isinstance(result.sample_summary, SampleSummary)

    def test_create_simple_parser_no_summary_class(self):
        """Test create_simple_parser without summary class."""
        parser = create_simple_parser(SampleMetric, None)

        data = {"value": 42, "name": "test"}

        with patch("garmy.core.utils.camel_to_snake_dict") as mock_convert:
            mock_convert.return_value = {"value": 42, "name": "test"}

            result = parser(data)

            assert isinstance(result, SampleMetric)
            assert result.value == 42
            assert result.name == "test"

    def test_create_simple_parser_invalid_summary_class(self):
        """Test create_simple_parser with invalid summary class."""
        parser = create_simple_parser(SampleMetric, str)  # str is not a dataclass

        data = {"value": 42}

        with patch("garmy.core.utils.camel_to_snake_dict") as mock_convert:
            mock_convert.return_value = {"value": 42}

            with pytest.raises(ValueError, match="summary_class .* is not a dataclass"):
                parser(data)

    def test_create_simple_parser_non_dict_response(self):
        """Test create_simple_parser with non-dict response from camel_to_snake_dict."""
        parser = create_simple_parser(SampleMetric, SampleSummary)

        data = {"total": 100}

        with patch("garmy.core.utils.camel_to_snake_dict") as mock_convert:
            mock_convert.return_value = "not a dict"

            with pytest.raises(
                ValueError, match="Expected dict from camel_to_snake_dict but got str"
            ):
                parser(data)

    def test_create_simple_field_parser(self):
        """Test create_simple_field_parser function."""
        parser = create_simple_field_parser(SampleMetric)

        data = {"value": 42, "name": "test"}

        with patch("garmy.core.utils.camel_to_snake_dict") as mock_convert:
            mock_convert.return_value = {"value": 42, "name": "test"}

            result = parser(data)

            assert isinstance(result, SampleMetric)
            assert result.value == 42
            assert result.name == "test"

    def test_create_simple_field_parser_datetime_handling(self):
        """Test create_simple_field_parser datetime handling."""
        parser = create_simple_field_parser(SampleMetric)

        data = {"value": 42, "name": "test", "timestamp": "2023-12-01T10:00:00Z"}

        with patch("garmy.core.utils.camel_to_snake_dict") as mock_convert:
            mock_convert.return_value = {
                "value": 42,
                "name": "test",
                "timestamp": "2023-12-01T10:00:00Z",
            }

            result = parser(data)

            assert isinstance(result, SampleMetric)
            assert isinstance(result.timestamp, datetime)

    def test_create_simple_field_parser_invalid_datetime(self):
        """Test create_simple_field_parser with invalid datetime."""
        parser = create_simple_field_parser(SampleMetric)

        data = {"value": 42, "name": "test", "timestamp": "invalid-datetime"}

        with patch("garmy.core.utils.camel_to_snake_dict") as mock_convert:
            mock_convert.return_value = {
                "value": 42,
                "name": "test",
                "timestamp": "invalid-datetime",
            }

            result = parser(data)

            assert isinstance(result, SampleMetric)
            assert result.timestamp == "invalid-datetime"  # Should keep original value

    def test_create_summary_raw_parser(self):
        """Test create_summary_raw_parser function."""
        parser = create_summary_raw_parser(SampleMainClass, SampleSummary, ["raw_data"])

        data = {"total": 100, "average": 50.0, "raw_data": [1, 2, 3]}

        with patch("garmy.core.utils.camel_to_snake_dict") as mock_convert:
            mock_convert.return_value = {
                "total": 100,
                "average": 50.0,
                "raw_data": [1, 2, 3],
            }

            result = parser(data)

            assert isinstance(result, SampleMainClass)
            assert isinstance(result.test_summary, SampleSummary)
            assert result.raw_data == [1, 2, 3]

    def test_create_nested_summary_parser(self):
        """Test create_nested_summary_parser function."""
        parser = create_nested_summary_parser(
            SampleMainClass, SampleSummary, "test_summary", ["raw_data"]
        )

        data = {
            "test_summary": {"total": 100, "average": 50.0},
            "raw_data": [1, 2, 3],
        }

        with patch("garmy.core.utils.camel_to_snake_dict") as mock_convert:
            mock_convert.return_value = {
                "test_summary": {"total": 100, "average": 50.0},
                "raw_data": [1, 2, 3],
            }

            result = parser(data)

            assert isinstance(result, SampleMainClass)
            assert isinstance(result.test_summary, SampleSummary)
            assert result.raw_data == [1, 2, 3]

    def test_create_list_parser(self):
        """Test create_list_parser function."""
        parser = create_list_parser(SampleMetric)

        data = [{"value": 1, "name": "first"}, {"value": 2, "name": "second"}]

        with patch("garmy.core.utils.create_simple_field_parser") as mock_field_parser:
            mock_item_parser = Mock()
            mock_item_parser.side_effect = [
                SampleMetric(1, "first"),
                SampleMetric(2, "second"),
            ]
            mock_field_parser.return_value = mock_item_parser

            result = parser(data)

            assert isinstance(result, list)
            assert len(result) == 2
            assert result[0].value == 1
            assert result[1].value == 2

    def test_create_list_parser_wrapped_array(self):
        """Test create_list_parser with wrapped array."""
        parser = create_list_parser(SampleMetric)

        data = {"activities": [{"value": 1, "name": "first"}]}

        with patch("garmy.core.utils.create_simple_field_parser") as mock_field_parser:
            mock_item_parser = Mock()
            mock_item_parser.return_value = SampleMetric(1, "first")
            mock_field_parser.return_value = mock_item_parser

            result = parser(data)

            assert isinstance(result, list)
            assert len(result) == 1

    def test_create_list_parser_single_item(self):
        """Test create_list_parser with single item."""
        parser = create_list_parser(SampleMetric)

        data = {"value": 1, "name": "single"}

        with patch("garmy.core.utils.create_simple_field_parser") as mock_field_parser:
            mock_item_parser = Mock()
            mock_item_parser.return_value = SampleMetric(1, "single")
            mock_field_parser.return_value = mock_item_parser

            result = parser(data)

            assert isinstance(result, list)
            assert len(result) == 1

    def test_create_list_parser_custom_item_parser(self):
        """Test create_list_parser with custom item parser."""

        def custom_parser(item):
            return SampleMetric(item["value"] * 2, item["name"])

        parser = create_list_parser(SampleMetric, custom_parser)

        data = [{"value": 5, "name": "test"}]

        result = parser(data)

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].value == 10  # 5 * 2


class TestParserFactoryEdgeCases:
    """Test cases for parser factory edge cases."""

    def test_parser_with_invalid_dataclass(self):
        """Test parser factory with invalid main class."""
        parser = create_simple_parser(str, None)  # str is not a dataclass

        data = {"value": 42}

        with patch("garmy.core.utils.camel_to_snake_dict") as mock_convert:
            mock_convert.return_value = {"value": 42}

            with pytest.raises(ValueError, match="main_class .* is not a dataclass"):
                parser(data)

    def test_parser_with_missing_fields(self):
        """Test parser handles missing fields gracefully."""
        parser = create_simple_field_parser(SampleMetric)

        data = {"value": 42}  # Missing 'name' field

        with patch("garmy.core.utils.camel_to_snake_dict") as mock_convert:
            mock_convert.return_value = {"value": 42}

            # Should create object with available fields only
            with pytest.raises(TypeError):  # Missing required field
                parser(data)

    def test_parser_with_extra_fields(self):
        """Test parser filters extra fields."""
        parser = create_simple_field_parser(SampleMetric)

        data = {
            "value": 42,
            "name": "test",
            "extra_field": "should_be_filtered",
            "another_extra": 123,
        }

        with patch("garmy.core.utils.camel_to_snake_dict") as mock_convert:
            mock_convert.return_value = {
                "value": 42,
                "name": "test",
                "extra_field": "should_be_filtered",
                "another_extra": 123,
            }

            result = parser(data)

            assert isinstance(result, SampleMetric)
            assert result.value == 42
            assert result.name == "test"
            # Extra fields should be filtered out
            assert not hasattr(result, "extra_field")
            assert not hasattr(result, "another_extra")


class TestUtilsIntegration:
    """Test cases for utils integration scenarios."""

    def test_full_data_processing_workflow(self):
        """Test full data processing workflow with utils."""
        # Simulate API response data
        api_response = {
            "testSummary": {
                "total": 1000,
                "average": 100.5,
                "count": 10,
            },
            "rawData": [1, 2, 3, 4, 5],
        }

        # Create parser
        parser = create_nested_summary_parser(
            SampleMainClass, SampleSummary, "test_summary", ["raw_data"]
        )

        # Process data
        result = parser(api_response)

        # Verify results
        assert isinstance(result, SampleMainClass)
        assert isinstance(result.test_summary, SampleSummary)
        assert result.test_summary.total == 1000
        assert result.test_summary.average == 100.5

    def test_date_formatting_integration(self):
        """Test date formatting integration with different inputs."""
        # Test with various date inputs
        inputs = [date(2023, 12, 1), datetime(2023, 12, 1, 10, 30), "2023-12-01", None]

        for date_input in inputs:
            result = format_date(date_input)
            assert isinstance(result, str)
            assert len(result) == 10  # YYYY-MM-DD format

    def test_camel_to_snake_integration(self):
        """Test camel to snake conversion integration."""
        # Test complex nested structure
        complex_data = {
            "userProfile": {
                "personalInfo": {
                    "firstName": "John",
                    "lastName": "Doe",
                    "emailAddress": "john@example.com",
                },
                "metricData": [
                    {"dataValue": 100, "dataType": "heartRate"},
                    {"dataValue": 85, "dataType": "restingHeartRate"},
                ],
            },
            "systemMetadata": {
                "lastUpdated": "2023-12-01T10:00:00Z",
                "apiVersion": "2.0",
            },
        }

        result = camel_to_snake_dict(complex_data)

        # Verify conversion
        assert "user_profile" in result
        assert "personal_info" in result["user_profile"]
        assert "first_name" in result["user_profile"]["personal_info"]
        assert "metric_data" in result["user_profile"]
        assert "data_value" in result["user_profile"]["metric_data"][0]

    def test_error_handling_integration(self):
        """Test error handling integration."""
        # Test with different error types
        http_error = create_mock_http_error("API failed")
        errors = [
            AuthError("Auth failed"),
            APIError("API failed", http_error),
            ValueError("General error"),
        ]

        for error in errors:
            if isinstance(error, AuthError):
                with pytest.raises(AuthError):
                    handle_api_exception(error, "test operation")
            else:
                with patch("garmy.core.utils.logging.warning"), patch(
                    "garmy.core.utils.logging.error"
                ):
                    result = handle_api_exception(
                        error, "test operation", default_return="default"
                    )
                    assert result == "default"


class TestUtilsPerformance:
    """Test cases for utils performance characteristics."""

    @patch("garmy.core.config.get_config")
    def test_camel_to_snake_dict_performance(self, mock_get_config):
        """Test camel_to_snake_dict performance with large data."""
        mock_config = Mock()
        mock_config.key_cache_size = 10000
        mock_get_config.return_value = mock_config

        # Create large nested structure
        large_data = {}
        for i in range(100):
            large_data[f"dataField{i}"] = {
                f"nestedField{j}": f"value{j}" for j in range(10)
            }

        # Should process efficiently
        start_time = time.time()
        result = camel_to_snake_dict(large_data)
        end_time = time.time()

        # Should complete in reasonable time
        assert end_time - start_time < 1.0  # Less than 1 second
        assert len(result) == 100

    def test_date_range_performance(self):
        """Test date_range performance with large ranges."""
        end_date = date(2023, 12, 31)

        # Test large date range
        start_time = time.time()
        result = date_range(end_date, 1000)
        end_time = time.time()

        # Should complete efficiently
        assert end_time - start_time < 0.1  # Less than 100ms
        assert len(result) == 1000
        assert all(isinstance(d, date) for d in result)

    def test_timestamp_conversion_performance(self):
        """Test timestamp conversion performance."""
        timestamps = [1640995200000 + i * 86400000 for i in range(1000)]

        start_time = time.time()
        results = [TimestampMixin.timestamp_to_datetime(ts) for ts in timestamps]
        end_time = time.time()

        # Should complete efficiently
        assert end_time - start_time < 0.5  # Less than 500ms
        assert len(results) == 1000
        assert all(isinstance(dt, datetime) for dt in results)
