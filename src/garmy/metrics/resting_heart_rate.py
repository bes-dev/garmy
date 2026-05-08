"""Resting Heart Rate metric module.

This module provides access to the dedicated Garmin resting heart rate endpoint
using the auto-discovery architecture. This endpoint provides the single resting
HR value computed each morning, separate from the general heart rate endpoint.

Data Source:
    Garmin Connect API endpoint:
    /userstats-service/wellness/daily/{display_name}?fromDate={date}&untilDate={date}
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from ..core.base import MetricConfig
from ..core.endpoint_builders import build_resting_heart_rate_endpoint


@dataclass
class RestingHeartRate:
    """Dedicated resting heart rate data from Garmin Connect API.

    The single resting HR value Garmin computes each morning, sourced from
    the user stats service rather than the general heart rate endpoint.

    Attributes:
        calendar_date: Date string (YYYY-MM-DD)
        value: Resting heart rate in bpm

    Example:
        >>> rhr = garmy.resting_heart_rate.get()
        >>> print(f"Resting HR: {rhr.value} bpm")
    """

    calendar_date: str = ""
    value: Optional[int] = None


def parse_resting_heart_rate_data(data: Dict[str, Any]) -> RestingHeartRate:
    """Parse resting heart rate API response into structured data.

    The API response is deeply nested with uppercase keys
    (allMetrics.metricsMap.WELLNESS_RESTING_HEART_RATE), so camel_to_snake_dict
    is not used here — the structure requires manual navigation.
    """
    if not isinstance(data, dict):
        raise ValueError(
            f"Expected dictionary from API response but got {type(data).__name__}. "
            f"Raw data: {data}"
        )

    calendar_date = ""
    value = None

    # Navigate nested response structure
    all_metrics = data.get("allMetrics", {})
    metrics_map = (
        all_metrics.get("metricsMap", {}) if isinstance(all_metrics, dict) else {}
    )
    rhr_entries = metrics_map.get("WELLNESS_RESTING_HEART_RATE", [])

    if rhr_entries and isinstance(rhr_entries, list):
        # Take the first (and typically only) entry
        entry = rhr_entries[0]
        if isinstance(entry, dict):
            calendar_date = entry.get("calendarDate", "")
            value = entry.get("value")
            if value is not None:
                try:
                    value = int(value)
                except (ValueError, TypeError):
                    value = None

    return RestingHeartRate(
        calendar_date=calendar_date,
        value=value,
    )


# Declarative configuration for auto-discovery with endpoint builder
METRIC_CONFIG = MetricConfig(
    endpoint="/userstats-service/wellness/daily",
    metric_class=RestingHeartRate,
    parser=parse_resting_heart_rate_data,
    endpoint_builder=build_resting_heart_rate_endpoint,
    requires_user_id=True,
    description="Dedicated resting heart rate from user stats service",
    version="1.0",
)

# Export for auto-discovery
__metric_config__ = METRIC_CONFIG
