"""
Core utility functions for data processing and formatting.

This module provides utility functions used throughout the garmy library
for common operations like string case conversion, date formatting,
and data structure transformation.

Functions:
    camel_to_snake: Convert camelCase strings to snake_case.
    format_date: Format date objects for API requests.
    date_range: Generate a range of date objects.
    camel_to_snake_dict: Recursively convert dictionary keys from camelCase to snake_case.

Classes:
    TimestampMixin: Mixin providing common datetime conversion utilities.

Example:
    >>> from garmy.core.utils import camel_to_snake, format_date
    >>> camel_to_snake("trainingReadiness")
    'training_readiness'
    >>> format_date(date(2023, 12, 1))
    '2023-12-01'
"""

import logging
import re
import threading
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Union


def camel_to_snake(camel_str: str) -> str:
    """Convert camelCase string to snake_case.

    Transforms camelCase and PascalCase strings to snake_case format
    by inserting underscores before uppercase letters and converting
    to lowercase.

    Args:
        camel_str: String in camelCase or PascalCase format.

    Returns:
        String converted to snake_case format.

    Example:
        >>> camel_to_snake("trainingReadiness")
        'training_readiness'
        >>> camel_to_snake("HTTPResponseCode")
        'http_response_code'
    """
    # First pass: Insert underscore before uppercase followed by lowercase
    # (e.g., 'XMLHttp' -> 'XML_Http')
    first_pass = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", camel_str)
    # Second pass: Insert underscore between lowercase/digit and uppercase
    # (e.g., 'Http2' -> 'Http_2')
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", first_pass).lower()


def format_date(date_input: Union[date, str, None] = None) -> str:
    """Format date for API calls.

    Converts various date input formats to the ISO date string format
    (YYYY-MM-DD) required by the Garmin Connect API.

    Args:
        date_input: Date to format. Can be a date object, ISO date string,
            or None (defaults to today's date).

    Returns:
        Date string in YYYY-MM-DD format.

    Example:
        >>> from datetime import date
        >>> format_date(date(2023, 12, 1))
        '2023-12-01'
        >>> format_date("2023-12-01")
        '2023-12-01'
        >>> format_date(None)  # Returns today's date
        '2023-12-15'
    """
    if date_input is None:
        date_input = date.today()
    elif isinstance(date_input, str):
        return date_input
    return date_input.strftime("%Y-%m-%d")


def date_range(end_date: Union[date, str], days: int) -> List[date]:
    """Generate a range of date objects (memory optimized).

    Creates a list of date objects going backwards from the end date
    for the specified number of days using efficient list pre-allocation.

    Performance optimizations:
    - Pre-allocated list for better memory efficiency
    - Single timedelta object reuse
    - Minimal object creation

    Args:
        end_date: End date for the range. Can be a date object or ISO date string.
        days: Number of days to include in the range.

    Returns:
        List of date objects in reverse chronological order (newest first).

    Example:
        >>> from datetime import date
        >>> dates = date_range(date(2023, 12, 3), 3)
        >>> [d.strftime('%Y-%m-%d') for d in dates]
        ['2023-12-03', '2023-12-02', '2023-12-01']
    """
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

    # Pre-allocate list for better memory efficiency
    dates: List[date] = [None] * days  # type: ignore

    # Generate dates efficiently
    for i in range(days):
        dates[i] = end_date - timedelta(days=i)

    return dates


