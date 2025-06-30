# Database Schema

Complete reference for Garmy's LocalDB database schema and structure.

## 🎯 Overview

The Garmy LocalDB uses SQLite with optimized tables for health data storage:

- **4 main tables** for different data types
- **Normalized structure** for efficient querying
- **Dedicated columns** for common health metrics
- **Sync tracking** for data integrity

## 📊 Schema Diagram

```
daily_health_metrics (Primary health data)
├── user_id, metric_date (PK)
├── Steps: total_steps, step_goal, total_distance_meters
├── Sleep: sleep_duration_hours, deep_sleep_hours, rem_sleep_hours
├── Heart Rate: resting_heart_rate, max_heart_rate, average_heart_rate
├── Stress: avg_stress_level, max_stress_level
├── Body Battery: body_battery_high, body_battery_low
├── Training: training_readiness_score, training_readiness_level
└── HRV: hrv_weekly_avg, hrv_last_night_avg, hrv_status

timeseries (High-frequency data)
├── user_id, metric_type, timestamp (PK)
├── value (Float)
└── meta_data (JSON)

activities (Workouts and activities)
├── user_id, activity_id (PK)
├── activity_date, activity_name
├── duration_seconds, avg_heart_rate
├── training_load, start_time
└── created_at

sync_status (Sync tracking)
├── user_id, sync_date, metric_type (PK)
├── status, synced_at
├── error_message
└── created_at
```

## 📋 Table Details

### `daily_health_metrics`
**Purpose:** Daily health summaries with normalized columns for efficient querying

**Primary Key:** `(user_id, metric_date)`

**Key Columns:**
```sql
-- Identity
user_id              INTEGER    -- User identifier
metric_date          DATE       -- Date of metrics

-- Steps and Movement  
total_steps          INTEGER    -- Daily step count
step_goal            INTEGER    -- Daily step goal
total_distance_meters FLOAT     -- Distance in meters

-- Calories
total_calories       INTEGER    -- Total calories burned
active_calories      INTEGER    -- Active calories
bmr_calories         INTEGER    -- Basal metabolic rate calories

-- Heart Rate
resting_heart_rate   INTEGER    -- Morning resting HR
max_heart_rate       INTEGER    -- Maximum HR during day
min_heart_rate       INTEGER    -- Minimum HR during day
average_heart_rate   INTEGER    -- Average HR during day

-- Stress and Recovery
avg_stress_level     INTEGER    -- Average stress (0-100)
max_stress_level     INTEGER    -- Maximum stress level
body_battery_high    INTEGER    -- Highest body battery
body_battery_low     INTEGER    -- Lowest body battery

-- Sleep
sleep_duration_hours FLOAT      -- Total sleep time
deep_sleep_hours     FLOAT      -- Deep sleep time
light_sleep_hours    FLOAT      -- Light sleep time  
rem_sleep_hours      FLOAT      -- REM sleep time
awake_hours          FLOAT      -- Time awake
deep_sleep_percentage FLOAT     -- % of sleep in deep
light_sleep_percentage FLOAT    -- % of sleep in light
rem_sleep_percentage FLOAT      -- % of sleep in REM
awake_percentage     FLOAT      -- % of time awake

-- Respiration and SpO2
average_spo2         FLOAT      -- Average blood oxygen
average_respiration  FLOAT      -- Average respiration rate
avg_waking_respiration_value FLOAT
avg_sleep_respiration_value FLOAT
lowest_respiration_value FLOAT
highest_respiration_value FLOAT

-- Training and HRV
training_readiness_score INTEGER  -- Training readiness (0-100)
training_readiness_level TEXT     -- Readiness level description
training_readiness_feedback TEXT  -- Readiness feedback
hrv_weekly_avg       FLOAT       -- Weekly HRV average
hrv_last_night_avg   FLOAT       -- Last night HRV
hrv_status           TEXT        -- HRV status description

-- Timestamps
created_at           DATETIME    -- Record creation time
updated_at           DATETIME    -- Last update time
```

### `timeseries`
**Purpose:** High-frequency data throughout the day (heart rate, stress, body battery)

**Primary Key:** `(user_id, metric_type, timestamp)`

**Columns:**
```sql
user_id      INTEGER    -- User identifier
metric_type  STRING     -- Type of metric (heart_rate, stress, body_battery)
timestamp    INTEGER    -- Unix timestamp in milliseconds
value        FLOAT      -- Metric value at timestamp
meta_data    JSON       -- Additional metadata (optional)
```

**Common Metric Types:**
- `heart_rate` - Heart rate readings
- `stress` - Stress level measurements  
- `body_battery` - Body battery levels
- `respiration` - Respiration rate readings

