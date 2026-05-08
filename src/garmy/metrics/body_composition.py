"""Body Composition Data Module.

==================

This module provides direct access to Garmin body composition data from the Connect API.
Data includes weight, body fat percentage, muscle mass, bone mass, and other metrics
from compatible smart scales.

Example:
    >>> from garmy import AuthClient, APIClient
    >>> auth_client = AuthClient()
    >>> api_client = APIClient(auth_client=auth_client)
    >>> auth_client.login("email@example.com", "password")
    >>>
    >>> # Get body composition for date range
    >>> from datetime import date, timedelta
    >>> end = date.today()
    >>> start = end - timedelta(days=30)
    >>> bc = api_client.metrics.get("body_composition").get_range(start, end)
    >>> for m in bc.measurements:
    ...     print(f"{m.calendar_date}: {m.weight_kg:.1f} kg, {m.body_fat}% body fat")

Data Source:
    Garmin Connect API endpoint: /weight-service/weight/range
"""

from dataclasses import dataclass, field
from datetime import date as date_type
from datetime import timedelta
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from ..core.base import MetricConfig

if TYPE_CHECKING:
    pass


@dataclass
class BodyCompositionEntry:
    """Single body composition measurement from a smart scale.

    Attributes:
        sample_pk: Garmin's unique identifier for this measurement
        calendar_date: Date of the measurement (YYYY-MM-DD)
        weight: Weight in grams
        bmi: Body Mass Index
        body_fat: Body fat percentage
        body_water: Body water percentage
        bone_mass: Bone mass in grams
        muscle_mass: Muscle mass in grams
        visceral_fat: Visceral fat rating
        metabolic_age: Estimated metabolic age
        physique_rating: Physique rating score
        source_type: Source device type (e.g., "INDEX_SCALE")
        timestamp_gmt: Unix timestamp in milliseconds (GMT)
    """

    sample_pk: str
    calendar_date: str
    weight: float  # grams
    bmi: Optional[float] = None
    body_fat: Optional[float] = None  # percentage
    body_water: Optional[float] = None  # percentage
    bone_mass: Optional[float] = None  # grams
    muscle_mass: Optional[float] = None  # grams
    visceral_fat: Optional[float] = None
    metabolic_age: Optional[int] = None
    physique_rating: Optional[float] = None
    source_type: Optional[str] = None
    timestamp_gmt: Optional[int] = None

    @property
    def weight_kg(self) -> float:
        """Get weight in kilograms."""
        return self.weight / 1000 if self.weight else 0

    @property
    def weight_lbs(self) -> float:
        """Get weight in pounds."""
        return self.weight_kg * 2.20462

    @property
    def bone_mass_kg(self) -> Optional[float]:
        """Get bone mass in kilograms."""
        return self.bone_mass / 1000 if self.bone_mass else None

    @property
    def muscle_mass_kg(self) -> Optional[float]:
        """Get muscle mass in kilograms."""
        return self.muscle_mass / 1000 if self.muscle_mass else None

    @property
    def bmi_category(self) -> Optional[str]:
        """Get BMI category based on WHO classification.

        Returns:
            Category string: "underweight", "normal", "overweight", or "obese"
        """
        if not self.bmi:
            return None
        if self.bmi < 18.5:
            return "underweight"
        elif self.bmi < 25:
            return "normal"
        elif self.bmi < 30:
            return "overweight"
        return "obese"


@dataclass
class BodyComposition:
    """Body composition data from Garmin weight service.

    Contains all body composition measurements for a date range,
    along with average values.

    Attributes:
        measurements: List of body composition entries
        total_average: Average values across the date range
    """

    measurements: List[BodyCompositionEntry] = field(default_factory=list)
    total_average: Optional[Dict[str, Any]] = None

    def __str__(self) -> str:
        """Format body composition for human-readable display."""
        if not self.measurements:
            return "No body composition data available"

        lines = [f"Body Composition: {len(self.measurements)} measurement(s)"]

        # Show most recent
        latest = self.measurements[-1]
        lines.append(f"  Latest ({latest.calendar_date}):")
        lines.append(
            f"    Weight: {latest.weight_kg:.1f} kg ({latest.weight_lbs:.1f} lbs)"
        )
        if latest.body_fat:
            lines.append(f"    Body Fat: {latest.body_fat}%")
        if latest.muscle_mass_kg:
            lines.append(f"    Muscle Mass: {latest.muscle_mass_kg:.1f} kg")
        if latest.bmi:
            lines.append(f"    BMI: {latest.bmi:.1f} ({latest.bmi_category})")

        return "\n".join(lines)

    @property
    def latest(self) -> Optional[BodyCompositionEntry]:
        """Get the most recent measurement."""
        return self.measurements[-1] if self.measurements else None


def parse_body_composition(data: Dict[str, Any]) -> BodyComposition:
    """Parse body composition API response.

    Args:
        data: Raw API response from /weight-service/weight/range/

    Returns:
        BodyComposition object with parsed measurements
    """
    measurements = []

    for summary in data.get("dailyWeightSummaries", []):
        latest = summary.get("latestWeight")
        if latest and latest.get("samplePk"):
            measurements.append(
                BodyCompositionEntry(
                    sample_pk=str(latest.get("samplePk", "")),
                    calendar_date=latest.get("calendarDate", ""),
                    weight=latest.get("weight", 0),
                    bmi=latest.get("bmi"),
                    body_fat=latest.get("bodyFat"),
                    body_water=latest.get("bodyWater"),
                    bone_mass=latest.get("boneMass"),
                    muscle_mass=latest.get("muscleMass"),
                    visceral_fat=latest.get("visceralFat"),
                    metabolic_age=latest.get("metabolicAge"),
                    physique_rating=latest.get("physiqueRating"),
                    source_type=latest.get("sourceType"),
                    timestamp_gmt=latest.get("timestampGMT"),
                )
            )

    return BodyComposition(
        measurements=measurements, total_average=data.get("totalAverage")
    )


def build_body_composition_endpoint(
    start_date: Union[date_type, str, None] = None,
    end_date: Union[date_type, str, None] = None,
    api_client: Any = None,
    **kwargs: Any,
) -> str:
    """Build body composition endpoint with date range.

    Args:
        start_date: Start of date range (default: 30 days ago)
        end_date: End of date range (default: today)
        api_client: API client (unused but required by interface)
        **kwargs: Additional arguments (unused)

    Returns:
        Endpoint URL string
    """
    if end_date is None:
        end_date = date_type.today()
    elif isinstance(end_date, str):
        end_date = date_type.fromisoformat(end_date)

    if start_date is None:
        start_date = end_date - timedelta(days=30)
    elif isinstance(start_date, str):
        start_date = date_type.fromisoformat(start_date)

    return f"/weight-service/weight/range/{start_date}/{end_date}"


# MetricConfig for auto-discovery
METRIC_CONFIG = MetricConfig(
    endpoint="",
    metric_class=BodyComposition,
    parser=parse_body_composition,
    endpoint_builder=build_body_composition_endpoint,
    requires_user_id=False,
    description="Body composition data including weight, body fat, muscle mass from smart scales",
    version="1.0",
)

__metric_config__ = METRIC_CONFIG
