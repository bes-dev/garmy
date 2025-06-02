"""
Training Readiness metric module.

This module provides access to Garmin training readiness data using the new
auto-discovery architecture. It contains both the data class definition and
the metric configuration for auto-discovery.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from ..core.base import MetricConfig


@dataclass
class TrainingReadiness:
    """Training Readiness data from Garmin Connect API.

    Raw training readiness data including overall score and contributing factors.
    All data comes directly from Garmin's training readiness service.

    Attributes:
        score: Overall training readiness score (0-100)
        level: Readiness level description (e.g., "READY", "MODERATE", "LOW")
        feedback_long: Detailed feedback text from Garmin
        feedback_short: Brief feedback summary from Garmin
        calendar_date: Date in YYYY-MM-DD format
        timestamp: UTC timestamp of the measurement
        user_profile_pk: Garmin user profile primary key
        device_id: ID of the device that recorded the data
        timestamp_local: Local timestamp of the measurement
        sleep_score: Sleep quality score (0-100) if available
        sleep_score_factor_percent: Sleep impact on readiness (percentage)
        sleep_score_factor_feedback: Text feedback about sleep impact
        sleep_history_factor_percent: Sleep history impact (percentage)
        sleep_history_factor_feedback: Text feedback about sleep history
        valid_sleep: Whether sleep data is valid for calculations
        hrv_factor_percent: HRV impact on readiness (percentage)
        hrv_factor_feedback: Text feedback about HRV impact
        hrv_weekly_average: Weekly average HRV value
        recovery_time: Estimated recovery time in hours
        recovery_time_factor_percent: Recovery impact on readiness (percentage)
        recovery_time_factor_feedback: Text feedback about recovery impact
        recovery_time_change_phrase: Description of recovery time changes
        acwr_factor_percent: Acute/chronic workload ratio impact (percentage)
        acwr_factor_feedback: Text feedback about training load impact
        acute_load: Current acute training load value
        stress_history_factor_percent: Stress history impact (percentage)
        stress_history_factor_feedback: Text feedback about stress impact
        input_context: Additional context about data inputs
        primary_activity_tracker: Whether this is the primary tracking device

    Example:
        >>> readiness = TrainingReadiness.get(date="2024-01-15")
        >>> print(f"Readiness: {readiness.readiness_summary}")
        >>> if readiness.sleep_score:
        ...     print(f"Sleep contributed {readiness.sleep_score_factor_percent}%")
    """

    # Core fields
    score: int
    level: str
    feedback_long: str
    feedback_short: str
    calendar_date: str
    timestamp: datetime

    # Profile and device info
    user_profile_pk: int
    device_id: int
    timestamp_local: Optional[datetime] = None

    # Sleep factors
    sleep_score: Optional[int] = None
    sleep_score_factor_percent: Optional[int] = None
    sleep_score_factor_feedback: Optional[str] = None
    sleep_history_factor_percent: Optional[int] = None
    sleep_history_factor_feedback: Optional[str] = None
    valid_sleep: Optional[bool] = None

    # HRV factors
    hrv_factor_percent: Optional[int] = None
    hrv_factor_feedback: Optional[str] = None
    hrv_weekly_average: Optional[int] = None

    # Recovery factors
    recovery_time: Optional[int] = None
    recovery_time_factor_percent: Optional[int] = None
    recovery_time_factor_feedback: Optional[str] = None
    recovery_time_change_phrase: Optional[str] = None

    # Training load factors
    acwr_factor_percent: Optional[int] = None
    acwr_factor_feedback: Optional[str] = None
    acute_load: Optional[int] = None

    # Stress factors
    stress_history_factor_percent: Optional[int] = None
    stress_history_factor_feedback: Optional[str] = None

    # Additional context
    input_context: Optional[str] = None
    primary_activity_tracker: Optional[bool] = None

    def __str__(self) -> str:
        """Format training readiness data for human-readable display."""
        lines = []
        if self.score:
            lines.append(f"• Readiness score: {self.score}/100")
        if self.level:
            lines.append(f"• Level: {self.level}")
        if self.feedback_short:
            lines.append(f"• Status: {self.feedback_short}")

        # Add contributing factors
        factors = []
        if self.sleep_score_factor_percent:
            factors.append(f"Sleep: {self.sleep_score_factor_percent}%")
        if self.hrv_factor_percent:
            factors.append(f"HRV: {self.hrv_factor_percent}%")
        if self.recovery_time_factor_percent:
            factors.append(f"Recovery: {self.recovery_time_factor_percent}%")
        if self.acwr_factor_percent:
            factors.append(f"Training load: {self.acwr_factor_percent}%")
        if self.stress_history_factor_percent:
            factors.append(f"Stress: {self.stress_history_factor_percent}%")

        if factors:
            lines.append(f"• Contributing factors: {', '.join(factors)}")

        if self.hrv_weekly_average:
            lines.append(f"• HRV weekly average: {self.hrv_weekly_average} ms")
        if self.recovery_time:
            lines.append(f"• Recovery time: {self.recovery_time} hours")

        return "\n".join(lines) if lines else "Training readiness data available"


def _create_default_training_readiness() -> TrainingReadiness:
    """Create a default TrainingReadiness object for empty/invalid data."""
    return TrainingReadiness(
        score=0,
        level="UNKNOWN",
        feedback_long="No data available",
        feedback_short="NO_DATA",
        calendar_date="1970-01-01",
        timestamp=datetime.fromtimestamp(0),
        user_profile_pk=0,
        device_id=0,
    )


# Create custom parser for training readiness (handles list response)
def parse_training_readiness_data(data: Any) -> TrainingReadiness:
    """Parse training readiness data from API response.

    Training readiness API returns a list with a single item containing the data.
    This parser extracts the first item and converts it to TrainingReadiness object.
    """
    from ..core.utils import camel_to_snake_dict

    # Handle case where API returns a list
    if isinstance(data, list):
        if not data:
            return _create_default_training_readiness()
        data = data[0]  # Take first item from list

    # Convert camelCase to snake_case
    snake_dict = camel_to_snake_dict(data)

    # Ensure we have a dictionary to work with
    if not isinstance(snake_dict, dict):
        raise ValueError(
            f"Expected dictionary from API response but got {type(snake_dict).__name__}. "
            f"Raw data: {data}"
        )

    # Filter to known fields only
    known_fields = {f.name for f in TrainingReadiness.__dataclass_fields__.values()}
    filtered_kwargs = {k: v for k, v in snake_dict.items() if k in known_fields}

    # Handle common datetime fields
    for field in ("timestamp", "timestamp_local"):
        if field in filtered_kwargs and isinstance(filtered_kwargs[field], str):
            try:
                from datetime import datetime

                filtered_kwargs[field] = datetime.fromisoformat(
                    filtered_kwargs[field].replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                filtered_kwargs[field] = None

    return TrainingReadiness(**filtered_kwargs)


# Declarative configuration for auto-discovery
METRIC_CONFIG = MetricConfig(
    endpoint="/metrics-service/metrics/trainingreadiness/{date}",
    metric_class=TrainingReadiness,
    parser=parse_training_readiness_data,
    description="Daily training readiness score and recommendations",
    version="1.0",
)

# Export for auto-discovery
__metric_config__ = METRIC_CONFIG
