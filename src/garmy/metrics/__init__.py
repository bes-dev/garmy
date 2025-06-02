"""Garmin metrics package.

This package provides direct access to Garmin Connect health and fitness data
through a unified interface. Each metric class uses the @metric decorator to
automatically handle API endpoint mapping and data fetching.

Available Metrics:
    TrainingReadiness: Training readiness scores and contributing factors
    BodyBattery: Energy level data throughout the day
    Stress: Stress level measurements based on HRV
    HRV: Heart rate variability data and autonomic nervous system metrics
    Sleep: Comprehensive sleep data with stages, SpO2, and respiration
    HeartRate: Daily heart rate data with continuous readings and resting HR trends
    Respiration: Daily respiration data with continuous readings and sleep patterns
    Steps: Daily step counts, goals, distances, and weekly aggregations
    Calories: Daily calorie data including burned, active, BMR, and goal tracking
    DailySummary: Comprehensive daily summary with all major health metrics in one place
    Activities: Activity summaries with type, duration, heart rate, and basic performance data

Modern API Usage:
    >>> from garmy import AuthClient, APIClient
    >>>
    >>> # Set up clients
    >>> auth_client = AuthClient()
    >>> api_client = APIClient(auth_client=auth_client)
    >>> auth_client.login("email@example.com", "password")
    >>>
    >>> # Use metrics directly (auto-discovery happens automatically)
    >>>
    >>> # Training readiness
    >>> readiness = api_client.metrics["training_readiness"].get()
    >>> print(f"Score: {readiness.score}/100")
    >>> print(f"Level: {readiness.level}")
    >>>
    >>> # Body Battery
    >>> battery = api_client.metrics["body_battery"].get()
    >>> for reading in battery.body_battery_readings:
    >>>     print(f"{reading.datetime}: {reading.level}% ({reading.status})")
    >>>
    >>> # Stress
    >>> stress = api_client.metrics["stress"].get()
    >>> print(f"Average: {stress.avg_stress_level}")
    >>> print(f"Max: {stress.max_stress_level}")
    >>>
    >>> # HRV
    >>> hrv = api_client.metrics["hrv"].get()
    >>> print(f"Status: {hrv.hrv_summary.status}")
    >>> print(f"Last night: {hrv.hrv_summary.last_night_avg}ms")
    >>>
    >>> # Sleep
    >>> sleep = api_client.metrics["sleep"].get()
    >>> print(f"Duration: {sleep.sleep_duration_hours:.1f} hours")
    >>> print(f"Deep sleep: {sleep.deep_sleep_percentage:.1f}%")
    >>> print(f"Average SpO2: {sleep.average_spo2}%")
    >>>
    >>> # Heart Rate
    >>> hr = api_client.metrics["heart_rate"].get()
    >>> print(f"Resting HR: {hr.heart_rate_summary.resting_heart_rate} bpm")
    >>> print(f"Max HR: {hr.heart_rate_summary.max_heart_rate} bpm")
    >>> print(f"Readings: {hr.readings_count} measurements")
    >>>
    >>> # Weekly data for any metric
    >>> weekly_steps = api_client.metrics["steps"].list(days=7)
    >>> weekly_sleep = api_client.metrics["sleep"].list(days=7)
    >>>
    >>> # Raw API data access
    >>> raw_data = api_client.metrics["training_readiness"].raw()
    >>> print(f"Raw API response: {raw_data}")

Data Philosophy:
    garmy provides raw Garmin Connect API data without interpretation or custom
    analytics. All data comes directly from Garmin's services, allowing you to
    perform your own analysis and create custom insights based on your needs.

Note:
    All metrics require authentication with Garmin Connect and compatible
    Garmin devices that support the corresponding measurements.
"""

from typing import List

from .activities import ActivitySummary
from .body_battery import BodyBattery
from .calories import Calories
from .daily_summary import DailySummary
from .heart_rate import HeartRate
from .hrv import HRV
from .respiration import Respiration
from .sleep import Sleep
from .steps import Steps
from .stress import Stress
from .training_readiness import TrainingReadiness

__all__: List[str] = [
    "HRV",
    "ActivitySummary",
    "BodyBattery",
    "Calories",
    "DailySummary",
    "HeartRate",
    "Respiration",
    "Sleep",
    "Steps",
    "Stress",
    "TrainingReadiness",
]
