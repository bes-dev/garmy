"""Tests for Health Snapshot localdb integration: extractor, DB store, sync."""

from datetime import date
from pathlib import Path
from typing import List
from unittest.mock import MagicMock

from garmy.localdb.db import HealthDB
from garmy.localdb.extractors import DataExtractor
from garmy.localdb.models import (
    HealthSnapshotRecord,
    HealthSnapshotSummaryStat,
    HealthSnapshotZoneTime,
    MetricType,
)
from garmy.localdb.sync import SyncManager
from garmy.metrics.health_snapshot import (
    HealthSnapshot,
    HealthSnapshotSummary,
    HealthSnapshotZone,
)


def make_snapshot(
    activity_uuid: str = "uuid-1",
    calendar_date: str = "2026-05-01",
) -> HealthSnapshot:
    """Build a fully-populated HealthSnapshot dataclass."""
    return HealthSnapshot(
        activity_uuid=activity_uuid,
        calendar_date=calendar_date,
        wellness_activity_type="HEALTH_MONITORING",
        summaries=[
            HealthSnapshotSummary("HEART_RATE",  68.5, 60.0, 80.0),
            HealthSnapshotSummary("RESPIRATION", 14.2, 12.0, 18.0),
            HealthSnapshotSummary("STRESS",      27.0, 20.0, 35.0),
            HealthSnapshotSummary("SPO2",        97.5, 96.0, 99.0),
            HealthSnapshotSummary("RMSSD_HRV",   45.0),
            HealthSnapshotSummary("SDRR_HRV",    48.0),
        ],
        time_in_zone=[
            HealthSnapshotZone(i, 1000 * i, 60 + 10 * i) for i in range(6)
        ],
        user_profile_pk=12345,
        start_timestamp_gmt=f"{calendar_date}T10:00:00.000",
        end_timestamp_gmt=f"{calendar_date}T10:02:00.000",
        start_timestamp_local=f"{calendar_date}T05:00:00.000",
        end_timestamp_local=f"{calendar_date}T05:02:00.000",
        rule_pk=1,
        notes=None,
        device_meta_data={"manufacturer": "garmin"},
    )


class TestExtractor:
    """Tests for DataExtractor.extract_health_snapshots."""

    def test_extract_returns_three_keyed_lists(self):
        extractor = DataExtractor()
        result = extractor.extract_health_snapshots([make_snapshot()])

        assert set(result.keys()) == {"records", "summaries", "zones"}
        assert len(result["records"]) == 1
        assert len(result["summaries"]) == 6
        assert len(result["zones"]) == 6

    def test_extract_record_fields(self):
        extractor = DataExtractor()
        snap = make_snapshot(activity_uuid="abc", calendar_date="2026-04-15")
        result = extractor.extract_health_snapshots([snap])

        record = result["records"][0]
        assert record["activity_uuid"] == "abc"
        assert record["calendar_date"] == date(2026, 4, 15)
        assert record["wellness_activity_type"] == "HEALTH_MONITORING"
        assert record["user_profile_pk"] == 12345
        assert record["device_meta_data"] == {"manufacturer": "garmin"}

    def test_extract_summary_rows_keyed_by_uuid(self):
        extractor = DataExtractor()
        snap = make_snapshot(activity_uuid="my-uuid")
        result = extractor.extract_health_snapshots([snap])

        for s in result["summaries"]:
            assert s["activity_uuid"] == "my-uuid"

        types = {s["summary_type"] for s in result["summaries"]}
        assert types == {"HEART_RATE", "RESPIRATION", "STRESS", "SPO2", "RMSSD_HRV", "SDRR_HRV"}

    def test_extract_hrv_min_max_are_none(self):
        extractor = DataExtractor()
        result = extractor.extract_health_snapshots([make_snapshot()])

        rmssd = next(s for s in result["summaries"] if s["summary_type"] == "RMSSD_HRV")
        assert rmssd["min_value"] is None
        assert rmssd["max_value"] is None
        assert rmssd["avg_value"] == 45.0

    def test_extract_zone_rows_match_uuid(self):
        extractor = DataExtractor()
        snap = make_snapshot(activity_uuid="zone-uuid")
        result = extractor.extract_health_snapshots([snap])

        for z in result["zones"]:
            assert z["activity_uuid"] == "zone-uuid"
        zones_by_num = {z["zone_number"]: z for z in result["zones"]}
        assert set(zones_by_num.keys()) == {0, 1, 2, 3, 4, 5}
        assert zones_by_num[3]["millis_in_zone"] == 3000

    def test_extract_skips_snapshots_without_uuid(self):
        extractor = DataExtractor()
        snap = make_snapshot()
        snap.activity_uuid = ""  # blank uuid
        result = extractor.extract_health_snapshots([snap])
        assert result["records"] == []
        assert result["summaries"] == []
        assert result["zones"] == []

    def test_extract_handles_unparseable_calendar_date(self):
        extractor = DataExtractor()
        snap = make_snapshot()
        snap.calendar_date = "not-a-date"
        result = extractor.extract_health_snapshots([snap])
        assert result["records"][0]["calendar_date"] is None


