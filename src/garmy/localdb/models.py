"""SQLAlchemy models and enums for health database."""

from datetime import datetime
from enum import Enum

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class MetricType(Enum):
    """Health metric types that can be stored in the database."""

    DAILY_SUMMARY = "daily_summary"
    SLEEP = "sleep"
    ACTIVITIES = "activities"
    BODY_BATTERY = "body_battery"
    STRESS = "stress"
    HEART_RATE = "heart_rate"
    TRAINING_READINESS = "training_readiness"
    HRV = "hrv"
    RESPIRATION = "respiration"
    STEPS = "steps"
    CALORIES = "calories"
    BODY_COMPOSITION = "body_composition"
    SPO2 = "spo2"
    RESTING_HEART_RATE = "resting_heart_rate"
    INTENSITY_MINUTES = "intensity_minutes"
    FLOORS = "floors"
    TRAINING_STATUS = "training_status"
    ENDURANCE_SCORE = "endurance_score"
    HEALTH_SNAPSHOT = "health_snapshot"


class TimeSeries(Base):
    """High-frequency timeseries data (heart rate, stress, body battery, etc.)."""

    __tablename__ = "timeseries"

    user_id = Column(Integer, primary_key=True, nullable=False)
    metric_type = Column(String, primary_key=True, nullable=False)
    timestamp = Column(Integer, primary_key=True, nullable=False)
    value = Column(Float, nullable=False)
    meta_data = Column(JSON)


class Activity(Base):
    """Individual activities and workouts with key metrics."""

    __tablename__ = "activities"

    user_id = Column(Integer, primary_key=True, nullable=False)
    activity_id = Column(String, primary_key=True, nullable=False)
    activity_date = Column(Date, nullable=False)
    activity_name = Column(String)
    duration_seconds = Column(Integer)
    avg_heart_rate = Column(Integer)
    training_load = Column(Float)
    start_time = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Activity type and detailed metrics
    activity_type = Column(String)  # running, cycling, strength_training, etc.
    distance_meters = Column(Float)
    calories = Column(Integer)
    elevation_gain = Column(Float)
    elevation_loss = Column(Float)
    avg_speed = Column(Float)  # meters per second
    max_speed = Column(Float)
    max_heart_rate = Column(Integer)

    # Strength training summary
    total_sets = Column(Integer)
    total_reps = Column(Integer)
    total_weight_kg = Column(Float)  # Calculated total volume

    # Sync tracking
    details_synced = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ExerciseSet(Base):
    """Exercise sets from strength training activities."""

    __tablename__ = "exercise_sets"

    user_id = Column(Integer, primary_key=True, nullable=False)
    activity_id = Column(String, primary_key=True, nullable=False)
    set_order = Column(
        Integer, primary_key=True, nullable=False
    )  # Order within activity

    exercise_category = Column(String)  # CURL, BENCH_PRESS, SQUAT, etc.
    exercise_name = Column(String)
    set_type = Column(String)  # ACTIVE, REST
    repetition_count = Column(Integer)
    weight_grams = Column(Float)  # Store in grams for precision
    duration_seconds = Column(Float)
    start_time = Column(String)

    created_at = Column(DateTime, default=datetime.utcnow)


class ActivitySplit(Base):
    """Lap/split data from cardio activities (running, cycling, walking, etc.)."""

    __tablename__ = "activity_splits"

    user_id = Column(Integer, primary_key=True, nullable=False)
    activity_id = Column(String, primary_key=True, nullable=False)
    lap_index = Column(
        Integer, primary_key=True, nullable=False
    )  # 1-indexed lap number

    # Timing
    start_time = Column(String)  # ISO timestamp
    duration_seconds = Column(Float)
    moving_duration_seconds = Column(Float)

    # Distance and speed
    distance_meters = Column(Float)
    avg_speed = Column(Float)  # m/s
    max_speed = Column(Float)  # m/s
    avg_moving_speed = Column(Float)  # m/s

    # Heart rate
    avg_heart_rate = Column(Integer)
    max_heart_rate = Column(Integer)

    # Elevation
    elevation_gain = Column(Float)  # meters
    elevation_loss = Column(Float)  # meters
    max_elevation = Column(Float)  # meters
    min_elevation = Column(Float)  # meters

    # Cadence (running/walking)
    avg_cadence = Column(Float)  # steps per minute
    max_cadence = Column(Float)  # steps per minute

    # Calories
    calories = Column(Float)

    # GPS coordinates
    start_latitude = Column(Float)
    start_longitude = Column(Float)
    end_latitude = Column(Float)
    end_longitude = Column(Float)

    # Type
    intensity_type = Column(String)  # ACTIVE, REST

    created_at = Column(DateTime, default=datetime.utcnow)


