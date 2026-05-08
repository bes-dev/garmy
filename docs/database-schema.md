# Database Schema

Complete reference for Garmy's LocalDB database schema and structure.

## 🎯 Overview

The Garmy LocalDB uses SQLite with optimized tables for health data storage:

- **7 main tables** for different data types
- **Normalized structure** for efficient querying
- **Dedicated columns** for common health metrics
- **Sync tracking** for data integrity
- **Automatic migrations** for schema updates

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
├── HRV: hrv_weekly_avg, hrv_last_night_avg, hrv_status
├── Intensity: moderate_intensity_minutes, vigorous_intensity_minutes
└── Floors: floors_ascended, floors_descended

timeseries (High-frequency data)
├── user_id, metric_type, timestamp (PK)
├── value (Float)
└── meta_data (JSON)

activities (Workouts and activities)
├── user_id, activity_id (PK)
├── activity_date, activity_name, activity_type
├── duration_seconds, avg_heart_rate, max_heart_rate
├── distance_meters, calories, elevation_gain/loss
├── training_load, start_time
├── total_sets, total_reps, total_weight_kg (strength)
└── details_synced, created_at, updated_at

exercise_sets (Strength training sets)
├── user_id, activity_id, set_order (PK)
├── exercise_category, exercise_name
├── repetition_count, weight_grams
├── set_type, duration_seconds
└── start_time, created_at

activity_splits (Cardio lap/split data)
├── user_id, activity_id, lap_index (PK)
├── start_time, duration_seconds, moving_duration_seconds
├── distance_meters, avg_speed, max_speed
├── avg_heart_rate, max_heart_rate
├── elevation_gain, elevation_loss
├── avg_cadence, max_cadence, calories
├── start_latitude, start_longitude, end_latitude, end_longitude
└── intensity_type, created_at

performance_metrics (Post-activity performance metrics)
├── user_id, metric_date (PK)
├── Training Load: acute_load, chronic_load, load_balance, load_type
├── Training Status: training_status (int code), training_status_feedback
├── Endurance: endurance_score, endurance_score_classification (int code)
└── created_at, updated_at

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

-- SpO2
average_spo2         FLOAT      -- Average blood oxygen
lowest_spo2          FLOAT      -- Lowest SpO2 reading

-- Respiration
average_respiration  FLOAT      -- Average respiration rate
avg_waking_respiration_value FLOAT
avg_sleep_respiration_value FLOAT
lowest_respiration_value FLOAT
highest_respiration_value FLOAT

-- Intensity Minutes
moderate_intensity_minutes INTEGER -- Weekly cumulative moderate minutes (from API)
vigorous_intensity_minutes INTEGER -- Weekly cumulative vigorous minutes (from API)
intensity_minutes_total INTEGER    -- Daily earned total (sum of 15-min timeseries)
intensity_minutes_goal INTEGER     -- Weekly goal (typically 150)

-- Floors
floors_ascended      INTEGER    -- Floors climbed during the day
floors_descended     INTEGER    -- Floors descended during the day

-- Dedicated Resting HR
dedicated_resting_heart_rate INTEGER -- From dedicated userstats endpoint

-- Training and HRV
training_readiness_score INTEGER  -- Training readiness (0-100)
training_readiness_level TEXT     -- Readiness level description
training_readiness_feedback TEXT  -- Readiness feedback
hrv_weekly_avg       FLOAT       -- Weekly HRV average
hrv_last_night_avg   FLOAT       -- Last night HRV
hrv_status           TEXT        -- HRV status description
hrv_last_night_5min_high FLOAT   -- Last night 5-min high HRV
hrv_baseline_low_upper FLOAT     -- Baseline range: low upper boundary
hrv_baseline_balanced_low FLOAT  -- Baseline range: balanced lower boundary
hrv_baseline_balanced_upper FLOAT -- Baseline range: balanced upper boundary

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
- `hrv` - Heart rate variability readings (during sleep)
- `spo2` - Blood oxygen saturation readings (overnight)
- `intensity_minutes` - Intensity minutes earned (15-min intervals)