### `activities`
**Purpose:** Individual workouts and physical activities

**Primary Key:** `(user_id, activity_id)`

**Columns:**
```sql
user_id         INTEGER    -- User identifier
activity_id     STRING     -- Garmin activity ID
activity_date   DATE       -- Date of activity
activity_name   STRING     -- Activity type (e.g., "Running", "Cycling")
duration_seconds INTEGER   -- Activity duration in seconds
avg_heart_rate  INTEGER    -- Average heart rate during activity
training_load   FLOAT      -- Training load/stress score
start_time      STRING     -- Activity start time
created_at      DATETIME   -- Record creation time
```

### `sync_status`
**Purpose:** Track synchronization status for each metric per date

**Primary Key:** `(user_id, sync_date, metric_type)`

**Columns:**
```sql
user_id      INTEGER    -- User identifier
sync_date    DATE       -- Date being synced
metric_type  STRING     -- Metric type being synced
status       STRING     -- Sync status (pending, completed, failed, skipped)
synced_at    DATETIME   -- When sync completed
error_message TEXT      -- Error message if sync failed
created_at   DATETIME   -- Record creation time
```

**Status Values:**
- `pending` - Sync not yet attempted
- `completed` - Successfully synced
- `failed` - Sync failed with error
- `skipped` - No data available or already exists

## 🔍 Common Queries

### Daily Health Trends
```sql
SELECT 
    metric_date,
    total_steps,
    sleep_duration_hours,
    resting_heart_rate,
    avg_stress_level
FROM daily_health_metrics 
WHERE user_id = 1 
    AND metric_date >= date('now', '-30 days')
ORDER BY metric_date;
```

### Sleep Analysis
```sql
SELECT 
    metric_date,
    sleep_duration_hours,
    deep_sleep_percentage,
    rem_sleep_percentage,
    hrv_last_night_avg
FROM daily_health_metrics 
WHERE user_id = 1 
    AND sleep_duration_hours IS NOT NULL
    AND metric_date >= date('now', '-7 days')
ORDER BY metric_date;
```

### Activity Performance
```sql
SELECT 
    activity_date,
    activity_name,
    duration_seconds / 60.0 as duration_minutes,
    avg_heart_rate,
    training_load
FROM activities 
WHERE user_id = 1 
    AND activity_date >= date('now', '-30 days')
ORDER BY activity_date DESC;
```

### Heart Rate Timeseries
```sql
SELECT 
    datetime(timestamp/1000, 'unixepoch') as time,
    value as heart_rate
FROM timeseries 
WHERE user_id = 1 
    AND metric_type = 'heart_rate'
    AND timestamp >= strftime('%s', date('now', '-1 day')) * 1000
ORDER BY timestamp;
```

### Sync Status Check
```sql
SELECT 
    sync_date,
    metric_type,
    status,
    synced_at,
    error_message
FROM sync_status 
WHERE user_id = 1 
    AND status = 'failed'
ORDER BY sync_date DESC;
```

## 📈 Data Relationships

### User-Centric Design
All tables use `user_id` as the primary identifier, allowing multi-user support.

### Date-Based Partitioning
- `daily_health_metrics`: Uses `metric_date` for daily aggregations
- `activities`: Uses `activity_date` for workout tracking
- `timeseries`: Uses `timestamp` for high-frequency data
- `sync_status`: Uses `sync_date` for sync tracking

### Metric Type Enumeration
Supported metric types in `sync_status` and `timeseries`:
- `DAILY_SUMMARY`
- `SLEEP`
- `ACTIVITIES` 
- `BODY_BATTERY`
- `STRESS`
- `HEART_RATE`
- `TRAINING_READINESS`
- `HRV`
- `RESPIRATION`
- `STEPS`
- `CALORIES`

## 🔧 Performance Considerations

### Indexes
The schema includes efficient indexes for:
- Primary key lookups
- Date range queries
- User-specific queries
- Metric type filtering

### NULL Value Handling
Many health metrics can be NULL when:
- Data not available from Garmin
- Sensor not worn/active
- Sync incomplete

Always use `IS NOT NULL` checks in analysis queries.

### Data Types
- **INTEGER**: Used for whole numbers (steps, heart rate)
- **FLOAT**: Used for decimal values (sleep hours, HRV)
- **TEXT**: Used for descriptions and status
- **DATE**: Used for date-only fields
- **DATETIME**: Used for timestamps
- **JSON**: Used for flexible metadata storage

## 🔗 Related Documentation

- **[LocalDB Guide](localdb-guide.md)** - Working with the database
- **[MCP Server Guide](mcp-server-guide.md)** - Querying via MCP
- **[Quick Start Guide](quick-start.md)** - Getting started