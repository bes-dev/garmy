"""SQLAlchemy models and enums for health database."""

from datetime import date, datetime
from enum import Enum

from sqlalchemy import Column, Integer, String, Float, Date, DateTime, JSON, Text
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
    average_respiration = Column(Float)

    training_readiness_score = Column(Integer)
    training_readiness_level = Column(Text)
    training_readiness_feedback = Column(Text)

    hrv_weekly_avg = Column(Float)
    hrv_last_night_avg = Column(Float)
    hrv_status = Column(Text)

    avg_waking_respiration_value = Column(Float)
    avg_sleep_respiration_value = Column(Float)
    lowest_respiration_value = Column(Float)
    highest_respiration_value = Column(Float)

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