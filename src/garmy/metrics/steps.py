"""Steps Data Module.

===================

This module provides direct access to Garmin steps data from the Connect API.
Data includes daily step counts, step goals, total distance, and weekly aggregations.

Example:
    >>> from garmy import AuthClient, APIClient, MetricAccessorFactory
    >>> auth_client = AuthClient()
    >>> api_client = APIClient(auth_client=auth_client)
    >>> auth_client.login("email@example.com", "password")
    >>>
    >>> # Get weekly steps data
    >>> factory = MetricAccessorFactory(api_client)
    >>> metrics = factory.discover_and_create_all()
    >>> steps = metrics.get("steps").get()
    >>> print(f"Weekly total: {steps.weekly_total} steps")
    >>> print(f"Daily average: {steps.aggregations.daily_average} steps")
    >>>
    >>> # Access individual days
    >>> for day in steps.daily_steps:
    >>>     print(f"{day.calendar_date}: {day.total_steps:,} steps")

Data Source:
    Garmin Connect API endpoint:
    /usersummary-service/stats/daily/{start_date}/{end_date}
    ?statsType=STEPS&currentDate={current_date}
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Union

from ..core.base import MetricConfig
from ..core.utils import camel_to_snake_dict, format_date


@dataclass
class DailySteps:
    """Daily steps data from Garmin API."""

    calendar_date: str
    total_steps: int
    step_goal: int
    total_distance: int  # in meters

    @property
    def distance_km(self) -> float:
        """Get total distance in kilometers."""
        return self.total_distance / 1000

    @property
    def distance_miles(self) -> float:
        """Get total distance in miles."""
        return self.total_distance / 1609.344

    @property
    def date(self) -> datetime:
        """Convert calendar_date to datetime object."""
        return datetime.strptime(self.calendar_date, "%Y-%m-%d")


@dataclass
class StepsAggregations:
    """Weekly steps aggregations from Garmin API."""

    daily_average: int
    weekly_total: int


def build_steps_endpoint(
    date_input: Union[date, str, None] = None, days: int = 7, **kwargs: Any
) -> str:
    """Build the Steps API endpoint with proper date range."""
    if date_input is None:
        end_date = date.today()
    elif isinstance(date_input, str):
        end_date = datetime.strptime(date_input, "%Y-%m-%d").date()
    else:
        end_date = date_input

    start_date = end_date - timedelta(days=days - 1)

    start_str = format_date(start_date)
    end_str = format_date(end_date)
    current_str = format_date(end_date)

    return (
        f"/usersummary-service/stats/daily/{start_str}/{end_str}"
        f"?statsType=STEPS&currentDate={current_str}"
    )


def parse_steps_data(data: Dict[str, Any]) -> "Steps":
    """Parser for Steps API response using unified pattern."""
    # Convert camelCase to snake_case
    snake_dict = camel_to_snake_dict(data)

    # Ensure we have a dictionary to work with
    if not isinstance(snake_dict, dict):
        # Raise explicit error instead of silent fallback
        raise ValueError(
            f"Expected dictionary from API response but got {type(snake_dict).__name__}. "
            f"Raw data: {data}"
        )

    # Parse daily values
    daily_steps = []
    for item in snake_dict.get("values", []):
        calendar_date = item.get("calendar_date", "")
        values = item.get("values", {})

        daily_step = DailySteps(
            calendar_date=calendar_date,
            total_steps=values.get("total_steps", 0),
            step_goal=values.get("step_goal", 0),
            total_distance=values.get("total_distance", 0),
        )
        daily_steps.append(daily_step)

    # Parse aggregations
    agg_data = snake_dict.get("aggregations", {})
    aggregations = StepsAggregations(
        daily_average=int(agg_data.get("total_steps_average", 0)),
        weekly_total=int(agg_data.get("total_steps_weekly_average", 0)),
    )

    return Steps(daily_steps=daily_steps, aggregations=aggregations)


@dataclass
class Steps:
    """Steps data from Garmin Connect API.

    Raw steps data including daily step counts, goals, distances, and weekly aggregations.
    All data comes directly from Garmin's usersummary service.

    Attributes:
        daily_steps: List of daily step data with convenient access
        aggregations: Weekly averages and totals

    Example:
        >>> steps = garmy.steps.get()
        >>> print(f"Weekly total: {steps.weekly_total} steps")
        >>> print(f"Daily average: {steps.aggregations.daily_average} steps")
        >>>
        >>> # Access individual days
        >>> for day in steps.daily_steps:
        >>>     print(f"{day.calendar_date}: {day.total_steps:,} steps")
        >>>     print(f"  Distance: {day.distance_km:.1f} km")
    """

    daily_steps: List[DailySteps] = field(default_factory=list)
    aggregations: StepsAggregations = field(
        default_factory=lambda: StepsAggregations(0, 0)
    )

    def __str__(self) -> str:
        """Format steps data for human-readable display."""
        lines = []
        if self.weekly_total:
            lines.append(f"• Weekly total: {self.weekly_total:,} steps")
        if self.aggregations.daily_average:
            lines.append(f"• Daily average: {self.aggregations.daily_average:,} steps")
        if self.total_distance_km:
            lines.append(f"• Total distance: {self.total_distance_km:.1f} km")

        # Add recent daily data
        if self.daily_steps:
            lines.append(f"• Daily records: {len(self.daily_steps)} days")
            # Show last few days
            recent_days = (
                self.daily_steps[-3:] if len(self.daily_steps) > 3 else self.daily_steps
            )
            for day in recent_days:
                goal_text = f"/{day.step_goal:,}" if day.step_goal else ""
                lines.append(
                    f"  {day.calendar_date}: {day.total_steps:,}{goal_text} steps ({day.distance_km:.1f} km)"
                )

        return "\n".join(lines) if lines else "Steps data available"

    @property
    def weekly_total(self) -> int:
        """Get total steps from aggregations or calculate from daily values."""
        if self.aggregations.weekly_total > 0:
            return self.aggregations.weekly_total

        # Fallback: calculate from daily values
        return sum(day.total_steps for day in self.daily_steps)

    @property
    def total_distance_km(self) -> float:
        """Calculate total distance in kilometers from daily values."""
        return sum(day.distance_km for day in self.daily_steps)


# MetricConfig for auto-discovery
METRIC_CONFIG = MetricConfig(
    endpoint="",
    metric_class=Steps,
    parser=parse_steps_data,
    endpoint_builder=build_steps_endpoint,
    requires_user_id=False,
    description="Steps data including daily counts, goals, distances, and weekly aggregations",
    version="1.0",
)

__metric_config__ = METRIC_CONFIG
