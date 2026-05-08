"""Training Status metric module.

This module provides access to Garmin training status and training load data
from a single API endpoint. Covers both the training load balance (acute vs
chronic load) and the overall training status assessment.

Data Source:
    Garmin Connect API endpoint:
    /metrics-service/metrics/trainingstatus/aggregated/{date}

API Response Structure:
    The response nests data under device IDs:
    - mostRecentTrainingStatus.latestTrainingStatusData.{deviceId}
      - trainingStatus (int), trainingStatusFeedbackPhrase (str)
      - acuteTrainingLoadDTO: dailyTrainingLoadAcute, dailyTrainingLoadChronic,
        dailyAcuteChronicWorkloadRatio, acwrStatus
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from ..core.base import MetricConfig


# Garmin training status numeric code -> label mapping
STATUS_MAP: Dict[int, str] = {
    0: "NOT_APPLICABLE",
    1: "DETRAINING",
    2: "RECOVERY",
    3: "UNPRODUCTIVE",
    4: "MAINTAINING",
    5: "PRODUCTIVE",
    6: "PEAKING",
    7: "OVERREACHING",
}


@dataclass
class TrainingStatus:
    """Training status and load data from Garmin Connect API.

    Post-activity metric combining training load balance (acute/chronic) and
    overall training status. Updated after activities are synced.

    Attributes:
        calendar_date: Date string (YYYY-MM-DD)
        acute_load: 7-day rolling training load
        chronic_load: 28-day rolling training load
        load_balance: Acute/chronic load ratio
        load_type: Load classification (OPTIMAL, OVERREACHING, etc.)
        training_status: Numeric status code (see STATUS_MAP)
        training_status_feedback: Feedback phrase from API

    Example:
        >>> ts = garmy.training_status.get()
        >>> print(f"Status: {ts.status_label}")
        >>> print(f"Load balance: {ts.load_balance:.2f}")
    """

    calendar_date: str = ""
    acute_load: Optional[float] = None
    chronic_load: Optional[float] = None
    load_balance: Optional[float] = None
    load_type: Optional[str] = None
    training_status: Optional[int] = None
    training_status_feedback: Optional[str] = None

    @property
    def status_label(self) -> Optional[str]:
        """Resolve numeric training status to human-readable label."""
        if self.training_status is None:
            return None
        return STATUS_MAP.get(self.training_status, f"UNKNOWN_{self.training_status}")


def _get_first_device_data(nested: Any) -> Optional[Dict[str, Any]]:
    """Extract first device's data from a {deviceId: data} dict."""
    if not isinstance(nested, dict):
        return None
    for value in nested.values():
        if isinstance(value, dict):
            return value
    return None


def parse_training_status_data(data: Dict[str, Any]) -> TrainingStatus:
    """Parse training status API response into structured data.

    Actual API nests data under device IDs:
    - mostRecentTrainingStatus.latestTrainingStatusData.{deviceId}
    - mostRecentTrainingStatus.latestTrainingStatusData.{deviceId}.acuteTrainingLoadDTO
    """
    if not isinstance(data, dict):
        raise ValueError(
            f"Expected dictionary from API response but got {type(data).__name__}. "
            f"Raw data: {data}"
        )

    calendar_date = ""
    training_status = None
    training_status_feedback = None
    acute_load = None
    chronic_load = None
    load_balance = None
    load_type = None

    # Navigate: mostRecentTrainingStatus.latestTrainingStatusData.{deviceId}
    mrt = data.get("mostRecentTrainingStatus") or {}
    status_map = mrt.get("latestTrainingStatusData") or {}
    status_data = _get_first_device_data(status_map)

    if status_data:
        calendar_date = status_data.get("calendarDate", "")
        training_status = _to_int(status_data.get("trainingStatus"))
        training_status_feedback = status_data.get("trainingStatusFeedbackPhrase")

        # Extract load from nested acuteTrainingLoadDTO
        load_dto = status_data.get("acuteTrainingLoadDTO") or {}
        if isinstance(load_dto, dict):
            acute_load = _to_float(load_dto.get("dailyTrainingLoadAcute"))
            chronic_load = _to_float(load_dto.get("dailyTrainingLoadChronic"))
            load_balance = _to_float(
                load_dto.get("dailyAcuteChronicWorkloadRatio")
            )
            load_type = load_dto.get("acwrStatus")

    return TrainingStatus(
        calendar_date=calendar_date,
        acute_load=acute_load,
        chronic_load=chronic_load,
        load_balance=load_balance,
        load_type=load_type,
        training_status=training_status,
        training_status_feedback=training_status_feedback,
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


# Declarative configuration for auto-discovery
METRIC_CONFIG = MetricConfig(
    endpoint="/metrics-service/metrics/trainingstatus/aggregated/{date}",
    metric_class=TrainingStatus,
    parser=parse_training_status_data,
    description="Training status and load balance (acute/chronic load, status assessment)",
    version="1.0",
)

# Export for auto-discovery
__metric_config__ = METRIC_CONFIG
