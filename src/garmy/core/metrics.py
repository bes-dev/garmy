r"""
Metric framework for direct metric data access.

This module provides the MetricAccessor base class for direct access to metric data
from the Garmin Connect API. It handles common operations like date formatting,
concurrent requests, and data transformation.

Classes:
    MetricAccessor: Base class providing get(), list(), and raw() methods for metrics.

Example:
    >>> from .metrics import MetricAccessor, TrainingReadiness
    >>> accessor = MetricAccessor(
    ...     api_client, TrainingReadiness,
    ...     "/metrics-service/metrics/trainingreadiness/{date}"
    ... )
    >>> readiness = accessor.get("2023-12-01")
"""

import contextlib
import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Type, Union

if TYPE_CHECKING:
    from .client import APIClient
from .config import Concurrency, Timeouts, get_config
from .utils import (
    camel_to_snake_dict,
    format_date,
    handle_api_exception,
)


class MetricHttpClient:
    """Handles HTTP requests for metric data.

    This class is responsible solely for making HTTP requests to metric endpoints
    and returning raw API responses.
    """

    def __init__(self, api_client: "APIClient"):
        """Initialize the HTTP client.

        Args:
            api_client: The API client for making requests.
        """
        self.api_client = api_client

    def fetch_raw_data(
        self,
        endpoint: str,
        date_input: Union[date, str, None] = None,
        endpoint_builder: Optional[Callable[..., str]] = None,
        **kwargs: Any,
    ) -> Any:
        """Fetch raw data from a metric endpoint.

        Args:
            endpoint: API endpoint pattern with optional {date} placeholder.
            date_input: Date for the request.
            endpoint_builder: Optional function to build dynamic endpoints.
            **kwargs: Additional parameters for endpoint_builder.

        Returns:
            Raw API response data.
        """
        if endpoint_builder:
            final_endpoint = endpoint_builder(
                date_input=date_input, api_client=self.api_client, **kwargs
            )
        else:
            date_str = format_date(date_input)
            final_endpoint = endpoint.format(date=date_str)

        try:
            return self.api_client.connectapi(final_endpoint)
        except Exception as e:
            return handle_api_exception(e, "fetching metric data", final_endpoint, [])


class MetricDataParser:
    """Handles parsing of metric API responses.

    This class is responsible for converting raw API responses into
    structured metric objects.
    """

    def __init__(
        self, metric_class: Type[Any], parse_func: Optional[Callable[[Any], Any]] = None
    ):
        """Initialize the data parser.

        Args:
            metric_class: The metric data class to create instances of.
            parse_func: Optional custom parsing function.
        """
        self.metric_class = metric_class
        self.parse_func = parse_func or self._default_parse

    def parse(self, data: Any) -> Union[Any, List[Any], None]:
        """Parse raw API response data into metric objects.

        Args:
            data: Raw API response data.

        Returns:
            Parsed metric instance(s) or None if no data.
        """
        if not data:
            return None
        return self.parse_func(data)

    def _default_parse(self, data: Any) -> Union[Any, List[Any]]:
        """Parse data using standard camelCase to snake_case conversion.

        Args:
            data: Raw API response data (dict or list of dicts).

        Returns:
            Parsed metric instance(s).
        """
        if isinstance(data, list):
            return [self._parse_single_item(item) for item in data]
        else:
            return self._parse_single_item(data)

    def _parse_single_item(self, item: Dict[str, Any]) -> Any:
        """Parse a single item using camel_to_snake_dict utility.

        Args:
            item: Single dictionary item from API response.

        Returns:
            Instance of the metric class with parsed data.
        """
        # Use the unified camel_to_snake_dict utility
        snake_dict = camel_to_snake_dict(item)
        # Ensure we have a dictionary to work with
        if not isinstance(snake_dict, dict):
            raise ValueError(f"Expected dict but got {type(snake_dict)}")

        # Handle common datetime fields
        for field in ("timestamp", "timestamp_local"):
            if field in snake_dict and isinstance(snake_dict[field], str):
                with contextlib.suppress(ValueError):
                    snake_dict[field] = datetime.fromisoformat(
                        snake_dict[field].replace("Z", "+00:00")
                    )

        # Gracefully handle unknown fields
        known_fields = {f.name for f in self.metric_class.__dataclass_fields__.values()}
        filtered_kwargs = {k: v for k, v in snake_dict.items() if k in known_fields}

        return self.metric_class(**filtered_kwargs)


