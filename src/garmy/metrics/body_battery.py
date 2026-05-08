"""Body Battery Data Module.

========================

This module provides direct access to Garmin Body Battery data from the Connect API.
Data includes energy levels throughout the day with charging/draining status.

Example:
    >>> from garmy import AuthClient, APIClient, MetricAccessorFactory
    >>> auth_client = AuthClient()
    >>> api_client = APIClient(auth_client=auth_client)
    >>> auth_client.login("email@example.com", "password")
    >>>
    >>> # Get today's Body Battery data
    >>> factory = MetricAccessorFactory(api_client)
    >>> metrics = factory.discover_and_create_all()
    >>> battery = metrics.get("body_battery").get()
    >>> print(f"Date: {battery.calendar_date}")
    >>> print(f"Readings: {len(battery.body_battery_readings)}")

Data Source:
    Garmin Connect API endpoint: /wellness-service/wellness/dailyStress/{date}
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, List, Optional

if TYPE_CHECKING:
    from datetime import datetime

from ..core.base import MetricConfig
from ..core.utils import TimestampMixin, create_simple_field_parser


@dataclass
class BodyBatteryReading(TimestampMixin):
    """Individual Body Battery reading from Garmin API."""

    timestamp: int
    level: int
    status: str
    version: float

    @property
    def datetime(self) -> "datetime":
        """Convert timestamp to datetime object."""
        return self.timestamp_to_datetime(self.timestamp)


@dataclass
class BodyBattery:
    """Daily Body Battery data from Garmin Connect API.

    Raw Body Battery data including energy levels throughout the day.
    All data comes directly from Garmin's wellness service.

    Attributes:
        user_profile_pk: User profile primary key
        calendar_date: Date in YYYY-MM-DD format
        body_battery_values_array: Raw Body Battery data as timestamp/level/status/version arrays

    Optional fields (ignored for Body Battery analysis):
        start_timestamp_gmt: Start time GMT
        end_timestamp_gmt: End time GMT
        start_timestamp_local: Start time local
        end_timestamp_local: End time local
        max_stress_level: Maximum stress level
        avg_stress_level: Average stress level
        stress_chart_value_offset: Stress chart offset
        stress_chart_y_axis_origin: Stress chart origin
        stress_value_descriptors_dto_list: Stress descriptors
        stress_values_array: Stress data array
        body_battery_value_descriptors_dto_list: Body Battery descriptors

    Example:
        >>> battery = garmy.body_battery.get()
        >>> print(f"Date: {battery.calendar_date}")
        >>> for reading in battery.body_battery_readings:
        >>>     print(f"{reading.datetime}: {reading.level}% ({reading.status})")
    """

    user_profile_pk: int
    calendar_date: str
    body_battery_values_array: Optional[List[List[Any]]] = None

    # Optional fields we ignore for Body Battery analysis
    start_timestamp_gmt: Optional["datetime"] = None
    end_timestamp_gmt: Optional["datetime"] = None
    start_timestamp_local: Optional["datetime"] = None
    end_timestamp_local: Optional["datetime"] = None
    max_stress_level: Optional[int] = None
    avg_stress_level: Optional[int] = None
    stress_chart_value_offset: Optional[int] = None
    stress_chart_y_axis_origin: Optional[int] = None
    stress_value_descriptors_dto_list: Optional[List] = None
    stress_values_array: Optional[List] = None
    body_battery_value_descriptors_dto_list: Optional[List] = None

    @property
    def body_battery_readings(self) -> List[BodyBatteryReading]:
        """Parse raw Body Battery data into structured readings."""
        readings = []
        if not self.body_battery_values_array:
            return readings
        for item in self.body_battery_values_array:
            if len(item) >= 4:
                readings.append(
                    BodyBatteryReading(
                        timestamp=item[0],
                        level=item[2],  # Level is at index 2
                        status=item[1],  # Status is at index 1
                        version=item[3] if len(item) > 3 else 1.0,
                    )
                )
        return readings


# Create parser using factory function
parse_body_battery_data = create_simple_field_parser(BodyBattery)

# Declarative configuration for auto-discovery
METRIC_CONFIG = MetricConfig(
    endpoint="/wellness-service/wellness/dailyStress/{date}",
    metric_class=BodyBattery,
    parser=parse_body_battery_data,
    description="Daily Body Battery energy levels and charging/draining status",
    version="1.0",
)

# Export for auto-discovery
__metric_config__ = METRIC_CONFIG
