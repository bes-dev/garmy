"""Stress Data Module.

==================

This module provides direct access to Garmin stress level data from the Connect API.
Data includes stress measurements throughout the day based on heart rate variability.

Example:
    >>> from garmy import AuthClient, APIClient, MetricAccessorFactory
    >>> auth_client = AuthClient()
    >>> api_client = APIClient(auth_client=auth_client)
    >>> auth_client.login("email@example.com", "password")
    >>>
    >>> # Get today's stress data
    >>> factory = MetricAccessorFactory(api_client)
    >>> metrics = factory.discover_and_create_all()
    >>> stress = metrics.get("stress").get()
    >>> print(f"Average stress: {stress.avg_stress_level}")
    >>> print(f"Max stress: {stress.max_stress_level}")
    >>> print(f"Readings: {len(stress.stress_readings)}")

Data Source:
    Garmin Connect API endpoint: /wellness-service/wellness/dailyStress/{date}
"""

from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from datetime import datetime

from ..core.base import MetricConfig
from ..core.utils import TimestampMixin, create_simple_field_parser


@dataclass
class StressReading(TimestampMixin):
    """Individual stress level reading from Garmin API.

    Attributes:
        timestamp: Unix timestamp when reading was taken
        stress_level: Stress level value (-1 to 100, -1 = rest/sleep)
    """

    timestamp: int
    stress_level: int

    @property
    def datetime(self) -> "datetime":
        """Convert timestamp to datetime object."""
        return self.timestamp_to_datetime(self.timestamp)

    @property
    def stress_category(self) -> str:
        """Get stress level category based on Garmin ranges."""
        if self.stress_level == -1:
            return "Rest"
        elif self.stress_level < 25:
            return "Low"
        elif self.stress_level < 50:
            return "Medium"
        elif self.stress_level < 75:
            return "High"
        else:
            return "Very High"


@dataclass
class Stress:
    """Daily stress data from Garmin Connect API.

    Raw stress data including summary metrics and individual readings throughout the day.
    All data comes directly from Garmin's wellness service.

    Attributes:
        user_profile_pk: User profile primary key
        calendar_date: Date in YYYY-MM-DD format
        max_stress_level: Maximum stress level for the day
        avg_stress_level: Average stress level for the day
        stress_values_array: Raw stress data as timestamp/value pairs

    Optional fields (ignored for stress analysis):
        start_timestamp_gmt: Start time GMT
        end_timestamp_gmt: End time GMT
        start_timestamp_local: Start time local
        end_timestamp_local: End time local
        stress_chart_value_offset: Stress chart offset
        stress_chart_y_axis_origin: Stress chart origin
        stress_value_descriptors_dto_list: Stress descriptors
        body_battery_value_descriptors_dto_list: Body Battery descriptors
        body_battery_values_array: Body Battery data array

    Example:
        >>> stress = garmy.stress.get()
        >>> print(f"Average: {stress.avg_stress_level}")
        >>> for reading in stress.stress_readings:
        >>>     print(f"{reading.datetime}: {reading.stress_level} ({reading.stress_category})")
    """

    user_profile_pk: int
    calendar_date: str
    max_stress_level: int
    avg_stress_level: int
    stress_values_array: List[List[int]]

    # Optional fields we don't need for stress analysis
    start_timestamp_gmt: Optional["datetime"] = None
    end_timestamp_gmt: Optional["datetime"] = None
    start_timestamp_local: Optional["datetime"] = None
    end_timestamp_local: Optional["datetime"] = None
    stress_chart_value_offset: Optional[int] = None
    stress_chart_y_axis_origin: Optional[int] = None
    stress_value_descriptors_dto_list: Optional[List] = None
    body_battery_value_descriptors_dto_list: Optional[List] = None
    body_battery_values_array: Optional[List] = None

    @property
    def stress_readings(self) -> List[StressReading]:
        """Parse raw stress data into structured readings (cached at module level).

        Returns:
            List of StressReading objects with timestamp and stress level
        """
        # Use module-level caching based on data hash for safety with dataclasses
        return _parse_stress_readings_cached(
            tuple(
                (item[0], item[1])
                for item in self.stress_values_array
                if len(item) >= 2
            )
        )


@lru_cache(maxsize=None)  # Size set dynamically by config
def _parse_stress_readings_cached(data_tuple: tuple) -> List[StressReading]:
    """Parse stress readings with module-level caching for dataclass safety.

    Args:
        data_tuple: Tuple of (timestamp, stress_level) pairs

    Returns:
        List of StressReading objects
    """
    return [
        StressReading(timestamp=item[0], stress_level=item[1]) for item in data_tuple
    ]


# Create parser using factory function
parse_stress_data = create_simple_field_parser(Stress)

# Declarative configuration for auto-discovery
METRIC_CONFIG = MetricConfig(
    endpoint="/wellness-service/wellness/dailyStress/{date}",
    metric_class=Stress,
    parser=parse_stress_data,
    description="Daily stress levels based on heart rate variability",
    version="1.0",
)

# Export for auto-discovery
__metric_config__ = METRIC_CONFIG
