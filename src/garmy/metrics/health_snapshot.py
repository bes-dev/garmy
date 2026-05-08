"""
Health Snapshot metric module.

This module provides access to Garmin Health Snapshot recordings, the on-demand
~2-minute multi-metric measurement (heart rate, respiration, stress, SpO2, HRV)
taken via the watch.

Health Snapshot uses a GraphQL POST endpoint on
`connectapi.garmin.com/graphql-gateway/graphql` and is range-based rather than
date-based. The Garmin GraphQL gateway enforces a maximum range of ~31 days per
call; the accessor's `range()` method auto-chunks larger windows.

Note: Health Snapshot uses a custom accessor class (HealthSnapshotAccessor) instead
of the standard MetricAccessor because it has a different API pattern (GraphQL POST,
range-based instead of date-based, and requires response unwrapping).
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Union

from ..core.exceptions import MetricDataError
from ..core.utils import format_date

DateInput = Union[date, str, None]


@dataclass
class HealthSnapshotSummary:
    """Per-metric summary stat for a single Health Snapshot recording.

    Each Health Snapshot includes 6 summary entries, one per measured metric.
    HEART_RATE, RESPIRATION, STRESS, and SPO2 carry min/max/avg values.
    RMSSD_HRV and SDRR_HRV only carry avg_value (min/max are None).

    Attributes:
        summary_type: One of HEART_RATE, RESPIRATION, STRESS, SPO2, RMSSD_HRV, SDRR_HRV
        min_value: Minimum value during the recording (None for HRV summary types)
        max_value: Maximum value during the recording (None for HRV summary types)
        avg_value: Average value during the recording
    """

    summary_type: str
    avg_value: float
    min_value: Optional[float] = None
    max_value: Optional[float] = None


@dataclass
class HealthSnapshotZone:
    """Per-zone time-in-zone for a single Health Snapshot recording.

    Each Health Snapshot reports time spent in 6 heart-rate zones (0..5).

    Attributes:
        zone_number: Zone index (0..5)
        millis_in_zone: Time spent in the zone, in milliseconds
        zone_low_boundary: Heart-rate threshold (BPM) for the lower bound of the zone
    """

    zone_number: int
    millis_in_zone: int
    zone_low_boundary: int


@dataclass
class HealthSnapshot:
    """Single Health Snapshot recording from Garmin Connect.

    A Health Snapshot is a ~2-minute on-demand measurement initiated from a
    compatible Garmin watch. It captures HR, respiration, stress, SpO2, and
    HRV (both RMSSD and SDRR) summary stats plus heart-rate zone time.

    Attributes:
        activity_uuid: Unique identifier for this snapshot recording
        calendar_date: ISO date string (YYYY-MM-DD) for the snapshot
        wellness_activity_type: Always "HEALTH_MONITORING" in observed data
        summaries: Per-metric summary stats (length 6)
        time_in_zone: Per-zone time data (length 6, zones 0..5)
        user_profile_pk: User profile primary key
        start_timestamp_gmt: Snapshot start time in GMT (ISO string)
        end_timestamp_gmt: Snapshot end time in GMT (ISO string)
        start_timestamp_local: Snapshot start time in local timezone (ISO string)
        end_timestamp_local: Snapshot end time in local timezone (ISO string)
        rule_pk: Optional rule identifier
        notes: Optional user-provided notes
        device_meta_data: Optional device metadata (watch model, firmware, etc.)

    Example:
        >>> snapshots = api_client.health_snapshots.latest(days=30)
        >>> for snap in snapshots:
        ...     print(f"{snap.calendar_date}: HR avg={snap.heart_rate.avg_value}, "
        ...           f"HRV={snap.rmssd_hrv.avg_value}ms")
    """

    activity_uuid: str
    calendar_date: str
    wellness_activity_type: str = "HEALTH_MONITORING"
    summaries: List[HealthSnapshotSummary] = field(default_factory=list)
    time_in_zone: List[HealthSnapshotZone] = field(default_factory=list)
    user_profile_pk: Optional[int] = None
    start_timestamp_gmt: Optional[str] = None
    end_timestamp_gmt: Optional[str] = None
    start_timestamp_local: Optional[str] = None
    end_timestamp_local: Optional[str] = None
    rule_pk: Optional[int] = None
    notes: Optional[str] = None
    device_meta_data: Optional[Dict[str, Any]] = None

    def _summary_by_type(self, summary_type: str) -> Optional[HealthSnapshotSummary]:
        for s in self.summaries:
            if s.summary_type == summary_type:
                return s
        return None

    @property
    def heart_rate(self) -> Optional[HealthSnapshotSummary]:
        """Heart rate summary (min/max/avg in BPM) for this snapshot."""
        return self._summary_by_type("HEART_RATE")

    @property
    def respiration(self) -> Optional[HealthSnapshotSummary]:
        """Respiration rate summary (min/max/avg in breaths/min)."""
        return self._summary_by_type("RESPIRATION")

    @property
    def stress(self) -> Optional[HealthSnapshotSummary]:
        """Stress level summary (min/max/avg, 0-100 scale)."""
        return self._summary_by_type("STRESS")

    @property
    def spo2(self) -> Optional[HealthSnapshotSummary]:
        """SpO2 summary (min/max/avg, percentage)."""
        return self._summary_by_type("SPO2")

    @property
    def rmssd_hrv(self) -> Optional[HealthSnapshotSummary]:
        """RMSSD HRV summary (avg only, in milliseconds)."""
        return self._summary_by_type("RMSSD_HRV")

    @property
    def sdrr_hrv(self) -> Optional[HealthSnapshotSummary]:
        """SDRR HRV summary (avg only, in milliseconds)."""
        return self._summary_by_type("SDRR_HRV")

    @property
    def calendar_date_obj(self) -> Optional[date]:
        """Parse calendar_date into a date object, or None if unparseable."""
        try:
            return datetime.strptime(self.calendar_date, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None


def _extract_uuid(raw_uuid: Any) -> str:
    """Extract a UUID string from Garmin's wrapped activityUuid format.

    Garmin returns activityUuid as a dict like {"uuid": "abc-..."}. Bare strings
    are also accepted as a fallback.
    """
    if isinstance(raw_uuid, dict):
        uuid_val = raw_uuid.get("uuid")
        if isinstance(uuid_val, str):
            return uuid_val
        return str(uuid_val) if uuid_val is not None else ""
    if isinstance(raw_uuid, str):
        return raw_uuid
    return ""


def _parse_summary_item(item: Dict[str, Any]) -> HealthSnapshotSummary:
    return HealthSnapshotSummary(
        summary_type=item.get("summaryType", ""),
        avg_value=float(item.get("avgValue", 0.0)),
        min_value=(
            float(item["minValue"]) if item.get("minValue") is not None else None
        ),
        max_value=(
            float(item["maxValue"]) if item.get("maxValue") is not None else None
        ),
    )


def _parse_zone_item(item: Dict[str, Any]) -> HealthSnapshotZone:
    return HealthSnapshotZone(
        zone_number=int(item.get("zoneNumber", 0)),
        millis_in_zone=int(item.get("millisInZone", 0)),
        zone_low_boundary=int(item.get("zoneLowBoundary", 0)),
    )


def _parse_single_snapshot(item: Dict[str, Any]) -> HealthSnapshot:
    return HealthSnapshot(
        activity_uuid=_extract_uuid(item.get("activityUuid")),
        calendar_date=item.get("calendarDate", ""),
        wellness_activity_type=item.get("wellnessActivityType", "HEALTH_MONITORING"),
        summaries=[
            _parse_summary_item(s) for s in (item.get("summaryTypeDataList") or [])
        ],
        time_in_zone=[
            _parse_zone_item(z) for z in (item.get("timeInZoneList") or [])
        ],
        user_profile_pk=item.get("userProfilePk"),
        start_timestamp_gmt=item.get("startTimestampGMT"),
        end_timestamp_gmt=item.get("endTimestampGMT"),
        start_timestamp_local=item.get("startTimestampLocal"),
        end_timestamp_local=item.get("endTimestampLocal"),
        rule_pk=item.get("rulePK"),
        notes=item.get("notes"),
        device_meta_data=item.get("deviceMetaData"),
    )


def parse_health_snapshots(raw_items: List[Dict[str, Any]]) -> List[HealthSnapshot]:
    """Parse the list inside data.healthSnapshotScalar into typed HealthSnapshot objects.

    Args:
        raw_items: List of snapshot dicts, as returned by the GraphQL endpoint
            under `data.healthSnapshotScalar`.

    Returns:
        List of HealthSnapshot dataclasses.
    """
    if not raw_items:
        return []
    return [_parse_single_snapshot(item) for item in raw_items if isinstance(item, dict)]


class HealthSnapshotAccessor:
    """Custom accessor for the Health Snapshot GraphQL endpoint.

    Health Snapshot data is fetched via POST to Garmin's GraphQL gateway
    (/graphql-gateway/graphql on connectapi.garmin.com). The endpoint accepts
    a date range and returns all snapshots within that range. The Garmin
    gateway enforces a maximum range of ~31 days per call; this accessor's
    `range()` method transparently chunks larger windows.

    Example:
        >>> from garmy import AuthClient, APIClient
        >>> api = APIClient(auth_client=AuthClient())
        >>> snapshots = api.health_snapshots.latest(days=30)
        >>> for s in snapshots:
        ...     print(s.calendar_date, s.heart_rate.avg_value)
    """

    GRAPHQL_PATH = "/graphql-gateway/graphql"
    MAX_RANGE_DAYS = 31

    def __init__(self, api_client: Any) -> None:
        """Initialize the accessor.

        Args:
            api_client: APIClient instance for making authenticated requests.
        """
        self.api_client = api_client

    def _build_query(self, start_date_str: str, end_date_str: str) -> Dict[str, str]:
        return {
            "query": (
                "query{healthSnapshotScalar("
                f'startDate:"{start_date_str}",'
                f'endDate:"{end_date_str}"'
                ")}"
            )
        }

    def raw(self, start_date: DateInput, end_date: DateInput) -> Dict[str, Any]:
        """Fetch the raw GraphQL response for a Health Snapshot date range.

        Args:
            start_date: Range start (date, ISO string, or None for today).
            end_date: Range end (date, ISO string, or None for today).

        Returns:
            Raw response dict with keys "data" and possibly "errors".

        Raises:
            APIError: If the HTTP request fails (non-2xx response).
        """
        start_str = format_date(start_date)
        end_str = format_date(end_date)
        body = self._build_query(start_str, end_str)
        resp = self.api_client.request(
            "POST",
            "connectapi",
            self.GRAPHQL_PATH,
            api=True,
            json=body,
        )
        try:
            data = resp.json()
        except ValueError as exc:
            raise MetricDataError(
                f"Health Snapshot response was not valid JSON: {exc}"
            ) from exc
        if not isinstance(data, dict):
            raise MetricDataError(
                f"Expected dict from GraphQL response, got {type(data).__name__}"
            )
        return data

    def get(
        self, start_date: DateInput, end_date: DateInput
    ) -> List[HealthSnapshot]:
        """Fetch parsed snapshots for a single ≤31-day window.

        For ranges longer than 31 days, use `range()` instead.

        Args:
            start_date: Range start (inclusive).
            end_date: Range end (inclusive).

        Returns:
            List of HealthSnapshot objects (may be empty).

        Raises:
            APIError: If the HTTP request fails.
            MetricDataError: If the GraphQL response contains errors or is
                shaped unexpectedly.
        """
        data = self.raw(start_date, end_date)
        if "errors" in data and data["errors"]:
            first_error = data["errors"][0]
            msg = (
                first_error.get("message", "unknown GraphQL error")
                if isinstance(first_error, dict)
                else str(first_error)
            )
            raise MetricDataError(f"Health Snapshot GraphQL error: {msg}")
        payload = data.get("data") or {}
        items = payload.get("healthSnapshotScalar") or []
        if not isinstance(items, list):
            raise MetricDataError(
                f"Expected list at data.healthSnapshotScalar, got {type(items).__name__}"
            )
        return parse_health_snapshots(items)

    def range(
        self, start_date: DateInput, end_date: DateInput
    ) -> List[HealthSnapshot]:
        """Fetch parsed snapshots for an arbitrary range, chunking ≤31-day windows.

        Snapshots are deduplicated by activity_uuid in case windows overlap.

        Args:
            start_date: Range start (inclusive).
            end_date: Range end (inclusive).

        Returns:
            List of HealthSnapshot objects covering the full range, sorted by
            start_timestamp_gmt ascending (None values last).
        """
        start = self._coerce_date(start_date)
        end = self._coerce_date(end_date)
        if start > end:
            return []
        seen: Dict[str, HealthSnapshot] = {}
        chunk_start = start
        while chunk_start <= end:
            chunk_end = min(chunk_start + timedelta(days=self.MAX_RANGE_DAYS - 1), end)
            for snap in self.get(chunk_start, chunk_end):
                if snap.activity_uuid:
                    seen[snap.activity_uuid] = snap
            chunk_start = chunk_end + timedelta(days=1)
        return sorted(
            seen.values(),
            key=lambda s: s.start_timestamp_gmt or "",
        )

    def latest(
        self, days: int = 30, limit: Optional[int] = None
    ) -> List[HealthSnapshot]:
        """Fetch the most recent snapshots within the last N days.

        Args:
            days: Number of days to look back from today (inclusive).
            limit: Optional cap on the number of results (most-recent first).

        Returns:
            List of HealthSnapshot objects sorted newest-first.
        """
        if days < 1:
            return []
        today = date.today()
        start = today - timedelta(days=days - 1)
        snaps = self.range(start, today)
        snaps.sort(key=lambda s: s.start_timestamp_gmt or "", reverse=True)
        if limit is not None:
            return snaps[:limit]
        return snaps

    def for_date(self, target_date: DateInput) -> List[HealthSnapshot]:
        """Fetch snapshots whose calendar_date matches the given date.

        Args:
            target_date: Target date (date object, ISO string, or None for today).

        Returns:
            List of HealthSnapshot objects with matching calendar_date.
        """
        target = self._coerce_date(target_date)
        target_iso = target.isoformat()
        return [
            s for s in self.get(target, target) if s.calendar_date == target_iso
        ]

    @staticmethod
    def _coerce_date(value: DateInput) -> date:
        if value is None:
            return date.today()
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, str):
            return datetime.strptime(value, "%Y-%m-%d").date()
        raise TypeError(
            f"Unsupported date input type: {type(value).__name__}"
        )


__all__ = [
    "HealthSnapshot",
    "HealthSnapshotAccessor",
    "HealthSnapshotSummary",
    "HealthSnapshotZone",
    "parse_health_snapshots",
]
