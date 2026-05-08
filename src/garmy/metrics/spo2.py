"""SpO2 (Blood Oxygen Saturation) metric module.

This module provides access to Garmin SpO2 data using the auto-discovery
architecture. Includes daily summary (average, min, max) and hourly average
readings for timeseries storage.

Data Source:
    Garmin Connect API endpoint: /wellness-service/wellness/daily/spo2/{date}
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..core.base import MetricConfig
from ..core.utils import camel_to_snake_dict


@dataclass
class SpO2:
    """Daily SpO2 data from Garmin Connect API.

    Raw SpO2 data including daily averages and hourly readings throughout
    the day. All data comes directly from Garmin's wellness service.

    Attributes:
        calendar_date: Date string (YYYY-MM-DD)
        average_spo2: Daily average SpO2
        lowest_spo2: Lowest SpO2 reading
        latest_spo2: Most recent SpO2 reading
        avg_sleep_spo2: Average SpO2 during sleep
        last_seven_days_avg_spo2: Rolling 7-day average
        spo2_hourly_averages: Hourly average readings as [timestamp_ms, value] pairs

    Example:
        >>> spo2 = garmy.spo2.get()
        >>> print(f"Average SpO2: {spo2.average_spo2}%")
        >>> print(f"Lowest: {spo2.lowest_spo2}%")
        >>> print(f"Hourly readings: {len(spo2.spo2_hourly_averages)}")
    """

    calendar_date: str = ""
    average_spo2: Optional[float] = None
    lowest_spo2: Optional[int] = None
    latest_spo2: Optional[int] = None
    avg_sleep_spo2: Optional[float] = None
    last_seven_days_avg_spo2: Optional[float] = None
    spo2_hourly_averages: List[List[Any]] = field(default_factory=list)

    @property
    def readings_count(self) -> int:
        """Get number of hourly average readings."""
        return len(self.spo2_hourly_averages)

    @property
    def valid_readings_count(self) -> int:
        """Get number of valid hourly readings (excluding None values)."""
        return len(
            [
                reading
                for reading in self.spo2_hourly_averages
                if len(reading) >= 2 and reading[1] is not None
            ]
        )


def parse_spo2_data(data: Dict[str, Any]) -> SpO2:
    """Parse SpO2 API response into structured data."""
    snake_dict = camel_to_snake_dict(data)

    if not isinstance(snake_dict, dict):
        raise ValueError(
            f"Expected dictionary from API response but got {type(snake_dict).__name__}. "
            f"Raw data: {data}"
        )

    return SpO2(
        calendar_date=snake_dict.get("calendar_date", ""),
        average_spo2=snake_dict.get("average_sp_o2"),
        lowest_spo2=snake_dict.get("lowest_sp_o2"),
        latest_spo2=snake_dict.get("latest_sp_o2"),
        avg_sleep_spo2=snake_dict.get("avg_sleep_sp_o2"),
        last_seven_days_avg_spo2=snake_dict.get("last_seven_days_avg_sp_o2"),
        spo2_hourly_averages=snake_dict.get("sp_o2_hourly_averages") or [],
    )


# Declarative configuration for auto-discovery with custom parser
METRIC_CONFIG = MetricConfig(
    endpoint="/wellness-service/wellness/daily/spo2/{date}",
    metric_class=SpO2,
    parser=parse_spo2_data,
    description="Daily blood oxygen saturation with hourly average readings",
    version="1.0",
)

# Export for auto-discovery
__metric_config__ = METRIC_CONFIG