class DailyHealthMetric(Base):
    """Normalized daily health metrics with dedicated columns for efficient querying."""

    __tablename__ = "daily_health_metrics"

    user_id = Column(Integer, primary_key=True, nullable=False)
    metric_date = Column(Date, primary_key=True, nullable=False)

    total_steps = Column(Integer)
    step_goal = Column(Integer)
    total_distance_meters = Column(Float)

    total_calories = Column(Integer)
    active_calories = Column(Integer)
    bmr_calories = Column(Integer)

    resting_heart_rate = Column(Integer)
    max_heart_rate = Column(Integer)
    min_heart_rate = Column(Integer)
    average_heart_rate = Column(Integer)

    avg_stress_level = Column(Integer)
    max_stress_level = Column(Integer)

    body_battery_high = Column(Integer)
    body_battery_low = Column(Integer)

    sleep_duration_hours = Column(Float)
    deep_sleep_hours = Column(Float)
    light_sleep_hours = Column(Float)
    rem_sleep_hours = Column(Float)
    awake_hours = Column(Float)

    deep_sleep_percentage = Column(Float)
    light_sleep_percentage = Column(Float)
    rem_sleep_percentage = Column(Float)
    awake_percentage = Column(Float)

    average_spo2 = Column(Float)
    lowest_spo2 = Column(Float)
    average_respiration = Column(Float)

    training_readiness_score = Column(Integer)
    training_readiness_level = Column(Text)
    training_readiness_feedback = Column(Text)

    hrv_weekly_avg = Column(Float)
    hrv_last_night_avg = Column(Float)
    hrv_status = Column(Text)
    hrv_last_night_5min_high = Column(Float)
    hrv_baseline_low_upper = Column(Float)
    hrv_baseline_balanced_low = Column(Float)
    hrv_baseline_balanced_upper = Column(Float)

    avg_waking_respiration_value = Column(Float)
    avg_sleep_respiration_value = Column(Float)
    lowest_respiration_value = Column(Float)
    highest_respiration_value = Column(Float)

    # Intensity minutes
    # moderate/vigorous are weekly cumulative values from the API
    moderate_intensity_minutes = Column(Integer)
    vigorous_intensity_minutes = Column(Integer)
    # Daily total: sum of 15-min timeseries values (not weekly cumulative)
    intensity_minutes_total = Column(Integer)
    # Weekly goal (typically 150)
    intensity_minutes_goal = Column(Integer)

    # Floors
    floors_ascended = Column(Integer)
    floors_descended = Column(Integer)

    # Dedicated resting HR (separate from daily_summary/heart_rate sources)
    dedicated_resting_heart_rate = Column(Integer)

    # Sleep enhancements
    sleep_score = Column(Integer)  # 0-100 overall score
    sleep_score_qualifier = Column(String)  # POOR, FAIR, GOOD, EXCELLENT
    sleep_bedtime = Column(String)  # ISO timestamp string
    sleep_wake_time = Column(String)  # ISO timestamp string
    sleep_need_minutes = Column(Integer)  # Target sleep in minutes

    # Skin temperature (Celsius only - Fahrenheit computed on read)
    skin_temp_deviation_c = Column(Float)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SyncStatus(Base):
    """Sync status tracking for each metric per date."""

    __tablename__ = "sync_status"

    user_id = Column(Integer, primary_key=True, nullable=False)
    sync_date = Column(Date, primary_key=True, nullable=False)
    metric_type = Column(String, primary_key=True, nullable=False)
    status = Column(String, nullable=False)
    synced_at = Column(DateTime)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class BodyComposition(Base):
    """Body composition measurements from smart scales."""

    __tablename__ = "body_composition"

    user_id = Column(Integer, primary_key=True, nullable=False)
    sample_pk = Column(String, primary_key=True, nullable=False)  # Garmin's unique ID
    measurement_date = Column(Date, nullable=False, index=True)
    timestamp_gmt = Column(DateTime)

    # Core measurements
    weight_grams = Column(Float)
    bmi = Column(Float)
    body_fat_percentage = Column(Float)
    body_water_percentage = Column(Float)
    bone_mass_grams = Column(Float)
    muscle_mass_grams = Column(Float)

    # Additional metrics (may be null depending on scale)
    visceral_fat = Column(Float)
    metabolic_age = Column(Integer)
    physique_rating = Column(Float)

    # Metadata
    source_type = Column(String)  # e.g., "INDEX_SCALE"
    created_at = Column(DateTime, default=datetime.utcnow)