class MetricConcurrencyManager:
    """Manages concurrent requests for metric data.

    This class handles the execution of multiple concurrent requests
    to improve performance when fetching data for multiple dates.
    Implements proper resource management and optimal threading.
    """

    def __init__(self, max_workers: Optional[int] = None):
        """Initialize the concurrency manager.

        Args:
            max_workers: Maximum number of concurrent workers. If None, automatically
                determines optimal worker count based on CPU cores and I/O characteristics.
        """
        self.max_workers = self._determine_optimal_workers(max_workers)

    def _determine_optimal_workers(self, max_workers: Optional[int]) -> int:
        """Determine optimal number of workers for concurrent requests.

        Args:
            max_workers: User-specified worker count or None for auto-detection.

        Returns:
            Optimal number of workers for I/O-bound metric requests.
        """
        config = get_config()

        if max_workers is not None:
            return max(Concurrency.MIN_WORKERS, min(max_workers, config.max_workers))

        # For I/O-bound metric requests, optimal workers = CPU cores * 2-4
        # But also consider environment variables and system constraints
        cpu_count = os.cpu_count() or Concurrency.OPTIMAL_MIN_WORKERS

        # Check for environment variable override
        env_workers = os.environ.get("GARMY_MAX_WORKERS")
        if env_workers:
            with contextlib.suppress(ValueError):
                return max(
                    Concurrency.MIN_WORKERS, min(int(env_workers), config.max_workers)
                )

        # Calculate optimal workers: CPU cores * 3 for I/O-bound operations
        # But cap between configured min and max for reasonable resource usage
        optimal = max(
            config.optimal_min_workers,
            min(cpu_count * Concurrency.CPU_MULTIPLIER, config.optimal_max_workers),
        )
        return optimal

    def fetch_multiple_dates(
        self, fetch_function: Callable[[date], Any], dates: List[date]
    ) -> List[Any]:
        """Fetch data for multiple dates concurrently.

        Args:
            fetch_function: Function that fetches data for a single date.
            dates: List of dates to fetch data for.

        Returns:
            List of results from all dates, flattened if necessary.
        """
        # Handle single date case
        if len(dates) == 1:
            return self._fetch_single_date(fetch_function, dates[0])

        # Handle multiple dates with concurrency
        raw_results = self._fetch_concurrent(fetch_function, dates)
        return self._flatten_results(raw_results)

    def _fetch_single_date(
        self, fetch_function: Callable[[date], Any], target_date: date
    ) -> List[Any]:
        """Fetch data for a single date without threading overhead.

        Args:
            fetch_function: Function that fetches data for a single date.
            target_date: The date to fetch data for.

        Returns:
            List containing the single result or empty list if no data.
        """
        data = fetch_function(target_date)
        return [data] if data else []

    def _fetch_concurrent(
        self, fetch_function: Callable[[date], Any], dates: List[date]
    ) -> List[Any]:
        """Execute concurrent requests for multiple dates with proper resource management.

        Uses ThreadPoolExecutor with context management to ensure proper cleanup
        and implements timeout handling to prevent hanging requests.

        Args:
            fetch_function: Function that fetches data for a single date.
            dates: List of dates to fetch data for.

        Returns:
            List of raw results from all concurrent requests.
        """
        max_workers = min(len(dates), self.max_workers)
        results = [None] * len(dates)  # Pre-allocate results list

        # Use context manager to ensure proper cleanup
        with ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="garmy-metric"
        ) as executor:
            try:
                # Submit all tasks and collect futures
                future_to_index = {
                    executor.submit(fetch_function, date_val): i
                    for i, date_val in enumerate(dates)
                }

                # Process completed futures with timeout handling
                for future in as_completed(
                    future_to_index.keys(), timeout=Timeouts.THREAD_POOL_SHUTDOWN
                ):
                    index = future_to_index[future]
                    try:
                        results[index] = future.result(timeout=Timeouts.INDIVIDUAL_TASK)
                    except Exception as exc:
                        # Log the error but continue with other requests
                        logging.warning(
                            f"Request for date {dates[index]} failed: {exc}"
                        )
                        results[index] = None

            except Exception as e:
                logging.error(f"Concurrent fetch operation failed: {e}")
                # Cancel any remaining futures to clean up
                for future in future_to_index:
                    future.cancel()
                raise

        return results

    def _flatten_results(self, results: List[Any]) -> List[Any]:
        """Flatten and filter results from concurrent requests.

        Args:
            results: List of results that may contain nested lists or None values.

        Returns:
            Flattened list of all valid results.
        """
        all_data = []
        for result in results:
            if result:
                if isinstance(result, list):
                    all_data.extend(result)
                else:
                    all_data.append(result)
        return all_data


