"""Tests for Health Snapshot metric module: dataclasses, parser, and accessor."""

from datetime import date
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

import pytest

from garmy.core.exceptions import MetricDataError
from garmy.metrics.health_snapshot import (
    HealthSnapshot,
    HealthSnapshotAccessor,
    HealthSnapshotSummary,
    HealthSnapshotZone,
    parse_health_snapshots,
)


def make_snapshot_dict(
    activity_uuid: str = "abc-123",
    calendar_date: str = "2026-05-01",
    summaries: Optional[List[Dict[str, Any]]] = None,
    time_in_zone: Optional[List[Dict[str, Any]]] = None,
    **overrides: Any,
) -> Dict[str, Any]:
    """Build a realistic Health Snapshot dict matching the Garmin GraphQL response."""
    if summaries is None:
        summaries = [
            {"summaryType": "HEART_RATE",  "minValue": 60.0, "maxValue": 80.0, "avgValue": 68.5},
            {"summaryType": "RESPIRATION", "minValue": 12.0, "maxValue": 18.0, "avgValue": 14.2},
            {"summaryType": "STRESS",      "minValue": 20.0, "maxValue": 35.0, "avgValue": 27.0},
            {"summaryType": "SPO2",        "minValue": 96.0, "maxValue": 99.0, "avgValue": 97.5},
            {"summaryType": "RMSSD_HRV",   "avgValue": 45.0},
            {"summaryType": "SDRR_HRV",    "avgValue": 48.0},
        ]
    if time_in_zone is None:
        time_in_zone = [
            {"zoneNumber": i, "millisInZone": 1000 * i, "zoneLowBoundary": 60 + 10 * i}
            for i in range(6)
        ]
    snapshot = {
        "activityUuid": {"uuid": activity_uuid},
        "calendarDate": calendar_date,
        "wellnessActivityType": "HEALTH_MONITORING",
        "summaryTypeDataList": summaries,
        "timeInZoneList": time_in_zone,
        "userProfilePk": 12345,
        "startTimestampGMT": f"{calendar_date}T10:00:00.000",
        "startTimestampLocal": f"{calendar_date}T05:00:00.000",
        "endTimestampGMT": f"{calendar_date}T10:02:00.000",
        "endTimestampLocal": f"{calendar_date}T05:02:00.000",
        "rulePK": 1,
        "notes": None,
        "deviceMetaData": {"manufacturer": "garmin"},
    }
    snapshot.update(overrides)
    return snapshot


class TestParseHealthSnapshots:
    """Tests for the parser."""

    def test_parse_full_snapshot_returns_typed_object(self):
        raw = [make_snapshot_dict()]
        result = parse_health_snapshots(raw)

        assert len(result) == 1
        snap = result[0]
        assert isinstance(snap, HealthSnapshot)
        assert snap.activity_uuid == "abc-123"
        assert snap.calendar_date == "2026-05-01"
        assert snap.wellness_activity_type == "HEALTH_MONITORING"
        assert snap.user_profile_pk == 12345
        assert len(snap.summaries) == 6
        assert len(snap.time_in_zone) == 6
        assert all(isinstance(s, HealthSnapshotSummary) for s in snap.summaries)
        assert all(isinstance(z, HealthSnapshotZone) for z in snap.time_in_zone)

    def test_parse_handles_hrv_without_min_max(self):
        raw = [make_snapshot_dict()]
        snap = parse_health_snapshots(raw)[0]

        rmssd = snap.rmssd_hrv
        sdrr = snap.sdrr_hrv
        assert rmssd is not None
        assert rmssd.avg_value == 45.0
        assert rmssd.min_value is None
        assert rmssd.max_value is None
        assert sdrr is not None
        assert sdrr.avg_value == 48.0
        assert sdrr.min_value is None
        assert sdrr.max_value is None

    def test_convenience_properties(self):
        raw = [make_snapshot_dict()]
        snap = parse_health_snapshots(raw)[0]

        assert snap.heart_rate.avg_value == 68.5
        assert snap.heart_rate.min_value == 60.0
        assert snap.heart_rate.max_value == 80.0
        assert snap.respiration.avg_value == 14.2
        assert snap.stress.avg_value == 27.0
        assert snap.spo2.avg_value == 97.5

    def test_uuid_extraction_from_dict_wrapper(self):
        raw = [make_snapshot_dict(activity_uuid="dict-uuid-789")]
        snap = parse_health_snapshots(raw)[0]
        assert snap.activity_uuid == "dict-uuid-789"

    def test_uuid_extraction_from_bare_string(self):
        raw_dict = make_snapshot_dict()
        raw_dict["activityUuid"] = "bare-string-uuid"
        snap = parse_health_snapshots([raw_dict])[0]
        assert snap.activity_uuid == "bare-string-uuid"

    def test_empty_list_returns_empty_list(self):
        assert parse_health_snapshots([]) == []

    def test_zone_data_parsed_correctly(self):
        raw = [make_snapshot_dict()]
        snap = parse_health_snapshots(raw)[0]
        # Zones 0..5 inclusive
        zones_by_num = {z.zone_number: z for z in snap.time_in_zone}
        assert set(zones_by_num.keys()) == {0, 1, 2, 3, 4, 5}
        assert zones_by_num[3].millis_in_zone == 3000
        assert zones_by_num[3].zone_low_boundary == 90

    def test_calendar_date_obj_parses(self):
        raw = [make_snapshot_dict(calendar_date="2026-05-01")]
        snap = parse_health_snapshots(raw)[0]
        assert snap.calendar_date_obj == date(2026, 5, 1)

    def test_calendar_date_obj_returns_none_when_unparseable(self):
        raw = [make_snapshot_dict(calendar_date="not-a-date")]
        snap = parse_health_snapshots(raw)[0]
        assert snap.calendar_date_obj is None


