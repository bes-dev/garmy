"""Endurance Score metric module.

This module provides access to Garmin endurance score data including the
absolute score and classification level.

Data Source:
    Garmin Connect API endpoint:
    /metrics-service/metrics/endurancescore?startDate={date}&endDate={date}&aggregation=daily

API Response Structure:
    Flat dict (NOT wrapped in enduranceScoreDTO):
    - overallScore: absolute endurance score (e.g. 4508)
    - classification: numeric code (1-7)
    - calendarDate, feedbackPhrase, contributors, etc.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from ..core.base import MetricConfig
from ..core.endpoint_builders import build_endurance_score_endpoint


# Garmin endurance score classification numeric code -> label mapping
# Derived from API response field names: classificationLowerLimitIntermediate,
# classificationLowerLimitTrained, etc.
CLASSIFICATION_MAP: Dict[int, str] = {
    1: "RECREATIONAL",
    2: "INTERMEDIATE",
    3: "TRAINED",
    4: "WELL_TRAINED",
    5: "EXPERT",
    6: "SUPERIOR",
    7: "ELITE",
}


@dataclass
class EnduranceScore:
    """Endurance score data from Garmin Connect API.

    Post-activity metric that provides an overall endurance score with
    a classification level. Updated after long efforts.

    Attributes:
        calendar_date: Date string (YYYY-MM-DD)
        endurance_score: Absolute endurance score (e.g. 4508)
        endurance_score_classification: Numeric classification code (see CLASSIFICATION_MAP)

    Example:
        >>> es = garmy.endurance_score.get()
        >>> print(f"Score: {es.endurance_score} ({es.classification_label})")
    """

    calendar_date: str = ""
    endurance_score: Optional[float] = None
    endurance_score_classification: Optional[int] = None

    @property
    def classification_label(self) -> Optional[str]:
        """Resolve numeric classification to human-readable label."""
        if self.endurance_score_classification is None:
            return None
        return CLASSIFICATION_MAP.get(
            self.endurance_score_classification,
            f"UNKNOWN_{self.endurance_score_classification}",
        )


def parse_endurance_score_data(data: Dict[str, Any]) -> EnduranceScore:
    """Parse endurance score API response into structured data.

    The response is a flat dict with overallScore and classification fields.
    """
    if not isinstance(data, dict):
        raise ValueError(
            f"Expected dictionary from API response but got {type(data).__name__}. "
            f"Raw data: {data}"
        )

    calendar_date = data.get("calendarDate", "")
    endurance_score = _to_float(data.get("overallScore"))
    endurance_score_classification = _to_int(data.get("classification"))

    return EnduranceScore(
        calendar_date=calendar_date,
        endurance_score=endurance_score,
        endurance_score_classification=endurance_score_classification,
    )


def _to_float(value: Any) -> Optional[float]:
    """Safely convert a value to float."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _to_int(value: Any) -> Optional[int]:
    """Safely convert a value to int."""
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


# Declarative configuration for auto-discovery with endpoint builder
METRIC_CONFIG = MetricConfig(
    endpoint="/metrics-service/metrics/endurancescore",
    metric_class=EnduranceScore,
    parser=parse_endurance_score_data,
    endpoint_builder=build_endurance_score_endpoint,
    description="Endurance score with classification level",
    version="1.0",
)

# Export for auto-discovery
__metric_config__ = METRIC_CONFIG
