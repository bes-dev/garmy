"""
Health Database Schema Definition

This module contains the complete database schema for the Garmin health metrics system.
Separating schema from database logic improves maintainability and makes schema evolution easier.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum


class SchemaVersion(Enum):
    """Database schema versions for migration support."""
    V1_0_0 = "1.0.0"
    CURRENT = V1_0_0


@dataclass
class TableDefinition:
    """Definition of a database table."""
    name: str
    sql: str
    description: str
    primary_key: List[str]
    indexes: List[str]


@dataclass
class DatabaseSchema:
    """Complete database schema with tables and indexes."""
    version: SchemaVersion
    tables: List[TableDefinition]
    global_indexes: List[str]

    def get_table(self, name: str) -> Optional[TableDefinition]:
        """Get table definition by name."""
        return next((t for t in self.tables if t.name == name), None)

    def get_all_sql_statements(self) -> List[str]:
        """Get all SQL statements needed to create the schema."""
        statements = []

        # Add table creation statements
        for table in self.tables:
            statements.append(table.sql)

        # Add table-specific indexes
        for table in self.tables:
            statements.extend(table.indexes)

        # Add global indexes
        statements.extend(self.global_indexes)

        return statements


# ========================================================================================
# TABLE DEFINITIONS
# ========================================================================================

# Note: daily_metrics table removed - JSON storage no longer supported

# High-frequency timeseries data
TIMESERIES = TableDefinition(
    name="timeseries",
    description="High-frequency timeseries data (heart rate, stress, body battery, etc.)",
    primary_key=["user_id", "metric_type", "timestamp"],
    sql="""
        CREATE TABLE IF NOT EXISTS timeseries (
            user_id INTEGER NOT NULL,
            metric_type TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            value REAL NOT NULL,
            metadata JSON,
            PRIMARY KEY (user_id, metric_type, timestamp)
        )
    """,
    indexes=[
        "CREATE INDEX IF NOT EXISTS idx_timeseries_user_type_time ON timeseries(user_id, metric_type, timestamp)"
    ]
)

# Activities table for efficient querying
ACTIVITIES = TableDefinition(
    name="activities",
    description="Individual activities and workouts with key metrics",
    primary_key=["user_id", "activity_id"],
    sql="""
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
    """,
    indexes=[
        "CREATE INDEX IF NOT EXISTS idx_activities_user_date ON activities(user_id, activity_date)",
        "CREATE INDEX IF NOT EXISTS idx_activities_name ON activities(activity_name)",
        "CREATE INDEX IF NOT EXISTS idx_activities_duration ON activities(duration_seconds)"
    ]
)

# Normalized daily health metrics for efficient querying
DAILY_HEALTH_METRICS = TableDefinition(
    name="daily_health_metrics",
    description="Normalized daily health metrics with dedicated columns for efficient querying",
    primary_key=["user_id", "metric_date"],
    sql="""
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

            -- HRV (Heart Rate Variability)
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
    """,
    indexes=[
        # Primary performance indexes
        "CREATE INDEX IF NOT EXISTS idx_health_user_date ON daily_health_metrics(user_id, metric_date)",

        # Common query indexes
        "CREATE INDEX IF NOT EXISTS idx_health_steps ON daily_health_metrics(total_steps)",
        "CREATE INDEX IF NOT EXISTS idx_health_sleep_duration ON daily_health_metrics(sleep_duration_hours)",
        "CREATE INDEX IF NOT EXISTS idx_health_resting_hr ON daily_health_metrics(resting_heart_rate)",
        "CREATE INDEX IF NOT EXISTS idx_health_stress ON daily_health_metrics(avg_stress_level)",
        "CREATE INDEX IF NOT EXISTS idx_health_body_battery ON daily_health_metrics(body_battery_high)",
        "CREATE INDEX IF NOT EXISTS idx_health_training_readiness ON daily_health_metrics(training_readiness_score)"
    ]
)

# ========================================================================================
# SCHEMA DEFINITION
# ========================================================================================

HEALTH_DB_SCHEMA = DatabaseSchema(
    version=SchemaVersion.CURRENT,
    tables=[
        TIMESERIES,
        ACTIVITIES,
        DAILY_HEALTH_METRICS
    ],
    global_indexes=[]  # Additional cross-table indexes can be added here
)


# ========================================================================================
# SCHEMA UTILITIES
# ========================================================================================

def get_schema_info() -> Dict[str, Any]:
    """Get comprehensive schema information."""
    return {
        "version": HEALTH_DB_SCHEMA.version.value,
        "tables": {
            table.name: {
                "description": table.description,
                "primary_key": table.primary_key,
                "indexes_count": len(table.indexes)
            }
            for table in HEALTH_DB_SCHEMA.tables
        },
        "total_tables": len(HEALTH_DB_SCHEMA.tables),
        "total_indexes": sum(len(table.indexes) for table in HEALTH_DB_SCHEMA.tables) + len(HEALTH_DB_SCHEMA.global_indexes)
    }


def validate_schema_version(current_version: str) -> bool:
    """Validate if current version matches expected schema version."""
    return current_version == HEALTH_DB_SCHEMA.version.value


def get_table_names() -> List[str]:
    """Get list of all table names in the schema."""
    return [table.name for table in HEALTH_DB_SCHEMA.tables]


def get_migration_statements(from_version: SchemaVersion, to_version: SchemaVersion) -> List[str]:
    """Get SQL statements for schema migration (placeholder for future use)."""
    if from_version == to_version:
        return []

    # Future migration logic would go here
    raise NotImplementedError(f"Migration from {from_version.value} to {to_version.value} not implemented")