def camel_to_snake_dict(
    data: Union[Dict[str, Any], List[Any], Any],
) -> Union[Dict[str, Any], List[Any], Any]:
    """Convert all keys in a dictionary from camelCase to snake_case (optimized).

    Efficiently processes a dictionary and all nested structures using a single pass
    with memoization to avoid redundant key conversions.

    Performance optimizations:
    - O(n) complexity instead of O(n²)
    - LRU cache with efficient eviction
    - In-place type checking
    - Minimal object creation

    Args:
        data: Dictionary, list, or any value to process.

    Returns:
        New structure with all dict keys converted to snake_case.
        Non-dict/list inputs are returned unchanged.

    Example:
        >>> data = {"userName": "john", "profileData": {"firstName": "John"}}
        >>> camel_to_snake_dict(data)
        {'user_name': 'john', 'profile_data': {'first_name': 'John'}}
    """
    # Use thread-local storage with LRU cache for efficient memory management
    from collections import OrderedDict

    from .config import get_config

    # Use function object as namespace for cache (mypy workaround)
    func_obj = camel_to_snake_dict
    if not hasattr(func_obj, "_cache"):
        func_obj._cache = threading.local()  # type: ignore[attr-defined]

    if not hasattr(func_obj._cache, "key_memo"):  # type: ignore[attr-defined]
        func_obj._cache.key_memo = OrderedDict()  # type: ignore[attr-defined]

    key_memo = func_obj._cache.key_memo  # type: ignore[attr-defined]

    def _convert_value(value: Any) -> Any:
        """Convert value recursively with optimized dispatch."""
        value_type = type(value)

        if value_type is dict:
            # Pre-allocate result dict for better memory efficiency
            result = {}
            for key, val in value.items():
                # LRU cache with efficient eviction
                if key in key_memo:
                    # Move to end (mark as recently used)
                    key_memo.move_to_end(key)
                    snake_key = key_memo[key]
                else:
                    # Add new key conversion
                    snake_key = camel_to_snake(key)
                    key_memo[key] = snake_key
                    # LRU eviction: remove oldest item if cache too large
                    config = get_config()
                    if len(key_memo) > config.key_cache_size:
                        key_memo.popitem(last=False)  # Remove oldest (FIFO)

                result[snake_key] = _convert_value(val)
            return result

        elif value_type is list:
            # Use list comprehension for better performance
            return [_convert_value(item) for item in value]

        else:
            # Return primitive values as-is
            return value

    return _convert_value(data)


def handle_api_exception(
    e: Exception, operation: str, endpoint: str = "", default_return: Any = None
) -> Any:
    """Handle API exceptions with proper error classification and logging.

    Args:
        e: The caught exception
        operation: Description of the operation being performed (e.g., "fetching Activities")
        endpoint: The API endpoint being accessed (optional)
        default_return: Value to return for recoverable errors (default: None)

    Returns:
        default_return for recoverable errors

    Raises:
        AuthError: For authentication-related errors (user needs to login)
        Exception: For unexpected errors after logging
    """
    # Use explicit imports to avoid circular dependencies
    from ..auth.exceptions import AuthError
    from .exceptions import APIError

    if isinstance(e, AuthError):
        # Re-raise authentication errors - user needs to take action
        raise AuthError(f"Authentication required for {operation}: {e}") from e
    elif isinstance(e, APIError):
        # Log API errors but allow graceful degradation
        endpoint_info = f" from {endpoint}" if endpoint else ""
        logging.warning(f"API error {operation}{endpoint_info}: {e}")
        return default_return
    else:
        # Log unexpected errors with full context
        endpoint_info = f" from {endpoint}" if endpoint else ""
        logging.error(
            f"Unexpected error {operation}{endpoint_info}: {e}", exc_info=True
        )
        return default_return


class TimestampMixin:
    """Mixin class providing common datetime conversion utilities.

    This mixin provides standardized methods for converting timestamps
    and ISO date strings to datetime objects, eliminating code duplication
    across metric classes.
    """

    @staticmethod
    def timestamp_to_datetime(timestamp: int) -> datetime:
        """Convert Unix timestamp (milliseconds) to a timezone-aware UTC datetime object.

        Args:
            timestamp: Unix timestamp in milliseconds.

        Returns:
            Corresponding timezone-aware UTC datetime object.

        Example:
            >>> from datetime import timezone
            >>> ts = TimestampMixin.timestamp_to_datetime(1640995200000)
            >>> ts.year == 2022 and ts.tzinfo == timezone.utc
            True
        """
        from datetime import timezone
        return datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)

    @staticmethod
    def iso_to_datetime(iso_string: Optional[str]) -> Optional[datetime]:
        """Convert ISO datetime string to datetime object.

        Handles ISO strings with 'Z' suffix by converting to UTC timezone.
        Returns None for empty or invalid strings.

        Args:
            iso_string: ISO datetime string (e.g., "2023-12-01T10:30:00.0Z").

        Returns:
            Parsed datetime object or None if invalid/empty.

        Example:
            >>> TimestampMixin.iso_to_datetime("2023-12-01T10:30:00.0Z")
            datetime.datetime(2023, 12, 1, 10, 30, tzinfo=...)
            >>> TimestampMixin.iso_to_datetime(None)
            None
        """
        if not iso_string:
            return None
        try:
            # Replace 'Z' with UTC timezone
            iso_string = iso_string.replace("Z", "+00:00")

            # Handle fractional seconds with single digit (e.g., ".0")
            # fromisoformat expects microseconds (6 digits) after the dot
            import re

            # Match pattern like "T10:30:00.0" and pad to 6 digits
            iso_string = re.sub(
                r"(\d{2}:\d{2}:\d{2})\.(\d{1,6})",
                lambda m: f"{m.group(1)}.{m.group(2).ljust(6, '0')}",
                iso_string,
            )

            return datetime.fromisoformat(iso_string)
        except (ValueError, AttributeError):
            return None


