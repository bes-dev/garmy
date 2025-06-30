# LocalDB Guide

Complete guide to Garmy's local database functionality for health data storage and synchronization.

## 🎯 Overview

The LocalDB module provides local SQLite storage for synchronized Garmin health data, enabling:
- **Offline analysis** of health metrics
- **Historical data preservation** 
- **Fast querying** with SQL
- **Data integrity** tracking

## 🚀 Quick Start

### 1. Install LocalDB Dependencies
```bash
pip install garmy[localdb]
```

### 2. Sync Health Data
```bash
# Sync last 7 days
garmy-sync sync --last-days 7

# Sync specific date range
garmy-sync sync --date-range 2024-01-01 2024-01-31

# Sync specific metrics only
garmy-sync sync --metrics DAILY_SUMMARY,SLEEP,BODY_BATTERY

# Check sync status
garmy-sync status

# Reset failed sync records
garmy-sync reset --force
```

## 📊 Database Schema

### Main Tables

#### `daily_health_metrics`
Normalized daily health data with dedicated columns for efficient querying.

**Key Fields:**
- `user_id`, `metric_date` (Primary Key)
- `total_steps`, `sleep_duration_hours`, `resting_heart_rate`
- `avg_stress_level`, `body_battery_high/low`
- `training_readiness_score`, `hrv_weekly_avg`

#### `timeseries`
High-frequency data (heart rate, stress, body battery readings).

**Key Fields:**
- `user_id`, `metric_type`, `timestamp` (Primary Key)
- `value`, `meta_data`

#### `activities`
Individual workouts and activities with performance metrics.

**Key Fields:**
- `user_id`, `activity_id` (Primary Key)
- `activity_name`, `duration_seconds`, `avg_heart_rate`
- `training_load`, `activity_date`

#### `sync_status`
Sync status tracking for each metric per date.

**Key Fields:**
- `user_id`, `sync_date`, `metric_type` (Primary Key)
- `status`, `synced_at`, `error_message`

## 🔧 Programmatic Usage

### Basic Sync Operations

```python
from garmy.localdb import SyncManager
from datetime import date, timedelta

# Initialize sync manager
sync_manager = SyncManager(db_path="my_health.db")
sync_manager.initialize("email@garmin.com", "password")

# Sync data
end_date = date.today()
start_date = end_date - timedelta(days=30)

stats = sync_manager.sync_range(
    user_id=1,
    start_date=start_date,
    end_date=end_date
)

print(f"Synced: {stats['completed']} records")
```

### Querying Health Data

```python
# Query health metrics
health_data = sync_manager.query_health_metrics(
    user_id=1,
    start_date=start_date,
    end_date=end_date
)

# Query activities
activities = sync_manager.query_activities(
    user_id=1,
    start_date=start_date,
    end_date=end_date,
    activity_name="Running"  # Optional filter
)

# Query timeseries data
from datetime import datetime
timeseries_data = sync_manager.query_timeseries(
    user_id=1,
    metric_type=MetricType.HEART_RATE,
    start_time=datetime(2024, 1, 1, 0, 0),
    end_time=datetime(2024, 1, 1, 23, 59)
)
```

### Direct Database Access

```python
from garmy.localdb import HealthDB

# Initialize database
db = HealthDB(db_path="health.db")

# Get health metrics for analysis
with db.get_session() as session:
    from garmy.localdb.models import DailyHealthMetric
    
    metrics = session.query(DailyHealthMetric).filter(
        DailyHealthMetric.user_id == 1,
        DailyHealthMetric.total_steps > 10000
    ).all()
    
    for metric in metrics:
        print(f"{metric.metric_date}: {metric.total_steps} steps")
```

## ⚙️ Configuration

### Sync Configuration

