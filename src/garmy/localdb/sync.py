"""Synchronization manager for Garmin health data."""

import asyncio
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from .activities_iterator import ActivitiesIterator
from .config import LocalDBConfig
from .db import HealthDB
from .extractors import DataExtractor
from .models import MetricType
from .progress import ProgressReporter


class SyncManager:
    """Synchronization manager for health metrics."""

    def __init__(
        self,
        db_path: Path = Path("health.db"),
        config: Optional[LocalDBConfig] = None,
        progress_reporter: Optional[ProgressReporter] = None,
        token_dir: Optional[str] = None,
    ):
        """Initialize sync manager.

        Args:
            db_path: Path to SQLite database file.
            config: Configuration object.
            progress_reporter: Custom progress reporter.
            token_dir: Directory path for authentication tokens.
                       Resolution priority:
                       1. This parameter if provided
                       2. GARMY_PROFILE_PATH environment variable
                       3. Default: ~/.garmy/
        """
        self.db_path = db_path
        self.config = config if config is not None else LocalDBConfig()
        self.token_dir = token_dir

        self.db = HealthDB(db_path, self.config.database)
        self.progress = progress_reporter or ProgressReporter()

        self.extractor = DataExtractor()
        self.api_client = None
        self.activities_iterator = None

    def initialize(self, email: Optional[str] = None, password: Optional[str] = None):
        """Initialize with Garmin credentials or saved tokens.

        Args:
            email: Garmin account email (optional if tokens are saved)
            password: Garmin account password (optional if tokens are saved)
        """
        try:
            from garmy import APIClient, AuthClient

            auth_client = AuthClient(token_dir=self.token_dir)

            # Check if already authenticated with saved tokens
            if not auth_client.is_authenticated:
                if auth_client.needs_refresh:
                    self.progress.info("Refreshing authentication tokens...")
                    auth_client.refresh_tokens()
                elif email and password:
                    auth_client.login(
                        email,
                        password,
                        prompt_mfa=lambda: input("MFA code: "),
                    )
                else:
                    raise RuntimeError(
                        "No valid saved tokens found. Please provide email and password."
                    )

            self.api_client = APIClient(auth_client=auth_client)

            self.activities_iterator = ActivitiesIterator(
                self.api_client, self.config.sync, self.progress
            )
            self.activities_iterator.initialize()

            self.progress.info("Successfully initialized Garmin API connection")

        except Exception as e:
            self.progress.error(f"Failed to initialize: {e}")
            raise

    def sync_range(
        self,
        user_id: int,
        start_date: date,
        end_date: date,
        metrics: Optional[List[MetricType]] = None,
        resync_days: int = 0,
    ) -> Dict[str, int]:
        """Sync metrics for date range.

        Args:
            user_id: User identifier
            start_date: Start of sync range
            end_date: End of sync range
            metrics: List of metrics to sync (default: all)
            resync_days: Number of recent days to force re-sync even if
                already completed. Useful for ensuring today's partial data
                gets updated with final totals on subsequent runs.

        Returns:
            Dict with sync statistics
        """
        if not self.api_client:
            raise RuntimeError("Must call initialize() before syncing")

        date_count = abs((end_date - start_date).days) + 1

        if date_count > self.config.sync.max_sync_days:
            raise ValueError(
                f"Date range too large: {date_count} days. Maximum allowed: {self.config.sync.max_sync_days} days"
            )

        # Reset completed status for recent days so they get re-fetched
        if resync_days > 0:
            resync_cutoff = date.today() - timedelta(days=resync_days - 1)
            resync_start = max(start_date, resync_cutoff)
            reset_count = self._reset_completed_statuses(
                user_id, resync_start, end_date
            )
            if reset_count > 0:
                self.progress.info(
                    f"Reset {reset_count} completed records for re-sync "
                    f"({resync_start} to {end_date})"
                )

        if metrics is None:
            metrics = list(MetricType)

        # Separate special metrics from regular date-by-date metrics
        # Activities, body composition, and health snapshots are handled separately
        non_activities_metrics = [
            m
            for m in metrics
            if m not in (
                MetricType.ACTIVITIES,
                MetricType.BODY_COMPOSITION,
                MetricType.HEALTH_SNAPSHOT,
            )
        ]
        has_activities = MetricType.ACTIVITIES in metrics
        has_body_composition = MetricType.BODY_COMPOSITION in metrics
        has_health_snapshot = MetricType.HEALTH_SNAPSHOT in metrics

        # Calculate total tasks for progress reporting
        total_tasks = date_count * len(non_activities_metrics)
        if has_activities:
            total_tasks += date_count
        if has_body_composition:
            total_tasks += 1  # Body composition is a single batch operation
        if has_health_snapshot:
            total_tasks += 1  # Health snapshots is a single batch operation

        self.progress.start_sync(total_tasks)

        stats = {"completed": 0, "skipped": 0, "failed": 0, "total_tasks": total_tasks}

        try:
            # Create sync status entries for all dates
            for current_date in self._date_range(start_date, end_date):
                for metric_type in metrics:
                    if not self.db.sync_status_exists(
                        user_id, current_date, metric_type
                    ):
                        self.db.create_sync_status(
                            user_id, current_date, metric_type, "pending"
                        )

            # Sync non-activities metrics (oldest to newest is fine)
            if non_activities_metrics:
                for current_date in self._date_range(start_date, end_date):
                    self._sync_date(
                        user_id, current_date, non_activities_metrics, stats
                    )

            # Sync activities separately in REVERSE order (newest to oldest)
            # This matches the ActivitiesIterator which returns activities newest-first
            if has_activities:
                # Reset iterator to ensure fresh state for this sync
                if self.activities_iterator:
                    self.activities_iterator.reset()
                # Use end_date to start_date order for activities
                for current_date in self._date_range(end_date, start_date):
                    self._sync_activities_for_date(user_id, current_date, stats)

            # Sync body composition (single batch for entire range)
            if has_body_composition:
                self._sync_body_composition_batch(user_id, start_date, end_date, stats)

            # Sync health snapshots (single batch for entire range)
            if has_health_snapshot:
                self._sync_health_snapshot_batch(user_id, start_date, end_date, stats)

        except Exception as e:
            raise
        finally:
            self.progress.end_sync()

        return stats

    def _sync_date(
        self,
        user_id: int,
        sync_date: date,
        metrics: List[MetricType],
        stats: Dict[str, int],
    ):
        """Sync all non-activities metrics for a single date.

        Note: Activities are handled separately in sync_range() because they
        require reverse date iteration to match the ActivitiesIterator.
        """
        for metric_type in metrics:
            try:
                self._sync_metric_for_date(user_id, sync_date, metric_type, stats)
            except Exception as e:
                self.db.update_sync_status(
                    user_id, sync_date, metric_type, "failed", str(e)
                )
                self.progress.task_failed(f"{metric_type.value}", sync_date)
                stats["failed"] += 1

    def _sync_metric_for_date(
        self,
        user_id: int,
        sync_date: date,
        metric_type: MetricType,
        stats: Dict[str, int],
    ):
        """Sync a single metric for a date."""
        if self._is_metric_completed(user_id, metric_type, sync_date):
            stats["skipped"] += 1
            self.progress.task_skipped(f"{metric_type.value}", sync_date)
            return

        try:
            data = self.api_client.metrics.get(metric_type.value).get(sync_date)

            # Extract summary/daily data for health metrics table
            extracted_data = self.extractor.extract_metric_data(data, metric_type)
            summary_stored = False

            if extracted_data and any(v is not None for v in extracted_data.values()):
                self._store_health_metric(
                    user_id, sync_date, metric_type, extracted_data
                )
                summary_stored = True

            # Also extract timeseries data for applicable metrics
            timeseries_stored = False
            if metric_type in [
                MetricType.BODY_BATTERY,
                MetricType.STRESS,
                MetricType.HEART_RATE,
                MetricType.RESPIRATION,
                MetricType.HRV,
                MetricType.SPO2,
                MetricType.INTENSITY_MINUTES,
            ]:
                timeseries_data = self.extractor.extract_timeseries_data(
                    data, metric_type
                )
                if timeseries_data:
                    self.db.store_timeseries_batch(
                        user_id, metric_type, timeseries_data
                    )
                    timeseries_stored = True

            # Update status based on what was stored
            if summary_stored or timeseries_stored:
                self.db.update_sync_status(user_id, sync_date, metric_type, "completed")
                stats["completed"] += 1
            else:
                self.db.update_sync_status(user_id, sync_date, metric_type, "skipped")
                stats["skipped"] += 1

            self.progress.task_complete(f"{metric_type.value}", sync_date)

        except Exception as e:
            self.db.update_sync_status(
                user_id, sync_date, metric_type, "failed", str(e)
            )
            self.progress.task_failed(f"{metric_type.value}", sync_date)
            stats["failed"] += 1

    def _sync_activities_for_date(
        self, user_id: int, sync_date: date, stats: Dict[str, int]
    ):
        """Sync activities for a specific date."""
        if not self.activities_iterator:
            stats["failed"] += 1
            return

        try:
            activities = self.activities_iterator.get_activities_for_date(sync_date)

            for activity in activities:
                activity_data = self.extractor.extract_metric_data(
                    activity, MetricType.ACTIVITIES
                )
                if not activity_data or "activity_id" not in activity_data:
                    continue

                activity_id = activity_data["activity_id"]

                if self.db.activity_exists(user_id, activity_id):
                    stats["skipped"] += 1
                    continue

                activity_data["activity_date"] = sync_date

                self.db.store_activity(user_id, activity_data)
                stats["completed"] += 1

                # Fetch and store activity details (exercise sets for strength training)
                activity_type = activity_data.get("activity_type")
                self._sync_activity_details(user_id, str(activity_id), activity_type)

            self.progress.task_complete("activities", sync_date)

        except Exception as e:
            self.progress.task_failed("activities", sync_date)
            stats["failed"] += 1

    # Activity types for fetching specific detail data
    STRENGTH_TYPES = ["strength_training", "indoor_strength_training"]
    CARDIO_TYPES = [
        "running",
        "treadmill_running",
        "trail_running",
        "track_running",
        "cycling",
        "indoor_cycling",
        "virtual_ride",
        "gravel_cycling",
        "road_cycling",
        "walking",
        "hiking",
        "swimming",
        "lap_swimming",
        "open_water_swimming",
        "elliptical",
        "stair_climbing",
        "rowing",
        "indoor_rowing",
    ]

    def _sync_activity_details(
        self, user_id: int, activity_id: str, activity_type: str = None
    ):
        """Sync detailed data for a single activity.

        For strength training activities, fetches exercise sets (reps, weight, etc.).
        For cardio activities, fetches lap/split data.
        Basic activity details (distance, calories, etc.) are already extracted from
        the activity list API response during the initial sync.

        Args:
            user_id: User identifier
            activity_id: Activity ID to fetch details for
            activity_type: Activity type key (e.g., 'strength_training', 'running')
        """
        try:
            activities_accessor = self.api_client.metrics.get("activities")
            api_called = False

            # Fetch exercise sets for strength training activities
            if activity_type and activity_type in self.STRENGTH_TYPES:
                self._sync_exercise_sets(user_id, activity_id, activities_accessor)
                api_called = True

            # Fetch splits/laps for cardio activities
            if activity_type and activity_type in self.CARDIO_TYPES:
                self._sync_activity_splits(user_id, activity_id, activities_accessor)
                api_called = True

            # Apply rate limiting delay after API calls
            if api_called:
                time.sleep(self.config.sync.rate_limit_delay)

            # Mark activity as having details synced
            self.db.update_activity_details(
                user_id, activity_id, {"details_synced": True}
            )

        except Exception as e:
            self.progress.warning(
                f"Failed to sync details for activity {activity_id}: {e}"
            )

    def _sync_exercise_sets(self, user_id: int, activity_id: str, activities_accessor):
        """Sync exercise sets for a strength training activity.

        Args:
            user_id: User identifier
            activity_id: Activity ID to fetch sets for
            activities_accessor: The activities API accessor
        """
        try:
            sets_data = activities_accessor.get_exercise_sets(activity_id)
            if sets_data:
                sets = self.extractor.extract_exercise_sets(sets_data, activity_id)
                if sets:
                    self.db.store_exercise_sets(user_id, activity_id, sets)

                    # Calculate and store summary
                    summary = self.extractor.calculate_strength_summary(sets)
                    self.db.update_activity_details(user_id, activity_id, summary)

        except Exception as e:
            self.progress.warning(
                f"Failed to sync exercise sets for activity {activity_id}: {e}"
            )

    def _sync_activity_splits(
        self, user_id: int, activity_id: str, activities_accessor
    ):
        """Sync lap/split data for a cardio activity.

        Args:
            user_id: User identifier
            activity_id: Activity ID to fetch splits for
            activities_accessor: The activities API accessor
        """
        try:
            # Skip if already has splits
            if self.db.activity_has_splits(user_id, activity_id):
                return

            splits_data = activities_accessor.get_activity_splits(activity_id)
            if splits_data:
                splits = self.extractor.extract_activity_splits(
                    splits_data, activity_id
                )
                if splits:
                    self.db.store_activity_splits(user_id, activity_id, splits)

                    # Calculate totals from splits and update activity record
                    summary = self.extractor.calculate_splits_summary(splits)
                    activity_updates = {}

                    # Update distance if available from splits
                    if summary.get("total_distance_meters"):
                        activity_updates["distance_meters"] = summary[
                            "total_distance_meters"
                        ]

                    # Update calories if available from splits
                    if summary.get("total_calories"):
                        activity_updates["calories"] = int(summary["total_calories"])

                    # Update elevation if available from splits
                    if summary.get("total_elevation_gain"):
                        activity_updates["elevation_gain"] = summary[
                            "total_elevation_gain"
                        ]

                    if activity_updates:
                        self.db.update_activity_details(
                            user_id, activity_id, activity_updates
                        )

        except Exception as e:
            self.progress.warning(
                f"Failed to sync splits for activity {activity_id}: {e}"
            )

    def _sync_body_composition_batch(
        self, user_id: int, start_date: date, end_date: date, stats: Dict[str, int]
    ) -> None:
        """Sync body composition for entire date range in one API call.

        Body composition uses a range endpoint, so we fetch all data at once
        rather than iterating date by date.

        Args:
            user_id: User identifier
            start_date: Start of sync range
            end_date: End of sync range
            stats: Stats dictionary to update
        """
        if not self.api_client:
            self.progress.error("API client not initialized")
            stats["failed"] += 1
            return

        try:
            self.progress.info(
                f"Syncing body composition for {start_date} to {end_date}"
            )

            # Single API call for entire range
            endpoint = f"/weight-service/weight/range/{start_date}/{end_date}"
            data = self.api_client.connectapi(endpoint)

            if not data:
                self.progress.info("No body composition data found")
                return

            # Extract entries using the extractor
            entries = self.extractor._extract_body_composition_data(data)

            if not entries:
                self.progress.info("No body composition entries to store")
                return

            # Store each entry
            stored = 0
            skipped = 0
            for entry in entries:
                sample_pk = entry.get("sample_pk")
                if not sample_pk:
                    continue

                if self.db.body_composition_exists(user_id, sample_pk):
                    skipped += 1
                else:
                    self.db.store_body_composition(user_id, entry)
                    stored += 1

            stats["completed"] += stored
            stats["skipped"] += skipped

            self.progress.info(
                f"Body composition: stored {stored}, skipped {skipped} existing"
            )

            # Rate limiting
            time.sleep(self.config.sync.rate_limit_delay)

        except Exception as e:
            self.progress.error(f"Body composition sync failed: {e}")
            stats["failed"] += 1

    def _sync_health_snapshot_batch(
        self, user_id: int, start_date: date, end_date: date, stats: Dict[str, int]
    ) -> None:
        """Sync Health Snapshots for entire date range via the GraphQL accessor.

        Health Snapshots use a GraphQL POST endpoint that accepts a date range
        directly (capped at ~31 days per call; the accessor auto-chunks).

        Args:
            user_id: User identifier
            start_date: Start of sync range (inclusive)
            end_date: End of sync range (inclusive)
            stats: Stats dictionary to update
        """
        if not self.api_client:
            self.progress.error("API client not initialized")
            stats["failed"] += 1
            return

        try:
            self.progress.info(
                f"Syncing health snapshots for {start_date} to {end_date}"
            )

            snapshots = self.api_client.health_snapshots.range(start_date, end_date)

            if not snapshots:
                self.progress.info("No health snapshots found in range")
                return

            extracted = self.extractor.extract_health_snapshots(snapshots)
            records = extracted.get("records", [])
            summaries = extracted.get("summaries", [])
            zones = extracted.get("zones", [])

            stored = 0
            skipped = 0
            for record in records:
                activity_uuid = record.get("activity_uuid")
                if not activity_uuid:
                    continue

                if self.db.health_snapshot_exists(user_id, activity_uuid):
                    skipped += 1
                    continue

                snap_summaries = [
                    s for s in summaries if s.get("activity_uuid") == activity_uuid
                ]
                snap_zones = [
                    z for z in zones if z.get("activity_uuid") == activity_uuid
                ]

                self.db.store_health_snapshot(
                    user_id, record, snap_summaries, snap_zones
                )
                stored += 1

            stats["completed"] += stored
            stats["skipped"] += skipped

            self.progress.info(
                f"Health snapshots: stored {stored}, skipped {skipped} existing"
            )

            time.sleep(self.config.sync.rate_limit_delay)

        except Exception as e:
            self.progress.error(f"Health snapshot sync failed: {e}")
            stats["failed"] += 1

    def backfill_activity_details(
        self, user_id: int, limit: int = 100
    ) -> Dict[str, int]:
        """Backfill detailed data for activities that don't have details synced.

        Args:
            user_id: User identifier
            limit: Maximum number of activities to process

        Returns:
            Dict with sync statistics
        """
        if not self.api_client:
            raise RuntimeError("Must call initialize() before backfilling")

        stats = {"completed": 0, "failed": 0, "total": 0}

        activities = self.db.get_activities_without_details(user_id, limit)
        stats["total"] = len(activities)

        self.progress.info(f"Backfilling details for {len(activities)} activities")

        for activity in activities:
            activity_id = activity["activity_id"]
            activity_type = activity.get("activity_type")
            try:
                self._sync_activity_details(user_id, str(activity_id), activity_type)
                stats["completed"] += 1
            except Exception as e:
                self.progress.warning(f"Failed to backfill activity {activity_id}: {e}")
                stats["failed"] += 1

        self.progress.info(
            f"Backfill complete: {stats['completed']} succeeded, {stats['failed']} failed"
        )
        return stats

    def backfill_activity_splits(
        self, user_id: int, limit: int = 100
    ) -> Dict[str, int]:
        """Backfill splits for cardio activities that don't have splits yet.

        This is useful for activities that were synced before the splits feature
        was added, or when activities have details_synced=True but no splits.

        Args:
            user_id: User identifier
            limit: Maximum number of activities to process

        Returns:
            Dict with sync statistics
        """
        if not self.api_client:
            raise RuntimeError("Must call initialize() before backfilling")

        stats = {"completed": 0, "skipped": 0, "failed": 0, "total": 0}

        # Get cardio activities that don't have splits
        activities = self._get_cardio_activities_without_splits(user_id, limit)
        stats["total"] = len(activities)

        self.progress.info(
            f"Backfilling splits for {len(activities)} cardio activities"
        )

        activities_accessor = self.api_client.metrics.get("activities")

        for activity in activities:
            activity_id = activity["activity_id"]
            activity_type = activity.get("activity_type")

            # Skip if not a cardio type
            if activity_type not in self.CARDIO_TYPES:
                stats["skipped"] += 1
                continue

            try:
                self._sync_activity_splits(
                    user_id, str(activity_id), activities_accessor
                )
                stats["completed"] += 1

                # Rate limiting
                time.sleep(self.config.sync.rate_limit_delay)

            except Exception as e:
                self.progress.warning(
                    f"Failed to backfill splits for activity {activity_id}: {e}"
                )
                stats["failed"] += 1

        self.progress.info(
            f"Splits backfill complete: {stats['completed']} succeeded, {stats['skipped']} skipped, {stats['failed']} failed"
        )
        return stats

    def backfill_activity_distance_from_splits(self, user_id: int) -> Dict[str, int]:
        """Backfill distance/calories/elevation for activities from existing splits.

        This updates activities that have splits stored but don't have distance
        populated in the main activities table. Useful for fixing activities
        synced before this feature was added.

        Args:
            user_id: User identifier

        Returns:
            Dict with update statistics
        """
        stats = {"updated": 0, "skipped": 0, "failed": 0, "total": 0}

        # Get activities that have splits but NULL distance
        activities = self._get_activities_with_splits_missing_distance(user_id)
        stats["total"] = len(activities)

        self.progress.info(
            f"Backfilling distance for {len(activities)} activities from splits"
        )

        for activity in activities:
            activity_id = activity["activity_id"]
            try:
                # Get splits for this activity
                splits = self.db.get_activity_splits(user_id, activity_id)
                if not splits:
                    stats["skipped"] += 1
                    continue

                # Calculate totals from splits
                summary = self.extractor.calculate_splits_summary(splits)
                activity_updates = {}

                if summary.get("total_distance_meters"):
                    activity_updates["distance_meters"] = summary["total_distance_meters"]

                if summary.get("total_calories"):
                    activity_updates["calories"] = int(summary["total_calories"])

                if summary.get("total_elevation_gain"):
                    activity_updates["elevation_gain"] = summary["total_elevation_gain"]

                if activity_updates:
                    self.db.update_activity_details(user_id, activity_id, activity_updates)
                    stats["updated"] += 1
                else:
                    stats["skipped"] += 1

            except Exception as e:
                self.progress.warning(
                    f"Failed to backfill distance for activity {activity_id}: {e}"
                )
                stats["failed"] += 1

        self.progress.info(
            f"Distance backfill complete: {stats['updated']} updated, "
            f"{stats['skipped']} skipped, {stats['failed']} failed"
        )
        return stats

    def _get_activities_with_splits_missing_distance(
        self, user_id: int
    ) -> List[Dict[str, Any]]:
        """Get activities that have splits but no distance in main table."""
        with self.db.get_session() as session:
            from sqlalchemy import and_, exists

            from .models import Activity, ActivitySplit

            # Subquery to find activities with splits
            has_splits = exists().where(
                and_(
                    ActivitySplit.user_id == Activity.user_id,
                    ActivitySplit.activity_id == Activity.activity_id,
                )
            )

            activities = (
                session.query(Activity)
                .filter(
                    and_(
                        Activity.user_id == user_id,
                        Activity.distance_meters.is_(None),
                        has_splits,
                    )
                )
                .order_by(Activity.activity_date.desc())
                .all()
            )

            return [self.db._activity_to_dict(a) for a in activities]

    def _get_cardio_activities_without_splits(
        self, user_id: int, limit: int
    ) -> List[Dict[str, Any]]:
        """Get cardio activities that don't have splits stored yet."""
        with self.db.get_session() as session:
            from sqlalchemy import and_, exists, not_

            from .models import Activity, ActivitySplit

            # Subquery to find activities with splits
            has_splits = exists().where(
                and_(
                    ActivitySplit.user_id == Activity.user_id,
                    ActivitySplit.activity_id == Activity.activity_id,
                )
            )

            activities = (
                session.query(Activity)
                .filter(
                    and_(
                        Activity.user_id == user_id,
                        Activity.activity_type.in_(self.CARDIO_TYPES),
                        ~has_splits,
                    )
                )
                .order_by(Activity.activity_date.desc())
                .limit(limit)
                .all()
            )

            return [self.db._activity_to_dict(a) for a in activities]

    # Performance metrics stored in separate table (update after activities, not daily)
    PERFORMANCE_METRIC_TYPES = {
        MetricType.TRAINING_STATUS,
        MetricType.ENDURANCE_SCORE,
    }

    def _store_health_metric(
        self, user_id: int, sync_date: date, metric_type: MetricType, data: Dict
    ):
        """Store health metric data in normalized table."""
        if metric_type in self.PERFORMANCE_METRIC_TYPES:
            self.db.store_performance_metric(user_id, sync_date, **data)
            return
        if metric_type == MetricType.DAILY_SUMMARY:
            self.db.store_health_metric(user_id, sync_date, **data)
        elif metric_type == MetricType.SLEEP:
            self.db.store_health_metric(user_id, sync_date, **data)
        elif metric_type == MetricType.TRAINING_READINESS:
            self.db.store_health_metric(
                user_id,
                sync_date,
                training_readiness_score=data.get("score"),
                training_readiness_level=data.get("level"),
                training_readiness_feedback=data.get("feedback"),
            )
        elif metric_type == MetricType.HRV:
            self.db.store_health_metric(user_id, sync_date, **data)
        elif metric_type in [
            MetricType.RESPIRATION,
            MetricType.HEART_RATE,
            MetricType.STRESS,
            MetricType.BODY_BATTERY,
            MetricType.STEPS,
            MetricType.CALORIES,
            MetricType.SPO2,
            MetricType.RESTING_HEART_RATE,
            MetricType.INTENSITY_MINUTES,
            MetricType.FLOORS,
        ]:
            # Store all extracted data for these metrics
            self.db.store_health_metric(user_id, sync_date, **data)

    def _reset_completed_statuses(
        self, user_id: int, start_date: date, end_date: date
    ) -> int:
        """Reset completed sync statuses to pending for a date range.

        Returns the number of records reset.
        """
        return self.db.reset_completed_statuses(user_id, start_date, end_date)

    def _is_metric_completed(
        self, user_id: int, metric_type: MetricType, sync_date: date
    ) -> bool:
        """Check if metric is already completed."""
        status = self.db.get_sync_status(user_id, sync_date, metric_type)
        return status == "completed"

    def _date_range(self, start_date: date, end_date: date):
        """Generate date range in either direction."""
        step = 1 if start_date <= end_date else -1
        current = start_date
        while (step > 0 and current <= end_date) or (step < 0 and current >= end_date):
            yield current
            current += timedelta(days=step)

    def query_health_metrics(
        self, user_id: int, start_date: date, end_date: date
    ) -> List[Dict]:
        """Query normalized health metrics for analysis."""
        return self.db.get_health_metrics(user_id, start_date, end_date)

    def query_activities(
        self,
        user_id: int,
        start_date: date,
        end_date: date,
        activity_name: Optional[str] = None,
    ) -> List[Dict]:
        """Query activities for date range."""
        return self.db.get_activities(user_id, start_date, end_date, activity_name)

    def query_timeseries(
        self,
        user_id: int,
        metric_type: MetricType,
        start_time: datetime,
        end_time: datetime,
    ) -> List[Dict]:
        """Query timeseries data for time range."""
        start_ts = int(start_time.timestamp()) * self.config.database.ms_per_second
        end_ts = int(end_time.timestamp()) * self.config.database.ms_per_second

        data = self.db.get_timeseries(user_id, metric_type, start_ts, end_ts)
        return [
            {"timestamp": ts, "value": value, "metadata": metadata}
            for ts, value, metadata in data
        ]
