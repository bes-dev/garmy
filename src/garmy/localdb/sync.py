"""Synchronization manager for Garmin health data."""

import asyncio
from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path

from .db import HealthDB
from .config import LocalDBConfig
from .models import MetricType
from .progress import ProgressReporter
from .extractors import DataExtractor
from .activities_iterator import ActivitiesIterator


class SyncManager:
    """Synchronization manager for health metrics."""

    def __init__(self,
                 db_path: Path = Path("health.db"),
                 config: Optional[LocalDBConfig] = None,
                 progress_reporter: Optional[ProgressReporter] = None):
        """Initialize sync manager.

        Args:
            db_path: Path to SQLite database file.
            config: Configuration object.
            progress_reporter: Custom progress reporter.
        """
        self.db_path = db_path
        self.config = config if config is not None else LocalDBConfig()

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
            from garmy import AuthClient, APIClient

            auth_client = AuthClient()

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

        date_count = abs((end_date - start_date).days) + 1

        if date_count > self.config.sync.max_sync_days:
            raise ValueError(f"Date range too large: {date_count} days. Maximum allowed: {self.config.sync.max_sync_days} days")

        if metrics is None:
            metrics = list(MetricType)

        non_activities_metrics = [m for m in metrics if m != MetricType.ACTIVITIES]
        total_tasks = date_count * len(metrics)

        self.progress.start_sync(total_tasks)

        stats = {'completed': 0, 'skipped': 0, 'failed': 0, 'total_tasks': total_tasks}

        try:
            for current_date in self._date_range(start_date, end_date):
                for metric_type in metrics:
                    if not self.db.sync_status_exists(user_id, current_date, metric_type):
                        self.db.create_sync_status(user_id, current_date, metric_type, 'pending')
            
            for current_date in self._date_range(start_date, end_date):
                self._sync_date(user_id, current_date, metrics, stats)

        except Exception as e:
            raise
        finally:
            self.progress.end_sync()

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
                self.db.update_sync_status(user_id, sync_date, metric_type, 'failed', str(e))
                self.progress.task_failed(f"{metric_type.value}", sync_date)
                stats['failed'] += 1

    def _sync_metric_for_date(self, user_id: int, sync_date: date, metric_type: MetricType, stats: Dict[str, int]):
        """Sync a single metric for a date."""
        if self._is_metric_completed(user_id, metric_type, sync_date):
            stats['skipped'] += 1
            self.progress.task_skipped(f"{metric_type.value}", sync_date)
            return

        try:
            data = self.api_client.metrics.get(metric_type.value).get(sync_date)
            
            # Extract summary/daily data for health metrics table
            extracted_data = self.extractor.extract_metric_data(data, metric_type)
            summary_stored = False
            
            
            if extracted_data and any(v is not None for v in extracted_data.values()):
                self._store_health_metric(user_id, sync_date, metric_type, extracted_data)
                summary_stored = True
            
            # Also extract timeseries data for applicable metrics
            timeseries_stored = False
            if metric_type in [MetricType.BODY_BATTERY, MetricType.STRESS, MetricType.HEART_RATE, MetricType.RESPIRATION]:
                timeseries_data = self.extractor.extract_timeseries_data(data, metric_type)
                if timeseries_data:
                    self.db.store_timeseries_batch(user_id, metric_type, timeseries_data)
                    timeseries_stored = True
            
            # Update status based on what was stored
            if summary_stored or timeseries_stored:
                self.db.update_sync_status(user_id, sync_date, metric_type, 'completed')
                stats['completed'] += 1
            else:
                self.db.update_sync_status(user_id, sync_date, metric_type, 'skipped')
                stats['skipped'] += 1

            self.progress.task_complete(f"{metric_type.value}", sync_date)

        except Exception as e:
            self.db.update_sync_status(user_id, sync_date, metric_type, 'failed', str(e))
            self.progress.task_failed(f"{metric_type.value}", sync_date)
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

                if self.db.activity_exists(user_id, activity_id):
                    stats['skipped'] += 1
                    continue

                activity_data['activity_date'] = sync_date

                self.db.store_activity(user_id, activity_data)
                stats['completed'] += 1

            # Update sync status for the entire ACTIVITIES metric for this date
            self.db.update_sync_status(user_id, sync_date, MetricType.ACTIVITIES, 'completed')
            self.progress.task_complete("activities", sync_date)

        except Exception as e:
            self.progress.task_failed("activities", sync_date)
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
        elif metric_type in [MetricType.RESPIRATION, MetricType.HEART_RATE, MetricType.STRESS, MetricType.BODY_BATTERY, MetricType.STEPS, MetricType.CALORIES]:
            # Store all extracted data for these metrics
            self.db.store_health_metric(user_id, sync_date, **data)

    def _is_metric_completed(self, user_id: int, metric_type: MetricType, sync_date: date) -> bool:
        """Check if metric is already completed."""
        status = self.db.get_sync_status(user_id, sync_date, metric_type)
        return status == 'completed'

    def _date_range(self, start_date: date, end_date: date):
        """Generate date range in either direction."""
        step = 1 if start_date <= end_date else -1
        current = start_date
        while (step > 0 and current <= end_date) or (step < 0 and current >= end_date):
            yield current
            current += timedelta(days=step)

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