### `activities`
**Purpose:** Individual workouts and physical activities

**Primary Key:** `(user_id, activity_id)`

**Columns:**
```sql
-- Identity
user_id         INTEGER    -- User identifier
activity_id     STRING     -- Garmin activity ID
activity_date   DATE       -- Date of activity
activity_name   STRING     -- Activity display name (e.g., "Morning Run")
activity_type   STRING     -- Activity type key (running, cycling, strength_training)

-- Performance Metrics
duration_seconds INTEGER   -- Activity duration in seconds
avg_heart_rate  INTEGER    -- Average heart rate during activity
max_heart_rate  INTEGER    -- Maximum heart rate during activity
training_load   FLOAT      -- Training load/stress score
start_time      STRING     -- Activity start time

-- Distance and Movement
distance_meters FLOAT      -- Total distance in meters
calories        INTEGER    -- Calories burned
elevation_gain  FLOAT      -- Elevation gained in meters
elevation_loss  FLOAT      -- Elevation lost in meters
avg_speed       FLOAT      -- Average speed (m/s)
max_speed       FLOAT      -- Maximum speed (m/s)

-- Strength Training Summary (populated for strength activities)
total_sets      INTEGER    -- Total active sets in workout
total_reps      INTEGER    -- Total repetitions across all sets
total_weight_kg FLOAT      -- Total volume (sum of weight × reps)

-- Sync Tracking
details_synced  BOOLEAN    -- Whether exercise sets have been synced
created_at      DATETIME   -- Record creation time
updated_at      DATETIME   -- Last update time
```

**Activity Types:**
- `running`, `cycling`, `swimming` - Cardio activities
- `strength_training`, `indoor_strength_training` - Strength workouts
- `walking`, `hiking` - Walking activities
- `yoga`, `pilates` - Flexibility/wellness

### `exercise_sets`
**Purpose:** Individual exercise sets from strength training activities

**Primary Key:** `(user_id, activity_id, set_order)`

**Columns:**
```sql
-- Identity
user_id           INTEGER    -- User identifier
activity_id       STRING     -- Parent activity ID (FK to activities)
set_order         INTEGER    -- Order within activity (0-indexed)

-- Exercise Info
exercise_category STRING     -- Exercise type (CURL, BENCH_PRESS, SQUAT, etc.)
exercise_name     STRING     -- Custom exercise name (if available)
set_type          STRING     -- Set type: ACTIVE or REST

-- Set Metrics
repetition_count  INTEGER    -- Number of reps in set
weight_grams      FLOAT      -- Weight in grams (divide by 1000 for kg)
duration_seconds  FLOAT      -- Set duration in seconds
start_time        STRING     -- Set start timestamp

-- Metadata
created_at        DATETIME   -- Record creation time
```

**Common Exercise Categories:**
- Upper body: `BENCH_PRESS`, `SHOULDER_PRESS`, `CURL`, `TRICEP_EXTENSION`, `LAT_PULLDOWN`, `ROW`
- Lower body: `SQUAT`, `DEADLIFT`, `LEG_PRESS`, `LUNGE`, `LEG_CURL`, `LEG_EXTENSION`
- Core: `PLANK`, `CRUNCH`, `RUSSIAN_TWIST`
- Other: `UNKNOWN` (when Garmin cannot identify the exercise)

### `activity_splits`
**Purpose:** Lap/split data from cardio activities (running, cycling, walking, swimming, etc.)

**Primary Key:** `(user_id, activity_id, lap_index)`