class TestHealthDBStore:
    """Tests for HealthDB.store_health_snapshot / health_snapshot_exists."""

    def test_store_and_exists(self, tmp_path: Path):
        db = HealthDB(tmp_path / "test.db")

        extractor = DataExtractor()
        snap = make_snapshot(activity_uuid="store-uuid")
        extracted = extractor.extract_health_snapshots([snap])

        # Initially absent
        assert db.health_snapshot_exists(1, "store-uuid") is False

        db.store_health_snapshot(
            1,
            extracted["records"][0],
            extracted["summaries"],
            extracted["zones"],
        )

        assert db.health_snapshot_exists(1, "store-uuid") is True

    def test_store_writes_three_table_rows(self, tmp_path: Path):
        db = HealthDB(tmp_path / "test.db")

        extractor = DataExtractor()
        snap = make_snapshot(activity_uuid="rows-uuid")
        extracted = extractor.extract_health_snapshots([snap])

        db.store_health_snapshot(
            1,
            extracted["records"][0],
            extracted["summaries"],
            extracted["zones"],
        )

        with db.get_session() as session:
            assert (
                session.query(HealthSnapshotRecord)
                .filter(HealthSnapshotRecord.activity_uuid == "rows-uuid")
                .count()
                == 1
            )
            assert (
                session.query(HealthSnapshotSummaryStat)
                .filter(HealthSnapshotSummaryStat.activity_uuid == "rows-uuid")
                .count()
                == 6
            )
            assert (
                session.query(HealthSnapshotZoneTime)
                .filter(HealthSnapshotZoneTime.activity_uuid == "rows-uuid")
                .count()
                == 6
            )

    def test_resync_is_idempotent(self, tmp_path: Path):
        db = HealthDB(tmp_path / "test.db")

        extractor = DataExtractor()
        snap = make_snapshot(activity_uuid="dup-uuid")
        extracted = extractor.extract_health_snapshots([snap])

        # Store twice
        db.store_health_snapshot(1, extracted["records"][0], extracted["summaries"], extracted["zones"])
        db.store_health_snapshot(1, extracted["records"][0], extracted["summaries"], extracted["zones"])

        # Should still be exactly one record / 6 summaries / 6 zones
        with db.get_session() as session:
            assert (
                session.query(HealthSnapshotRecord)
                .filter(HealthSnapshotRecord.activity_uuid == "dup-uuid")
                .count()
                == 1
            )
            assert (
                session.query(HealthSnapshotSummaryStat)
                .filter(HealthSnapshotSummaryStat.activity_uuid == "dup-uuid")
                .count()
                == 6
            )

    def test_store_parses_iso_timestamps(self, tmp_path: Path):
        db = HealthDB(tmp_path / "test.db")

        extractor = DataExtractor()
        snap = make_snapshot()
        extracted = extractor.extract_health_snapshots([snap])

        db.store_health_snapshot(1, extracted["records"][0], extracted["summaries"], extracted["zones"])

        with db.get_session() as session:
            stored = (
                session.query(HealthSnapshotRecord)
                .filter(HealthSnapshotRecord.user_id == 1)
                .first()
            )
            assert stored is not None
            assert stored.start_timestamp_gmt is not None
            assert stored.start_timestamp_gmt.year == 2026
            assert stored.start_timestamp_gmt.month == 5
            assert stored.start_timestamp_gmt.day == 1


