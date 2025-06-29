"""Minimal SQLite database for health metrics storage."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple, TYPE_CHECKING

from .models import MetricType
from .schema import HEALTH_DB_SCHEMA

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



class HealthDB:
    """Minimal SQLite database for health metrics."""
    
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
        """Initialize database schema using centralized schema definition."""
        try:
            with self.connection() as conn:
                # Execute all schema statements from the centralized definition
                for statement in HEALTH_DB_SCHEMA.get_all_sql_statements():
                    conn.execute(statement)
                    
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to initialize database schema: {e}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error during database initialization: {e}")
    
    def get_schema_info(self) -> Dict[str, Any]:
        """Get current database schema information."""
        from .schema import get_schema_info
        return get_schema_info()
    
    def validate_schema(self) -> bool:
        """Validate current database schema matches expected schema."""
        from .schema import get_table_names
        
        try:
            with self.connection() as conn:
                # Check if all expected tables exist
                expected_tables = set(get_table_names())
                existing_tables = set()
                
                for table_info in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
                    existing_tables.add(table_info[0])
                
                return expected_tables.issubset(existing_tables)
        except sqlite3.Error:
            return False
    
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
    
    # ========================================================================================
    # CORE STORAGE METHODS (Required for sync)
    # ========================================================================================
    
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
    
    # ========================================================================================
    # EXISTENCE CHECKS (Required for sync)
    # ========================================================================================
    
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
    
    # ========================================================================================
    # BASIC QUERIES (Required for sync and export)
    # ========================================================================================
    
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