"""
Activities metric module.

This module provides access to Garmin activity data using the new auto-discovery
architecture. It contains the data class definitions, custom accessor, and
metric configuration for auto-discovery.

Note: Activities uses a custom accessor class instead of the standard MetricAccessor
because it has a different API pattern (list-based rather than date-based).
"""

from dataclasses import dataclass, field
from datetime import datetime
from functools import lru_cache
from typing import Any, Dict, List, Optional

from ..core.base import MetricConfig
from ..core.utils import TimestampMixin, create_list_parser


@dataclass
class ActivitySummary(TimestampMixin):
    """Basic activity summary from Garmin Connect API.

    Raw activity data including type, duration, heart rate, and timing information.
    All data comes directly from Garmin's activitylist service.

    Attributes:
        activity_id: Unique activity identifier
        activity_name: User-defined activity name
        start_time_local: Activity start time in local timezone
        start_time_gmt: Activity start time in GMT
        activity_type: Activity type information (raw dict)
        event_type: Event type information (raw dict)
        duration: Activity duration in seconds
        elapsed_duration: Total elapsed time in seconds
        moving_duration: Moving time in seconds
        owner_id: Owner's user ID
        owner_display_name: Owner's display name
        owner_full_name: Owner's full name
        average_hr: Average heart rate (if available)
        max_hr: Maximum heart rate (if available)
        sport_type_id: Sport type identifier
        device_id: Device identifier
        manufacturer: Device manufacturer
        lap_count: Number of laps
        has_polyline: Whether activity has GPS track
        has_images: Whether activity has images
        privacy: Privacy settings (raw dict)
        begin_timestamp: Activity start timestamp (milliseconds)
        end_time_gmt: Activity end time in GMT
        auto_calc_calories: Whether calories were auto-calculated
        manual_activity: Whether activity was manually entered
        favorite: Whether activity is marked as favorite

        # Optional training metrics
        aerobic_training_effect: Aerobic training effect
        anaerobic_training_effect: Anaerobic training effect
        training_effect_label: Training effect description
        activity_training_load: Training load value

        # Optional wellness metrics
        avg_stress: Average stress level during activity
        start_stress: Stress level at activity start
        end_stress: Stress level at activity end
        max_stress: Maximum stress level during activity
        difference_stress: Stress level change
        difference_body_battery: Body battery change

        # Optional respiration metrics
        min_respiration_rate: Minimum respiration rate
        max_respiration_rate: Maximum respiration rate
        avg_respiration_rate: Average respiration rate

    Example:
        >>> activity = garmy.activities.list()[0]
        >>> print(f"Name: {activity.activity_name}")
        >>> print(f"Type: {activity.activity_type_name}")
        >>> print(f"Duration: {activity.duration_minutes:.1f} minutes")
        >>> print(f"Heart Rate: {activity.average_hr} bpm")
        >>> print(f"Date: {activity.start_date}")
    """

    activity_id: int = 0
    activity_name: str = ""
    start_time_local: str = ""
    start_time_gmt: str = ""
    activity_type: Dict[str, Any] = field(default_factory=dict)
    event_type: Dict[str, Any] = field(default_factory=dict)
    duration: float = 0.0
    elapsed_duration: float = 0.0
    moving_duration: float = 0.0
    owner_id: int = 0
    owner_display_name: str = ""
    owner_full_name: str = ""
    average_hr: Optional[float] = None
    max_hr: Optional[float] = None
    sport_type_id: int = 0
    device_id: Optional[int] = None
    manufacturer: str = ""
    lap_count: int = 0
    has_polyline: bool = False
    has_images: bool = False
    privacy: Dict[str, Any] = field(default_factory=dict)
    begin_timestamp: int = 0
    end_time_gmt: str = ""
    auto_calc_calories: bool = False
    manual_activity: bool = False
    favorite: bool = False

    # Training metrics (optional)
    aerobic_training_effect: float = 0.0
    anaerobic_training_effect: float = 0.0
    training_effect_label: str = ""
    activity_training_load: float = 0.0

    # Wellness metrics (optional)
    avg_stress: Optional[float] = None
    start_stress: Optional[float] = None
    end_stress: Optional[float] = None
    max_stress: Optional[float] = None
    difference_stress: Optional[float] = None
    difference_body_battery: Optional[int] = None

    # Respiration metrics (optional)
    min_respiration_rate: Optional[float] = None
    max_respiration_rate: Optional[float] = None
    avg_respiration_rate: Optional[float] = None

    def __post_init__(self) -> None:
        """Initialize default values for nested dicts."""
        # These checks are no longer needed since we use field(default_factory=dict)
        pass

    @property
    def activity_type_name(self) -> str:
        """Get activity type name from activity_type dict."""
        return str(self.activity_type.get("typeKey", "unknown"))

    @property
    def activity_type_id(self) -> int:
        """Get activity type ID from activity_type dict."""
        return int(self.activity_type.get("typeId", 0))

    @property
    def duration_minutes(self) -> float:
        """Get activity duration in minutes."""
        return self.duration / 60

    @property
    def duration_hours(self) -> float:
        """Get activity duration in hours."""
        return self.duration / 3600

    @property
    def moving_duration_minutes(self) -> float:
        """Get moving duration in minutes."""
        return self.moving_duration / 60

    @property
    def start_datetime_local(self) -> Optional[datetime]:
        """Convert start_time_local to datetime object (cached using module-level cache)."""
        return _parse_datetime_cached(self.start_time_local)

    @property
    def start_datetime_gmt(self) -> Optional[datetime]:
        """Convert start_time_gmt to datetime object (cached using module-level cache)."""
        return _parse_datetime_cached(self.start_time_gmt)

    @property
    def start_date(self) -> str:
        """Get activity start date in YYYY-MM-DD format."""
        dt = self.start_datetime_local
        return dt.strftime("%Y-%m-%d") if dt else ""

    @property
    def privacy_type(self) -> str:
        """Get privacy type from privacy dict."""
        return str(self.privacy.get("typeKey", "unknown"))

    @property
    def heart_rate_range(self) -> Optional[float]:
        """Get heart rate range (max - average) if both available."""
        if self.max_hr is not None and self.average_hr is not None:
            return self.max_hr - self.average_hr
        return None

    @property
    def has_heart_rate(self) -> bool:
        """Check if activity has heart rate data."""
        return self.average_hr is not None and self.average_hr > 0

    @property
    def has_stress_data(self) -> bool:
        """Check if activity has stress data."""
        return self.avg_stress is not None

    @property
    def has_respiration_data(self) -> bool:
        """Check if activity has respiration data."""
        return self.avg_respiration_rate is not None

    @property
    def stress_impact(self) -> Optional[str]:
        """Categorize stress impact during activity."""
        if self.difference_stress is None:
            return None

        if self.difference_stress < -5:
            return "stress_reducing"
        elif self.difference_stress > 5:
            return "stress_increasing"
        else:
            return "stress_neutral"


