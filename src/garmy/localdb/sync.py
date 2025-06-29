"""Simple sequential sync manager for Garmin data."""

import asyncio
import logging
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path

from ..core.client import APIClient
from ..auth.client import AuthClient
from .db import HealthDB
from .models import MetricType
from .config import LocalDBConfig
from .progress import create_reporter, ProgressReporter


class SyncManager:
    """Simple sequential sync manager - no task queues, no complexity."""
    
    def __init__(self, 
                 db_path: Path = Path("health.db"), 
                 config: Optional[LocalDBConfig] = None,
                 progress_reporter: Optional[ProgressReporter] = None):
        """Initialize sync manager.
        
        Args:
            db_path: Path to SQLite database file (default: "health.db")
            config: Sync configuration (default: LocalDBConfig())
            progress_reporter: Custom progress reporter (optional)
        """
        self.config = config if config is not None else LocalDBConfig()
        self.db = HealthDB(db_path, self.config.database)
        self.api_client: Optional[APIClient] = None
        self.logger = logging.getLogger(__name__)
        
        # Настройка прогресса
        if progress_reporter:
            self.progress = progress_reporter
        else:
            self.progress = create_reporter(
                self.config.sync.progress_reporter,
                name="garmin_sync",
                show_details=self.config.sync.progress_show_details,
                logger=self.logger,
                log_level=logging.INFO,
                progress_interval=self.config.sync.progress_log_interval
            )
        
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup basic logging."""
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    async def initialize(self, email: str, password: str):
        """Initialize with Garmin credentials."""
        if not email or not isinstance(email, str):
            raise ValueError("Email must be a non-empty string")
        if not password or not isinstance(password, str):
            raise ValueError("Password must be a non-empty string")
        
        try:
            auth_client = AuthClient()
            self.api_client = APIClient(auth_client=auth_client)
            auth_client.login(email, password)
            self.progress.info("Garmin authentication successful")
        except Exception as e:
            self.api_client = None
            self.progress.error(f"Failed to authenticate with Garmin: {e}")
            raise RuntimeError(f"Failed to authenticate with Garmin: {e}") from e
    
    async def sync_range(self, user_id: int, start_date: date, end_date: date, 
                        metrics: Optional[List[MetricType]] = None, max_retries: Optional[int] = None) -> Dict[str, int]:
        """
        Simple sequential sync for date range.
        
        Args:
            user_id: User ID
            start_date: Start date for sync
            end_date: End date for sync  
            metrics: Specific metrics to sync (default: all)
            max_retries: Max retry attempts per metric
            
        Returns:
            Dict with sync statistics
        """
        if not self.api_client:
            raise RuntimeError("Sync manager not initialized. Call initialize() first.")
        
        # Validate input parameters
        if not isinstance(user_id, int) or user_id <= 0:
            raise ValueError(f"Invalid user_id: {user_id}")
        if not isinstance(start_date, date):
            raise ValueError(f"start_date must be a date object, got {type(start_date)}")
        if not isinstance(end_date, date):
            raise ValueError(f"end_date must be a date object, got {type(end_date)}")
        if start_date > end_date:
            raise ValueError(f"start_date ({start_date}) cannot be after end_date ({end_date})")
        
        if metrics is None:
            metrics = list(MetricType)
        elif not isinstance(metrics, list) or not all(isinstance(m, MetricType) for m in metrics):
            raise ValueError("metrics must be a list of MetricType enum values")
        
        if max_retries is None:
            max_retries = self.config.sync.max_retries
        elif not isinstance(max_retries, int) or max_retries < 1:
            raise ValueError(f"max_retries must be a positive integer, got {max_retries}")
        
        # Calculate total work
        date_count = (end_date - start_date).days + 1
        
        # Prevent extremely large sync ranges
        MAX_SYNC_DAYS = 3650  # ~10 years
        if date_count > MAX_SYNC_DAYS:
            raise ValueError(f"Date range too large: {date_count} days. Maximum allowed: {MAX_SYNC_DAYS} days")
        
        non_activities_metrics = [m for m in metrics if m != MetricType.ACTIVITIES]
        total_tasks = date_count * len(metrics)  # Include activities in total count
        
        stats = {
            'total_tasks': total_tasks,
            'completed': 0,
            'failed': 0,
            'skipped': 0
        }
        
        current_date = end_date  # Start from newest date
        task_num = 0
        
        # Initialize activities iterator if needed
        activities_iterator = None
        if MetricType.ACTIVITIES in metrics:
            activities_iterator = ActivitiesIterator(self.api_client, self.config.sync, self.progress)
            self.progress.info(f"Initialized activities iterator for date-based sync")
        
        # Начинаем синхронизацию
        description = f"{date_count} days × {len(metrics)} metrics"
        self.progress.start_sync(total_tasks, description)
        
        while current_date >= start_date:
            # Sync regular metrics (non-activities)
            for metric in non_activities_metrics:
                task_num += 1
                
                # Skip if already synced
                if self._has_metric_data(user_id, metric, current_date):
                    self.progress.task_skipped(f"{metric.value} {current_date}", "Already exists")
                    stats['skipped'] += 1
                    continue
                
                # Start task
                self.progress.task_start(f"{metric.value} {current_date}")
                
                # Sync with retry logic
                success = await self._sync_metric_with_retry(
                    user_id, metric, current_date, max_retries
                )
                
                if success:
                    self.progress.task_complete(f"{metric.value} {current_date}")
                    stats['completed'] += 1
                else:
                    self.progress.task_failed(f"{metric.value} {current_date}")
                    stats['failed'] += 1
                
                # Rate limiting
                await asyncio.sleep(self.config.sync.rate_limit_delay)
            
            # Sync activities for this date using iterator
            if activities_iterator:
                task_num += 1
                task_name = f"activities {current_date}"
                
                try:
                    self.progress.task_start(task_name)
                    date_activities = await activities_iterator.get_activities_for_date(current_date)
                    
                    if date_activities:
                        activities_synced = 0
                        for activity in date_activities:
                            # Extract and validate activity data
                            activity_data = self._extract_activity_data(activity)
                            
                            if not activity_data or not activity_data.get('activity_id'):
                                stats['failed'] += 1
                                continue
                                
                            activity_id = activity_data['activity_id']
                            
                            # Check if already stored
                            if self.db.activity_exists(user_id, activity_id):
                                stats['skipped'] += 1
                                continue
                            
                            # Store activity in dedicated table
                            activity_data['activity_date'] = current_date
                            self.db.store_activity(user_id, activity_data)
                            activities_synced += 1
                            stats['completed'] += 1
                        
                        if activities_synced > 0:
                            self.progress.activity_synced(str(current_date), activities_synced)
                            self.progress.task_complete(task_name, f"{activities_synced} activities")
                        else:
                            self.progress.task_skipped(task_name, "No new activities")
                            stats['skipped'] += 1
                    else:
                        # No activities for this date - this is normal
                        self.progress.task_skipped(task_name, "No activities found")
                        stats['skipped'] += 1
                        
                except Exception as e:
                    self.progress.task_failed(task_name, str(e))
                    stats['failed'] += 1
            
            current_date -= timedelta(days=1)
        
        # Завершаем синхронизацию
        success = stats['failed'] == 0
        self.progress.end_sync(success)
        return stats
    
    async def _sync_metric_with_retry(self, user_id: int, metric_type: MetricType, 
                                    sync_date: date, max_retries: int) -> bool:
        """Sync single metric with retry logic."""
        for attempt in range(max_retries):
            try:
                data = await self._fetch_metric_data(metric_type, sync_date)
                
                if data is None:
                    # No data available - this is normal, mark as success
                    return True
                
                # Store data in appropriate table
                records_stored = self._store_metric_data(user_id, metric_type, sync_date, data)
                
                if records_stored > 0:
                    self.progress.metric_synced(metric_type.value, str(sync_date), records_stored)
                
                return True
                
            except Exception as e:
                if attempt == max_retries - 1:
                    self.progress.error(f"Failed to sync {metric_type.value} for {sync_date} after {max_retries} attempts: {e}")
                    return False
                else:
                    wait_time = self.config.sync.retry_exponential_base ** attempt  # Exponential backoff
                    self.progress.warning(f"Retry {attempt + 1}/{max_retries} for {metric_type.value} {sync_date} in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
        
        return False
    
    # Note: _sync_activities_batch method removed - replaced with ActivitiesIterator integration
    
    # Note: _extract_activity_date moved to ActivitiesIterator class
    
    
    async def _fetch_metric_data(self, metric_type: MetricType, sync_date: date) -> Optional[Any]:
        """Fetch metric data from Garmin API."""
        date_str = sync_date.strftime('%Y-%m-%d')
        
        try:
            metric_accessor = self.api_client.metrics.get(metric_type.value)
            
            if metric_type == MetricType.ACTIVITIES:
                # Activities API doesn't support date-specific queries
                # Skip individual date sync - activities are handled separately
                return None
            else:
                data = metric_accessor.get(date_str)
            
            return data if isinstance(data, list) else [data] if data else None
            
        except Exception as e:
            error_str = str(e).lower()
            # Handle common "no data" scenarios
            if any(phrase in error_str for phrase in [
                "404", "no data", "not found", "missing 1 required positional argument",
                "required field", "missing required", "validation error"
            ]):
                return None
            # Re-raise unexpected errors with context
            raise RuntimeError(f"Failed to fetch {metric_type.value} data for {date_str}: {e}") from e
    
    def _store_metric_data(self, user_id: int, metric_type: MetricType, 
                          sync_date: date, data: List[Any]) -> int:
        """Store metric data using proper extraction methods."""
        records_stored = 0
        
        for item in data:
            try:
                # Extract data using metric-specific methods
                extracted_data = self._extract_metric_data(item, metric_type)
                
                # Only store if there's actual data (not empty dict)
                if extracted_data and any(value is not None for value in extracted_data.values()):
                    if metric_type in [MetricType.BODY_BATTERY, MetricType.STRESS, 
                                     MetricType.HEART_RATE, MetricType.RESPIRATION]:
                        # Try timeseries first, fallback to summary
                        timeseries_data = self._extract_timeseries_data(item, metric_type)
                        if timeseries_data:
                            self.db.store_timeseries_batch(user_id, metric_type, timeseries_data)
                            records_stored += len(timeseries_data)
                        
                        # Also store summary data in normalized table
                        if extracted_data:
                            self._store_health_metric(user_id, sync_date, metric_type, extracted_data)
                            records_stored += 1
                    elif metric_type in [MetricType.DAILY_SUMMARY, MetricType.SLEEP, 
                                       MetricType.TRAINING_READINESS, MetricType.HRV]:
                        # Store in normalized health metrics table
                        self._store_health_metric(user_id, sync_date, metric_type, extracted_data)
                        records_stored += 1
                    else:
                        # Legacy metrics - skip or log warning
                        self.progress.warning(f"Metric {metric_type.value} not supported in normalized schema")
                        records_stored += 1
                        
            except Exception as e:
                self.progress.warning(f"Failed to process {metric_type.value} item: {e}")
        
        return records_stored
    
    def _extract_metric_data(self, data: Any, metric_type: MetricType) -> Optional[Dict]:
        """Extract data using proper metric architecture."""
        try:
            if metric_type == MetricType.DAILY_SUMMARY:
                return self._extract_daily_summary_data(data)
            elif metric_type == MetricType.SLEEP:
                return self._extract_sleep_data(data)
            elif metric_type == MetricType.HEART_RATE:
                return self._extract_heart_rate_summary(data)
            elif metric_type == MetricType.TRAINING_READINESS:
                return self._extract_training_readiness_data(data)
            elif metric_type == MetricType.HRV:
                return self._extract_hrv_data(data)
            elif metric_type == MetricType.RESPIRATION:
                return self._extract_respiration_summary(data)
            elif metric_type == MetricType.ACTIVITIES:
                return self._extract_activity_data(data)
                
        except Exception as e:
            self.progress.warning(f"Failed to extract {metric_type.value} data: {e}")
        
        return None
    
    def _extract_daily_summary_data(self, data: Any) -> Dict[str, Any]:
        """Extract comprehensive daily summary - main hub for daily metrics."""
        return {
            # Steps metrics (primary source)
            'total_steps': getattr(data, 'total_steps', None),
            'step_goal': getattr(data, 'step_goal', None),
            'total_distance_meters': getattr(data, 'total_distance', None),
            
            # Calories metrics (primary source)
            'total_calories': getattr(data, 'total_kilocalories', None),
            'active_calories': getattr(data, 'active_kilocalories', None),
            'bmr_calories': getattr(data, 'bmr_kilocalories', None),
            
            # Heart rate metrics (primary source)
            'resting_heart_rate': getattr(data, 'resting_heart_rate', None),
            'max_heart_rate': getattr(data, 'max_heart_rate', None),
            'min_heart_rate': getattr(data, 'min_heart_rate', None),
            
            # Stress metrics (primary source)
            'avg_stress_level': getattr(data, 'average_stress_level', None),
            'max_stress_level': getattr(data, 'max_stress_level', None),
            
            # Body Battery metrics (primary source)
            'body_battery_high': getattr(data, 'body_battery_highest_value', None),
            'body_battery_low': getattr(data, 'body_battery_lowest_value', None)
        }
    
    def _extract_sleep_data(self, data: Any) -> Dict[str, Any]:
        """Extract sleep metrics - unique to sleep."""
        return {
            'sleep_duration_hours': getattr(data, 'sleep_duration_hours', None),
            'deep_sleep_percentage': getattr(data, 'deep_sleep_percentage', None),
            'light_sleep_percentage': getattr(data, 'light_sleep_percentage', None),
            'rem_sleep_percentage': getattr(data, 'rem_sleep_percentage', None),
            'awake_percentage': getattr(data, 'awake_percentage', None),
            'average_spo2': getattr(data, 'average_spo2', None),
            'average_respiration': getattr(data, 'average_respiration', None)
        }
    
    def _extract_heart_rate_summary(self, data: Any) -> Dict[str, Any]:
        """Extract heart rate summary - unique fields not in daily_summary."""
        return {
            'average_heart_rate': getattr(data, 'average_heart_rate', None)
        }
    
    def _extract_training_readiness_data(self, data: Any) -> Dict[str, Any]:
        """Extract training readiness data."""
        return {
            'score': getattr(data, 'score', None),
            'level': getattr(data, 'level', None),
            'feedback': getattr(data, 'feedback_short', None)
        }
    
    def _extract_hrv_data(self, data: Any) -> Dict[str, Any]:
        """Extract HRV using nested summary."""
        hrv_summary = getattr(data, 'hrv_summary', None)
        if hrv_summary:
            return {
                'weekly_avg': getattr(hrv_summary, 'weekly_avg', None),
                'last_night_avg': getattr(hrv_summary, 'last_night_avg', None),
                'status': getattr(hrv_summary, 'status', None)
            }
        return {}
    
    
    def _extract_respiration_summary(self, data: Any) -> Dict[str, Any]:
        """Extract respiration summary - unique respiratory metrics."""
        summary = getattr(data, 'respiration_summary', None)
        if summary:
            return {
                'avg_waking_respiration_value': getattr(summary, 'avg_waking_respiration_value', None),
                'avg_sleep_respiration_value': getattr(summary, 'avg_sleep_respiration_value', None),
                'lowest_respiration_value': getattr(summary, 'lowest_respiration_value', None),
                'highest_respiration_value': getattr(summary, 'highest_respiration_value', None)
            }
        return {}
    
    def _extract_activity_data(self, data: Any) -> Dict[str, Any]:
        """Extract activity data from both parsed and raw formats."""
        # Handle both object attributes and dict keys
        def get_value(obj, *keys):
            for key in keys:
                if hasattr(obj, key):
                    return getattr(obj, key, None)
                elif isinstance(obj, dict) and key in obj:
                    return obj[key]
            return None
        
        activity_id = get_value(data, 'activity_id', 'activityId')
        if activity_id:
            return {
                'activity_id': activity_id,
                'activity_name': get_value(data, 'activity_name', 'activityName', 'activityTypeName'),
                'duration_seconds': get_value(data, 'duration', 'movingDuration', 'elapsedDuration'),
                'avg_heart_rate': get_value(data, 'average_hr', 'averageHR', 'avgHR'),
                'training_load': get_value(data, 'activity_training_load', 'trainingLoad'),
                'start_time': get_value(data, 'start_time_local', 'startTimeLocal', 'start_time')
            }
        return {}
    
    def _extract_timeseries_data(self, data: Any, metric_type: MetricType) -> List[tuple]:
        """Extract timeseries using computed properties."""
        try:
            if metric_type == MetricType.BODY_BATTERY:
                readings = getattr(data, 'body_battery_readings', []) or []
                return [(r.timestamp, r.level, {'status': r.status}) for r in readings]
            
            elif metric_type == MetricType.STRESS:
                readings = getattr(data, 'stress_readings', []) or []
                return [(r.timestamp, r.stress_level, {'category': getattr(r, 'stress_category', None)}) 
                       for r in readings]
            
            elif metric_type == MetricType.HEART_RATE:
                # HeartRate doesn't have computed readings property, use raw array
                values = getattr(data, 'heart_rate_values_array', []) or []
                result = []
                for item in values:
                    if isinstance(item, (list, tuple)) and len(item) >= self.config.sync.min_timeseries_fields:
                        ts, val = item[0], item[1]
                        if ts and val is not None:
                            result.append((ts, val, None))
                return result
            
            elif metric_type == MetricType.RESPIRATION:
                # Respiration uses raw arrays
                values = getattr(data, 'respiration_values_array', []) or []
                result = []
                for item in values:
                    if isinstance(item, (list, tuple)) and len(item) >= self.config.sync.min_timeseries_fields:
                        ts, val = item[0], item[1]
                        if ts and val is not None:
                            result.append((ts, val, None))
                return result
                            
        except Exception as e:
            self.progress.warning(f"Failed to extract timeseries for {metric_type}: {e}")
        
        return []
    
    
    def _store_health_metric(self, user_id: int, sync_date: date, metric_type: MetricType, data: Dict):
        """Store data in normalized health metrics table."""
        if metric_type == MetricType.DAILY_SUMMARY:
            self.db.store_health_metric(
                user_id, sync_date,
                total_steps=data.get('total_steps'),
                step_goal=data.get('step_goal'),
                total_distance_meters=data.get('total_distance_meters'),
                total_calories=data.get('total_calories'),
                active_calories=data.get('active_calories'),
                bmr_calories=data.get('bmr_calories'),
                resting_heart_rate=data.get('resting_heart_rate'),
                max_heart_rate=data.get('max_heart_rate'),
                min_heart_rate=data.get('min_heart_rate'),
                avg_stress_level=data.get('avg_stress_level'),
                max_stress_level=data.get('max_stress_level'),
                body_battery_high=data.get('body_battery_high'),
                body_battery_low=data.get('body_battery_low')
            )
        elif metric_type == MetricType.SLEEP:
            self.db.store_health_metric(
                user_id, sync_date,
                sleep_duration_hours=data.get('sleep_duration_hours'),
                deep_sleep_percentage=data.get('deep_sleep_percentage'),
                light_sleep_percentage=data.get('light_sleep_percentage'),
                rem_sleep_percentage=data.get('rem_sleep_percentage'),
                awake_percentage=data.get('awake_percentage'),
                average_spo2=data.get('average_spo2'),
                average_respiration=data.get('average_respiration')
            )
        elif metric_type == MetricType.HEART_RATE:
            self.db.store_health_metric(
                user_id, sync_date,
                average_heart_rate=data.get('average_heart_rate')
            )
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
            self.db.store_health_metric(
                user_id, sync_date,
                avg_waking_respiration_value=data.get('avg_waking_respiration_value'),
                avg_sleep_respiration_value=data.get('avg_sleep_respiration_value'),
                lowest_respiration_value=data.get('lowest_respiration_value'),
                highest_respiration_value=data.get('highest_respiration_value')
            )
    
    def _has_metric_data(self, user_id: int, metric_type: MetricType, sync_date: date) -> bool:
        """Universal method to check if metric data exists."""
        if metric_type in [MetricType.DAILY_SUMMARY, MetricType.SLEEP, 
                          MetricType.TRAINING_READINESS, MetricType.HRV, MetricType.RESPIRATION]:
            return self.db.health_metric_exists(user_id, sync_date)
        elif metric_type in [MetricType.BODY_BATTERY, MetricType.STRESS, MetricType.HEART_RATE]:
            # Check both timeseries and normalized table
            return (self.db.health_metric_exists(user_id, sync_date) or 
                   self.db.has_data_for_date(user_id, metric_type, sync_date))
        else:
            # Legacy metrics
            return self.db.has_data_for_date(user_id, metric_type, sync_date)
    
    def query_health_metrics(self, user_id: int, start_date: date, end_date: date) -> List[Dict]:
        """Query normalized health metrics for analysis."""
        return self.db.get_health_metrics(user_id, start_date, end_date)
    
    def query_activities(self, user_id: int, start_date: date, end_date: date, 
                        activity_name: Optional[str] = None) -> List[Dict]:
        """Query activities for analysis."""
        return self.db.get_activities(user_id, start_date, end_date, activity_name)
    
    def query_timeseries(self, user_id: int, metric_type: MetricType, 
                        start_time: datetime, end_time: datetime) -> List[Dict]:
        """Query timeseries data."""
        start_ts = int(start_time.timestamp() * self.config.database.ms_per_second)
        end_ts = int(end_time.timestamp() * self.config.database.ms_per_second)
        
        data = self.db.get_timeseries(user_id, metric_type, start_ts, end_ts)
        
        return [{
            'timestamp': ts,
            'datetime': datetime.fromtimestamp(ts / self.config.database.ms_per_second).isoformat(),
            'value': value,
            'metadata': metadata
        } for ts, value, metadata in data]
    
    # Analytics methods
    def get_sleep_analysis(self, user_id: int, start_date: date, end_date: date) -> Dict[str, Any]:
        """Get comprehensive sleep analysis."""
        return self.db.get_sleep_analysis(user_id, start_date, end_date)
    
    def get_activity_summary(self, user_id: int, start_date: date, end_date: date) -> Dict[str, Any]:
        """Get activity summary and statistics."""
        return self.db.get_activity_summary(user_id, start_date, end_date)
    
    def get_health_trends(self, user_id: int, start_date: date, end_date: date) -> Dict[str, Any]:
        """Get health trends and key metrics."""
        return self.db.get_health_trends(user_id, start_date, end_date)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        return self.db.get_stats()


class ActivitiesIterator:
    """Iterator-based activities synchronization with automatic pagination."""
    
    def __init__(self, api_client, sync_config, progress_reporter):
        """Initialize activities iterator."""
        self.api_client = api_client
        self.config = sync_config
        self.progress = progress_reporter
        self.metric_accessor = api_client.metrics.get('activities')
        
        # Pagination state
        self.current_offset = 0
        self.batch_size = sync_config.activities_batch_size
        self.current_batch = []
        self.batch_index = 0
        self.exhausted = False
        
        # Activity processing state
        self.current_activity = None
        self.current_activity_date = None
        
    async def _fetch_next_batch(self) -> bool:
        """Fetch next batch of activities. Returns True if more data available."""
        if self.exhausted:
            return False
            
        try:
            batch = self.metric_accessor.raw(limit=self.batch_size, start=self.current_offset)
            
            if not batch or len(batch) == 0:
                self.exhausted = True
                return False
                
            self.current_batch = batch
            self.batch_index = 0
            self.current_offset += len(batch)
            
            # Check if we've reached the end
            if len(batch) < self.batch_size:
                self.exhausted = True
                
            # Rate limiting
            await asyncio.sleep(self.config.rate_limit_delay)
            return True
            
        except Exception as e:
            self.progress.error(f"Failed to fetch activities batch at offset {self.current_offset}: {e}")
            self.exhausted = True
            # For critical network/API errors, we should fail fast rather than silently continue
            if "network" in str(e).lower() or "connection" in str(e).lower():
                raise RuntimeError(f"Network error during activities sync: {e}") from e
            return False
    
    async def _advance_to_next_activity(self) -> bool:
        """Move to next activity. Returns True if activity available."""
        # Try to get next activity from current batch
        while self.batch_index >= len(self.current_batch):
            # Need to fetch next batch
            if not await self._fetch_next_batch():
                self.current_activity = None
                self.current_activity_date = None
                return False
        
        # Get current activity from batch
        raw_activity = self.current_batch[self.batch_index]
        self.batch_index += 1
        
        # Parse activity data
        try:
            if isinstance(raw_activity, dict):
                activity_obj = type('Activity', (), raw_activity)
            else:
                activity_obj = raw_activity
                
            self.current_activity = activity_obj
            self.current_activity_date = self._extract_activity_date(activity_obj)
            
            if not self.current_activity_date:
                return await self._advance_to_next_activity()  # Try next activity
                
            return True
            
        except Exception as e:
            self.progress.warning(f"Failed to parse activity: {e}")
            return await self._advance_to_next_activity()  # Try next activity
    
    def _extract_activity_date(self, activity) -> Optional[date]:
        """Extract date from activity start time."""
        try:
            start_time = getattr(activity, 'start_time_local', None) or \
                        getattr(activity, 'startTimeLocal', None) or \
                        getattr(activity, 'start_time', None)
            
            if start_time:
                if isinstance(start_time, str):
                    from datetime import datetime
                    start_time = start_time.replace('Z', '+00:00')
                    if '.' in start_time and '+' in start_time:
                        dt = datetime.fromisoformat(start_time)
                    else:
                        dt = datetime.fromisoformat(start_time)
                    return dt.date()
                elif hasattr(start_time, 'date'):
                    return start_time.date()
        except Exception:
            pass
        return None
    
    async def get_activities_for_date(self, target_date: date) -> List[Any]:
        """Get all activities for a specific date."""
        activities = []
        
        # Ensure we have a current activity
        if self.current_activity is None:
            if not await self._advance_to_next_activity():
                return activities
        
        # Process activities while they match or are newer than target_date
        while self.current_activity is not None:
            if self.current_activity_date is None:
                # Skip activities without dates
                if not await self._advance_to_next_activity():
                    break
                continue
                
            if self.current_activity_date > target_date:
                # Activity is newer than target - skip it
                if not await self._advance_to_next_activity():
                    break
                continue
                
            elif self.current_activity_date == target_date:
                # Activity matches target date - collect it
                activities.append(self.current_activity)
                if not await self._advance_to_next_activity():
                    break
                continue
                
            else:  # self.current_activity_date < target_date
                # Activity is older than target - we're done for this date
                break
        
        return activities
    