class MetricAccessor:
    """Thread-safe orchestrator for metric data access using composition of specialized components.

    This class uses the Single Responsibility Principle by delegating specific
    tasks to specialized components:
    - MetricHttpClient: Handles HTTP requests
    - MetricDataParser: Handles data parsing
    - MetricConcurrencyManager: Handles concurrent operations

    Implements thread-safety for concurrent access to shared resources.

    Args:
        api_client: The API client instance for making requests.
        metric_class: The metric data class that defines the data structure.
        endpoint: API endpoint pattern, may include {date} placeholder.
        parse_func: Optional custom parsing function for API responses.
        endpoint_builder: Optional function to build dynamic endpoints.

    Attributes:
        endpoint: The API endpoint pattern.
        endpoint_builder: Optional endpoint builder function.
        http_client: Component handling HTTP requests.
        parser: Component handling data parsing.
        concurrency_manager: Component handling concurrent operations.
    """

    def __init__(
        self,
        api_client: "APIClient",
        metric_class: Type[Any],
        endpoint: str,
        parse_func: Optional[Callable[[Any], Any]] = None,
        endpoint_builder: Optional[Callable[..., str]] = None,
        max_workers: Optional[int] = None,
    ) -> None:
        """Initialize the metric accessor with composed components.

        Args:
            api_client: The API client for making requests.
            metric_class: The data class representing the metric structure.
            endpoint: API endpoint pattern with optional {date} placeholder.
            parse_func: Optional custom parsing function. If None, uses default parsing.
            endpoint_builder: Optional function to build dynamic endpoints with custom parameters.
            max_workers: Maximum concurrent workers for multi-date requests. If None,
                automatically determines optimal count based on CPU cores.
        """
        self.endpoint = endpoint
        self.endpoint_builder = endpoint_builder

        # Thread-safe initialization lock
        self._init_lock = threading.RLock()

        # Compose with specialized components following SRP
        with self._init_lock:
            self.http_client = MetricHttpClient(api_client)
            self.parser = MetricDataParser(metric_class, parse_func)
            self.concurrency_manager = MetricConcurrencyManager(max_workers)

        # Keep reference to metric class for compatibility
        self.metric_class = metric_class

        # Optional simple cache for repeated requests (thread-safe)
        self._cache_lock = threading.RLock()
        self._cache: Dict[Any, Any] = {}
        self._cache_enabled = (
            os.environ.get("GARMY_ENABLE_CACHE", "false").lower() == "true"
        )

    def raw(self, date_input: Union[date, str, None] = None, **kwargs: Any) -> Any:
        """Get raw API response without parsing (thread-safe with optional caching).

        Delegates to the HTTP client component to fetch raw data.
        Implements optional thread-safe caching for performance.

        Args:
            date_input: Date for the request. Can be a date object, ISO date string,
                or None for today's date.
            **kwargs: Additional parameters passed to endpoint_builder if available.

        Returns:
            Raw API response data (usually a dict or list).
            Returns empty list if request fails.
        """
        # Create cache key if caching is enabled
        if self._cache_enabled:
            # Normalize date_input for consistent caching
            normalized_date = (
                format_date(date_input) if date_input else format_date(date.today())
            )
            cache_key = (self.endpoint, normalized_date, tuple(sorted(kwargs.items())))

            # Double-checked locking to prevent race conditions
            # First check without acquiring write lock
            with self._cache_lock:
                if cache_key in self._cache:
                    return self._cache[cache_key]

                # If not in cache, acquire write lock and check again
                # This prevents multiple threads from fetching the same data
                if cache_key in self._cache:
                    return self._cache[cache_key]

                # Fetch data from API while holding the lock
                result = self.http_client.fetch_raw_data(
                    self.endpoint, date_input, self.endpoint_builder, **kwargs
                )

                # Cache result immediately
                if result:
                    # Limit cache size to prevent memory issues
                    config = get_config()
                    if len(self._cache) > config.metric_cache_size:
                        # Remove oldest entries (simple FIFO)
                        oldest_key = next(iter(self._cache))
                        del self._cache[oldest_key]
                    self._cache[cache_key] = result

                return result

        # No caching - fetch directly
        return self.http_client.fetch_raw_data(
            self.endpoint, date_input, self.endpoint_builder, **kwargs
        )

    def get(
        self, date_input: Union[date, str, None] = None, **kwargs: Any
    ) -> Union[Any, List[Any], None]:
        """Get parsed metric data for a single date.

        Combines HTTP client for data fetching and parser for data transformation.

        Args:
            date_input: Date for the request. Can be a date object, ISO date string,
                or None for today's date.
            **kwargs: Additional parameters passed to endpoint_builder if available.

        Returns:
            Parsed metric instance(s) or None if no data available.
            Can return a single object or list depending on the API response.
        """
        raw_data = self.raw(date_input, **kwargs)
        return self.parser.parse(raw_data)

    def list(self, end: Union[date, str, None] = None, days: int = 7) -> List[Any]:
        """Get metric data for multiple days.

        Uses the concurrency manager for efficient parallel data fetching.

        Args:
            end: End date for the range. Can be a date object, ISO date string,
                or None for today's date.
            days: Number of days to fetch (going backwards from end date).

        Returns:
            List of parsed metric instances from all requested dates.
            Empty list if no data is available.
        """
        if end is None:
            end = date.today()
        elif isinstance(end, str):
            end = datetime.strptime(end, "%Y-%m-%d").date()

        # Generate date range
        dates = [end - timedelta(days=i) for i in range(days)]

        # Delegate to concurrency manager for efficient parallel fetching
        return self.concurrency_manager.fetch_multiple_dates(self.get, dates)

    def clear_cache(self) -> None:
        """Clear the thread-safe cache (if caching is enabled).

        This method is useful for testing or when you need to force fresh data.
        """
        if self._cache_enabled:
            with self._cache_lock:
                self._cache.clear()

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics (thread-safe).

        Returns:
            Dictionary with cache size and enabled status.
        """
        if not self._cache_enabled:
            return {"enabled": False, "size": 0}

        with self._cache_lock:
            return {"enabled": True, "size": len(self._cache)}