def make_response(items, errors=None):
    """Build a fake requests.Response-like object with a .json() method."""
    body = {}
    if errors is not None:
        body["errors"] = errors
    if items is not None:
        body["data"] = {"healthSnapshotScalar": items}
    resp = MagicMock()
    resp.json.return_value = body
    resp.status_code = 200
    return resp


class TestHealthSnapshotAccessor:
    """Tests for HealthSnapshotAccessor methods."""

    def test_get_builds_correct_graphql_body(self):
        api_client = MagicMock()
        api_client.request.return_value = make_response([])
        accessor = HealthSnapshotAccessor(api_client)

        accessor.get(date(2026, 4, 1), date(2026, 4, 30))

        api_client.request.assert_called_once()
        call_args = api_client.request.call_args
        assert call_args.args[0] == "POST"
        assert call_args.args[1] == "connectapi"
        assert call_args.args[2] == "/graphql-gateway/graphql"
        assert call_args.kwargs["api"] is True
        body = call_args.kwargs["json"]
        assert "healthSnapshotScalar" in body["query"]
        assert 'startDate:"2026-04-01"' in body["query"]
        assert 'endDate:"2026-04-30"' in body["query"]

    def test_get_accepts_iso_string_dates(self):
        api_client = MagicMock()
        api_client.request.return_value = make_response([])
        accessor = HealthSnapshotAccessor(api_client)

        accessor.get("2026-04-01", "2026-04-30")

        body = api_client.request.call_args.kwargs["json"]
        assert 'startDate:"2026-04-01"' in body["query"]
        assert 'endDate:"2026-04-30"' in body["query"]

    def test_get_returns_parsed_snapshots(self):
        api_client = MagicMock()
        items = [make_snapshot_dict(activity_uuid="x"), make_snapshot_dict(activity_uuid="y")]
        api_client.request.return_value = make_response(items)
        accessor = HealthSnapshotAccessor(api_client)

        result = accessor.get(date(2026, 4, 1), date(2026, 4, 30))
        assert len(result) == 2
        assert {s.activity_uuid for s in result} == {"x", "y"}

    def test_get_raises_metric_data_error_on_graphql_errors(self):
        api_client = MagicMock()
        api_client.request.return_value = make_response(
            None, errors=[{"message": "Field 'foo' is undefined"}]
        )
        accessor = HealthSnapshotAccessor(api_client)

        with pytest.raises(MetricDataError, match="GraphQL error"):
            accessor.get(date(2026, 4, 1), date(2026, 4, 30))

    def test_empty_response_returns_empty_list(self):
        api_client = MagicMock()
        api_client.request.return_value = make_response([])
        accessor = HealthSnapshotAccessor(api_client)

        assert accessor.get(date(2026, 4, 1), date(2026, 4, 30)) == []

    def test_range_chunks_at_31_days_no_duplicates(self):
        api_client = MagicMock()
        # Each call returns one snapshot keyed by the *start* date passed in the query.
        # We track call count and return distinct UUIDs per call so we can verify
        # chunking + dedup.

        call_uuids: List[str] = []

        def request_side_effect(*args: Any, **kwargs: Any):
            # Extract the startDate from the GraphQL query for uniqueness
            body = kwargs.get("json") or {}
            query = body.get("query", "")
            start = query.split('startDate:"')[1].split('"')[0]
            call_uuids.append(start)
            return make_response([make_snapshot_dict(activity_uuid=f"snap-{start}")])

        api_client.request.side_effect = request_side_effect
        accessor = HealthSnapshotAccessor(api_client)

        # 90-day window — should produce 3 chunks (31+31+28)
        result = accessor.range(date(2026, 2, 6), date(2026, 5, 6))

        assert api_client.request.call_count == 3
        # 3 distinct UUIDs, no duplicates
        assert len({s.activity_uuid for s in result}) == 3
        # Chunk start dates should not overlap
        assert call_uuids == ["2026-02-06", "2026-03-09", "2026-04-09"]

    def test_range_dedupes_overlapping_uuids(self):
        api_client = MagicMock()
        # Both chunks return a snapshot with the same UUID — dedup should keep one.
        api_client.request.return_value = make_response(
            [make_snapshot_dict(activity_uuid="dup-uuid")]
        )
        accessor = HealthSnapshotAccessor(api_client)

        result = accessor.range(date(2026, 2, 6), date(2026, 5, 6))
        # Multiple chunks but same uuid each time -> 1 unique
        assert len(result) == 1
        assert result[0].activity_uuid == "dup-uuid"

    def test_range_empty_when_start_after_end(self):
        api_client = MagicMock()
        accessor = HealthSnapshotAccessor(api_client)

        result = accessor.range(date(2026, 5, 1), date(2026, 4, 1))
        assert result == []
        api_client.request.assert_not_called()

    def test_latest_returns_newest_first_with_limit(self):
        api_client = MagicMock()
        api_client.request.return_value = make_response([
            make_snapshot_dict(
                activity_uuid="old",
                startTimestampGMT="2026-04-01T10:00:00.000",
            ),
            make_snapshot_dict(
                activity_uuid="new",
                startTimestampGMT="2026-04-30T10:00:00.000",
            ),
            make_snapshot_dict(
                activity_uuid="mid",
                startTimestampGMT="2026-04-15T10:00:00.000",
            ),
        ])
        accessor = HealthSnapshotAccessor(api_client)

        result = accessor.latest(days=30, limit=2)
        assert [s.activity_uuid for s in result] == ["new", "mid"]

    def test_for_date_filters_by_calendar_date(self):
        api_client = MagicMock()
        api_client.request.return_value = make_response([
            make_snapshot_dict(activity_uuid="match-1", calendar_date="2026-05-01"),
            make_snapshot_dict(activity_uuid="other",   calendar_date="2026-05-02"),
            make_snapshot_dict(activity_uuid="match-2", calendar_date="2026-05-01"),
        ])
        accessor = HealthSnapshotAccessor(api_client)

        result = accessor.for_date(date(2026, 5, 1))
        assert {s.activity_uuid for s in result} == {"match-1", "match-2"}

    def test_raw_returns_dict_with_data(self):
        api_client = MagicMock()
        api_client.request.return_value = make_response([make_snapshot_dict()])
        accessor = HealthSnapshotAccessor(api_client)

        result = accessor.raw(date(2026, 4, 1), date(2026, 4, 30))
        assert "data" in result
        assert "healthSnapshotScalar" in result["data"]

    def test_invalid_date_type_raises(self):
        accessor = HealthSnapshotAccessor(MagicMock())
        with pytest.raises(TypeError, match="Unsupported date input"):
            accessor.range(123456, date(2026, 5, 1))


class TestUnitConversionEdgeCases:
    """Robustness tests for messy / edge-case inputs."""

    def test_parser_skips_non_dict_items(self):
        raw = [make_snapshot_dict(), "not a dict", 42, None]
        result = parse_health_snapshots(raw)
        assert len(result) == 1

    def test_parser_handles_missing_summary_types(self):
        snap = make_snapshot_dict(summaries=[])
        result = parse_health_snapshots([snap])[0]
        assert result.heart_rate is None
        assert result.rmssd_hrv is None

    def test_parser_handles_missing_time_in_zone(self):
        snap = make_snapshot_dict(time_in_zone=[])
        result = parse_health_snapshots([snap])[0]
        assert result.time_in_zone == []