# Module-level datetime caching function
@lru_cache(maxsize=None)  # Size set dynamically by config
def _parse_datetime_cached(datetime_str: Optional[str]) -> Optional[datetime]:
    """Parse datetime string with LRU caching to avoid repeated strptime calls.

    Args:
        datetime_str: Datetime string in format '%Y-%m-%d %H:%M:%S'

    Returns:
        Parsed datetime object or None if parsing fails
    """
    if not datetime_str:
        return None

    try:
        return datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return None


# Create parser using factory function for list data
parse_activities_data = create_list_parser(ActivitySummary)


class ActivitiesAccessor:
    """Simplified accessor for Activities API with list-based interface."""

    def __init__(self, api_client: Any) -> None:
        """Initialize Activities accessor.

        Args:
            api_client: API client for making requests.
        """
        self.api_client = api_client
        self.parse_func = parse_activities_data

    def raw(self, limit: int = 20, start: int = 0, sort_order: str = "desc") -> Any:
        """Get raw API response for activities data.

        Args:
            limit: Maximum number of activities to return
            start: Starting offset for pagination
            sort_order: Sort order - "asc" for oldest first, "desc" for newest first (default)
        """
        endpoint = f"/activitylist-service/activities/search/activities?limit={limit}&start={start}&sortOrder={sort_order}"
        try:
            return self.api_client.connectapi(endpoint)
        except (SystemExit, KeyboardInterrupt, GeneratorExit):
            raise
        except Exception as e:
            from ..core.utils import handle_api_exception

            return handle_api_exception(e, "fetching Activities", endpoint, [])

    def list(self, limit: int = 20, start: int = 0, sort_order: str = "desc") -> List[ActivitySummary]:
        """Get parsed activities data.

        Args:
            limit: Maximum number of activities to return (default: 20)
            start: Starting offset for pagination (default: 0)
            sort_order: Sort order - "asc" for oldest first, "desc" for newest first (default)

        Returns:
            List of ActivitySummary objects
        """
        raw_data = self.raw(limit, start, sort_order)
        if not raw_data:
            return []
        result = self.parse_func(raw_data)
        # parse_func should return List[ActivitySummary] since it's created by create_list_parser
        return list(result) if result else []

    def get_recent(self, days: int = 7, limit: int = 50) -> List[ActivitySummary]:
        """Get recent activities from the last N days."""
        from datetime import date, timedelta

        activities = self.list(limit=limit)
        if not activities:
            return []

        cutoff_date = date.today() - timedelta(days=days)

        # Optimized filtering using list comprehension and cached datetime parsing
        def is_recent_activity(activity: ActivitySummary) -> bool:
            # Use cached datetime property instead of repeated parsing
            start_dt = activity.start_datetime_local
            if start_dt:
                return start_dt.date() >= cutoff_date
            return False

        # Filter activities efficiently in single pass
        return [activity for activity in activities if is_recent_activity(activity)]

    def get_by_type(self, activity_type: str, limit: int = 50) -> List[ActivitySummary]:
        """Get activities filtered by type."""
        activities = self.list(limit=limit)
        return [
            activity
            for activity in activities
            if activity.activity_type_name.lower() == activity_type.lower()
        ]

    # For compatibility with MetricAccessor interface
    def get(self, *_args: Any, **_kwargs: Any) -> Any:
        """Not applicable for Activities - use list() instead."""
        return self.list()


# Create a special accessor factory function for activities
def create_activities_accessor(api_client: Any) -> ActivitiesAccessor:
    """Create activities accessor using factory pattern."""
    return ActivitiesAccessor(api_client)


# Declarative configuration for auto-discovery with custom accessor factory
# Note: Activities is special and doesn't use the standard MetricAccessor pattern
METRIC_CONFIG = MetricConfig(
    endpoint="/activitylist-service/activities/search/activities",
    metric_class=ActivitySummary,
    parser=parse_activities_data,
    description="Activity summaries with performance and wellness metrics",
    version="1.0",
)

# Export for auto-discovery
__metric_config__ = METRIC_CONFIG

# Special flag to indicate this metric needs custom accessor handling
__custom_accessor_factory__ = create_activities_accessor