def create_simple_parser(
    main_class: type, summary_class: type, raw_fields: Optional[List[str]] = None
) -> Any:
    """Create a standardized parser function for metrics.

    This factory function creates parsers that follow the common pattern:
    1. Convert camelCase to snake_case
    2. Create summary object from structured fields
    3. Pass raw arrays as-is to main class
    4. Handle unknown fields gracefully

    Args:
        main_class: The main metric class (e.g., HeartRate)
        summary_class: The summary dataclass (e.g., HeartRateSummary)
        raw_fields: List of field names that should be passed as raw arrays

    Returns:
        Parser function that can be used with @metric decorator

    Example:
        >>> parse_heart_rate_data = create_simple_parser(
        ...     HeartRate,
        ...     HeartRateSummary,
        ...     ["heart_rate_values", "heart_rate_value_descriptors"]
        ... )
    """
    if raw_fields is None:
        raw_fields = []

    def parser(data: Dict[str, Any]) -> Any:
        # Convert camelCase to snake_case at top level
        snake_dict = camel_to_snake_dict(data)

        # Ensure we have a dictionary to work with
        if not isinstance(snake_dict, dict):
            raise ValueError(
                f"Expected dict from camel_to_snake_dict but got {type(snake_dict).__name__}"
            )

        # Separate summary data from raw arrays
        summary_data = {}
        raw_data = {}

        for key, value in snake_dict.items():
            if key in raw_fields:
                raw_data[key] = value
            else:
                summary_data[key] = value

        # Create summary object with graceful unknown field handling
        if summary_class:
            # Ensure we have a dataclass
            if not hasattr(summary_class, "__dataclass_fields__"):
                raise ValueError(f"summary_class {summary_class} is not a dataclass")
            fields = getattr(summary_class, "__dataclass_fields__", {})
            known_fields = {f.name for f in fields.values()}
            summary_kwargs = {
                k: v for k, v in summary_data.items() if k in known_fields
            }
            summary_obj = summary_class(**summary_kwargs)

            # For simple pattern: main_class(summary=summary_obj, **raw_data)
            # Infer the summary field name from class name
            summary_field_name = summary_class.__name__.lower().replace(
                "summary", "_summary"
            )
            return main_class(**{summary_field_name: summary_obj, **raw_data})
        else:
            # No summary class, just pass everything to main class
            if not hasattr(main_class, "__dataclass_fields__"):
                raise ValueError(f"main_class {main_class} is not a dataclass")
            known_fields = {f.name for f in main_class.__dataclass_fields__.values()}
            # Ensure snake_dict is a dictionary before calling items()
            if not isinstance(snake_dict, dict):
                raise ValueError(f"Expected dict but got {type(snake_dict).__name__}")
            main_kwargs = {k: v for k, v in snake_dict.items() if k in known_fields}
            return main_class(**main_kwargs)

    return parser


