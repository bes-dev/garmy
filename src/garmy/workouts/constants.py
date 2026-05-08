"""
Constants and enums for Garmin workout API.

This module defines the enumerations used by the Garmin Connect workout API
for sport types, step types, end conditions, and targets.
"""

from enum import Enum
from typing import NamedTuple


class SportTypeValue(NamedTuple):
    """Sport type with numeric ID and string key."""

    id: int
    key: str


class SportType(Enum):
    """Sport types supported by Garmin workouts.

    Each sport type has a numeric ID and string key used by the API.
    IDs verified against Garmin Connect workout-service API.
    Note: These IDs are used by Garmin to determine sport type (key is ignored).
    """

    RUNNING = SportTypeValue(1, "running")
    CYCLING = SportTypeValue(2, "cycling")
    OTHER = SportTypeValue(3, "other")
    SWIMMING = SportTypeValue(4, "swimming")
    STRENGTH = SportTypeValue(5, "strength_training")
    CARDIO = SportTypeValue(6, "cardio_training")
    YOGA = SportTypeValue(7, "yoga")
    PILATES = SportTypeValue(8, "pilates")
    HIIT = SportTypeValue(9, "hiit")
    MOBILITY = SportTypeValue(11, "mobility")
    WALKING = SportTypeValue(12, "walking")

    @property
    def id(self) -> int:
        """Get the numeric sport type ID."""
        return self.value.id

    @property
    def key(self) -> str:
        """Get the string sport type key."""
        return self.value.key

    @classmethod
    def from_id(cls, sport_id: int) -> "SportType":
        """Get SportType by numeric ID."""
        for sport in cls:
            if sport.id == sport_id:
                return sport
        return cls.OTHER

    @classmethod
    def from_key(cls, key: str) -> "SportType":
        """Get SportType by string key."""
        key_lower = key.lower()
        for sport in cls:
            if sport.key == key_lower:
                return sport
        return cls.OTHER


class StepType(Enum):
    """Workout step types."""

    WARMUP = "warmup"
    COOLDOWN = "cooldown"
    INTERVAL = "interval"
    RECOVERY = "recovery"
    REST = "rest"
    REPEAT = "repeat"
    OTHER = "other"

    @property
    def type_id(self) -> int:
        """Get the numeric step type ID for API."""
        type_ids = {
            StepType.WARMUP: 1,
            StepType.COOLDOWN: 2,
            StepType.INTERVAL: 3,
            StepType.RECOVERY: 4,
            StepType.REST: 5,
            StepType.REPEAT: 6,
            StepType.OTHER: 7,
        }
        return type_ids.get(self, 7)

    @classmethod
    def from_type_id(cls, type_id: int) -> "StepType":
        """Get StepType from numeric type ID."""
        id_to_type = {
            1: cls.WARMUP,
            2: cls.COOLDOWN,
            3: cls.INTERVAL,
            4: cls.RECOVERY,
            5: cls.REST,
            6: cls.REPEAT,
            7: cls.OTHER,
        }
        return id_to_type.get(type_id, cls.OTHER)


class EndConditionType(Enum):
    """How a workout step ends."""

    LAP_BUTTON = "lap.button"
    TIME = "time"
    DISTANCE = "distance"
    CALORIES = "calories"
    HEART_RATE_LESS_THAN = "heart.rate.less.than"
    HEART_RATE_GREATER_THAN = "heart.rate.greater.than"
    POWER_LESS_THAN = "power.less.than"
    POWER_GREATER_THAN = "power.greater.than"
    ITERATIONS = "iterations"
    REPS = "reps"

    @property
    def condition_type_id(self) -> int:
        """Get the numeric condition type ID for API."""
        type_ids = {
            EndConditionType.LAP_BUTTON: 1,
            EndConditionType.TIME: 2,
            EndConditionType.DISTANCE: 3,
            EndConditionType.CALORIES: 4,
            EndConditionType.HEART_RATE_LESS_THAN: 5,
            EndConditionType.HEART_RATE_GREATER_THAN: 6,
            EndConditionType.POWER_LESS_THAN: 11,
            EndConditionType.POWER_GREATER_THAN: 12,
            EndConditionType.ITERATIONS: 7,
            EndConditionType.REPS: 10,  # Garmin uses ID 10 for reps
        }
        return type_ids.get(self, 1)

    @classmethod
    def from_condition_type_id(cls, type_id: int) -> "EndConditionType":
        """Get EndConditionType from numeric type ID."""
        id_to_type = {
            1: cls.LAP_BUTTON,
            2: cls.TIME,
            3: cls.DISTANCE,
            4: cls.CALORIES,
            5: cls.HEART_RATE_LESS_THAN,
            6: cls.HEART_RATE_GREATER_THAN,
            7: cls.ITERATIONS,
            10: cls.REPS,  # Garmin uses ID 10 for reps
            11: cls.POWER_LESS_THAN,
            12: cls.POWER_GREATER_THAN,
        }
        return id_to_type.get(type_id, cls.LAP_BUTTON)


