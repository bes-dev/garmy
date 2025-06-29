"""Simple SQLite database for health metrics storage."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple, TYPE_CHECKING

from .models import MetricType

if TYPE_CHECKING:
    from .config import DatabaseConfig
else:
    # Import for runtime use
    DatabaseConfig = None


def _get_default_config() -> 'DatabaseConfig':
    """Get default database configuration."""
    if DatabaseConfig is None:
        from .config import DatabaseConfig as _DatabaseConfig
        return _DatabaseConfig()
    return DatabaseConfig()


class HealthMetric:
    """Simple data class for health metrics."""
    def __init__(self, user_id: int, metric_date: date, data: Dict[str, Any]):
        self.user_id = user_id
        self.metric_date = metric_date
        self.data = data


class HealthDB:
    """Simple SQLite database for health metrics."""
    
    def __init__(self, 
                 db_path: Path = Path("health.db"), 
                 config: Optional['DatabaseConfig'] = None):
        """Initialize database.
        
        Args:
            db_path: Path to SQLite database file (default: "health.db")
            config: Database configuration (default: DatabaseConfig())
        """
        self.db_path = db_path
        self.config = config if config is not None else _get_default_config()
        self._init_schema()
    
    def _init_schema(self):
        """Initialize database schema."""
        try:
            with self.connection() as conn:
                # Daily aggregated metrics
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS daily_metrics (
                        user_id INTEGER NOT NULL,
                        metric_date DATE NOT NULL,
                        data JSON NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (user_id, metric_date)
                    )
                """)
            
                # High-frequency timeseries data
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS timeseries (
                        user_id INTEGER NOT NULL,
                        metric_type TEXT NOT NULL,
                        timestamp INTEGER NOT NULL,
                        value REAL NOT NULL,
                        metadata JSON,
                        PRIMARY KEY (user_id, metric_type, timestamp)
                    )
                """)
                
                # Activities table for efficient querying
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS activities (
                        user_id INTEGER NOT NULL,
                        activity_id TEXT NOT NULL,
                        activity_date DATE NOT NULL,
                        activity_name TEXT,
                        duration_seconds INTEGER,
                        avg_heart_rate INTEGER,
                        training_load REAL,
                        start_time TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (user_id, activity_id)
                    )
                """)
                
                # Normalized daily health metrics for efficient querying
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS daily_health_metrics (
                        user_id INTEGER NOT NULL,
                        metric_date DATE NOT NULL,
                        
                        -- Steps & Distance
                        total_steps INTEGER,
                        step_goal INTEGER,
                        total_distance_meters REAL,
                        
                        -- Calories
                        total_calories INTEGER,
                        active_calories INTEGER,
                        bmr_calories INTEGER,
                        
                        -- Heart Rate (daily summary)
                        resting_heart_rate INTEGER,
                        max_heart_rate INTEGER,
                        min_heart_rate INTEGER,
                        average_heart_rate INTEGER,
                        
                        -- Stress
                        avg_stress_level INTEGER,
                        max_stress_level INTEGER,
                        
                        -- Body Battery
                        body_battery_high INTEGER,
                        body_battery_low INTEGER,
                        
                        -- Sleep Duration (hours)
                        sleep_duration_hours REAL,
                        deep_sleep_hours REAL,
                        light_sleep_hours REAL,
                        rem_sleep_hours REAL,
                        awake_hours REAL,
                        
                        -- Sleep Percentages
                        deep_sleep_percentage REAL,
                        light_sleep_percentage REAL,
                        rem_sleep_percentage REAL,
                        awake_percentage REAL,
                        
                        -- Sleep Quality
                        average_spo2 REAL,
                        average_respiration REAL,
                        
                        -- Training Readiness
                        training_readiness_score INTEGER,
                        training_readiness_level TEXT,
                        training_readiness_feedback TEXT,
                        
                        -- HRV
                        hrv_weekly_avg REAL,
                        hrv_last_night_avg REAL,
                        hrv_status TEXT,
                        
                        -- Respiration
                        avg_waking_respiration_value REAL,
                        avg_sleep_respiration_value REAL,
                        lowest_respiration_value REAL,
                        highest_respiration_value REAL,
                        
                        -- Metadata
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        
                        PRIMARY KEY (user_id, metric_date)
                    )
                """)
                
                # Indices for performance
                conn.execute("CREATE INDEX IF NOT EXISTS idx_daily_user_date ON daily_metrics(user_id, metric_date)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_timeseries_user_type_time ON timeseries(user_id, metric_type, timestamp)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_activities_user_date ON activities(user_id, activity_date)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_activities_name ON activities(activity_name)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_activities_duration ON activities(duration_seconds)")
                
                # Indices for daily health metrics
                conn.execute("CREATE INDEX IF NOT EXISTS idx_health_user_date ON daily_health_metrics(user_id, metric_date)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_health_steps ON daily_health_metrics(total_steps)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_health_sleep_duration ON daily_health_metrics(sleep_duration_hours)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_health_resting_hr ON daily_health_metrics(resting_heart_rate)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_health_stress ON daily_health_metrics(avg_stress_level)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_health_body_battery ON daily_health_metrics(body_battery_high)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_health_training_readiness ON daily_health_metrics(training_readiness_score)")
                
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to initialize database schema: {e}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error during database initialization: {e}")
    
    @contextmanager
    def connection(self):
        """Database connection context manager."""
        conn = sqlite3.connect(str(self.db_path), timeout=self.config.timeout)
        conn.row_factory = sqlite3.Row
        
        # Enable WAL mode for better concurrency if configured
        if self.config.enable_wal_mode:
            conn.execute("PRAGMA journal_mode=WAL")
        
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def store_daily_metric(self, user_id: int, metric_date: date, data: Dict[str, Any]):
        """Store or update daily metric data."""
        if not isinstance(user_id, int) or user_id <= 0:
            raise ValueError(f"Invalid user_id: {user_id}")
        if not isinstance(metric_date, date):
            raise ValueError(f"metric_date must be a date object, got {type(metric_date)}")
        if not isinstance(data, dict):
            raise ValueError(f"data must be a dictionary, got {type(data)}")
            
        try:
            with self.connection() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO daily_metrics (user_id, metric_date, data, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """, (user_id, metric_date.isoformat(), json.dumps(data)))
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to store daily metric: {e}")
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid data format for JSON serialization: {e}")
    
    def store_timeseries_batch(self, user_id: int, metric_type: MetricType, data: List[Tuple]):
        """Store batch of timeseries data."""
        if not isinstance(user_id, int) or user_id <= 0:
            raise ValueError(f"Invalid user_id: {user_id}")
        if not isinstance(metric_type, MetricType):
            raise ValueError(f"metric_type must be MetricType enum, got {type(metric_type)}")
        if not isinstance(data, list):
            raise ValueError(f"data must be a list of tuples, got {type(data)}")
        
        try:
            with self.connection() as conn:
                for i, item in enumerate(data):
                    if not isinstance(item, (tuple, list)) or len(item) < 2:
                        raise ValueError(f"Item {i} must be tuple/list with at least 2 elements: (timestamp, value[, metadata])")
                    
                    timestamp, value = item[0], item[1]
                    metadata = item[2] if len(item) > 2 else None
                    
                    if not isinstance(timestamp, (int, float)):
                        raise ValueError(f"Timestamp must be numeric, got {type(timestamp)} for item {i}")
                    if not isinstance(value, (int, float)):
                        raise ValueError(f"Value must be numeric, got {type(value)} for item {i}")
                    
                    metadata_json = json.dumps(metadata) if metadata else None
                    conn.execute("""
                        INSERT OR REPLACE INTO timeseries (user_id, metric_type, timestamp, value, metadata)
                        VALUES (?, ?, ?, ?, ?)
                    """, (user_id, metric_type.value, timestamp, value, metadata_json))
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to store timeseries batch: {e}")
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid data format: {e}")
    
    def store_activity(self, user_id: int, activity_data: Dict[str, Any]):
        """Store individual activity in activities table."""
        if not isinstance(user_id, int) or user_id <= 0:
            raise ValueError(f"Invalid user_id: {user_id}")
        if not isinstance(activity_data, dict):
            raise ValueError(f"activity_data must be a dictionary, got {type(activity_data)}")
        
        required_fields = ['activity_id', 'activity_date']
        for field in required_fields:
            if field not in activity_data or activity_data[field] is None:
                raise ValueError(f"Missing required field: {field}")
        
        try:
            with self.connection() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO activities 
                    (user_id, activity_id, activity_date, activity_name, duration_seconds, 
                     avg_heart_rate, training_load, start_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id,
                    activity_data['activity_id'],
                    activity_data['activity_date'].isoformat() if hasattr(activity_data['activity_date'], 'isoformat') else activity_data['activity_date'],
                    activity_data.get('activity_name'),
                    activity_data.get('duration_seconds'),
                    activity_data.get('avg_heart_rate'),
                    activity_data.get('training_load'),
                    activity_data.get('start_time')
                ))
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to store activity: {e}")
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid activity data format: {e}")
    
    def store_health_metric(self, user_id: int, metric_date: date, **kwargs):
        """Store or update daily health metrics in normalized table."""
        if not isinstance(user_id, int) or user_id <= 0:
            raise ValueError(f"Invalid user_id: {user_id}")
        if not isinstance(metric_date, date):
            raise ValueError(f"metric_date must be a date object, got {type(metric_date)}")
        
        # Calculate sleep hours from percentages if sleep_duration_hours is provided
        if 'sleep_duration_hours' in kwargs and kwargs['sleep_duration_hours']:
            total_sleep = kwargs['sleep_duration_hours']
            if 'deep_sleep_percentage' in kwargs and kwargs['deep_sleep_percentage']:
                kwargs['deep_sleep_hours'] = total_sleep * (kwargs['deep_sleep_percentage'] / 100)
            if 'light_sleep_percentage' in kwargs and kwargs['light_sleep_percentage']:
                kwargs['light_sleep_hours'] = total_sleep * (kwargs['light_sleep_percentage'] / 100)
            if 'rem_sleep_percentage' in kwargs and kwargs['rem_sleep_percentage']:
                kwargs['rem_sleep_hours'] = total_sleep * (kwargs['rem_sleep_percentage'] / 100)
            if 'awake_percentage' in kwargs and kwargs['awake_percentage']:
                kwargs['awake_hours'] = total_sleep * (kwargs['awake_percentage'] / 100)
        
        # Build dynamic INSERT OR REPLACE query
        fields = ['user_id', 'metric_date'] + [k for k in kwargs.keys() if kwargs[k] is not None]
        placeholders = ', '.join(['?' for _ in fields])
        field_names = ', '.join(fields)
        values = [user_id, metric_date.isoformat()] + [kwargs[k] for k in kwargs.keys() if kwargs[k] is not None]
        
        try:
            with self.connection() as conn:
                # First, get existing record
                existing = conn.execute(
                    "SELECT * FROM daily_health_metrics WHERE user_id = ? AND metric_date = ?",
                    (user_id, metric_date.isoformat())
                ).fetchone()
                
                if existing:
                    # Update existing record with new values
                    update_fields = [f"{k} = ?" for k in kwargs.keys() if kwargs[k] is not None]
                    if update_fields:
                        query = f"UPDATE daily_health_metrics SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP WHERE user_id = ? AND metric_date = ?"
                        update_values = [kwargs[k] for k in kwargs.keys() if kwargs[k] is not None] + [user_id, metric_date.isoformat()]
                        conn.execute(query, update_values)
                else:
                    # Insert new record
                    query = f"INSERT INTO daily_health_metrics ({field_names}) VALUES ({placeholders})"
                    conn.execute(query, values)
                    
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to store health metric: {e}")
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid health metric data: {e}")
    
    def get_daily_metrics(self, user_id: int, start_date: date, end_date: date) -> List[HealthMetric]:
        """Get daily metrics for date range."""
        if not isinstance(user_id, int) or user_id <= 0:
            raise ValueError(f"Invalid user_id: {user_id}")
        if not isinstance(start_date, date):
            raise ValueError(f"start_date must be a date object, got {type(start_date)}")
        if not isinstance(end_date, date):
            raise ValueError(f"end_date must be a date object, got {type(end_date)}")
        if start_date > end_date:
            raise ValueError(f"start_date ({start_date}) cannot be after end_date ({end_date})")
        
        try:
            with self.connection() as conn:
                rows = conn.execute("""
                    SELECT user_id, metric_date, data 
                    FROM daily_metrics 
                    WHERE user_id = ? AND metric_date BETWEEN ? AND ?
                    ORDER BY metric_date
                """, (user_id, start_date.isoformat(), end_date.isoformat())).fetchall()
                
                return [HealthMetric(
                    user_id=row['user_id'],
                    metric_date=date.fromisoformat(row['metric_date']),
                    data=json.loads(row['data'])
                ) for row in rows]
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to fetch daily metrics: {e}")
        except (json.JSONDecodeError, ValueError) as e:
            raise RuntimeError(f"Database contains invalid data: {e}")
    
    def get_timeseries(self, user_id: int, metric_type: MetricType, 
                      start_time: int, end_time: int) -> List[Tuple[int, float, Dict]]:
        """Get timeseries data for time range."""
        with self.connection() as conn:
            rows = conn.execute("""
                SELECT timestamp, value, metadata 
                FROM timeseries 
                WHERE user_id = ? AND metric_type = ? AND timestamp BETWEEN ? AND ?
                ORDER BY timestamp
            """, (user_id, metric_type.value, start_time, end_time)).fetchall()
            
            return [(row['timestamp'], row['value'], 
                    json.loads(row['metadata']) if row['metadata'] else {}) 
                   for row in rows]
    
    def get_activities(self, user_id: int, start_date: date, end_date: date, 
                      activity_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get activities for date range with optional filtering by activity name."""
        if not isinstance(user_id, int) or user_id <= 0:
            raise ValueError(f"Invalid user_id: {user_id}")
        if not isinstance(start_date, date):
            raise ValueError(f"start_date must be a date object, got {type(start_date)}")
        if not isinstance(end_date, date):
            raise ValueError(f"end_date must be a date object, got {type(end_date)}")
        if start_date > end_date:
            raise ValueError(f"start_date ({start_date}) cannot be after end_date ({end_date})")
        
        try:
            with self.connection() as conn:
                if activity_name:
                    rows = conn.execute("""
                        SELECT * FROM activities 
                        WHERE user_id = ? AND activity_date BETWEEN ? AND ? AND activity_name = ?
                        ORDER BY activity_date, start_time
                    """, (user_id, start_date.isoformat(), end_date.isoformat(), activity_name)).fetchall()
                else:
                    rows = conn.execute("""
                        SELECT * FROM activities 
                        WHERE user_id = ? AND activity_date BETWEEN ? AND ?
                        ORDER BY activity_date, start_time
                    """, (user_id, start_date.isoformat(), end_date.isoformat())).fetchall()
                
                return [dict(row) for row in rows]
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to fetch activities: {e}")
    
    def activity_exists(self, user_id: int, activity_id: str) -> bool:
        """Check if activity already exists."""
        if not isinstance(user_id, int) or user_id <= 0:
            raise ValueError(f"Invalid user_id: {user_id}")
        if not activity_id:
            raise ValueError("activity_id cannot be empty")
        
        try:
            with self.connection() as conn:
                result = conn.execute(
                    "SELECT 1 FROM activities WHERE user_id = ? AND activity_id = ?",
                    (user_id, activity_id)
                ).fetchone()
                return result is not None
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to check activity existence: {e}")
    
    def get_health_metrics(self, user_id: int, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """Get normalized daily health metrics for date range."""
        if not isinstance(user_id, int) or user_id <= 0:
            raise ValueError(f"Invalid user_id: {user_id}")
        if not isinstance(start_date, date):
            raise ValueError(f"start_date must be a date object, got {type(start_date)}")
        if not isinstance(end_date, date):
            raise ValueError(f"end_date must be a date object, got {type(end_date)}")
        if start_date > end_date:
            raise ValueError(f"start_date ({start_date}) cannot be after end_date ({end_date})")
        
        try:
            with self.connection() as conn:
                rows = conn.execute("""
                    SELECT * FROM daily_health_metrics 
                    WHERE user_id = ? AND metric_date BETWEEN ? AND ?
                    ORDER BY metric_date
                """, (user_id, start_date.isoformat(), end_date.isoformat())).fetchall()
                
                return [dict(row) for row in rows]
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to fetch health metrics: {e}")
    
    def health_metric_exists(self, user_id: int, metric_date: date) -> bool:
        """Check if health metrics exist for a specific date."""
        if not isinstance(user_id, int) or user_id <= 0:
            raise ValueError(f"Invalid user_id: {user_id}")
        if not isinstance(metric_date, date):
            raise ValueError(f"metric_date must be a date object, got {type(metric_date)}")
        
        try:
            with self.connection() as conn:
                result = conn.execute(
                    "SELECT 1 FROM daily_health_metrics WHERE user_id = ? AND metric_date = ?",
                    (user_id, metric_date.isoformat())
                ).fetchone()
                return result is not None
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to check health metric existence: {e}")
    
    def get_sleep_analysis(self, user_id: int, start_date: date, end_date: date) -> Dict[str, Any]:
        """Get sleep analysis with aggregated statistics."""
        try:
            with self.connection() as conn:
                result = conn.execute("""
                    SELECT 
                        COUNT(*) as total_nights,
                        AVG(sleep_duration_hours) as avg_sleep_duration,
                        AVG(deep_sleep_percentage) as avg_deep_sleep_pct,
                        AVG(rem_sleep_percentage) as avg_rem_sleep_pct,
                        AVG(average_spo2) as avg_spo2,
                        MIN(sleep_duration_hours) as min_sleep,
                        MAX(sleep_duration_hours) as max_sleep
                    FROM daily_health_metrics 
                    WHERE user_id = ? AND metric_date BETWEEN ? AND ?
                    AND sleep_duration_hours IS NOT NULL
                """, (user_id, start_date.isoformat(), end_date.isoformat())).fetchone()
                
                return dict(result) if result else {}
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to get sleep analysis: {e}")
    
    def get_activity_summary(self, user_id: int, start_date: date, end_date: date) -> Dict[str, Any]:
        """Get activity summary with aggregated statistics."""
        try:
            with self.connection() as conn:
                result = conn.execute("""
                    SELECT 
                        COUNT(*) as total_activities,
                        COUNT(DISTINCT activity_name) as unique_activity_types,
                        SUM(duration_seconds) as total_duration_seconds,
                        AVG(duration_seconds) as avg_duration_seconds,
                        AVG(avg_heart_rate) as avg_heart_rate_across_activities,
                        activity_name as most_common_activity
                    FROM activities 
                    WHERE user_id = ? AND activity_date BETWEEN ? AND ?
                    GROUP BY activity_name
                    ORDER BY COUNT(*) DESC
                    LIMIT 1
                """, (user_id, start_date.isoformat(), end_date.isoformat())).fetchone()
                
                return dict(result) if result else {}
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to get activity summary: {e}")
    
    def get_health_trends(self, user_id: int, start_date: date, end_date: date) -> Dict[str, Any]:
        """Get health trends and correlations."""
        try:
            with self.connection() as conn:
                result = conn.execute("""
                    SELECT 
                        AVG(total_steps) as avg_daily_steps,
                        AVG(resting_heart_rate) as avg_resting_hr,
                        AVG(avg_stress_level) as avg_stress,
                        AVG(body_battery_high) as avg_body_battery_high,
                        AVG(training_readiness_score) as avg_training_readiness,
                        COUNT(CASE WHEN total_steps > 10000 THEN 1 END) as days_over_10k_steps,
                        COUNT(CASE WHEN sleep_duration_hours > 8 THEN 1 END) as days_over_8h_sleep
                    FROM daily_health_metrics 
                    WHERE user_id = ? AND metric_date BETWEEN ? AND ?
                """, (user_id, start_date.isoformat(), end_date.isoformat())).fetchone()
                
                return dict(result) if result else {}
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to get health trends: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        with self.connection() as conn:
            stats = {}
            
            # Count records
            stats['daily_metrics_count'] = conn.execute("SELECT COUNT(*) FROM daily_metrics").fetchone()[0]
            stats['timeseries_count'] = conn.execute("SELECT COUNT(*) FROM timeseries").fetchone()[0]
            stats['activities_count'] = conn.execute("SELECT COUNT(*) FROM activities").fetchone()[0]
            stats['health_metrics_count'] = conn.execute("SELECT COUNT(*) FROM daily_health_metrics").fetchone()[0]
            
            # Users
            stats['users'] = conn.execute("SELECT COUNT(DISTINCT user_id) FROM daily_health_metrics").fetchone()[0]
            
            # Date range from new normalized table
            date_range = conn.execute("""
                SELECT MIN(metric_date) as min_date, MAX(metric_date) as max_date 
                FROM daily_health_metrics
            """).fetchone()
            stats['date_range'] = dict(date_range) if date_range['min_date'] else {}
            
            # Health metrics coverage
            coverage = conn.execute("""
                SELECT 
                    COUNT(CASE WHEN total_steps IS NOT NULL THEN 1 END) as days_with_steps,
                    COUNT(CASE WHEN sleep_duration_hours IS NOT NULL THEN 1 END) as days_with_sleep,
                    COUNT(CASE WHEN resting_heart_rate IS NOT NULL THEN 1 END) as days_with_hr,
                    COUNT(CASE WHEN training_readiness_score IS NOT NULL THEN 1 END) as days_with_readiness
                FROM daily_health_metrics
            """).fetchone()
            stats['coverage'] = dict(coverage) if coverage else {}
            
            return stats
    
    def has_data_for_date(self, user_id: int, metric_type: MetricType, sync_date: date) -> bool:
        """Check if legacy data exists for specific date and metric (for backwards compatibility)."""
        # Check daily data (legacy JSON storage)
        daily_data = self.get_daily_metrics(user_id, sync_date, sync_date)
        if daily_data and metric_type.value in daily_data[0].data:
            return True
        
        # Check timeseries data for timeseries metrics
        if metric_type in [MetricType.BODY_BATTERY, MetricType.STRESS, 
                          MetricType.HEART_RATE, MetricType.RESPIRATION]:
            start_ts = int(sync_date.strftime('%s')) * self.config.ms_per_second
            end_ts = start_ts + (self.config.seconds_per_day * self.config.ms_per_second) - 1
            timeseries_data = self.get_timeseries(user_id, metric_type, start_ts, end_ts)
            if timeseries_data:
                return True
        
        return False