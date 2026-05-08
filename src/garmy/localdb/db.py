"""SQLAlchemy database for health metrics storage."""

from datetime import date, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import and_, create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from .models import (
    Activity,
    ActivitySplit,
    Base,
    BodyComposition,
    DailyHealthMetric,
    ExerciseSet,
    HealthSnapshotRecord,
    HealthSnapshotSummaryStat,
    HealthSnapshotZoneTime,
    MetricType,
    PerformanceMetric,
    SyncStatus,
    TimeSeries,
)

if TYPE_CHECKING:
    from .config import DatabaseConfig
else:
    DatabaseConfig = None


def _get_default_config() -> "DatabaseConfig":
    """Get default database configuration."""
    if DatabaseConfig is None:
        from .config import DatabaseConfig as _DatabaseConfig

        return _DatabaseConfig()
    return DatabaseConfig()


class HealthDB:
    """SQLAlchemy database for health metrics."""

    def __init__(
        self,
        db_path: Path = Path("health.db"),
        config: Optional["DatabaseConfig"] = None,
    ):
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

        # Run migrations to add new columns to existing databases
        self._migrate_schema()

    def _migrate_schema(self):
        """Migrate database schema to add new columns for existing databases."""
        inspector = inspect(self.engine)

        # Check if activities table exists and needs migration
        if "activities" in inspector.get_table_names():
            existing_columns = {
                col["name"] for col in inspector.get_columns("activities")
            }

            # New columns to add to activities table
            new_activity_columns = [
                ("activity_type", "VARCHAR"),
                ("distance_meters", "FLOAT"),
                ("calories", "INTEGER"),
                ("elevation_gain", "FLOAT"),
                ("elevation_loss", "FLOAT"),
                ("avg_speed", "FLOAT"),
                ("max_speed", "FLOAT"),
                ("max_heart_rate", "INTEGER"),
                ("total_sets", "INTEGER"),
                ("total_reps", "INTEGER"),
                ("total_weight_kg", "FLOAT"),
                ("details_synced", "BOOLEAN DEFAULT 0"),
                ("updated_at", "DATETIME"),
            ]

            with self.engine.connect() as conn:
                for col_name, col_type in new_activity_columns:
                    if col_name not in existing_columns:
                        try:
                            conn.execute(
                                text(
                                    f"ALTER TABLE activities ADD COLUMN {col_name} {col_type}"
                                )
                            )
                            conn.commit()
                        except Exception:
                            # Column might already exist or other issue, continue
                            pass

        # Migrate daily_health_metrics table for new sleep/skin temp columns
        if "daily_health_metrics" in inspector.get_table_names():
            existing_columns = {
                col["name"] for col in inspector.get_columns("daily_health_metrics")
            }

            new_health_columns = [
                ("sleep_score", "INTEGER"),
                ("sleep_score_qualifier", "VARCHAR"),
                ("sleep_bedtime", "VARCHAR"),
                ("sleep_wake_time", "VARCHAR"),
                ("sleep_need_minutes", "INTEGER"),
                ("skin_temp_deviation_c", "FLOAT"),
                # SpO2 fields
                ("lowest_spo2", "FLOAT"),
                # Intensity minutes
                ("moderate_intensity_minutes", "INTEGER"),
                ("vigorous_intensity_minutes", "INTEGER"),
                ("intensity_minutes_total", "INTEGER"),
                ("intensity_minutes_goal", "INTEGER"),
                # Floors
                ("floors_ascended", "INTEGER"),
                ("floors_descended", "INTEGER"),
                # Dedicated resting HR
                ("dedicated_resting_heart_rate", "INTEGER"),
                # HRV baseline fields
                ("hrv_last_night_5min_high", "FLOAT"),
                ("hrv_baseline_low_upper", "FLOAT"),
                ("hrv_baseline_balanced_low", "FLOAT"),
                ("hrv_baseline_balanced_upper", "FLOAT"),
            ]

            with self.engine.connect() as conn:
                for col_name, col_type in new_health_columns:
                    if col_name not in existing_columns:
                        try:
                            conn.execute(
                                text(
                                    f"ALTER TABLE daily_health_metrics ADD COLUMN {col_name} {col_type}"
                                )
                            )
                            conn.commit()
                        except Exception:
                            # Column might already exist or other issue, continue
                            pass

        # Create exercise_sets table if it doesn't exist (handled by create_all above)

    def get_session(self) -> Session:
        """Get database session."""
        return self.SessionLocal()

    def get_schema_info(self) -> Dict[str, Any]:
        """Get database schema information."""
        return {
            "tables": [table.name for table in Base.metadata.tables.values()],
            "db_path": str(self.db_path),
        }

    def validate_schema(self) -> bool:
        """Validate database schema."""
        try:
            expected_tables = {
                "timeseries",
                "activities",
                "daily_health_metrics",
                "sync_status",
                "exercise_sets",
                "activity_splits",
                "body_composition",
                "performance_metrics",
            }
            actual_tables = set(Base.metadata.tables.keys())
            return expected_tables.issubset(actual_tables)
        except Exception:
            return False

    def store_timeseries_batch(
        self, user_id: int, metric_type: MetricType, data: List[tuple]
    ):
        """Store batch of timeseries data."""
        import math

        with self.get_session() as session:
            with session.no_autoflush:
                for timestamp, value, metadata in data:
                    # Skip entries with None/NaN values (NOT NULL constraint)
                    if value is None or (
                        isinstance(value, float) and math.isnan(value)
                    ):
                        continue
                    timeseries = TimeSeries(
                        user_id=user_id,
                        metric_type=metric_type.value,
                        timestamp=timestamp,
                        value=value,
                        meta_data=metadata,
                    )
                    session.merge(timeseries)
            session.commit()

    def store_activity(self, user_id: int, activity_data: Dict[str, Any]):
        """Store activity data including all available fields from API."""
        with self.get_session() as session:
            activity = Activity(
                user_id=user_id,
                activity_id=activity_data["activity_id"],
                activity_date=activity_data["activity_date"],
                activity_name=activity_data.get("activity_name"),
                duration_seconds=activity_data.get("duration_seconds"),
                avg_heart_rate=activity_data.get("avg_heart_rate"),
                max_heart_rate=activity_data.get("max_heart_rate"),
                training_load=activity_data.get("training_load"),
                start_time=activity_data.get("start_time"),
                # Extended fields from activity list
                activity_type=activity_data.get("activity_type"),
                distance_meters=activity_data.get("distance_meters"),
                calories=activity_data.get("calories"),
                elevation_gain=activity_data.get("elevation_gain"),
                elevation_loss=activity_data.get("elevation_loss"),
                avg_speed=activity_data.get("avg_speed"),
                max_speed=activity_data.get("max_speed"),
            )
            session.merge(activity)
            session.commit()

    def store_health_metric(self, user_id: int, metric_date: date, **kwargs):
        """Store daily health metric data."""
        with self.get_session() as session:
            # Get existing record or create new one
            metric = (
                session.query(DailyHealthMetric)
                .filter(
                    and_(
                        DailyHealthMetric.user_id == user_id,
                        DailyHealthMetric.metric_date == metric_date,
                    )
                )
                .first()
            )

            if metric is None:
                metric = DailyHealthMetric(user_id=user_id, metric_date=metric_date)

            # Update fields from kwargs
            for field, value in kwargs.items():
                if hasattr(metric, field):
                    setattr(metric, field, value)

            session.merge(metric)
            session.commit()

    def store_performance_metric(self, user_id: int, metric_date: date, **kwargs):
        """Store performance metric data (training load/status, endurance score)."""
        with self.get_session() as session:
            metric = (
                session.query(PerformanceMetric)
                .filter(
                    and_(
                        PerformanceMetric.user_id == user_id,
                        PerformanceMetric.metric_date == metric_date,
                    )
                )
                .first()
            )

            if metric is None:
                metric = PerformanceMetric(user_id=user_id, metric_date=metric_date)

            for field, value in kwargs.items():
                if hasattr(metric, field):
                    setattr(metric, field, value)

            session.merge(metric)
            session.commit()

    def create_sync_status(
        self,
        user_id: int,
        sync_date: date,
        metric_type: MetricType,
        status: str = "pending",
    ):
        """Create sync status record."""
        with self.get_session() as session:
            sync_status = SyncStatus(
                user_id=user_id,
                sync_date=sync_date,
                metric_type=metric_type.value,
                status=status,
            )
            session.merge(sync_status)
            session.commit()

    def update_sync_status(
        self,
        user_id: int,
        sync_date: date,
        metric_type: MetricType,
        status: str,
        error_message: Optional[str] = None,
    ):
        """Update sync status record."""
        with self.get_session() as session:
            from datetime import datetime

            sync_status = (
                session.query(SyncStatus)
                .filter(
                    and_(
                        SyncStatus.user_id == user_id,
                        SyncStatus.sync_date == sync_date,
                        SyncStatus.metric_type == metric_type.value,
                    )
                )
                .first()
            )

            if sync_status:
                sync_status.status = status
                sync_status.synced_at = datetime.utcnow()
                if error_message:
                    sync_status.error_message = error_message
                session.commit()

    def get_sync_status(
        self, user_id: int, sync_date: date, metric_type: MetricType
    ) -> Optional[str]:
        """Get sync status for specific metric."""
        with self.get_session() as session:
            sync_status = (
                session.query(SyncStatus)
                .filter(
                    and_(
                        SyncStatus.user_id == user_id,
                        SyncStatus.sync_date == sync_date,
                        SyncStatus.metric_type == metric_type.value,
                    )
                )
                .first()
            )
            return sync_status.status if sync_status else None

    def reset_completed_statuses(
        self, user_id: int, start_date: date, end_date: date
    ) -> int:
        """Reset completed sync statuses to pending for a date range.

        Returns the number of records reset.
        """
        with self.get_session() as session:
            count = (
                session.query(SyncStatus)
                .filter(
                    and_(
                        SyncStatus.user_id == user_id,
                        SyncStatus.sync_date >= start_date,
                        SyncStatus.sync_date <= end_date,
                        SyncStatus.status == "completed",
                    )
                )
                .update({"status": "pending"})
            )
            session.commit()
            return count

    def get_pending_metrics(self, user_id: int, sync_date: date) -> List[str]:
        """Get list of pending metrics for date."""
        with self.get_session() as session:
            pending_statuses = (
                session.query(SyncStatus)
                .filter(
                    and_(
                        SyncStatus.user_id == user_id,
                        SyncStatus.sync_date == sync_date,
                        SyncStatus.status == "pending",
                    )
                )
                .all()
            )
            return [status.metric_type for status in pending_statuses]

    def sync_status_exists(
        self, user_id: int, sync_date: date, metric_type: MetricType
    ) -> bool:
        """Check if sync status record exists."""
        with self.get_session() as session:
            return (
                session.query(SyncStatus)
                .filter(
                    and_(
                        SyncStatus.user_id == user_id,
                        SyncStatus.sync_date == sync_date,
                        SyncStatus.metric_type == metric_type.value,
                    )
                )
                .first()
                is not None
            )

    def activity_exists(self, user_id: int, activity_id: str) -> bool:
        """Check if activity exists."""
        with self.get_session() as session:
            return (
                session.query(Activity)
                .filter(
                    and_(
                        Activity.user_id == user_id, Activity.activity_id == activity_id
                    )
                )
                .first()
                is not None
            )

    def health_metric_exists(self, user_id: int, metric_date: date) -> bool:
        """Check if health metric exists for date."""
        with self.get_session() as session:
            return (
                session.query(DailyHealthMetric)
                .filter(
                    and_(
                        DailyHealthMetric.user_id == user_id,
                        DailyHealthMetric.metric_date == metric_date,
                    )
                )
                .first()
                is not None
            )

    def get_health_metrics(
        self, user_id: int, start_date: date, end_date: date
    ) -> List[Dict[str, Any]]:
        """Query health metrics for date range."""
        with self.get_session() as session:
            metrics = (
                session.query(DailyHealthMetric)
                .filter(
                    and_(
                        DailyHealthMetric.user_id == user_id,
                        DailyHealthMetric.metric_date >= start_date,
                        DailyHealthMetric.metric_date <= end_date,
                    )
                )
                .order_by(DailyHealthMetric.metric_date)
                .all()
            )

            return [self._metric_to_dict(metric) for metric in metrics]

    def get_activities(
        self,
        user_id: int,
        start_date: date,
        end_date: date,
        activity_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Query activities for date range."""
        with self.get_session() as session:
            query = session.query(Activity).filter(
                and_(
                    Activity.user_id == user_id,
                    Activity.activity_date >= start_date,
                    Activity.activity_date <= end_date,
                )
            )

            if activity_name:
                query = query.filter(Activity.activity_name == activity_name)

            activities = query.order_by(Activity.activity_date).all()
            return [self._activity_to_dict(activity) for activity in activities]

    def get_timeseries(
        self,
        user_id: int,
        metric_type: MetricType,
        start_timestamp: int,
        end_timestamp: int,
    ) -> List[tuple]:
        """Query timeseries data for time range."""
        with self.get_session() as session:
            timeseries = (
                session.query(TimeSeries)
                .filter(
                    and_(
                        TimeSeries.user_id == user_id,
                        TimeSeries.metric_type == metric_type.value,
                        TimeSeries.timestamp >= start_timestamp,
                        TimeSeries.timestamp <= end_timestamp,
                    )
                )
                .order_by(TimeSeries.timestamp)
                .all()
            )

            return [(ts.timestamp, ts.value, ts.meta_data) for ts in timeseries]

    def _metric_to_dict(self, metric: DailyHealthMetric) -> Dict[str, Any]:
        """Convert DailyHealthMetric to dictionary."""
        return {
            "user_id": metric.user_id,
            "metric_date": metric.metric_date,
            "total_steps": metric.total_steps,
            "step_goal": metric.step_goal,
            "total_distance_meters": metric.total_distance_meters,
            "total_calories": metric.total_calories,
            "active_calories": metric.active_calories,
            "bmr_calories": metric.bmr_calories,
            "resting_heart_rate": metric.resting_heart_rate,
            "max_heart_rate": metric.max_heart_rate,
            "min_heart_rate": metric.min_heart_rate,
            "average_heart_rate": metric.average_heart_rate,
            "avg_stress_level": metric.avg_stress_level,
            "max_stress_level": metric.max_stress_level,
            "body_battery_high": metric.body_battery_high,
            "body_battery_low": metric.body_battery_low,
            "sleep_duration_hours": metric.sleep_duration_hours,
            "deep_sleep_hours": metric.deep_sleep_hours,
            "light_sleep_hours": metric.light_sleep_hours,
            "rem_sleep_hours": metric.rem_sleep_hours,
            "awake_hours": metric.awake_hours,
            "deep_sleep_percentage": metric.deep_sleep_percentage,
            "light_sleep_percentage": metric.light_sleep_percentage,
            "rem_sleep_percentage": metric.rem_sleep_percentage,
            "awake_percentage": metric.awake_percentage,
            "average_spo2": metric.average_spo2,
            "lowest_spo2": metric.lowest_spo2,
            "average_respiration": metric.average_respiration,
            "training_readiness_score": metric.training_readiness_score,
            "training_readiness_level": metric.training_readiness_level,
            "training_readiness_feedback": metric.training_readiness_feedback,
            "hrv_weekly_avg": metric.hrv_weekly_avg,
            "hrv_last_night_avg": metric.hrv_last_night_avg,
            "hrv_status": metric.hrv_status,
            "hrv_last_night_5min_high": metric.hrv_last_night_5min_high,
            "hrv_baseline_low_upper": metric.hrv_baseline_low_upper,
            "hrv_baseline_balanced_low": metric.hrv_baseline_balanced_low,
            "hrv_baseline_balanced_upper": metric.hrv_baseline_balanced_upper,
            "avg_waking_respiration_value": metric.avg_waking_respiration_value,
            "avg_sleep_respiration_value": metric.avg_sleep_respiration_value,
            "lowest_respiration_value": metric.lowest_respiration_value,
            "highest_respiration_value": metric.highest_respiration_value,
            # Intensity minutes
            "moderate_intensity_minutes": metric.moderate_intensity_minutes,
            "vigorous_intensity_minutes": metric.vigorous_intensity_minutes,
            "intensity_minutes_total": metric.intensity_minutes_total,
            "intensity_minutes_goal": metric.intensity_minutes_goal,
            # Floors
            "floors_ascended": metric.floors_ascended,
            "floors_descended": metric.floors_descended,
            # Dedicated resting HR
            "dedicated_resting_heart_rate": metric.dedicated_resting_heart_rate,
            # Sleep enhancements
            "sleep_score": metric.sleep_score,
            "sleep_score_qualifier": metric.sleep_score_qualifier,
            "sleep_bedtime": metric.sleep_bedtime,
            "sleep_wake_time": metric.sleep_wake_time,
            "sleep_need_minutes": metric.sleep_need_minutes,
            # Skin temperature
            "skin_temp_deviation_c": metric.skin_temp_deviation_c,
            "skin_temp_deviation_f": (
                metric.skin_temp_deviation_c * 1.8
                if metric.skin_temp_deviation_c
                else None
            ),
            "created_at": metric.created_at,
            "updated_at": metric.updated_at,
        }

    def _activity_to_dict(self, activity: Activity) -> Dict[str, Any]:
        """Convert Activity to dictionary."""
        return {
            "user_id": activity.user_id,
            "activity_id": activity.activity_id,
            "activity_date": activity.activity_date,
            "activity_name": activity.activity_name,
            "duration_seconds": activity.duration_seconds,
            "avg_heart_rate": activity.avg_heart_rate,
            "training_load": activity.training_load,
            "start_time": activity.start_time,
            "created_at": activity.created_at,
            # Extended activity details
            "activity_type": activity.activity_type,
            "distance_meters": activity.distance_meters,
            "calories": activity.calories,
            "elevation_gain": activity.elevation_gain,
            "elevation_loss": activity.elevation_loss,
            "avg_speed": activity.avg_speed,
            "max_speed": activity.max_speed,
            "max_heart_rate": activity.max_heart_rate,
            # Strength training summary
            "total_sets": activity.total_sets,
            "total_reps": activity.total_reps,
            "total_weight_kg": activity.total_weight_kg,
            "details_synced": activity.details_synced,
            "updated_at": activity.updated_at,
        }

    def store_exercise_sets(
        self, user_id: int, activity_id: str, sets: List[Dict[str, Any]]
    ):
        """Store exercise sets for an activity."""
        with self.get_session() as session:
            for set_data in sets:
                exercise_set = ExerciseSet(
                    user_id=user_id,
                    activity_id=activity_id,
                    set_order=set_data.get("set_order", 0),
                    exercise_category=set_data.get("exercise_category"),
                    exercise_name=set_data.get("exercise_name"),
                    set_type=set_data.get("set_type"),
                    repetition_count=set_data.get("repetition_count"),
                    weight_grams=set_data.get("weight_grams"),
                    duration_seconds=set_data.get("duration_seconds"),
                    start_time=set_data.get("start_time"),
                )
                session.merge(exercise_set)
            session.commit()

    def get_exercise_sets(self, user_id: int, activity_id: str) -> List[Dict[str, Any]]:
        """Get exercise sets for an activity."""
        with self.get_session() as session:
            sets = (
                session.query(ExerciseSet)
                .filter(
                    and_(
                        ExerciseSet.user_id == user_id,
                        ExerciseSet.activity_id == activity_id,
                    )
                )
                .order_by(ExerciseSet.set_order)
                .all()
            )
            return [self._exercise_set_to_dict(s) for s in sets]

    def get_all_exercise_sets(
        self, user_id: int, start_date: date, end_date: date
    ) -> List[Dict[str, Any]]:
        """Get all exercise sets for activities in date range."""
        with self.get_session() as session:
            # Join with activities to filter by date
            sets = (
                session.query(ExerciseSet)
                .join(
                    Activity,
                    and_(
                        ExerciseSet.user_id == Activity.user_id,
                        ExerciseSet.activity_id == Activity.activity_id,
                    ),
                )
                .filter(
                    and_(
                        ExerciseSet.user_id == user_id,
                        Activity.activity_date >= start_date,
                        Activity.activity_date <= end_date,
                    )
                )
                .order_by(Activity.activity_date, ExerciseSet.set_order)
                .all()
            )
            return [self._exercise_set_to_dict(s) for s in sets]

    def update_activity_details(
        self, user_id: int, activity_id: str, details: Dict[str, Any]
    ):
        """Update activity with detailed data."""
        with self.get_session() as session:
            activity = (
                session.query(Activity)
                .filter(
                    and_(
                        Activity.user_id == user_id, Activity.activity_id == activity_id
                    )
                )
                .first()
            )

            if activity:
                for field, value in details.items():
                    if hasattr(activity, field):
                        setattr(activity, field, value)
                activity.details_synced = True
                session.commit()

    def get_activities_without_details(
        self, user_id: int, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get activities that haven't had details synced yet."""
        with self.get_session() as session:
            activities = (
                session.query(Activity)
                .filter(
                    and_(
                        Activity.user_id == user_id,
                        Activity.details_synced == False,  # noqa: E712
                    )
                )
                .order_by(Activity.activity_date.desc())
                .limit(limit)
                .all()
            )
            return [self._activity_to_dict(a) for a in activities]

    def _exercise_set_to_dict(self, exercise_set: ExerciseSet) -> Dict[str, Any]:
        """Convert ExerciseSet to dictionary."""
        return {
            "user_id": exercise_set.user_id,
            "activity_id": exercise_set.activity_id,
            "set_order": exercise_set.set_order,
            "exercise_category": exercise_set.exercise_category,
            "exercise_name": exercise_set.exercise_name,
            "set_type": exercise_set.set_type,
            "repetition_count": exercise_set.repetition_count,
            "weight_grams": exercise_set.weight_grams,
            "weight_kg": (
                exercise_set.weight_grams / 1000 if exercise_set.weight_grams else None
            ),
            "duration_seconds": exercise_set.duration_seconds,
            "start_time": exercise_set.start_time,
            "created_at": exercise_set.created_at,
        }

    def store_activity_splits(
        self, user_id: int, activity_id: str, splits: List[Dict[str, Any]]
    ):
        """Store lap/split data for an activity."""
        with self.get_session() as session:
            for split_data in splits:
                split = ActivitySplit(
                    user_id=user_id,
                    activity_id=activity_id,
                    lap_index=split_data.get("lap_index", 0),
                    start_time=split_data.get("start_time"),
                    duration_seconds=split_data.get("duration_seconds"),
                    moving_duration_seconds=split_data.get("moving_duration_seconds"),
                    distance_meters=split_data.get("distance_meters"),
                    avg_speed=split_data.get("avg_speed"),
                    max_speed=split_data.get("max_speed"),
                    avg_moving_speed=split_data.get("avg_moving_speed"),
                    avg_heart_rate=split_data.get("avg_heart_rate"),
                    max_heart_rate=split_data.get("max_heart_rate"),
                    elevation_gain=split_data.get("elevation_gain"),
                    elevation_loss=split_data.get("elevation_loss"),
                    max_elevation=split_data.get("max_elevation"),
                    min_elevation=split_data.get("min_elevation"),
                    avg_cadence=split_data.get("avg_cadence"),
                    max_cadence=split_data.get("max_cadence"),
                    calories=split_data.get("calories"),
                    start_latitude=split_data.get("start_latitude"),
                    start_longitude=split_data.get("start_longitude"),
                    end_latitude=split_data.get("end_latitude"),
                    end_longitude=split_data.get("end_longitude"),
                    intensity_type=split_data.get("intensity_type"),
                )
                session.merge(split)
            session.commit()

    def get_activity_splits(
        self, user_id: int, activity_id: str
    ) -> List[Dict[str, Any]]:
        """Get lap/split data for an activity."""
        with self.get_session() as session:
            splits = (
                session.query(ActivitySplit)
                .filter(
                    and_(
                        ActivitySplit.user_id == user_id,
                        ActivitySplit.activity_id == activity_id,
                    )
                )
                .order_by(ActivitySplit.lap_index)
                .all()
            )
            return [self._split_to_dict(s) for s in splits]

    def get_all_activity_splits(
        self, user_id: int, start_date: date, end_date: date
    ) -> List[Dict[str, Any]]:
        """Get all splits for activities in date range."""
        with self.get_session() as session:
            # Join with activities to filter by date
            splits = (
                session.query(ActivitySplit)
                .join(
                    Activity,
                    and_(
                        ActivitySplit.user_id == Activity.user_id,
                        ActivitySplit.activity_id == Activity.activity_id,
                    ),
                )
                .filter(
                    and_(
                        ActivitySplit.user_id == user_id,
                        Activity.activity_date >= start_date,
                        Activity.activity_date <= end_date,
                    )
                )
                .order_by(Activity.activity_date, ActivitySplit.lap_index)
                .all()
            )
            return [self._split_to_dict(s) for s in splits]

    def activity_has_splits(self, user_id: int, activity_id: str) -> bool:
        """Check if activity already has splits stored."""
        with self.get_session() as session:
            return (
                session.query(ActivitySplit)
                .filter(
                    and_(
                        ActivitySplit.user_id == user_id,
                        ActivitySplit.activity_id == activity_id,
                    )
                )
                .first()
                is not None
            )

    def _split_to_dict(self, split: ActivitySplit) -> Dict[str, Any]:
        """Convert ActivitySplit to dictionary."""
        # Calculate pace in min/km if we have distance and duration
        pace_min_km = None
        if (
            split.distance_meters
            and split.duration_seconds
            and split.distance_meters > 0
        ):
            pace_min_km = (split.duration_seconds / 60) / (split.distance_meters / 1000)

        return {
            "user_id": split.user_id,
            "activity_id": split.activity_id,
            "lap_index": split.lap_index,
            "start_time": split.start_time,
            "duration_seconds": split.duration_seconds,
            "moving_duration_seconds": split.moving_duration_seconds,
            "distance_meters": split.distance_meters,
            "distance_km": (
                split.distance_meters / 1000 if split.distance_meters else None
            ),
            "avg_speed": split.avg_speed,
            "max_speed": split.max_speed,
            "avg_moving_speed": split.avg_moving_speed,
            "pace_min_km": pace_min_km,
            "avg_heart_rate": split.avg_heart_rate,
            "max_heart_rate": split.max_heart_rate,
            "elevation_gain": split.elevation_gain,
            "elevation_loss": split.elevation_loss,
            "max_elevation": split.max_elevation,
            "min_elevation": split.min_elevation,
            "avg_cadence": split.avg_cadence,
            "max_cadence": split.max_cadence,
            "calories": split.calories,
            "start_latitude": split.start_latitude,
            "start_longitude": split.start_longitude,
            "end_latitude": split.end_latitude,
            "end_longitude": split.end_longitude,
            "intensity_type": split.intensity_type,
            "created_at": split.created_at,
        }

    def store_body_composition(self, user_id: int, entry: Dict[str, Any]):
        """Store body composition measurement."""
        # Convert measurement_date string to date object if needed
        measurement_date = entry["measurement_date"]
        if isinstance(measurement_date, str):
            measurement_date = date.fromisoformat(measurement_date)

        with self.get_session() as session:
            composition = BodyComposition(
                user_id=user_id,
                sample_pk=entry["sample_pk"],
                measurement_date=measurement_date,
                timestamp_gmt=(
                    datetime.fromtimestamp(entry["timestamp_gmt"] / 1000)
                    if entry.get("timestamp_gmt")
                    else None
                ),
                weight_grams=entry.get("weight_grams"),
                bmi=entry.get("bmi"),
                body_fat_percentage=entry.get("body_fat_percentage"),
                body_water_percentage=entry.get("body_water_percentage"),
                bone_mass_grams=entry.get("bone_mass_grams"),
                muscle_mass_grams=entry.get("muscle_mass_grams"),
                visceral_fat=entry.get("visceral_fat"),
                metabolic_age=entry.get("metabolic_age"),
                physique_rating=entry.get("physique_rating"),
                source_type=entry.get("source_type"),
            )
            session.merge(composition)
            session.commit()

    def get_body_composition(
        self, user_id: int, start_date: date, end_date: date
    ) -> List[Dict[str, Any]]:
        """Get body composition measurements for date range."""
        with self.get_session() as session:
            measurements = (
                session.query(BodyComposition)
                .filter(
                    and_(
                        BodyComposition.user_id == user_id,
                        BodyComposition.measurement_date >= start_date,
                        BodyComposition.measurement_date <= end_date,
                    )
                )
                .order_by(BodyComposition.measurement_date)
                .all()
            )
            return [self._body_composition_to_dict(m) for m in measurements]

    def body_composition_exists(self, user_id: int, sample_pk: str) -> bool:
        """Check if body composition entry exists."""
        with self.get_session() as session:
            return (
                session.query(BodyComposition)
                .filter(
                    and_(
                        BodyComposition.user_id == user_id,
                        BodyComposition.sample_pk == sample_pk,
                    )
                )
                .first()
                is not None
            )

    def store_health_snapshot(
        self,
        user_id: int,
        record: Dict[str, Any],
        summaries: List[Dict[str, Any]],
        zones: List[Dict[str, Any]],
    ) -> None:
        """Store a single Health Snapshot and its related summary/zone rows.

        Uses session.merge() so re-syncing the same activity_uuid upserts.

        Args:
            user_id: User identifier.
            record: Top-level snapshot dict (matches HealthSnapshotRecord columns,
                without user_id which is added here).
            summaries: List of 6 summary dicts (HealthSnapshotSummaryStat rows).
            zones: List of 6 zone dicts (HealthSnapshotZoneTime rows).
        """
        activity_uuid = record.get("activity_uuid")
        if not activity_uuid:
            return

        with self.get_session() as session:
            def _parse_ts(value: Any) -> Optional[datetime]:
                if value is None or isinstance(value, datetime):
                    return value
                if isinstance(value, str):
                    try:
                        return datetime.fromisoformat(value.replace("Z", "+00:00"))
                    except (ValueError, TypeError):
                        return None
                return None

            cal_date = record.get("calendar_date")
            if isinstance(cal_date, str):
                try:
                    cal_date = date.fromisoformat(cal_date)
                except (ValueError, TypeError):
                    cal_date = None

            snap = HealthSnapshotRecord(
                user_id=user_id,
                activity_uuid=activity_uuid,
                calendar_date=cal_date,
                start_timestamp_gmt=_parse_ts(record.get("start_timestamp_gmt")),
                start_timestamp_local=_parse_ts(record.get("start_timestamp_local")),
                end_timestamp_gmt=_parse_ts(record.get("end_timestamp_gmt")),
                end_timestamp_local=_parse_ts(record.get("end_timestamp_local")),
                wellness_activity_type=record.get("wellness_activity_type"),
                notes=record.get("notes"),
                rule_pk=record.get("rule_pk"),
                user_profile_pk=record.get("user_profile_pk"),
                device_meta_data=record.get("device_meta_data"),
            )
            session.merge(snap)

            for s in summaries:
                if s.get("activity_uuid") != activity_uuid:
                    continue
                session.merge(
                    HealthSnapshotSummaryStat(
                        user_id=user_id,
                        activity_uuid=activity_uuid,
                        summary_type=s.get("summary_type", ""),
                        min_value=s.get("min_value"),
                        max_value=s.get("max_value"),
                        avg_value=s.get("avg_value", 0.0),
                    )
                )

            for z in zones:
                if z.get("activity_uuid") != activity_uuid:
                    continue
                session.merge(
                    HealthSnapshotZoneTime(
                        user_id=user_id,
                        activity_uuid=activity_uuid,
                        zone_number=z.get("zone_number", 0),
                        millis_in_zone=z.get("millis_in_zone", 0),
                        zone_low_boundary=z.get("zone_low_boundary", 0),
                    )
                )

            session.commit()

    def health_snapshot_exists(self, user_id: int, activity_uuid: str) -> bool:
        """Check if a Health Snapshot with this activity_uuid is already stored."""
        with self.get_session() as session:
            return (
                session.query(HealthSnapshotRecord)
                .filter(
                    and_(
                        HealthSnapshotRecord.user_id == user_id,
                        HealthSnapshotRecord.activity_uuid == activity_uuid,
                    )
                )
                .first()
                is not None
            )

    def _body_composition_to_dict(self, bc: BodyComposition) -> Dict[str, Any]:
        """Convert BodyComposition to dictionary."""
        return {
            "user_id": bc.user_id,
            "sample_pk": bc.sample_pk,
            "measurement_date": bc.measurement_date,
            "timestamp_gmt": bc.timestamp_gmt,
            "weight_grams": bc.weight_grams,
            "weight_kg": bc.weight_grams / 1000 if bc.weight_grams else None,
            "bmi": bc.bmi,
            "body_fat_percentage": bc.body_fat_percentage,
            "body_water_percentage": bc.body_water_percentage,
            "bone_mass_grams": bc.bone_mass_grams,
            "bone_mass_kg": bc.bone_mass_grams / 1000 if bc.bone_mass_grams else None,
            "muscle_mass_grams": bc.muscle_mass_grams,
            "muscle_mass_kg": (
                bc.muscle_mass_grams / 1000 if bc.muscle_mass_grams else None
            ),
            "visceral_fat": bc.visceral_fat,
            "metabolic_age": bc.metabolic_age,
            "physique_rating": bc.physique_rating,
            "source_type": bc.source_type,
            "created_at": bc.created_at,
        }
