"""Simple data models for local database."""

from enum import Enum


class MetricType(Enum):
    """Available Garmin metrics."""
    DAILY_SUMMARY = "daily_summary"
    SLEEP = "sleep"
    BODY_BATTERY = "body_battery"
    HEART_RATE = "heart_rate"
    STRESS = "stress"
    TRAINING_READINESS = "training_readiness"
    ACTIVITIES = "activities"
    STEPS = "steps"
    CALORIES = "calories"
    HRV = "hrv"
    RESPIRATION = "respiration"