class PerformanceMetric(Base):
    """Post-activity performance metrics (training load/status, endurance score).

    These metrics update irregularly after activities, not on a fixed daily schedule.
    Stored separately from daily_health_metrics to avoid NULLs on rest days.
    """

    __tablename__ = "performance_metrics"

    user_id = Column(Integer, primary_key=True, nullable=False)
    metric_date = Column(Date, primary_key=True, nullable=False)

    # Training Load (from acuteTrainingLoadDTO)
    acute_load = Column(Float)  # 7-day rolling
    chronic_load = Column(Float)  # 28-day rolling
    load_balance = Column(Float)  # acute / chronic ratio
    load_type = Column(Text)  # OPTIMAL, OVERREACHING, etc.

    # Training Status (numeric code + feedback phrase)
    training_status = Column(Integer)  # Numeric code (see TrainingStatus.STATUS_MAP)
    training_status_feedback = Column(Text)  # e.g. "MAINTAINING_1"

    # Endurance Score
    endurance_score = Column(Float)  # Absolute value (e.g. 4508)
    endurance_score_classification = Column(Integer)  # Numeric code (see EnduranceScore.CLASSIFICATION_MAP)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class HealthSnapshotRecord(Base):
    """Health Snapshot recording (~2-min on-demand multi-metric measurement).

    One row per snapshot. Each snapshot has 6 related summary stats (in
    health_snapshot_summaries) and 6 zone time entries (in health_snapshot_zones),
    keyed by (user_id, activity_uuid).
    """

    __tablename__ = "health_snapshots"

    user_id = Column(Integer, primary_key=True, nullable=False)
    activity_uuid = Column(String, primary_key=True, nullable=False)
    calendar_date = Column(Date, nullable=False, index=True)

    start_timestamp_gmt = Column(DateTime)
    start_timestamp_local = Column(DateTime)
    end_timestamp_gmt = Column(DateTime)
    end_timestamp_local = Column(DateTime)

    wellness_activity_type = Column(String)  # "HEALTH_MONITORING"
    notes = Column(Text)
    rule_pk = Column(Integer)
    user_profile_pk = Column(Integer)
    device_meta_data = Column(JSON)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class HealthSnapshotSummaryStat(Base):
    """Per-metric summary stat for a single Health Snapshot.

    summary_type values: HEART_RATE, RESPIRATION, STRESS, SPO2, RMSSD_HRV, SDRR_HRV.
    HEART_RATE / RESPIRATION / STRESS / SPO2 carry min/max/avg.
    RMSSD_HRV / SDRR_HRV only carry avg_value (min/max are NULL).
    """

    __tablename__ = "health_snapshot_summaries"

    user_id = Column(Integer, primary_key=True, nullable=False)
    activity_uuid = Column(String, primary_key=True, nullable=False)
    summary_type = Column(String, primary_key=True, nullable=False)

    min_value = Column(Float)
    max_value = Column(Float)
    avg_value = Column(Float, nullable=False)


class HealthSnapshotZoneTime(Base):
    """Per-zone time-in-zone for a single Health Snapshot.

    Each snapshot reports time spent in 6 heart-rate zones (0..5).
    """

    __tablename__ = "health_snapshot_zones"

    user_id = Column(Integer, primary_key=True, nullable=False)
    activity_uuid = Column(String, primary_key=True, nullable=False)
    zone_number = Column(Integer, primary_key=True, nullable=False)

    millis_in_zone = Column(Integer)
    zone_low_boundary = Column(Integer)