**Columns:**
```sql
-- Identity
user_id           INTEGER    -- User identifier
activity_id       STRING     -- Parent activity ID (FK to activities)
lap_index         INTEGER    -- 1-indexed lap number

-- Timing
start_time        STRING     -- Lap start timestamp (ISO format)
duration_seconds  FLOAT      -- Total lap duration
moving_duration_seconds FLOAT -- Moving time (excludes pauses)

-- Distance and Speed
distance_meters   FLOAT      -- Distance covered in lap
avg_speed         FLOAT      -- Average speed (m/s)
max_speed         FLOAT      -- Maximum speed (m/s)
avg_moving_speed  FLOAT      -- Average speed while moving (m/s)

-- Heart Rate
avg_heart_rate    INTEGER    -- Average HR during lap
max_heart_rate    INTEGER    -- Maximum HR during lap

-- Elevation
elevation_gain    FLOAT      -- Meters gained in lap
elevation_loss    FLOAT      -- Meters lost in lap
max_elevation     FLOAT      -- Highest point (meters)
min_elevation     FLOAT      -- Lowest point (meters)

-- Cadence (running/walking)
avg_cadence       FLOAT      -- Average steps per minute
max_cadence       FLOAT      -- Maximum steps per minute

-- Energy
calories          FLOAT      -- Calories burned in lap

-- GPS Coordinates
start_latitude    FLOAT      -- Lap start latitude
start_longitude   FLOAT      -- Lap start longitude
end_latitude      FLOAT      -- Lap end latitude
end_longitude     FLOAT      -- Lap end longitude

-- Type
intensity_type    STRING     -- Lap type: ACTIVE or REST

-- Metadata
created_at        DATETIME   -- Record creation time
```

**Supported Activity Types:**
- Running: `running`, `treadmill_running`, `trail_running`, `track_running`
- Cycling: `cycling`, `indoor_cycling`, `virtual_ride`, `gravel_cycling`, `road_cycling`
- Walking/Hiking: `walking`, `hiking`
- Swimming: `swimming`, `lap_swimming`, `open_water_swimming`
- Other: `elliptical`, `stair_climbing`, `rowing`, `indoor_rowing`

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

### `performance_metrics`
**Purpose:** Post-activity performance metrics that update irregularly (after activities, not daily)

**Primary Key:** `(user_id, metric_date)`

**Columns:**
```sql
user_id                          INTEGER  -- User identifier
metric_date                      DATE     -- Date of metric
-- Training Load (from acuteTrainingLoadDTO)
acute_load                       FLOAT    -- 7-day rolling training load
chronic_load                     FLOAT    -- 28-day rolling training load
load_balance                     FLOAT    -- Acute/chronic load ratio
load_type                        TEXT     -- OPTIMAL, OVERREACHING, etc.
-- Training Status (numeric code + feedback phrase)
training_status                  INTEGER  -- Numeric code: 1=DETRAINING, 2=RECOVERY, 3=UNPRODUCTIVE, 4=MAINTAINING, 5=PRODUCTIVE, 6=PEAKING, 7=OVERREACHING
training_status_feedback         TEXT     -- Feedback phrase (e.g. "MAINTAINING_1")
-- Endurance Score
endurance_score                  FLOAT    -- Absolute score (e.g. 4508)
endurance_score_classification   INTEGER  -- Numeric code: 1=RECREATIONAL, 2=INTERMEDIATE, 3=TRAINED, 4=WELL_TRAINED, 5=EXPERT, 6=SUPERIOR, 7=ELITE
-- Metadata
created_at                       DATETIME -- Record creation time
updated_at                       DATETIME -- Last update time
```

**Query Pattern:** Use "last known value" since these update irregularly:
```sql
SELECT * FROM performance_metrics
WHERE user_id = 1 AND metric_date <= '2026-03-24'
ORDER BY metric_date DESC LIMIT 1;
```

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

