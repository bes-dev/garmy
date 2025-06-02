"""Heart Rate Data Module.

=======================

This module provides direct access to Garmin heart rate data from the Connect API.
Data includes daily heart rate summary and continuous heart rate readings throughout the day.

Example:
    >>> from garmy import AuthClient, APIClient, MetricAccessorFactory
    >>> auth_client = AuthClient()
    >>> api_client = APIClient(auth_client=auth_client)
    >>> auth_client.login("email@example.com", "password")
    >>>
    >>> # Get today's heart rate data
    >>> factory = MetricAccessorFactory(api_client)
    >>> metrics = factory.discover_and_create_all()
    >>> hr = metrics.get("heart_rate").get()
    >>> print(f"Resting HR: {hr.heart_rate_summary.resting_heart_rate} bpm")
    >>> print(f"Max HR: {hr.heart_rate_summary.max_heart_rate} bpm")
    >>> print(f"Readings: {hr.readings_count} measurements")

Data Source:
    Garmin Connect API endpoint: /wellness-service/wellness/dailyHeartRate
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

if TYPE_CHECKING:
    from datetime import date, datetime

from ..core.base import MetricConfig
from ..core.endpoint_builders import (
    build_heart_rate_endpoint as _build_heart_rate_endpoint,
)
from ..core.utils import (
    TimestampMixin,
    create_summary_raw_parser,
)


@dataclass
class HeartRateSummary(TimestampMixin):
    """Main heart rate data structure from Garmin API."""

    user_profile_pk: int = 0
    calendar_date: str = ""
    start_timestamp_gmt: str = ""
    end_timestamp_gmt: str = ""
    start_timestamp_local: str = ""
    end_timestamp_local: str = ""
    max_heart_rate: int = 0
    min_heart_rate: int = 0
    resting_heart_rate: int = 0
    last_seven_days_avg_resting_heart_rate: int = 0

    @property
    def heart_rate_range(self) -> int:
        """Get heart rate range (max - min)."""
        return self.max_heart_rate - self.min_heart_rate

    @property
    def start_datetime_gmt(self) -> Optional["datetime"]:
        """Convert GMT start timestamp to datetime."""
        return self.iso_to_datetime(self.start_timestamp_gmt)

    @property
    def end_datetime_gmt(self) -> Optional["datetime"]:
        """Convert GMT end timestamp to datetime."""
        return self.iso_to_datetime(self.end_timestamp_gmt)

    @property
    def start_datetime_local(self) -> Optional["datetime"]:
        """Convert local start timestamp to datetime."""
        return self.iso_to_datetime(self.start_timestamp_local)

    @property
    def end_datetime_local(self) -> Optional["datetime"]:
        """Convert local end timestamp to datetime."""
        return self.iso_to_datetime(self.end_timestamp_local)


@dataclass
class HeartRate:
    """Daily heart rate data from Garmin Connect API.

    Raw heart rate data including continuous readings throughout the day
    and daily summary statistics. All data comes directly from Garmin's wellness service.

    Attributes:
        heart_rate_summary: Main heart rate summary with daily stats and timestamps
        heart_rate_values_array: Raw heart rate readings (list of [timestamp, heartrate] pairs)
        heart_rate_value_descriptors: Raw descriptors for heart rate data format

    Example:
        >>> hr = garmy.heart_rate.get()
        >>> print(f"Resting HR: {hr.heart_rate_summary.resting_heart_rate} bpm")
        >>> print(f"Range: {hr.heart_rate_summary.heart_rate_range} bpm")
        >>> print(f"Average: {hr.average_heart_rate:.1f} bpm")
        >>>
        >>> # Access raw readings
        >>> for reading in hr.heart_rate_values_array[:10]:
        >>>     timestamp, heart_rate = reading[0], reading[1]
        >>>     print(f"HR: {heart_rate} bpm")
    """

    heart_rate_summary: HeartRateSummary
    heart_rate_values_array: List[List[Any]] = field(default_factory=list)
    heart_rate_value_descriptors: List[Dict[str, Any]] = field(default_factory=list)

    def __str__(self) -> str:
        """Format heart rate data for human-readable display."""
        lines = []
        if (
            hasattr(self.heart_rate_summary, "resting_heart_rate")
            and self.heart_rate_summary.resting_heart_rate
        ):
            lines.append(
                f"• Resting HR: {self.heart_rate_summary.resting_heart_rate} bpm"
            )
        if (
            hasattr(self.heart_rate_summary, "max_heart_rate")
            and self.heart_rate_summary.max_heart_rate
        ):
            lines.append(f"• Max HR: {self.heart_rate_summary.max_heart_rate} bpm")
        if (
            hasattr(self.heart_rate_summary, "heart_rate_range")
            and self.heart_rate_summary.heart_rate_range
        ):
            lines.append(f"• HR range: {self.heart_rate_summary.heart_rate_range} bpm")
        if self.average_heart_rate:
            lines.append(f"• Average HR: {self.average_heart_rate:.1f} bpm")
        if self.readings_count:
            lines.append(f"• Readings: {self.readings_count} data points")

        return "\n".join(lines) if lines else "Heart rate data available"

    @property
    def readings_count(self) -> int:
        """Get number of heart rate readings."""
        return len(self.heart_rate_values_array)

    @property
    def average_heart_rate(self) -> float:
        """Calculate average heart rate from all readings."""
        if not self.heart_rate_values_array:
            return 0.0
        valid_readings = [
            reading[1]
            for reading in self.heart_rate_values_array
            if len(reading) >= 2 and reading[1] is not None
        ]
        if not valid_readings:
            return 0.0
        return float(sum(valid_readings)) / len(valid_readings)


# Create parser using factory function for summary + raw data
parse_heart_rate_data = create_summary_raw_parser(
    HeartRate, HeartRateSummary, ["heart_rate_values", "heart_rate_value_descriptors"]
)


def build_heart_rate_endpoint(
    date_input: Union["date", str, None] = None, api_client: Any = None, **kwargs: Any
) -> str:
    """Build the HeartRate API endpoint with user ID and date."""
    return _build_heart_rate_endpoint(date_input, api_client, **kwargs)


# MetricConfig for auto-discovery
METRIC_CONFIG = MetricConfig(
    endpoint="",
    metric_class=HeartRate,
    parser=parse_heart_rate_data,
    endpoint_builder=build_heart_rate_endpoint,
    requires_user_id=True,
    description="Daily heart rate data including continuous readings and summary statistics",
    version="1.0",
)

__metric_config__ = METRIC_CONFIG
