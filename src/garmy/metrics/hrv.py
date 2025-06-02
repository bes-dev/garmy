"""
Heart Rate Variability (HRV) metric module.

This module provides access to Garmin HRV data using the new auto-discovery
architecture. It contains the data class definitions, custom parser, and
metric configuration for auto-discovery.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..core.base import MetricConfig
from ..core.utils import TimestampMixin, camel_to_snake_dict


@dataclass
class HRVBaseline:
    """HRV baseline values from Garmin API."""

    low_upper: int
    balanced_low: int
    balanced_upper: int
    marker_value: float


@dataclass
class HRVSummary:
    """Daily HRV summary from Garmin API."""

    calendar_date: str
    weekly_avg: int
    last_night_avg: int
    last_night_5_min_high: int
    baseline: HRVBaseline
    status: str
    feedback_phrase: str
    create_time_stamp: str

    @property
    def date(self) -> datetime:
        """Convert calendar_date to datetime object."""
        return datetime.strptime(self.calendar_date, "%Y-%m-%d")


@dataclass
class HRVReading(TimestampMixin):
    """Individual HRV reading from Garmin API."""

    hrv_value: int
    reading_time_gmt: str
    reading_time_local: str

    @property
    def datetime_gmt(self) -> Optional[datetime]:
        """Convert GMT reading time to datetime object."""
        return self.iso_to_datetime(self.reading_time_gmt)

    @property
    def datetime_local(self) -> Optional[datetime]:
        """Convert local reading time to datetime object."""
        return self.iso_to_datetime(self.reading_time_local)


def parse_hrv_data(data: Dict[str, Any]) -> "HRV":
    """Parse HRV API response into structured data."""
    # Convert camelCase keys to snake_case recursively
    snake_dict = camel_to_snake_dict(data)

    # Ensure we have a dictionary to work with
    if not isinstance(snake_dict, dict):
        raise ValueError(
            f"Expected dictionary from API response but got {type(snake_dict).__name__}. "
            f"Raw data: {data}"
        )

    # Parse HRV summary
    hrv_summary_data = snake_dict.get("hrv_summary", {})
    baseline_data = hrv_summary_data.get("baseline", {})

    baseline = HRVBaseline(
        low_upper=baseline_data.get("low_upper", 0),
        balanced_low=baseline_data.get("balanced_low", 0),
        balanced_upper=baseline_data.get("balanced_upper", 0),
        marker_value=baseline_data.get("marker_value", 0.0),
    )

    hrv_summary = HRVSummary(
        calendar_date=hrv_summary_data.get("calendar_date", ""),
        weekly_avg=hrv_summary_data.get("weekly_avg", 0),
        last_night_avg=hrv_summary_data.get("last_night_avg", 0),
        last_night_5_min_high=hrv_summary_data.get("last_night_5_min_high", 0),
        baseline=baseline,
        status=hrv_summary_data.get("status", ""),
        feedback_phrase=hrv_summary_data.get("feedback_phrase", ""),
        create_time_stamp=hrv_summary_data.get("create_time_stamp", ""),
    )

    # Parse HRV readings
    hrv_readings = []
    for reading_data in snake_dict.get("hrv_readings", []):
        reading = HRVReading(
            hrv_value=reading_data.get("hrv_value", 0),
            reading_time_gmt=reading_data.get("reading_time_gmt", ""),
            reading_time_local=reading_data.get("reading_time_local", ""),
        )
        hrv_readings.append(reading)

    return HRV(
        user_profile_pk=snake_dict.get("user_profile_pk", 0),
        hrv_summary=hrv_summary,
        hrv_readings=hrv_readings,
        start_timestamp_gmt=snake_dict.get("start_timestamp_gmt"),
        end_timestamp_gmt=snake_dict.get("end_timestamp_gmt"),
        start_timestamp_local=snake_dict.get("start_timestamp_local"),
        end_timestamp_local=snake_dict.get("end_timestamp_local"),
        sleep_start_timestamp_gmt=snake_dict.get("sleep_start_timestamp_gmt"),
        sleep_end_timestamp_gmt=snake_dict.get("sleep_end_timestamp_gmt"),
        sleep_start_timestamp_local=snake_dict.get("sleep_start_timestamp_local"),
        sleep_end_timestamp_local=snake_dict.get("sleep_end_timestamp_local"),
    )


@dataclass
class HRV:
    """Daily HRV data from Garmin Connect API.

    Raw HRV data including summary metrics and individual readings collected
    during sleep periods. All data comes directly from Garmin's HRV service.

    Attributes:
        user_profile_pk: User profile primary key
        hrv_summary: Daily HRV summary with status and averages
        hrv_readings: Individual HRV readings throughout the sleep period
        start_timestamp_gmt: Sleep period start time (GMT)
        end_timestamp_gmt: Sleep period end time (GMT)
        start_timestamp_local: Sleep period start time (local)
        end_timestamp_local: Sleep period end time (local)
        sleep_start_timestamp_gmt: Actual sleep start time (GMT)
        sleep_end_timestamp_gmt: Actual sleep end time (GMT)
        sleep_start_timestamp_local: Actual sleep start time (local)
        sleep_end_timestamp_local: Actual sleep end time (local)

    Example:
        >>> hrv = garmy.hrv.get()
        >>> print(f"Status: {hrv.hrv_summary.status}")
        >>> print(f"Average: {hrv.hrv_summary.last_night_avg}ms")
        >>> print(f"Readings: {len(hrv.hrv_readings)}")
    """

    user_profile_pk: int
    hrv_summary: HRVSummary
    hrv_readings: List[HRVReading]
    start_timestamp_gmt: Optional[str] = None
    end_timestamp_gmt: Optional[str] = None
    start_timestamp_local: Optional[str] = None
    end_timestamp_local: Optional[str] = None
    sleep_start_timestamp_gmt: Optional[str] = None
    sleep_end_timestamp_gmt: Optional[str] = None
    sleep_start_timestamp_local: Optional[str] = None
    sleep_end_timestamp_local: Optional[str] = None


# Declarative configuration for auto-discovery with custom parser
METRIC_CONFIG = MetricConfig(
    endpoint="/hrv-service/hrv/{date}",
    metric_class=HRV,
    parser=parse_hrv_data,
    description="Daily heart rate variability data with readings and baseline",
    version="1.0",
)

# Export for auto-discovery
__metric_config__ = METRIC_CONFIG
