"""Daily Summary Data Module.

===========================

This module provides comprehensive daily summary data from the Garmin Connect API.
Data includes activities, calories, steps, heart rate, stress, sleep, body battery,
SpO2, respiration, and floors - all in one convenient metric.

Example:
    >>> from garmy import AuthClient, APIClient, MetricAccessorFactory
    >>> auth_client = AuthClient()
    >>> api_client = APIClient(auth_client=auth_client)
    >>> auth_client.login("email@example.com", "password")
    >>>
    >>> # Get today's complete daily summary
    >>> factory = MetricAccessorFactory(api_client)
    >>> metrics = factory.discover_and_create_all()
    >>> summary = metrics.get("daily_summary").get()
    >>> print(f"Total steps: {summary.total_steps}")
    >>> print(f"Total calories: {summary.total_kilocalories}")
    >>> print(f"Stress level: {summary.average_stress_level}")
    >>> print(f"Body Battery: {summary.body_battery_most_recent_value}%")

Data Source:
    Garmin Connect API endpoint:
    /usersummary-service/usersummary/daily/{user_id}?calendarDate={date}
"""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Optional, Union

from ..core.base import MetricConfig
from ..core.endpoint_builders import (
    build_daily_summary_endpoint as _build_daily_summary_endpoint,
)
from ..core.utils import TimestampMixin, create_simple_field_parser