```python
from garmy.localdb.config import LocalDBConfig, SyncConfig, DatabaseConfig

# Custom configuration
config = LocalDBConfig(
    sync=SyncConfig(
        max_sync_days=365,  # Maximum sync range
        retry_failed=True,
        batch_size=10
    ),
    database=DatabaseConfig(
        connection_timeout=30,
        query_timeout=60
    )
)

sync_manager = SyncManager(db_path="health.db", config=config)
```

### Environment Variables

```bash
# Database path for CLI tools
export GARMY_DB_PATH="/path/to/health.db"

# API credentials (optional)
export GARMIN_EMAIL="your_email@garmin.com"  
export GARMIN_PASSWORD="your_password"
```

## 📈 Data Analysis Examples

### Sleep Analysis
```python
# Get sleep trends
sleep_query = """
    SELECT 
        metric_date,
        sleep_duration_hours,
        deep_sleep_percentage,
        rem_sleep_percentage
    FROM daily_health_metrics 
    WHERE user_id = 1 
        AND sleep_duration_hours IS NOT NULL
        AND metric_date >= date('now', '-30 days')
    ORDER BY metric_date
"""

with db.get_session() as session:
    results = session.execute(text(sleep_query)).fetchall()
    
    for row in results:
        print(f"{row.metric_date}: {row.sleep_duration_hours:.1f}h sleep, "
              f"{row.deep_sleep_percentage:.1f}% deep")
```

### Activity Performance
```python
# Analyze workout intensity
activity_query = """
    SELECT 
        activity_name,
        AVG(avg_heart_rate) as avg_hr,
        AVG(training_load) as avg_load,
        COUNT(*) as workout_count
    FROM activities 
    WHERE user_id = 1 
        AND activity_date >= date('now', '-90 days')
    GROUP BY activity_name
    HAVING workout_count >= 3
    ORDER BY avg_load DESC
"""

with db.get_session() as session:
    results = session.execute(text(activity_query)).fetchall()
    
    for row in results:
        print(f"{row.activity_name}: {row.avg_hr:.0f} BPM avg, "
              f"{row.avg_load:.1f} training load ({row.workout_count} workouts)")
```

## 🔄 Advanced Sync Operations

### Selective Metric Sync
```python
from garmy.localdb.models import MetricType

# Sync only specific metrics
metrics_to_sync = [
    MetricType.DAILY_SUMMARY,
    MetricType.SLEEP,
    MetricType.TRAINING_READINESS
]

stats = sync_manager.sync_range(
    user_id=1,
    start_date=start_date,
    end_date=end_date,
    metrics=metrics_to_sync
)
```

### Progress Monitoring
```python
from garmy.localdb.progress import ProgressReporter

# Enable progress monitoring
progress = ProgressReporter(use_tqdm=True)
sync_manager = SyncManager(
    db_path="health.db",
    progress_reporter=progress
)

# Sync with progress bar
stats = sync_manager.sync_range(user_id=1, start_date=start_date, end_date=end_date)
```

## 🛠️ Troubleshooting

### Common Issues

1. **Database Lock Errors**
   ```python
   # Ensure proper session management
   with db.get_session() as session:
       # Your database operations here
       pass  # Session automatically closed
   ```

2. **Sync Failures**
   ```bash
   # Reset failed sync records
   garmy-sync reset --force
   
   # Check sync status
   garmy-sync status
   ```

3. **Large Dataset Performance**
   ```python
   # Use smaller date ranges for large syncs
   from datetime import timedelta
   
   current_date = start_date
   while current_date <= end_date:
       chunk_end = min(current_date + timedelta(days=7), end_date)
       sync_manager.sync_range(user_id=1, start_date=current_date, end_date=chunk_end)
       current_date = chunk_end + timedelta(days=1)
   ```

## 🔗 Related Documentation

- **[Database Schema](database-schema.md)** - Detailed schema documentation
- **[Sync Operations](sync-operations.md)** - Advanced sync patterns
- **[MCP Server Guide](mcp-server-guide.md)** - AI integration with local data
- **[API Reference](api-reference.md)** - Complete API documentation