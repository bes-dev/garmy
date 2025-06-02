"""Calories Data Module.

=====================

This module provides direct access to Garmin calories data from the Connect API.
Data includes total calories burned, active calories, BMR calories, and calorie goals.

Example:
    >>> from garmy import AuthClient, APIClient, MetricAccessorFactory
    >>> auth_client = AuthClient()
    >>> api_client = APIClient(auth_client=auth_client)
    >>> auth_client.login("email@example.com", "password")
    >>>
    >>> # Get today's calories data
    >>> factory = MetricAccessorFactory(api_client)
    >>> metrics = factory.discover_and_create_all()
    >>> calories = metrics.get("calories").get()
    >>> print(f"Total calories: {calories.total_kilocalories}")
    >>> print(f"Active calories: {calories.active_kilocalories}")
    >>> print(f"BMR calories: {calories.bmr_kilocalories}")

Data Source:
    Garmin Connect API endpoint:
    /usersummary-service/usersummary/daily/{user_id}?calendarDate={date}
"""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Optional, Union

from ..core.base import MetricConfig
from ..core.endpoint_builders import build_calories_endpoint as _build_calories_endpoint
from ..core.utils import TimestampMixin, create_simple_field_parser


def build_calories_endpoint(
    date_input: Union[date, str, None] = None, api_client: Any = None, **kwargs: Any
) -> str:
    """Build the Calories API endpoint with user ID and date."""
    return _build_calories_endpoint(date_input, api_client, **kwargs)


@dataclass
class Calories(TimestampMixin):
    """Calories data from Garmin Connect API.

    Raw calories data including total burned, active, BMR, and goal information.
    All data comes directly from Garmin's usersummary service.

    Attributes:
        user_profile_id: User profile identifier
        calendar_date: Date of the data
        total_kilocalories: Total calories burned during the day
        active_kilocalories: Calories burned during active periods
        bmr_kilocalories: Basal metabolic rate calories
        wellness_kilocalories: Calories from wellness data
        burned_kilocalories: Total burned calories (if available)
        consumed_kilocalories: Calories consumed (if tracked)
        remaining_kilocalories: Remaining calories for the day
        wellness_active_kilocalories: Active calories from wellness data
        net_remaining_kilocalories: Net remaining calories
        net_calorie_goal: Daily calorie goal

    Example:
        >>> calories = garmy.calories.get()
        >>> print(f"Total: {calories.total_kilocalories} kcal")
        >>> print(f"Active: {calories.active_kilocalories} kcal")
        >>> print(f"BMR: {calories.bmr_kilocalories} kcal")
        >>> print(f"Efficiency: {calories.activity_efficiency:.1f}%")
    """

    user_profile_id: int = 0
    calendar_date: str = ""
    total_kilocalories: int = 0
    active_kilocalories: int = 0
    bmr_kilocalories: int = 0
    wellness_kilocalories: int = 0
    burned_kilocalories: Optional[int] = None
    consumed_kilocalories: Optional[int] = None
    remaining_kilocalories: Optional[int] = None
    wellness_active_kilocalories: int = 0
    net_remaining_kilocalories: int = 0
    net_calorie_goal: Optional[int] = None

    @property
    def date(self) -> datetime:
        """Convert calendar_date to datetime object."""
        return datetime.strptime(self.calendar_date, "%Y-%m-%d")

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

    @property
    def total_burned(self) -> int:
        """Get total burned calories, preferring burned_kilocalories over total_kilocalories."""
        return self.burned_kilocalories or self.total_kilocalories

    @property
    def calorie_balance(self) -> Optional[int]:
        """Calculate calorie balance (consumed - burned) if both are available."""
        if (
            self.consumed_kilocalories is not None
            and self.burned_kilocalories is not None
        ):
            return self.consumed_kilocalories - self.burned_kilocalories
        return None

    @property
    def goal_progress(self) -> Optional[float]:
        """Calculate progress towards calorie goal as percentage."""
        if self.net_calorie_goal and self.net_calorie_goal > 0:
            return (self.total_kilocalories / self.net_calorie_goal) * 100
        return None


# Create parser using factory function
parse_calories_data = create_simple_field_parser(Calories)

# MetricConfig for auto-discovery
METRIC_CONFIG = MetricConfig(
    endpoint="",
    metric_class=Calories,
    parser=parse_calories_data,
    endpoint_builder=build_calories_endpoint,
    requires_user_id=True,
    description="Calories data including total burned, active, BMR, and goal information",
    version="1.0",
)

__metric_config__ = METRIC_CONFIG