def create_simple_field_parser(dataclass_type: type) -> Any:
    """Create a parser for simple field filtering pattern.

    This is the most common pattern where we just need to:
    1. Convert camelCase to snake_case
    2. Filter fields that exist in the dataclass
    3. Create the dataclass instance

    Args:
        dataclass_type: The dataclass to create instances of

    Returns:
        Parser function that handles camelCase conversion and field filtering

    Example:
        >>> parse_calories_data = create_simple_field_parser(Calories)
        >>> calories = parse_calories_data(api_response)
    """

    def parser(data: Dict[str, Any]) -> Any:
        # Convert camelCase to snake_case
        snake_dict = camel_to_snake_dict(data)

        # Ensure we have a dataclass
        if not hasattr(dataclass_type, "__dataclass_fields__"):
            raise ValueError(f"dataclass_type {dataclass_type} is not a dataclass")

        # Ensure snake_dict is a dictionary before calling items()
        if not isinstance(snake_dict, dict):
            raise ValueError(
                f"Expected dict from camel_to_snake_dict but got {type(snake_dict).__name__}"
            )

        # Filter to known fields only
        known_fields = {f.name for f in dataclass_type.__dataclass_fields__.values()}
        filtered_kwargs = {k: v for k, v in snake_dict.items() if k in known_fields}

        # Handle common datetime fields
        for field in ("timestamp", "timestamp_local", "calendar_date"):
            if field in filtered_kwargs and isinstance(filtered_kwargs[field], str):
                try:
                    from datetime import datetime

                    if field == "calendar_date":
                        # Keep calendar_date as string for now
                        continue
                    filtered_kwargs[field] = datetime.fromisoformat(
                        filtered_kwargs[field].replace("Z", "+00:00")
                    )
                except ValueError:
                    pass  # Keep original value if parsing fails

        return dataclass_type(**filtered_kwargs)

    return parser


def create_summary_raw_parser(
    main_class: type, summary_class: type, raw_fields: List[str]
) -> Any:
    """Create a parser for summary + raw data pattern.

    This pattern is used when API responses contain both summary statistics
    and raw time-series data that should be handled separately.

    Args:
        main_class: The main metric class that contains both summary and raw data
        summary_class: The summary dataclass for aggregate statistics
        raw_fields: List of field names that contain raw time-series data

    Returns:
        Parser function that separates summary and raw data

    Example:
        >>> parse_heart_rate = create_summary_raw_parser(
        ...     HeartRate, HeartRateSummary,
        ...     ["heart_rate_values", "heart_rate_value_descriptors"]
        ... )
    """

    def parser(data: Dict[str, Any]) -> Any:
        # Convert camelCase to snake_case
        snake_dict = camel_to_snake_dict(data)

        # Ensure snake_dict is a dictionary before calling items()
        if not isinstance(snake_dict, dict):
            raise ValueError(
                f"Expected dict from camel_to_snake_dict but got {type(snake_dict).__name__}"
            )

        # Separate summary data from raw arrays
        summary_data = {k: v for k, v in snake_dict.items() if k not in raw_fields}

        # Create summary object with field filtering
        if not hasattr(summary_class, "__dataclass_fields__"):
            raise ValueError(f"summary_class {summary_class} is not a dataclass")
        summary_known_fields = {
            f.name for f in summary_class.__dataclass_fields__.values()
        }
        summary_kwargs = {
            k: v for k, v in summary_data.items() if k in summary_known_fields
        }
        summary_obj = summary_class(**summary_kwargs)

        # Determine summary field name in main class
        if not hasattr(main_class, "__dataclass_fields__"):
            raise ValueError(f"main_class {main_class} is not a dataclass")
        main_fields = {f.name for f in main_class.__dataclass_fields__.values()}
        summary_field_name = None
        for field_name in main_fields:
            if "summary" in field_name.lower():
                summary_field_name = field_name
                break

        if summary_field_name:
            # Create main object with summary and raw data
            main_kwargs = {summary_field_name: summary_obj}

            # Map raw field names to main class field names
            for raw_field in raw_fields:
                if raw_field in snake_dict:
                    # Try to find matching field in main class
                    target_field = raw_field
                    if f"{raw_field}_array" in main_fields:
                        target_field = f"{raw_field}_array"
                    elif raw_field.replace("_array", "") in main_fields:
                        target_field = raw_field.replace("_array", "")

                    if target_field in main_fields:
                        main_kwargs[target_field] = snake_dict[raw_field]

            # Add any remaining fields that belong to main class
            for k, v in snake_dict.items():
                if k in main_fields and k != summary_field_name and k not in raw_fields:
                    main_kwargs[k] = v

            return main_class(**main_kwargs)
        else:
            # Fallback: try to pass everything to main class
            main_known_fields = {
                f.name for f in main_class.__dataclass_fields__.values()
            }
            main_kwargs = {
                k: v for k, v in snake_dict.items() if k in main_known_fields
            }
            return main_class(**main_kwargs)

    return parser