@dataclass
class DailySummary(TimestampMixin):
    """Comprehensive daily summary data from Garmin Connect API.

    Complete daily health and fitness summary including all major metrics
    from Garmin's usersummary service in one convenient data structure.

    Attributes:
        user_profile_id: User profile identifier
        calendar_date: Date of the data

        # Activity & Movement
        total_steps: Total steps taken
        daily_step_goal: Daily step goal
        total_distance_meters: Total distance in meters
        wellness_distance_meters: Wellness distance in meters
        highly_active_seconds: Seconds of high activity
        active_seconds: Seconds of moderate activity
        sedentary_seconds: Seconds of sedentary time
        sleeping_seconds: Seconds of sleep
        moderate_intensity_minutes: Minutes of moderate intensity
        vigorous_intensity_minutes: Minutes of vigorous intensity
        intensity_minutes_goal: Goal for intensity minutes
        floors_ascended: Number of floors climbed
        floors_descended: Number of floors descended
        floors_ascended_in_meters: Floors climbed in meters
        floors_descended_in_meters: Floors descended in meters
        user_floors_ascended_goal: Daily floors goal

        # Calories
        total_kilocalories: Total calories burned
        active_kilocalories: Active calories burned
        bmr_kilocalories: Basal metabolic rate calories
        wellness_kilocalories: Wellness calories
        wellness_active_kilocalories: Wellness active calories
        burned_kilocalories: Total burned calories (if tracked)
        consumed_kilocalories: Consumed calories (if tracked)
        remaining_kilocalories: Remaining calories
        net_remaining_kilocalories: Net remaining calories
        net_calorie_goal: Daily calorie goal

        # Heart Rate
        min_heart_rate: Minimum heart rate
        max_heart_rate: Maximum heart rate
        resting_heart_rate: Resting heart rate
        last_seven_days_avg_resting_heart_rate: 7-day average resting HR
        min_avg_heart_rate: Minimum average heart rate
        max_avg_heart_rate: Maximum average heart rate
        abnormal_heart_rate_alerts_count: Count of abnormal HR alerts

        # Stress
        average_stress_level: Average stress level (0-100)
        max_stress_level: Maximum stress level
        stress_duration: Duration of stress measurement (seconds)
        rest_stress_duration: Duration of rest stress (seconds)
        activity_stress_duration: Duration of activity stress (seconds)
        uncategorized_stress_duration: Duration of uncategorized stress (seconds)
        total_stress_duration: Total stress measurement duration (seconds)
        low_stress_duration: Duration of low stress (seconds)
        medium_stress_duration: Duration of medium stress (seconds)
        high_stress_duration: Duration of high stress (seconds)
        stress_percentage: Overall stress percentage
        rest_stress_percentage: Rest stress percentage
        activity_stress_percentage: Activity stress percentage
        uncategorized_stress_percentage: Uncategorized stress percentage
        low_stress_percentage: Low stress percentage
        medium_stress_percentage: Medium stress percentage
        high_stress_percentage: High stress percentage
        stress_qualifier: Stress level qualifier (e.g., "BALANCED")

        # Body Battery
        body_battery_charged_value: Body battery charged amount
        body_battery_drained_value: Body battery drained amount
        body_battery_highest_value: Highest body battery level
        body_battery_lowest_value: Lowest body battery level
        body_battery_most_recent_value: Current body battery level
        body_battery_during_sleep: Body battery gained during sleep
        body_battery_at_wake_time: Body battery level at wake time
        body_battery_version: Body battery algorithm version

        # SpO2
        average_spo2: Average SpO2 percentage
        lowest_spo2: Lowest SpO2 reading
        latest_spo2: Latest SpO2 reading
        latest_spo2_reading_time_gmt: Time of latest SpO2 reading (GMT)
        latest_spo2_reading_time_local: Time of latest SpO2 reading (local)

        # Respiration
        avg_waking_respiration_value: Average waking respiration rate
        highest_respiration_value: Highest respiration rate
        lowest_respiration_value: Lowest respiration rate
        latest_respiration_value: Latest respiration rate
        latest_respiration_time_gmt: Time of latest respiration reading
        respiration_algorithm_version: Respiration algorithm version

        # Sleep
        measurable_awake_duration: Measurable awake time (seconds)
        measurable_asleep_duration: Measurable sleep time (seconds)

        # Metadata
        wellness_start_time_gmt: Start of wellness tracking period
        wellness_end_time_gmt: End of wellness tracking period
        wellness_start_time_local: Start of wellness tracking period (local)
        wellness_end_time_local: End of wellness tracking period (local)
        last_sync_timestamp_gmt: Last device sync time
        duration_in_milliseconds: Total tracking duration
        includes_wellness_data: Whether wellness data is included
        includes_activity_data: Whether activity data is included
        includes_calorie_consumed_data: Whether calorie consumption is tracked
        source: Data source (e.g., "GARMIN")

    Example:
        >>> summary = garmy.daily_summary.get()
        >>> print(f"Steps: {summary.total_steps:,} ({summary.step_goal_progress:.1f}%)")
        >>> print(
            f"Calories: {summary.total_kilocalories:,} "
            f"({summary.activity_efficiency:.1f}% active)"
        )
        >>> print(f"Stress: {summary.average_stress_level}/100 ({summary.stress_qualifier})")
        >>> print(f"Body Battery: {summary.body_battery_most_recent_value}%")
        >>> print(f"SpO2: {summary.average_spo2}%")
    """

    user_profile_id: int = 0
    calendar_date: str = ""

    # Activity & Movement
    total_steps: int = 0
    daily_step_goal: int = 0
    total_distance_meters: int = 0
    wellness_distance_meters: int = 0
    highly_active_seconds: int = 0
    active_seconds: int = 0
    sedentary_seconds: int = 0
    sleeping_seconds: int = 0
    moderate_intensity_minutes: int = 0
    vigorous_intensity_minutes: int = 0
    intensity_minutes_goal: int = 0
    floors_ascended: int = 0
    floors_descended: int = 0
    floors_ascended_in_meters: int = 0
    floors_descended_in_meters: int = 0
    user_floors_ascended_goal: int = 0

    # Calories
    total_kilocalories: int = 0
    active_kilocalories: int = 0
    bmr_kilocalories: int = 0
    wellness_kilocalories: int = 0
    wellness_active_kilocalories: int = 0
    burned_kilocalories: Optional[int] = None
    consumed_kilocalories: Optional[int] = None
    remaining_kilocalories: Optional[int] = None
    net_remaining_kilocalories: int = 0
    net_calorie_goal: Optional[int] = None

    # Heart Rate
    min_heart_rate: int = 0
    max_heart_rate: int = 0
    resting_heart_rate: int = 0
    last_seven_days_avg_resting_heart_rate: int = 0
    min_avg_heart_rate: int = 0
    max_avg_heart_rate: int = 0
    abnormal_heart_rate_alerts_count: Optional[int] = None

    # Stress
    average_stress_level: int = 0
    max_stress_level: int = 0
    stress_duration: int = 0
    rest_stress_duration: int = 0
    activity_stress_duration: int = 0
    uncategorized_stress_duration: int = 0
    total_stress_duration: int = 0
    low_stress_duration: int = 0
    medium_stress_duration: int = 0
    high_stress_duration: int = 0
    stress_percentage: float = 0.0
    rest_stress_percentage: float = 0.0
    activity_stress_percentage: float = 0.0
    uncategorized_stress_percentage: float = 0.0
    low_stress_percentage: float = 0.0
    medium_stress_percentage: float = 0.0
    high_stress_percentage: float = 0.0
    stress_qualifier: str = ""

    # Body Battery
    body_battery_charged_value: int = 0
    body_battery_drained_value: int = 0
    body_battery_highest_value: int = 0
    body_battery_lowest_value: int = 0
    body_battery_most_recent_value: int = 0
    body_battery_during_sleep: int = 0
    body_battery_at_wake_time: int = 0
    body_battery_version: int = 0

    # SpO2
    average_spo2: int = 0
    lowest_spo2: int = 0
    latest_spo2: int = 0
    latest_spo2_reading_time_gmt: str = ""
    latest_spo2_reading_time_local: str = ""

    # Respiration
    avg_waking_respiration_value: int = 0
    highest_respiration_value: int = 0
    lowest_respiration_value: int = 0
    latest_respiration_value: int = 0
    latest_respiration_time_gmt: str = ""
    respiration_algorithm_version: int = 0

    # Sleep
    measurable_awake_duration: int = 0
    measurable_asleep_duration: int = 0

    # Metadata
    wellness_start_time_gmt: str = ""
    wellness_end_time_gmt: str = ""
    wellness_start_time_local: str = ""
    wellness_end_time_local: str = ""
    last_sync_timestamp_gmt: str = ""
    duration_in_milliseconds: int = 0
    includes_wellness_data: bool = False
    includes_activity_data: bool = False
    includes_calorie_consumed_data: bool = False
    source: str = ""

    @property
    def date(self) -> datetime:
        """Convert calendar_date to datetime object."""
        return datetime.strptime(self.calendar_date, "%Y-%m-%d")

    # Activity convenience properties
    @property
    def distance_km(self) -> float:
        """Get total distance in kilometers."""
        return self.total_distance_meters / 1000

    @property
    def distance_miles(self) -> float:
        """Get total distance in miles."""
        return self.total_distance_meters / 1609.344

    @property
    def step_goal_progress(self) -> float:
        """Calculate step goal progress as percentage."""
        if self.daily_step_goal > 0:
            return (self.total_steps / self.daily_step_goal) * 100
        return 0.0

    @property
    def total_active_minutes(self) -> float:
        """Get total active time in minutes."""
        return (self.highly_active_seconds + self.active_seconds) / 60

    @property
    def total_sedentary_hours(self) -> float:
        """Get total sedentary time in hours."""
        return self.sedentary_seconds / 3600

    @property
    def intensity_minutes_progress(self) -> float:
        """Calculate intensity minutes goal progress as percentage."""
        total_intensity = self.moderate_intensity_minutes + (
            self.vigorous_intensity_minutes * 2
        )
        if self.intensity_minutes_goal > 0:
            return (total_intensity / self.intensity_minutes_goal) * 100
        return 0.0

    # Calorie convenience properties
    @property
    def activity_efficiency(self) -> float:
        """Calculate percentage of calories from active vs total."""
        if self.total_kilocalories > 0:
            return (self.active_kilocalories / self.total_kilocalories) * 100
        return 0.0

    @property
    def bmr_percentage(self) -> float:
        """Calculate percentage of calories from BMR vs total."""
        if self.total_kilocalories > 0:
            return (self.bmr_kilocalories / self.total_kilocalories) * 100
        return 0.0

    # Heart rate convenience properties
    @property
    def heart_rate_range(self) -> int:
        """Get heart rate range (max - min)."""
        return self.max_heart_rate - self.min_heart_rate

    @property
    def resting_hr_trend(self) -> int:
        """Get resting heart rate trend vs 7-day average."""
        return self.resting_heart_rate - self.last_seven_days_avg_resting_heart_rate

    # Stress convenience properties
    @property
    def stress_range(self) -> int:
        """Get stress range (max - average)."""
        return self.max_stress_level - self.average_stress_level

    @property
    def total_stress_hours(self) -> float:
        """Get total stress measurement time in hours."""
        return self.total_stress_duration / 3600

    # Body Battery convenience properties
    @property
    def body_battery_range(self) -> int:
        """Get body battery range (highest - lowest)."""
        return self.body_battery_highest_value - self.body_battery_lowest_value

    @property
    def net_body_battery_change(self) -> int:
        """Get net body battery change (charged - drained)."""
        return self.body_battery_charged_value - self.body_battery_drained_value

    # SpO2 convenience properties
    @property
    def spo2_range(self) -> int:
        """Get SpO2 range (average - lowest)."""
        return self.average_spo2 - self.lowest_spo2

    # Respiration convenience properties
    @property
    def respiration_range(self) -> int:
        """Get respiration range (highest - lowest)."""
        return self.highest_respiration_value - self.lowest_respiration_value

    # Sleep convenience properties
    @property
    def sleep_hours(self) -> float:
        """Get sleep duration in hours."""
        return self.sleeping_seconds / 3600

    @property
    def measurable_sleep_hours(self) -> float:
        """Get measurable sleep duration in hours."""
        return self.measurable_asleep_duration / 3600

    # Metadata convenience properties
    @property
    def wellness_duration_hours(self) -> float:
        """Get wellness tracking duration in hours."""
        return self.duration_in_milliseconds / 3600000

    @property
    def last_sync_datetime_gmt(self) -> Optional[datetime]:
        """Convert last sync timestamp to datetime."""
        return self.iso_to_datetime(self.last_sync_timestamp_gmt)


# Create parser using factory function
parse_daily_summary_data = create_simple_field_parser(DailySummary)


def build_daily_summary_endpoint(
    date_input: Union[date, str, None] = None, api_client: Any = None, **kwargs: Any
) -> str:
    """Build the DailySummary API endpoint with user ID and date."""
    return _build_daily_summary_endpoint(date_input, api_client, **kwargs)


# MetricConfig for auto-discovery
METRIC_CONFIG = MetricConfig(
    endpoint="",
    metric_class=DailySummary,
    parser=parse_daily_summary_data,
    endpoint_builder=build_daily_summary_endpoint,
    requires_user_id=True,
    description=(
        "Comprehensive daily summary with activities, calories, steps, "
        "heart rate, stress, and more"
    ),
    version="1.0",
)

__metric_config__ = METRIC_CONFIG