class TargetType(Enum):
    """Target metric types for workout steps."""

    NO_TARGET = "no.target"
    POWER_ZONE = "power.zone"
    CADENCE_ZONE = "cadence.zone"
    HEART_RATE_ZONE = "heart.rate.zone"
    SPEED_ZONE = "speed.zone"
    PACE_ZONE = "pace.zone"
    POWER_LAP = "power.lap"
    HEART_RATE_LAP = "heart.rate.lap"
    SPEED_LAP = "speed.lap"

    @property
    def target_type_id(self) -> int:
        """Get the numeric target type ID for API."""
        type_ids = {
            TargetType.NO_TARGET: 1,
            TargetType.POWER_ZONE: 2,
            TargetType.CADENCE_ZONE: 3,
            TargetType.HEART_RATE_ZONE: 4,
            TargetType.SPEED_ZONE: 5,
            TargetType.PACE_ZONE: 6,
            TargetType.POWER_LAP: 7,
            TargetType.HEART_RATE_LAP: 8,
            TargetType.SPEED_LAP: 9,
        }
        return type_ids.get(self, 1)

    @classmethod
    def from_target_type_id(cls, type_id: int) -> "TargetType":
        """Get TargetType from numeric target type ID."""
        id_to_type = {
            1: cls.NO_TARGET,
            2: cls.POWER_ZONE,
            3: cls.CADENCE_ZONE,
            4: cls.HEART_RATE_ZONE,
            5: cls.SPEED_ZONE,
            6: cls.PACE_ZONE,
            7: cls.POWER_LAP,
            8: cls.HEART_RATE_LAP,
            9: cls.SPEED_LAP,
        }
        return id_to_type.get(type_id, cls.NO_TARGET)


class IntensityType(Enum):
    """Intensity levels for workout steps."""

    ACTIVE = "active"
    REST = "rest"
    WARMUP = "warmup"
    COOLDOWN = "cooldown"
    RECOVERY = "recovery"
    INTERVAL = "interval"

    @property
    def intensity_type_id(self) -> int:
        """Get the numeric intensity type ID for API."""
        type_ids = {
            IntensityType.ACTIVE: 1,
            IntensityType.REST: 2,
            IntensityType.WARMUP: 3,
            IntensityType.COOLDOWN: 4,
            IntensityType.RECOVERY: 5,
            IntensityType.INTERVAL: 6,
        }
        return type_ids.get(self, 1)

    @classmethod
    def from_intensity_type_id(cls, type_id: int) -> "IntensityType":
        """Get IntensityType from numeric intensity type ID."""
        id_to_type = {
            1: cls.ACTIVE,
            2: cls.REST,
            3: cls.WARMUP,
            4: cls.COOLDOWN,
            5: cls.RECOVERY,
            6: cls.INTERVAL,
        }
        return id_to_type.get(type_id, cls.ACTIVE)


# Unit conversion constants
METERS_PER_KILOMETER = 1000
METERS_PER_MILE = 1609.344
SECONDS_PER_MINUTE = 60
SECONDS_PER_HOUR = 3600