def create_list_parser(item_class: type, item_parser: Optional[Any] = None) -> Any:
    """Create a parser for list/array responses.

    This pattern is used when API returns an array of items that need
    to be parsed individually.

    Args:
        item_class: The dataclass for individual items
        item_parser: Optional custom parser for items (defaults to simple field parser)

    Returns:
        Parser function that handles arrays of items

    Example:
        >>> parse_activities = create_list_parser(ActivitySummary)
        >>> activities = parse_activities(api_response)  # Returns List[ActivitySummary]
    """
    if item_parser is None:
        item_parser = create_simple_field_parser(item_class)

    def parser(data: Any) -> Any:
        if isinstance(data, list):
            return [item_parser(item) for item in data]
        elif isinstance(data, dict) and "activities" in data:
            # Handle wrapped arrays like {"activities": [...]}
            return [item_parser(item) for item in data["activities"]]
        else:
            # Single item
            return [item_parser(data)]

    return parser


def create_nested_summary_parser(
    main_class: type,
    summary_class: type,
    nested_key: str,
    raw_fields: Optional[List[str]] = None,
) -> Any:
    """Create a parser for nested summary + raw data pattern.

    This pattern is used when the summary data is nested inside a specific key
    in the API response, like Sleep where summary is in 'daily_sleep_dto'.

    Args:
        main_class: The main metric class
        summary_class: The summary dataclass
        nested_key: Key containing the nested summary data
        raw_fields: List of field names that contain raw data (default: empty)

    Returns:
        Parser function that handles nested summary extraction

    Example:
        >>> parse_sleep = create_nested_summary_parser(
        ...     Sleep, SleepSummary, 'daily_sleep_dto',
        ...     ["sleep_movement", "wellness_epoch_spo2_data_dto_list"]
        ... )
    """
    if raw_fields is None:
        raw_fields = []

    def parser(data: Dict[str, Any]) -> Any:
        # Convert camelCase to snake_case
        snake_dict = camel_to_snake_dict(data)

        # Ensure snake_dict is a dictionary before calling get()
        if not isinstance(snake_dict, dict):
            raise ValueError(
                f"Expected dict from camel_to_snake_dict but got {type(snake_dict).__name__}"
            )

        # Extract nested summary data
        nested_data = snake_dict.get(nested_key, {})

        # Create summary object with field filtering
        if not hasattr(summary_class, "__dataclass_fields__"):
            raise ValueError(f"summary_class {summary_class} is not a dataclass")
        summary_known_fields = {
            f.name for f in summary_class.__dataclass_fields__.values()
        }
        summary_kwargs = {
            k: v for k, v in nested_data.items() if k in summary_known_fields
        }
        summary_obj = summary_class(**summary_kwargs)

        # Determine summary field name in main class
        if not hasattr(main_class, "__dataclass_fields__"):
            raise ValueError(f"main_class {main_class} is not a dataclass")
        main_fields = {f.name for f in main_class.__dataclass_fields__.values()}
        summary_field_name = None
        for field_name in main_fields:
            if "summary" in field_name.lower():
                summary_field_name = field_name
                break

        if summary_field_name:
            # Create main object with summary and raw data
            main_kwargs = {summary_field_name: summary_obj}

            # Add raw fields from top level
            for raw_field in raw_fields:
                if raw_field in snake_dict:
                    main_kwargs[raw_field] = snake_dict[raw_field]

            # Add any remaining top-level fields that belong to main class
            for k, v in snake_dict.items():
                if k in main_fields and k != nested_key and k not in raw_fields:
                    main_kwargs[k] = v

            return main_class(**main_kwargs)
        else:
            # Fallback: try to pass everything to main class
            main_known_fields = {
                f.name for f in main_class.__dataclass_fields__.values()
            }
            main_kwargs = {
                k: v for k, v in snake_dict.items() if k in main_known_fields
            }
            return main_class(**main_kwargs)

    return parser
