"""Respiration Data Module.

========================

This module provides direct access to Garmin respiration data from the Connect API.
Data includes daily respiration summary, continuous respiration readings throughout the day,
and averaged respiration data for analysis.

Example:
    >>> from garmy import AuthClient, APIClient, MetricAccessorFactory
    >>> auth_client = AuthClient()
    >>> api_client = APIClient(auth_client=auth_client)
    >>> auth_client.login("email@example.com", "password")
    >>>
    >>> # Get today's respiration data
    >>> factory = MetricAccessorFactory(api_client)
    >>> metrics = factory.discover_and_create_all()
    >>> resp = metrics.get("respiration").get()
    >>> print(f"Avg Waking: {resp.avg_waking_respiration_value} bpm")
    >>> print(f"Avg Sleep: {resp.avg_sleep_respiration_value} bpm")
    >>> print(f"Readings: {resp.readings_count} measurements")

Data Source:
    Garmin Connect API endpoint: /wellness-service/wellness/daily/respiration/{date}
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

if TYPE_CHECKING:
    from datetime import date, datetime

from ..core.base import MetricConfig
from ..core.endpoint_builders import (
    build_respiration_endpoint as _build_respiration_endpoint,
)
from ..core.utils import (
    TimestampMixin,
    create_summary_raw_parser,
)


@dataclass
class RespirationSummary(TimestampMixin):
    """Main respiration data structure from Garmin API."""

    user_profile_pk: int = 0
    calendar_date: str = ""
    start_timestamp_gmt: str = ""
    end_timestamp_gmt: str = ""
    start_timestamp_local: str = ""
    end_timestamp_local: str = ""
    sleep_start_timestamp_gmt: str = ""
    sleep_end_timestamp_gmt: str = ""
    sleep_start_timestamp_local: str = ""
    sleep_end_timestamp_local: str = ""
    tomorrow_sleep_start_timestamp_gmt: Optional[str] = None
    tomorrow_sleep_end_timestamp_gmt: Optional[str] = None
    tomorrow_sleep_start_timestamp_local: Optional[str] = None
    tomorrow_sleep_end_timestamp_local: Optional[str] = None
    lowest_respiration_value: int = 0
    highest_respiration_value: int = 0
    avg_waking_respiration_value: int = 0
    avg_sleep_respiration_value: int = 0
    avg_tomorrow_sleep_respiration_value: Optional[int] = None
    respiration_version: int = 0

    @property
    def respiration_range(self) -> int:
        """Get respiration range (highest - lowest)."""
        return self.highest_respiration_value - self.lowest_respiration_value

    @property
    def waking_vs_sleep_difference(self) -> int:
        """Get difference between waking and sleep respiration rates."""
        return self.avg_waking_respiration_value - self.avg_sleep_respiration_value

    @property
    def sleep_start_datetime_gmt(self) -> Optional["datetime"]:
        """Convert GMT sleep start timestamp to datetime."""
        return self.iso_to_datetime(self.sleep_start_timestamp_gmt)

    @property
    def sleep_end_datetime_gmt(self) -> Optional["datetime"]:
        """Convert GMT sleep end timestamp to datetime."""
        return self.iso_to_datetime(self.sleep_end_timestamp_gmt)

    @property
    def sleep_start_datetime_local(self) -> Optional["datetime"]:
        """Convert local sleep start timestamp to datetime."""
        return self.iso_to_datetime(self.sleep_start_timestamp_local)

    @property
    def sleep_end_datetime_local(self) -> Optional["datetime"]:
        """Convert local sleep end timestamp to datetime."""
        return self.iso_to_datetime(self.sleep_end_timestamp_local)


@dataclass
class Respiration:
    """Daily respiration data from Garmin Connect API.

    Raw respiration data including continuous readings throughout the day,
    averaged period data, daily summary statistics, and sleep respiration patterns.
    All data comes directly from Garmin's wellness service.

    Attributes:
        respiration_summary: Main respiration summary with daily stats and timestamps
        respiration_values_array: Raw detailed respiration readings
            (list of [timestamp, value] pairs)
        respiration_averages_values_array: Raw averaged respiration data
            (list of [timestamp, avg, high, low] arrays)
        respiration_value_descriptors_dto_list: Raw descriptors for readings format
        respiration_averages_value_descriptor_dto_list: Raw descriptors for averages format

    Example:
        >>> resp = garmy.respiration.get()
        >>> print(f"Waking: {resp.respiration_summary.avg_waking_respiration_value} bpm")
        >>> print(f"Sleep: {resp.respiration_summary.avg_sleep_respiration_value} bpm")
        >>> print(f"Range: {resp.respiration_summary.respiration_range} bpm")
        >>>
        >>> # Access raw readings
        >>> for reading in resp.respiration_values_array[:10]:
        >>>     timestamp, value = reading[0], reading[1]
        >>>     if value != -1:  # Valid reading
        >>>         print(f"Respiration: {value} bpm")
    """

    respiration_summary: RespirationSummary
    respiration_values_array: List[List[Any]] = field(default_factory=list)
    respiration_averages_values_array: List[List[Any]] = field(default_factory=list)
    respiration_value_descriptors_dto_list: List[Dict[str, Any]] = field(
        default_factory=list
    )
    respiration_averages_value_descriptor_dto_list: List[Dict[str, Any]] = field(
        default_factory=list
    )

    @property
    def readings_count(self) -> int:
        """Get number of respiration readings."""
        return len(self.respiration_values_array)

    @property
    def valid_readings_count(self) -> int:
        """Get number of valid respiration readings (excluding -1 values)."""
        return len(
            [
                reading
                for reading in self.respiration_values_array
                if len(reading) >= 2 and reading[1] != -1
            ]
        )

    @property
    def averages_count(self) -> int:
        """Get number of averaged respiration periods."""
        return len(self.respiration_averages_values_array)


# Create parser using factory function for summary + raw data
parse_respiration_data = create_summary_raw_parser(
    Respiration,
    RespirationSummary,
    [
        "respiration_values_array",
        "respiration_averages_values_array",
        "respiration_value_descriptors_dto_list",
        "respiration_averages_value_descriptor_dto_list",
    ],
)


def build_respiration_endpoint(
    date_input: Union["date", str, None] = None, api_client: Any = None, **kwargs: Any
) -> str:
    """Build the Respiration API endpoint with user ID and date."""
    return _build_respiration_endpoint(date_input, api_client, **kwargs)


# MetricConfig for auto-discovery
METRIC_CONFIG = MetricConfig(
    endpoint="/wellness-service/wellness/daily/respiration/{date}",
    metric_class=Respiration,
    parser=parse_respiration_data,
    requires_user_id=False,
    description="Daily respiration data including continuous readings and averages",
    version="1.0",
)

__metric_config__ = METRIC_CONFIG