### Strength Training Volume
```sql
-- Weekly workout volume
SELECT
    strftime('%Y-W%W', activity_date) as week,
    COUNT(*) as workouts,
    SUM(total_sets) as total_sets,
    SUM(total_reps) as total_reps,
    ROUND(SUM(total_weight_kg), 1) as total_volume_kg
FROM activities
WHERE user_id = 1
    AND activity_type IN ('strength_training', 'indoor_strength_training')
    AND activity_date >= date('now', '-90 days')
GROUP BY week
ORDER BY week;
```

### Exercise Progression
```sql
-- Track max weight progression for an exercise
SELECT
    a.activity_date,
    e.exercise_category,
    MAX(e.weight_grams) / 1000.0 as max_weight_kg,
    SUM(e.repetition_count) as total_reps
FROM exercise_sets e
JOIN activities a ON e.activity_id = a.activity_id AND e.user_id = a.user_id
WHERE e.user_id = 1
    AND e.exercise_category = 'BENCH_PRESS'
    AND e.set_type = 'ACTIVE'
GROUP BY a.activity_date
ORDER BY a.activity_date;
```

### Exercise Category Summary
```sql
-- Volume by exercise category
SELECT
    exercise_category,
    COUNT(*) as total_sets,
    SUM(repetition_count) as total_reps,
    ROUND(SUM(weight_grams) / 1000.0, 1) as total_weight_kg,
    ROUND(AVG(weight_grams) / 1000.0, 1) as avg_weight_kg,
    ROUND(AVG(repetition_count), 1) as avg_reps
FROM exercise_sets
WHERE user_id = 1
    AND set_type = 'ACTIVE'
    AND weight_grams > 0
GROUP BY exercise_category
ORDER BY total_weight_kg DESC;
```

### Lap/Split Analysis
```sql
-- Detailed splits for a specific activity
SELECT
    lap_index,
    distance_meters,
    duration_seconds,
    ROUND(duration_seconds / (distance_meters / 1000.0), 1) as pace_sec_per_km,
    avg_heart_rate,
    max_heart_rate,
    elevation_gain,
    avg_cadence
FROM activity_splits
WHERE user_id = 1
    AND activity_id = '123456789'
ORDER BY lap_index;
```

### Running Pace Consistency
```sql
-- Analyze pace consistency across runs
SELECT
    a.activity_date,
    a.activity_name,
    COUNT(s.lap_index) as total_laps,
    ROUND(AVG(s.duration_seconds / (s.distance_meters / 1000.0)), 1) as avg_pace_sec_km,
    ROUND(MAX(s.duration_seconds / (s.distance_meters / 1000.0)) -
          MIN(s.duration_seconds / (s.distance_meters / 1000.0)), 1) as pace_variance
FROM activities a
JOIN activity_splits s ON a.activity_id = s.activity_id AND a.user_id = s.user_id
WHERE a.user_id = 1
    AND a.activity_type = 'running'
    AND s.distance_meters > 0
    AND a.activity_date >= date('now', '-30 days')
GROUP BY a.activity_id
ORDER BY a.activity_date DESC;
```

### Heart Rate Zones Per Lap
```sql
-- Analyze HR distribution across laps
SELECT
    lap_index,
    avg_heart_rate,
    CASE
        WHEN avg_heart_rate < 120 THEN 'Zone 1 (Easy)'
        WHEN avg_heart_rate < 140 THEN 'Zone 2 (Aerobic)'
        WHEN avg_heart_rate < 160 THEN 'Zone 3 (Tempo)'
        WHEN avg_heart_rate < 175 THEN 'Zone 4 (Threshold)'
        ELSE 'Zone 5 (Max)'
    END as hr_zone,
    distance_meters,
    duration_seconds
FROM activity_splits
WHERE user_id = 1
    AND activity_id = '123456789'
    AND avg_heart_rate IS NOT NULL
ORDER BY lap_index;
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
- `SPO2`
- `RESTING_HEART_RATE`
- `INTENSITY_MINUTES`
- `FLOORS`
- `TRAINING_STATUS`
- `ENDURANCE_SCORE`

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