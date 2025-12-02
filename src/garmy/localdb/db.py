"""SQLAlchemy database for health metrics storage."""

from datetime import date
from pathlib import Path
from typing import List, Dict, Any, Optional, TYPE_CHECKING

from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker, Session

from .models import Base, TimeSeries, Activity, DailyHealthMetric, SyncStatus, MetricType

if TYPE_CHECKING:
    from .config import DatabaseConfig
else:
    DatabaseConfig = None


def _get_default_config() -> 'DatabaseConfig':
    """Get default database configuration."""
    if DatabaseConfig is None:
        from .config import DatabaseConfig as _DatabaseConfig
        return _DatabaseConfig()
    return DatabaseConfig()


class HealthDB:
    """SQLAlchemy database for health metrics."""
    
    def __init__(self, 
                 db_path: Path = Path("health.db"), 
                 config: Optional['DatabaseConfig'] = None):
        """Initialize database.
        
        Args:
            db_path: Path to SQLite database file.
            config: Database configuration.
        """
        self.db_path = db_path
        self.config = config if config is not None else _get_default_config()
        
        self.engine = create_engine(f"sqlite:///{db_path}")
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        Base.metadata.create_all(self.engine)
    
    def get_session(self) -> Session:
        """Get database session."""
        return self.SessionLocal()
    
    def get_schema_info(self) -> Dict[str, Any]:
        """Get database schema information."""
        return {
            "tables": [table.name for table in Base.metadata.tables.values()],
            "db_path": str(self.db_path)
        }
    
    def validate_schema(self) -> bool:
        """Validate database schema."""
        try:
            expected_tables = {'timeseries', 'activities', 'daily_health_metrics', 'sync_status'}
            actual_tables = set(Base.metadata.tables.keys())
            return expected_tables.issubset(actual_tables)
        except Exception:
            return False
    
    def store_timeseries_batch(self, user_id: int, metric_type: MetricType, data: List[tuple]):
        """Store batch of timeseries data."""
        with self.get_session() as session:
            for timestamp, value, metadata in data:
                # Skip entries with None values (NOT NULL constraint)
                if value is None:
                    continue
                timeseries = TimeSeries(
                    user_id=user_id,
                    metric_type=metric_type.value,
                    timestamp=timestamp,
                    value=value,
                    meta_data=metadata
                )
                session.merge(timeseries)
            session.commit()
    
    def store_activity(self, user_id: int, activity_data: Dict[str, Any]):
        """Store activity data."""
        with self.get_session() as session:
            activity = Activity(
                user_id=user_id,
                activity_id=activity_data['activity_id'],
                activity_date=activity_data['activity_date'],
                activity_name=activity_data.get('activity_name'),
                duration_seconds=activity_data.get('duration_seconds'),
                avg_heart_rate=activity_data.get('avg_heart_rate'),
                training_load=activity_data.get('training_load'),
                start_time=activity_data.get('start_time')
            )
            session.merge(activity)
            session.commit()
    
    def store_health_metric(self, user_id: int, metric_date: date, **kwargs):
        """Store daily health metric data."""
        with self.get_session() as session:
            # Get existing record or create new one
            metric = session.query(DailyHealthMetric).filter(
                and_(
                    DailyHealthMetric.user_id == user_id,
                    DailyHealthMetric.metric_date == metric_date
                )
            ).first()
            
            if metric is None:
                metric = DailyHealthMetric(user_id=user_id, metric_date=metric_date)
            
            # Update fields from kwargs
            for field, value in kwargs.items():
                if hasattr(metric, field):
                    setattr(metric, field, value)
            
            session.merge(metric)
            session.commit()
    
    
    def create_sync_status(self, user_id: int, sync_date: date, metric_type: MetricType, status: str = 'pending'):
        """Create sync status record."""
        with self.get_session() as session:
            sync_status = SyncStatus(
                user_id=user_id,
                sync_date=sync_date,
                metric_type=metric_type.value,
                status=status
            )
            session.merge(sync_status)
            session.commit()
    
    def update_sync_status(self, user_id: int, sync_date: date, metric_type: MetricType, 
                          status: str, error_message: Optional[str] = None):
        """Update sync status record."""
        with self.get_session() as session:
            from datetime import datetime
            sync_status = session.query(SyncStatus).filter(
                and_(
                    SyncStatus.user_id == user_id,
                    SyncStatus.sync_date == sync_date,
                    SyncStatus.metric_type == metric_type.value
                )
            ).first()
            
            if sync_status:
                sync_status.status = status
                sync_status.synced_at = datetime.utcnow()
                if error_message:
                    sync_status.error_message = error_message
                session.commit()
    
    def get_sync_status(self, user_id: int, sync_date: date, metric_type: MetricType) -> Optional[str]:
        """Get sync status for specific metric."""
        with self.get_session() as session:
            sync_status = session.query(SyncStatus).filter(
                and_(
                    SyncStatus.user_id == user_id,
                    SyncStatus.sync_date == sync_date,
                    SyncStatus.metric_type == metric_type.value
                )
            ).first()
            return sync_status.status if sync_status else None
    
    def get_pending_metrics(self, user_id: int, sync_date: date) -> List[str]:
        """Get list of pending metrics for date."""
        with self.get_session() as session:
            pending_statuses = session.query(SyncStatus).filter(
                and_(
                    SyncStatus.user_id == user_id,
                    SyncStatus.sync_date == sync_date,
                    SyncStatus.status == 'pending'
                )
            ).all()
            return [status.metric_type for status in pending_statuses]
    
    def sync_status_exists(self, user_id: int, sync_date: date, metric_type: MetricType) -> bool:
        """Check if sync status record exists."""
        with self.get_session() as session:
            return session.query(SyncStatus).filter(
                and_(
                    SyncStatus.user_id == user_id,
                    SyncStatus.sync_date == sync_date,
                    SyncStatus.metric_type == metric_type.value
                )
            ).first() is not None
    
    
    def activity_exists(self, user_id: int, activity_id: str) -> bool:
        """Check if activity exists."""
        with self.get_session() as session:
            return session.query(Activity).filter(
                and_(
                    Activity.user_id == user_id,
                    Activity.activity_id == activity_id
                )
            ).first() is not None
    
    def health_metric_exists(self, user_id: int, metric_date: date) -> bool:
        """Check if health metric exists for date."""
        with self.get_session() as session:
            return session.query(DailyHealthMetric).filter(
                and_(
                    DailyHealthMetric.user_id == user_id,
                    DailyHealthMetric.metric_date == metric_date
                )
            ).first() is not None
    
    
    def get_health_metrics(self, user_id: int, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """Query health metrics for date range."""
        with self.get_session() as session:
            metrics = session.query(DailyHealthMetric).filter(
                and_(
                    DailyHealthMetric.user_id == user_id,
                    DailyHealthMetric.metric_date >= start_date,
                    DailyHealthMetric.metric_date <= end_date
                )
            ).order_by(DailyHealthMetric.metric_date).all()
            
            return [self._metric_to_dict(metric) for metric in metrics]
    
    def get_activities(self, user_id: int, start_date: date, end_date: date, 
                      activity_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Query activities for date range."""
        with self.get_session() as session:
            query = session.query(Activity).filter(
                and_(
                    Activity.user_id == user_id,
                    Activity.activity_date >= start_date,
                    Activity.activity_date <= end_date
                )
            )
            
            if activity_name:
                query = query.filter(Activity.activity_name == activity_name)
            
            activities = query.order_by(Activity.activity_date).all()
            return [self._activity_to_dict(activity) for activity in activities]
    
    def get_timeseries(self, user_id: int, metric_type: MetricType,
                      start_timestamp: int, end_timestamp: int) -> List[tuple]:
        """Query timeseries data for time range."""
        with self.get_session() as session:
            timeseries = session.query(TimeSeries).filter(
                and_(
                    TimeSeries.user_id == user_id,
                    TimeSeries.metric_type == metric_type.value,
                    TimeSeries.timestamp >= start_timestamp,
                    TimeSeries.timestamp <= end_timestamp
                )
            ).order_by(TimeSeries.timestamp).all()
            
            return [(ts.timestamp, ts.value, ts.meta_data) for ts in timeseries]
    
    
    def _metric_to_dict(self, metric: DailyHealthMetric) -> Dict[str, Any]:
        """Convert DailyHealthMetric to dictionary."""
        return {
            'user_id': metric.user_id,
            'metric_date': metric.metric_date,
            'total_steps': metric.total_steps,
            'step_goal': metric.step_goal,
            'total_distance_meters': metric.total_distance_meters,
            'total_calories': metric.total_calories,
            'active_calories': metric.active_calories,
            'bmr_calories': metric.bmr_calories,
            'resting_heart_rate': metric.resting_heart_rate,
            'max_heart_rate': metric.max_heart_rate,
            'min_heart_rate': metric.min_heart_rate,
            'average_heart_rate': metric.average_heart_rate,
            'avg_stress_level': metric.avg_stress_level,
            'max_stress_level': metric.max_stress_level,
            'body_battery_high': metric.body_battery_high,
            'body_battery_low': metric.body_battery_low,
            'sleep_duration_hours': metric.sleep_duration_hours,
            'deep_sleep_hours': metric.deep_sleep_hours,
            'light_sleep_hours': metric.light_sleep_hours,
            'rem_sleep_hours': metric.rem_sleep_hours,
            'awake_hours': metric.awake_hours,
            'deep_sleep_percentage': metric.deep_sleep_percentage,
            'light_sleep_percentage': metric.light_sleep_percentage,
            'rem_sleep_percentage': metric.rem_sleep_percentage,
            'awake_percentage': metric.awake_percentage,
            'average_spo2': metric.average_spo2,
            'average_respiration': metric.average_respiration,
            'training_readiness_score': metric.training_readiness_score,
            'training_readiness_level': metric.training_readiness_level,
            'training_readiness_feedback': metric.training_readiness_feedback,
            'hrv_weekly_avg': metric.hrv_weekly_avg,
            'hrv_last_night_avg': metric.hrv_last_night_avg,
            'hrv_status': metric.hrv_status,
            'avg_waking_respiration_value': metric.avg_waking_respiration_value,
            'avg_sleep_respiration_value': metric.avg_sleep_respiration_value,
            'lowest_respiration_value': metric.lowest_respiration_value,
            'highest_respiration_value': metric.highest_respiration_value,
            'created_at': metric.created_at,
            'updated_at': metric.updated_at
        }
    
    def _activity_to_dict(self, activity: Activity) -> Dict[str, Any]:
        """Convert Activity to dictionary."""
        return {
            'user_id': activity.user_id,
            'activity_id': activity.activity_id,
            'activity_date': activity.activity_date,
            'activity_name': activity.activity_name,
            'duration_seconds': activity.duration_seconds,
            'avg_heart_rate': activity.avg_heart_rate,
            'training_load': activity.training_load,
            'start_time': activity.start_time,
            'created_at': activity.created_at
        }