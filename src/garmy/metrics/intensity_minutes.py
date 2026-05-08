"""Intensity Minutes metric module.

This module provides access to Garmin intensity minutes data using the
auto-discovery architecture. The API returns both a 15-minute timeseries
(imValuesArray) and weekly cumulative summary values.

Data Source:
    Garmin Connect API endpoint: /wellness-service/wellness/daily/im/{date}

Storage strategy:
    - Timeseries: imValuesArray stored in the timeseries table at 15-min resolution.
      Each value is the intensity minutes earned in that 15-min window.
    - Daily summary: intensity_minutes_total is computed as the sum of the
      timeseries values (actual minutes earned that day, not weekly cumulative).
    - Weekly context: moderate_intensity_minutes and vigorous_intensity_minutes
      store weekly cumulative values from the API (useful for weekly goal tracking).

API field mapping (camelCase → snake_case after camel_to_snake_dict):
    moderateMinutes    → moderate_minutes    (weekly cumulative moderate)
    vigorousMinutes    → vigorous_minutes    (weekly cumulative vigorous)
    weeklyTotal        → weekly_total        (WHO-weighted: moderate + 2*vigorous)
    weekGoal           → week_goal           (weekly goal, typically 150)
    imValuesArray      → im_values_array     (15-min timeseries: [timestamp_ms, value])
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..core.base import MetricConfig
from ..core.utils import camel_to_snake_dict


@dataclass
class IntensityMinutes:
    """Intensity minutes data from Garmin Connect API.

    Contains both the 15-minute timeseries and weekly cumulative summaries.
    Vigorous minutes count double toward the weekly goal (WHO formula).

    Attributes:
        calendar_date: Date string (YYYY-MM-DD)
        moderate_minutes: Weekly cumulative moderate intensity minutes
        vigorous_minutes: Weekly cumulative vigorous intensity minutes
        weekly_total: WHO-weighted weekly total (moderate + 2x vigorous)
        week_goal: Weekly intensity minutes goal (typically 150)
        im_values_array: 15-min timeseries as [timestamp_ms, value] pairs.
            Each value is the intensity minutes earned in that window.

    Example:
        >>> im = garmy.intensity_minutes.get()
        >>> print(f"Weekly total: {im.weekly_total} / {im.week_goal}")
        >>> print(f"Today's readings: {im.readings_count}")
    """

    calendar_date: str = ""
    moderate_minutes: Optional[int] = None
    vigorous_minutes: Optional[int] = None
    weekly_total: Optional[int] = None
    week_goal: Optional[int] = None
    im_values_array: List[List[Any]] = field(default_factory=list)

    @property
    def readings_count(self) -> int:
        """Get number of 15-minute readings."""
        return len(self.im_values_array)

    @property
    def daily_total(self) -> Optional[int]:
        """Compute daily intensity minutes earned from the timeseries.

        Sums all non-None values in imValuesArray. Returns None if no
        readings are available.
        """
        if not self.im_values_array:
            return None
        total = 0
        has_data = False
        for entry in self.im_values_array:
            if isinstance(entry, (list, tuple)) and len(entry) >= 2:
                value = entry[1]
                if value is not None:
                    total += int(value)
                    has_data = True
        return total if has_data else None


def parse_intensity_minutes_data(data: Dict[str, Any]) -> IntensityMinutes:
    """Parse intensity minutes API response into structured data."""
    snake_dict = camel_to_snake_dict(data)

    if not isinstance(snake_dict, dict):
        raise ValueError(
            f"Expected dictionary from API response but got {type(snake_dict).__name__}. "
            f"Raw data: {data}"
        )

    return IntensityMinutes(
        calendar_date=snake_dict.get("calendar_date", ""),
        moderate_minutes=snake_dict.get("moderate_minutes"),
        vigorous_minutes=snake_dict.get("vigorous_minutes"),
        weekly_total=snake_dict.get("weekly_total"),
        week_goal=snake_dict.get("week_goal"),
        im_values_array=snake_dict.get("im_values_array") or [],
    )


# Declarative configuration for auto-discovery with custom parser
METRIC_CONFIG = MetricConfig(
    endpoint="/wellness-service/wellness/daily/im/{date}",
    metric_class=IntensityMinutes,
    parser=parse_intensity_minutes_data,
    description="Intensity minutes with 15-min timeseries and weekly cumulative summaries",
    version="1.0",
)

# Export for auto-discovery
__metric_config__ = METRIC_CONFIG
