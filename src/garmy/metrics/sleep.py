"""Sleep Data Module.

==================

This module provides direct access to Garmin sleep data from the Connect API.
Data includes comprehensive sleep metrics, stages, SpO2, respiration, and detailed
temporal readings throughout the night.

Example:
    >>> from garmy import AuthClient, APIClient, MetricAccessorFactory
    >>> auth_client = AuthClient()
    >>> api_client = APIClient(auth_client=auth_client)
    >>> auth_client.login("email@example.com", "password")
    >>>
    >>> # Get today's sleep data
    >>> factory = MetricAccessorFactory(api_client)
    >>> metrics = factory.discover_and_create_all()
    >>> sleep = metrics.get("sleep").get()
    >>> print(f"Sleep duration: {sleep.sleep_duration_hours:.1f} hours")
    >>> print(f"Deep sleep: {sleep.deep_sleep_percentage:.1f}%")
    >>> print(f"SpO2 average: {sleep.daily_sleep_dto.average_sp_o2_value}%")

Data Source:
    Garmin Connect API endpoint: /sleep-service/sleep/dailySleepData
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

if TYPE_CHECKING:
    from datetime import date, datetime

from ..core.base import MetricConfig
from ..core.endpoint_builders import build_sleep_endpoint as _build_sleep_endpoint
from ..core.utils import (
    TimestampMixin,
    create_nested_summary_parser,
)


@dataclass
class SleepSummary(TimestampMixin):
    """Main sleep data structure from Garmin API."""

    # Core sleep timing
    id: int = 0
    user_profile_pk: int = 0
    calendar_date: str = ""
    sleep_time_seconds: int = 0
    nap_time_seconds: int = 0
    sleep_start_timestamp_gmt: int = 0
    sleep_end_timestamp_gmt: int = 0
    sleep_start_timestamp_local: int = 0
    sleep_end_timestamp_local: int = 0

    # Sleep stages
    deep_sleep_seconds: int = 0
    light_sleep_seconds: int = 0
    rem_sleep_seconds: int = 0
    awake_sleep_seconds: int = 0
    unmeasurable_sleep_seconds: int = 0
    awake_count: int = 0

    # Sleep quality
    sleep_window_confirmed: bool = False
    sleep_window_confirmation_type: str = ""
    device_rem_capable: bool = False
    retro: bool = False
    sleep_from_device: bool = False

    # Physiological measurements
    average_sp_o2_value: Optional[int] = None
    lowest_sp_o2_value: Optional[int] = None
    highest_sp_o2_value: Optional[int] = None
    average_sp_o2_hr_sleep: Optional[int] = None
    average_respiration_value: Optional[float] = None
    lowest_respiration_value: Optional[float] = None
    highest_respiration_value: Optional[float] = None
    avg_sleep_stress: Optional[float] = None

    # Optional metadata
    auto_sleep_start_timestamp_gmt: Optional[int] = None
    auto_sleep_end_timestamp_gmt: Optional[int] = None
    sleep_quality_type_pk: Optional[int] = None
    sleep_result_type_pk: Optional[int] = None
    age_group: Optional[str] = None
    sleep_score_feedback: Optional[str] = None
    sleep_score_insight: Optional[str] = None
    sleep_score_personalized_insight: Optional[str] = None
    sleep_version: Optional[int] = None

    # Nested objects as raw dicts (following garmy philosophy)
    sleep_scores: Optional[Dict[str, Any]] = None
    sleep_need: Optional[Dict[str, Any]] = None
    next_sleep_need: Optional[Dict[str, Any]] = None

    @property
    def sleep_start_datetime_gmt(self) -> "datetime":
        """Convert GMT sleep start timestamp to datetime."""
        return self.timestamp_to_datetime(self.sleep_start_timestamp_gmt)

    @property
    def sleep_end_datetime_gmt(self) -> "datetime":
        """Convert GMT sleep end timestamp to datetime."""
        return self.timestamp_to_datetime(self.sleep_end_timestamp_gmt)

    @property
    def sleep_start_datetime_local(self) -> "datetime":
        """Convert local sleep start timestamp to datetime."""
        return self.timestamp_to_datetime(self.sleep_start_timestamp_local)

    @property
    def sleep_end_datetime_local(self) -> "datetime":
        """Convert local sleep end timestamp to datetime."""
        return self.timestamp_to_datetime(self.sleep_end_timestamp_local)

    @property
    def total_sleep_duration_hours(self) -> Optional[float]:
        """Get total sleep duration in hours."""
        if self.sleep_time_seconds is None:
            return None
        return self.sleep_time_seconds / 3600

    @property
    def sleep_efficiency_percentage(self) -> Optional[float]:
        """Calculate sleep efficiency (sleep time / time in bed)."""
        if (
            self.sleep_end_timestamp_local is None
            or self.sleep_start_timestamp_local is None
            or self.sleep_time_seconds is None
        ):
            return None
        time_in_bed = (
            self.sleep_end_timestamp_local - self.sleep_start_timestamp_local
        ) / 1000
        if time_in_bed > 0:
            return (self.sleep_time_seconds / time_in_bed) * 100
        return 0


@dataclass
class Sleep:
    """Comprehensive sleep data from Garmin Connect API.

    Raw sleep data including detailed sleep stages, SpO2, respiration, and
    temporal readings throughout the night. All data comes directly from
    Garmin's sleep service.

    Attributes:
        sleep_summary: Main sleep summary with stages, timing, and scores
        sleep_movement: Raw movement data throughout the night (list of dicts)
        wellness_epoch_spo2_data_dto_list: SpO2 readings throughout the night (list of dicts)
        wellness_epoch_respiration_data_dto_list: Respiration readings throughout the night
            (list of dicts)
        skin_temp_data_exists: Whether skin temperature data is available
        skin_temp_deviation_c: Skin temperature deviation in Celsius
        skin_temp_deviation_f: Skin temperature deviation in Fahrenheit

    Example:
        >>> sleep = garmy.sleep.get()
        >>> print(f"Sleep duration: {sleep.sleep_duration_hours:.1f} hours")
        >>> print(f"Deep sleep: {sleep.deep_sleep_percentage:.1f}%")
        >>> print(f"Average SpO2: {sleep.sleep_summary.average_sp_o2_value}%")
        >>>
        >>> # Access raw SpO2 readings
        >>> for reading in sleep.wellness_epoch_spo2_data_dto_list[:5]:
        >>>     print(f"SpO2: {reading['value']}% at {reading['startGMT']}")
    """

    sleep_summary: SleepSummary
    sleep_movement: List[Dict[str, Any]] = field(default_factory=list)
    wellness_epoch_spo2_data_dto_list: List[Dict[str, Any]] = field(
        default_factory=list
    )
    wellness_epoch_respiration_data_dto_list: List[Dict[str, Any]] = field(
        default_factory=list
    )

    # Top-level skin temperature fields
    skin_temp_data_exists: bool = False
    skin_temp_deviation_c: Optional[float] = None
    skin_temp_deviation_f: Optional[float] = None

    def __str__(self) -> str:
        """Format sleep data for human-readable display."""
        lines = []
        if self.sleep_duration_hours:
            lines.append(f"• Duration: {self.sleep_duration_hours:.1f} hours")
        if self.deep_sleep_percentage:
            lines.append(f"• Deep sleep: {self.deep_sleep_percentage:.1f}%")
        if self.light_sleep_percentage:
            lines.append(f"• Light sleep: {self.light_sleep_percentage:.1f}%")
        if self.rem_sleep_percentage:
            lines.append(f"• REM sleep: {self.rem_sleep_percentage:.1f}%")
        if self.awake_percentage:
            lines.append(f"• Awake: {self.awake_percentage:.1f}%")
        if self.sleep_summary.average_sp_o2_value:
            lines.append(f"• Average SpO2: {self.sleep_summary.average_sp_o2_value}%")
        if self.sleep_summary.average_respiration_value:
            lines.append(
                f"• Respiration: {self.sleep_summary.average_respiration_value:.1f} breaths/min"
            )
        if self.sleep_summary.awake_count:
            lines.append(f"• Awakenings: {self.sleep_summary.awake_count}")

        # Add data availability info
        data_counts = []
        if self.spo2_readings_count:
            data_counts.append(f"{self.spo2_readings_count} SpO2 readings")
        if self.respiration_readings_count:
            data_counts.append(
                f"{self.respiration_readings_count} respiration readings"
            )
        if self.movement_readings_count:
            data_counts.append(f"{self.movement_readings_count} movement readings")

        if data_counts:
            lines.append(f"• Data available: {', '.join(data_counts)}")

        return "\n".join(lines) if lines else "Sleep data available"

    @property
    def sleep_duration_hours(self) -> Optional[float]:
        """Get total sleep duration in hours."""
        return self.sleep_summary.total_sleep_duration_hours

    @property
    def deep_sleep_percentage(self) -> Optional[float]:
        """Get deep sleep as percentage of total sleep."""
        total = self.sleep_summary.sleep_time_seconds
        deep = self.sleep_summary.deep_sleep_seconds
        if total and total > 0 and deep is not None:
            return (deep / total) * 100
        return None

    @property
    def light_sleep_percentage(self) -> Optional[float]:
        """Get light sleep as percentage of total sleep."""
        total = self.sleep_summary.sleep_time_seconds
        light = self.sleep_summary.light_sleep_seconds
        if total and total > 0 and light is not None:
            return (light / total) * 100
        return None

    @property
    def rem_sleep_percentage(self) -> Optional[float]:
        """Get REM sleep as percentage of total sleep."""
        total = self.sleep_summary.sleep_time_seconds
        rem = self.sleep_summary.rem_sleep_seconds
        if total and total > 0 and rem is not None:
            return (rem / total) * 100
        return None

    @property
    def awake_percentage(self) -> Optional[float]:
        """Get awake time as percentage of total sleep period."""
        total = self.sleep_summary.sleep_time_seconds
        awake = self.sleep_summary.awake_sleep_seconds
        if total and total > 0 and awake is not None:
            return (awake / total) * 100
        return None

    @property
    def spo2_readings_count(self) -> int:
        """Get number of SpO2 readings."""
        return len(self.wellness_epoch_spo2_data_dto_list)

    @property
    def respiration_readings_count(self) -> int:
        """Get number of respiration readings."""
        return len(self.wellness_epoch_respiration_data_dto_list)

    @property
    def movement_readings_count(self) -> int:
        """Get number of movement readings."""
        return len(self.sleep_movement)


def parse_sleep_data(data: Dict[str, Any]) -> Sleep:
    """Parse sleep data including top-level skin temperature fields.

    This custom parser extends the standard nested summary parser to also
    capture skin temperature data that exists at the top level of the
    API response (not nested in dailySleepDTO).
    """
    # Use existing parser for nested summary and base data
    base_parser = create_nested_summary_parser(
        Sleep,
        SleepSummary,
        "daily_sleep_dto",
        [
            "sleep_movement",
            "wellness_epoch_spo2_data_dto_list",
            "wellness_epoch_respiration_data_dto_list",
        ],
    )

    # Parse base data
    sleep = base_parser(data)

    # Add top-level skin temp fields (these are outside dailySleepDTO)
    sleep.skin_temp_data_exists = data.get("skinTempDataExists", False)
    sleep.skin_temp_deviation_c = data.get("avgSkinTempDeviationC")
    sleep.skin_temp_deviation_f = data.get("avgSkinTempDeviationF")

    return sleep


def build_sleep_endpoint(
    date_input: Union["date", str, None] = None, api_client: Any = None, **kwargs: Any
) -> str:
    """Build the Sleep API endpoint with user ID and date."""
    return _build_sleep_endpoint(date_input, api_client, **kwargs)


# MetricConfig for auto-discovery
METRIC_CONFIG = MetricConfig(
    endpoint="",
    metric_class=Sleep,
    parser=parse_sleep_data,
    endpoint_builder=build_sleep_endpoint,
    requires_user_id=True,
    description="Comprehensive sleep data including stages, SpO2, respiration, and movement",
    version="1.0",
)

__metric_config__ = METRIC_CONFIG
