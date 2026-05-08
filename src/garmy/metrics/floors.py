"""Floors metric module.

This module provides access to Garmin floors climbed data using the
auto-discovery architecture. The API returns a time series of floor values
which must be summed to produce daily totals.

Data Source:
    Garmin Connect API endpoint: /wellness-service/wellness/floorsChartData/daily/{date}
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ..core.base import MetricConfig
from ..core.utils import camel_to_snake_dict


@dataclass
class Floors:
    """Daily floors data from Garmin Connect API.

    Floors climbed and descended during the day, computed from the watch
    barometer. The API returns an array of readings that must be summed.

    Attributes:
        calendar_date: Date string (YYYY-MM-DD)
        floors_ascended: Total floors climbed during the day
        floors_descended: Total floors descended during the day

    Example:
        >>> floors = garmy.floors.get()
        >>> print(f"Climbed: {floors.floors_ascended} floors")
        >>> print(f"Descended: {floors.floors_descended} floors")
    """

    calendar_date: str = ""
    floors_ascended: Optional[int] = None
    floors_descended: Optional[int] = None


def parse_floors_data(data: Dict[str, Any]) -> Floors:
    """Parse floors chart API response into structured data.

    The API returns floorValuesArray with [timestamp_ms, ascended, descended]
    triples. Daily totals are computed by summing the array.
    """
    snake_dict = camel_to_snake_dict(data)

    if not isinstance(snake_dict, dict):
        raise ValueError(
            f"Expected dictionary from API response but got {type(snake_dict).__name__}. "
            f"Raw data: {data}"
        )

    # Extract calendar date from startTimestampGMT or fallback
    calendar_date = snake_dict.get("calendar_date", "")
    if not calendar_date:
        # Try to derive from startTimestampGMT
        start_ts = snake_dict.get("start_timestamp_gmt") or snake_dict.get(
            "start_timestamp_local"
        )
        if start_ts and isinstance(start_ts, str):
            # ISO format: take date portion
            calendar_date = start_ts[:10]

    # Sum floor values from the array
    floor_values = snake_dict.get("floor_values_array") or []
    floors_ascended = None
    floors_descended = None

    if floor_values:
        total_ascended = 0
        total_descended = 0
        has_data = False

        for entry in floor_values:
            if isinstance(entry, (list, tuple)) and len(entry) >= 3:
                ascended = entry[1]
                descended = entry[2]
                try:
                    if ascended is not None:
                        total_ascended += int(ascended)
                        has_data = True
                except (ValueError, TypeError):
                    pass
                try:
                    if descended is not None:
                        total_descended += int(descended)
                        has_data = True
                except (ValueError, TypeError):
                    pass

        if has_data:
            floors_ascended = total_ascended
            floors_descended = total_descended

    return Floors(
        calendar_date=calendar_date,
        floors_ascended=floors_ascended,
        floors_descended=floors_descended,
    )


# Declarative configuration for auto-discovery with custom parser
METRIC_CONFIG = MetricConfig(
    endpoint="/wellness-service/wellness/floorsChartData/daily/{date}",
    metric_class=Floors,
    parser=parse_floors_data,
    description="Daily floors climbed and descended from barometer data",
    version="1.0",
)

# Export for auto-discovery
__metric_config__ = METRIC_CONFIG
