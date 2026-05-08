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

# Backfill activity details for existing activities
garmy-sync backfill --limit 100

# Backfill splits/laps for cardio activities
garmy-sync backfill-splits --limit 100
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
- `activity_name`, `activity_type`, `duration_seconds`
- `avg_heart_rate`, `max_heart_rate`, `training_load`
- `distance_meters`, `calories`, `elevation_gain/loss`
- `total_sets`, `total_reps`, `total_weight_kg` (strength training)

#### `exercise_sets`
Individual exercise sets from strength training activities.

**Key Fields:**
- `user_id`, `activity_id`, `set_order` (Primary Key)
- `exercise_category` (CURL, BENCH_PRESS, SQUAT, etc.)
- `repetition_count`, `weight_grams`, `duration_seconds`

#### `activity_splits`
Lap/split data from cardio activities (running, cycling, walking, etc.).

**Key Fields:**
- `user_id`, `activity_id`, `lap_index` (Primary Key)
- `distance_meters`, `duration_seconds`, `moving_duration_seconds`
- `avg_speed`, `max_speed`, `avg_heart_rate`, `max_heart_rate`
- `elevation_gain`, `elevation_loss`, `avg_cadence`
- `start_latitude`, `start_longitude`, `end_latitude`, `end_longitude`

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

### Strength Training Analysis
```python
# Analyze workout volume over time
volume_query = """
    SELECT
        activity_date,
        activity_name,
        total_sets,
        total_reps,
        total_weight_kg
    FROM activities
    WHERE user_id = 1
        AND activity_type = 'strength_training'
        AND activity_date >= date('now', '-30 days')
    ORDER BY activity_date DESC
"""

# Analyze specific exercise categories
exercise_query = """
    SELECT
        exercise_category,
        COUNT(*) as total_sets,
        SUM(repetition_count) as total_reps,
        ROUND(SUM(weight_grams) / 1000.0, 1) as total_weight_kg,
        ROUND(AVG(weight_grams) / 1000.0, 1) as avg_weight_kg
    FROM exercise_sets
    WHERE user_id = 1
        AND set_type = 'ACTIVE'
    GROUP BY exercise_category
    ORDER BY total_weight_kg DESC
"""

# Track strength progression for a specific exercise
progression_query = """
    SELECT
        a.activity_date,
        e.exercise_category,
        MAX(e.weight_grams) / 1000.0 as max_weight_kg,
        AVG(e.repetition_count) as avg_reps
    FROM exercise_sets e
    JOIN activities a ON e.activity_id = a.activity_id AND e.user_id = a.user_id
    WHERE e.user_id = 1
        AND e.exercise_category = 'BENCH_PRESS'
        AND e.set_type = 'ACTIVE'
    GROUP BY a.activity_date
    ORDER BY a.activity_date
"""
```

### Cardio Splits Analysis
```python
# Analyze pace per lap for a running activity
pace_query = """
    SELECT
        lap_index,
        distance_meters,
        duration_seconds,
        ROUND(duration_seconds / (distance_meters / 1000.0), 1) as pace_sec_per_km,
        avg_heart_rate,
        elevation_gain
    FROM activity_splits
    WHERE user_id = 1
        AND activity_id = '123456789'
    ORDER BY lap_index
"""

# Compare lap consistency across runs
consistency_query = """
    SELECT
        a.activity_date,
        a.activity_name,
        COUNT(s.lap_index) as total_laps,
        AVG(s.avg_speed) as avg_lap_speed,
        MAX(s.avg_speed) - MIN(s.avg_speed) as speed_variance
    FROM activities a
    JOIN activity_splits s ON a.activity_id = s.activity_id AND a.user_id = s.user_id
    WHERE a.user_id = 1
        AND a.activity_type = 'running'
        AND a.activity_date >= date('now', '-30 days')
    GROUP BY a.activity_id
    ORDER BY a.activity_date DESC
"""

# Negative splits analysis (running faster in later laps)
negative_splits_query = """
    SELECT
        a.activity_date,
        a.activity_name,
        s1.avg_speed as first_half_speed,
        s2.avg_speed as second_half_speed,
        CASE WHEN s2.avg_speed > s1.avg_speed THEN 'Negative Split' ELSE 'Positive Split' END as split_type
    FROM activities a
    JOIN activity_splits s1 ON a.activity_id = s1.activity_id AND a.user_id = s1.user_id AND s1.lap_index = 1
    JOIN activity_splits s2 ON a.activity_id = s2.activity_id AND a.user_id = s2.user_id AND s2.lap_index = 2
    WHERE a.user_id = 1
        AND a.activity_type = 'running'
    ORDER BY a.activity_date DESC
"""
```

## 🔄 Advanced Sync Operations

### Activity Details and Exercise Sets

When syncing activities, the system automatically fetches exercise sets for strength training activities. This includes:
- Exercise category (CURL, BENCH_PRESS, SQUAT, etc.)
- Repetition count and weight
- Set duration and timing

**Backfilling existing activities:**
```bash
# Backfill details for activities that were synced before this feature
garmy-sync backfill --limit 100

# Check backfill progress
garmy-sync status
```

The backfill command fetches exercise sets for strength training activities that don't have details yet. Use `--limit` to control how many activities to process per run.

### Splits/Laps for Cardio Activities

For cardio activities (running, cycling, walking, swimming, etc.), the system automatically fetches split/lap data. This includes:
- Distance and timing per lap
- Heart rate (avg/max) per lap
- Speed and pace metrics
- Elevation changes
- GPS coordinates (start/end)
- Cadence (for running/walking)

**Backfilling splits for existing activities:**
```bash
# Backfill splits for cardio activities that don't have them
garmy-sync backfill-splits --limit 100

# Check sync status
garmy-sync status
```

**Supported cardio activity types:**
- Running: `running`, `treadmill_running`, `trail_running`, `track_running`
- Cycling: `cycling`, `indoor_cycling`, `virtual_ride`, `gravel_cycling`, `road_cycling`
- Walking/Hiking: `walking`, `hiking`
- Swimming: `swimming`, `lap_swimming`, `open_water_swimming`
- Other: `elliptical`, `stair_climbing`, `rowing`, `indoor_rowing`

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

### Database Migrations

Database schema migrations are **automatic**. When new columns or tables are added (like `exercise_sets`), they are created automatically when you use the database. No manual migration steps required.

For existing databases, new columns are added to the `activities` table using `ALTER TABLE` statements on first use.

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
- **[MCP Server Guide](mcp-server-guide.md)** - AI integration with local data
- **[Quick Start Guide](quick-start.md)** - Getting started
- **[Examples](../examples/)** - Usage examples