class TestSyncManagerBatch:
    """Tests for SyncManager._sync_health_snapshot_batch."""

    def _build_manager(self, tmp_path: Path, snapshots: List[HealthSnapshot]) -> SyncManager:
        manager = SyncManager(db_path=tmp_path / "sync.db")
        # Mock the api_client and its health_snapshots accessor
        manager.api_client = MagicMock()
        manager.api_client.health_snapshots.range.return_value = snapshots
        return manager

    def test_batch_writes_snapshots(self, tmp_path: Path):
        manager = self._build_manager(tmp_path, [
            make_snapshot(activity_uuid="batch-1"),
            make_snapshot(activity_uuid="batch-2"),
        ])
        stats = {"completed": 0, "skipped": 0, "failed": 0, "total_tasks": 1}

        manager._sync_health_snapshot_batch(
            user_id=1,
            start_date=date(2026, 4, 1),
            end_date=date(2026, 5, 1),
            stats=stats,
        )

        assert stats["completed"] == 2
        assert stats["skipped"] == 0
        assert stats["failed"] == 0
        assert manager.db.health_snapshot_exists(1, "batch-1")
        assert manager.db.health_snapshot_exists(1, "batch-2")

    def test_batch_skips_already_existing(self, tmp_path: Path):
        # First populate with one snapshot
        first_run_snaps = [make_snapshot(activity_uuid="exists-1")]
        manager = self._build_manager(tmp_path, first_run_snaps)
        stats = {"completed": 0, "skipped": 0, "failed": 0, "total_tasks": 1}
        manager._sync_health_snapshot_batch(1, date(2026, 4, 1), date(2026, 5, 1), stats)
        assert stats["completed"] == 1

        # Re-run with same UUID + a new one
        manager.api_client.health_snapshots.range.return_value = [
            make_snapshot(activity_uuid="exists-1"),
            make_snapshot(activity_uuid="new-2"),
        ]
        stats = {"completed": 0, "skipped": 0, "failed": 0, "total_tasks": 1}
        manager._sync_health_snapshot_batch(1, date(2026, 4, 1), date(2026, 5, 1), stats)
        assert stats["completed"] == 1  # only the new one
        assert stats["skipped"] == 1    # the existing one

    def test_batch_handles_empty_response(self, tmp_path: Path):
        manager = self._build_manager(tmp_path, [])
        stats = {"completed": 0, "skipped": 0, "failed": 0, "total_tasks": 1}

        manager._sync_health_snapshot_batch(
            user_id=1,
            start_date=date(2026, 4, 1),
            end_date=date(2026, 5, 1),
            stats=stats,
        )

        assert stats["completed"] == 0
        assert stats["failed"] == 0

    def test_batch_records_failure_on_exception(self, tmp_path: Path):
        manager = SyncManager(db_path=tmp_path / "sync.db")
        manager.api_client = MagicMock()
        manager.api_client.health_snapshots.range.side_effect = RuntimeError("boom")
        stats = {"completed": 0, "skipped": 0, "failed": 0, "total_tasks": 1}

        manager._sync_health_snapshot_batch(
            user_id=1,
            start_date=date(2026, 4, 1),
            end_date=date(2026, 5, 1),
            stats=stats,
        )

        assert stats["failed"] == 1
        assert stats["completed"] == 0

    def test_batch_fails_when_no_api_client(self, tmp_path: Path):
        manager = SyncManager(db_path=tmp_path / "sync.db")
        # api_client not initialized
        stats = {"completed": 0, "skipped": 0, "failed": 0, "total_tasks": 1}

        manager._sync_health_snapshot_batch(
            user_id=1,
            start_date=date(2026, 4, 1),
            end_date=date(2026, 5, 1),
            stats=stats,
        )

        assert stats["failed"] == 1


class TestSyncRangeIntegration:
    """Tests that sync_range routes HEALTH_SNAPSHOT to the batch path."""

    def test_sync_range_excludes_health_snapshot_from_per_day_path(self, tmp_path: Path):
        manager = SyncManager(db_path=tmp_path / "integration.db")
        manager.api_client = MagicMock()
        manager.api_client.health_snapshots.range.return_value = [make_snapshot()]
        # Other metric calls should never happen for HEALTH_SNAPSHOT only
        manager.api_client.metrics.get.return_value = MagicMock()

        stats = manager.sync_range(
            user_id=1,
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 5),
            metrics=[MetricType.HEALTH_SNAPSHOT],
        )

        # Only the batch path should have run — exactly 1 health_snapshots.range call
        assert manager.api_client.health_snapshots.range.call_count == 1
        # The per-day metric path should NOT have been used
        assert manager.api_client.metrics.get.call_count == 0
        assert stats["completed"] == 1
