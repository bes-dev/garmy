"""Minimal and clean synchronization manager."""

import asyncio
from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path

from .db import HealthDB
from .config import LocalDBConfig
from .models import MetricType
from .progress import create_reporter, ProgressReporter
from .extractors import DataExtractor
from .activities_iterator import ActivitiesIterator


class SyncManager:
    """Minimal synchronization manager for health metrics."""

    def __init__(self,
                 db_path: Path = Path("health.db"),
                 config: Optional[LocalDBConfig] = None,
                 progress_reporter: Optional[ProgressReporter] = None):
        """Initialize sync manager.

        Args:
            db_path: Path to SQLite database file
            config: Configuration object (default: LocalDBConfig())
            progress_reporter: Custom progress reporter (default: from config)
        """
        self.db_path = db_path
        self.config = config if config is not None else LocalDBConfig()

        # Initialize database
        self.db = HealthDB(db_path, self.config.database)

        # Initialize progress reporter
        if progress_reporter:
            self.progress = progress_reporter
        else:
            self.progress = create_reporter(
                self.config.sync.progress_reporter,
                name="garmin_sync",
                show_details=self.config.sync.progress_show_details
            )

        # Initialize utilities
        self.extractor = DataExtractor()
        self.api_client = None
        self.activities_iterator = None

    def initialize(self, email: str, password: str):
        """Initialize with Garmin credentials."""
        try:
            from garmy import AuthClient, APIClient

            # Setup authentication
            auth_client = AuthClient()
            auth_client.login(email, password)
            self.api_client = APIClient(auth_client=auth_client)

            # Initialize activities iterator
            self.activities_iterator = ActivitiesIterator(
                self.api_client,
                self.config.sync,
                self.progress
            )
            self.activities_iterator.initialize()

            self.progress.info("Successfully initialized Garmin API connection")

        except Exception as e:
            self.progress.error(f"Failed to initialize: {e}")
            raise

    def sync_range(self, user_id: int, start_date: date, end_date: date,
                        metrics: Optional[List[MetricType]] = None) -> Dict[str, int]:
        """Sync metrics for date range.

        Args:
            user_id: User identifier
            start_date: Start of sync range
            end_date: End of sync range
            metrics: List of metrics to sync (default: all)

        Returns:
            Dict with sync statistics
        """
        if not self.api_client:
            raise RuntimeError("Must call initialize() before syncing")

        # # Validate date range
        # if start_date > end_date:
        #     raise ValueError(f"start_date ({start_date}) cannot be after end_date ({end_date})")

        # Calculate total work
        date_count = abs((end_date - start_date).days) + 1

        # Prevent extremely large sync ranges
        if date_count > self.config.sync.max_sync_days:
            raise ValueError(f"Date range too large: {date_count} days. Maximum allowed: {self.config.sync.max_sync_days} days")

        # Use all metrics if none specified
        if metrics is None:
            metrics = list(MetricType)

        # Calculate work
        non_activities_metrics = [m for m in metrics if m != MetricType.ACTIVITIES]
        total_tasks = date_count * len(metrics)

        # Initialize progress
        self.progress.start_sync(total_tasks, f"Syncing {date_count} days")

        # Sync statistics
        stats = {'completed': 0, 'skipped': 0, 'failed': 0, 'total_tasks': total_tasks}

        try:
            # Process each date
            for current_date in self._date_range(start_date, end_date):
                self._sync_date(user_id, current_date, metrics, stats)

        except Exception as e:
            self.progress.error(f"Sync failed: {e}")
            raise
        finally:
            self.progress.end_sync(stats['failed'] == 0)

        return stats

    def _sync_date(self, user_id: int, sync_date: date, metrics: List[MetricType], stats: Dict[str, int]):
        """Sync all metrics for a single date."""
        for metric_type in metrics:
            try:
                if metric_type == MetricType.ACTIVITIES:
                    self._sync_activities_for_date(user_id, sync_date, stats)
                else:
                    self._sync_metric_for_date(user_id, sync_date, metric_type, stats)

            except Exception as e:
                self.progress.warning(f"Failed to sync {metric_type.value} for {sync_date}: {e}")
                stats['failed'] += 1

    def _sync_metric_for_date(self, user_id: int, sync_date: date, metric_type: MetricType, stats: Dict[str, int]):
        """Sync a single metric for a date."""
        # Check if already exists
        if self._has_metric_data(user_id, metric_type, sync_date):
            stats['skipped'] += 1
            self.progress.task_skipped(f"{metric_type.value} for {sync_date}", "Already exists")
            return

        try:
            # Fetch data from API
            if metric_type in [MetricType.BODY_BATTERY, MetricType.STRESS, MetricType.HEART_RATE, MetricType.RESPIRATION]:
                # Timeseries data
                data = self.api_client.metrics.get(metric_type.value).get(sync_date)
                timeseries_data = self.extractor.extract_timeseries_data(data, metric_type)
                if timeseries_data:
                    self.db.store_timeseries_batch(user_id, metric_type, timeseries_data)
                    stats['completed'] += 1
                else:
                    stats['skipped'] += 1
            else:
                # Daily metrics
                data = self.api_client.metrics.get(metric_type.value).get(sync_date)
                extracted_data = self.extractor.extract_metric_data(data, metric_type)

                if extracted_data and any(v is not None for v in extracted_data.values()):
                    self._store_health_metric(user_id, sync_date, metric_type, extracted_data)
                    stats['completed'] += 1
                else:
                    stats['skipped'] += 1

            self.progress.task_complete(f"{metric_type.value} for {sync_date}")

        except Exception as e:
            self.progress.warning(f"Failed to sync {metric_type.value} for {sync_date}: {e}")
            stats['failed'] += 1

    def _sync_activities_for_date(self, user_id: int, sync_date: date, stats: Dict[str, int]):
        """Sync activities for a specific date."""
        if not self.activities_iterator:
            stats['failed'] += 1
            return

        try:
            activities = self.activities_iterator.get_activities_for_date(sync_date)

            for activity in activities:
                activity_data = self.extractor.extract_metric_data(activity, MetricType.ACTIVITIES)
                if not activity_data or 'activity_id' not in activity_data:
                    continue

                activity_id = activity_data['activity_id']

                # Check if already stored
                if self.db.activity_exists(user_id, activity_id):
                    stats['skipped'] += 1
                    continue

                # Add required date field
                activity_data['activity_date'] = sync_date

                # Store activity
                self.db.store_activity(user_id, activity_data)
                stats['completed'] += 1

            self.progress.task_complete(f"activities for {sync_date}")

        except Exception as e:
            self.progress.warning(f"Failed to sync activities for {sync_date}: {e}")
            stats['failed'] += 1

    def _store_health_metric(self, user_id: int, sync_date: date, metric_type: MetricType, data: Dict):
        """Store health metric data in normalized table."""
        if metric_type == MetricType.DAILY_SUMMARY:
            self.db.store_health_metric(user_id, sync_date, **data)
        elif metric_type == MetricType.SLEEP:
            self.db.store_health_metric(user_id, sync_date, **data)
        elif metric_type == MetricType.TRAINING_READINESS:
            self.db.store_health_metric(
                user_id, sync_date,
                training_readiness_score=data.get('score'),
                training_readiness_level=data.get('level'),
                training_readiness_feedback=data.get('feedback')
            )
        elif metric_type == MetricType.HRV:
            self.db.store_health_metric(
                user_id, sync_date,
                hrv_weekly_avg=data.get('weekly_avg'),
                hrv_last_night_avg=data.get('last_night_avg'),
                hrv_status=data.get('status')
            )
        elif metric_type == MetricType.RESPIRATION:
            self.db.store_health_metric(user_id, sync_date, **data)

    def _has_metric_data(self, user_id: int, metric_type: MetricType, sync_date: date) -> bool:
        """Check if metric data already exists."""
        if metric_type in [MetricType.DAILY_SUMMARY, MetricType.SLEEP,
                          MetricType.TRAINING_READINESS, MetricType.HRV, MetricType.RESPIRATION]:
            return self.db.health_metric_exists(user_id, sync_date)
        else:
            # For other metrics, just check normalized table
            return self.db.health_metric_exists(user_id, sync_date)

    def _date_range(self, start_date: date, end_date: date):
        """Generate date range in either direction."""
        step = 1 if start_date <= end_date else -1
        current = start_date
        while (step > 0 and current <= end_date) or (step < 0 and current >= end_date):
            yield current
            current += timedelta(days=step)

    # ========================================================================================
    # QUERY METHODS (Basic data access)
    # ========================================================================================

    def query_health_metrics(self, user_id: int, start_date: date, end_date: date) -> List[Dict]:
        """Query normalized health metrics for analysis."""
        return self.db.get_health_metrics(user_id, start_date, end_date)

    def query_activities(self, user_id: int, start_date: date, end_date: date,
                        activity_name: Optional[str] = None) -> List[Dict]:
        """Query activities for date range."""
        return self.db.get_activities(user_id, start_date, end_date, activity_name)

    def query_timeseries(self, user_id: int, metric_type: MetricType,
                        start_time: datetime, end_time: datetime) -> List[Dict]:
        """Query timeseries data for time range."""
        start_ts = int(start_time.timestamp()) * self.config.database.ms_per_second
        end_ts = int(end_time.timestamp()) * self.config.database.ms_per_second

        data = self.db.get_timeseries(user_id, metric_type, start_ts, end_ts)
        return [{
            'timestamp': ts,
            'value': value,
            'metadata': metadata
        } for ts, value, metadata in data]
