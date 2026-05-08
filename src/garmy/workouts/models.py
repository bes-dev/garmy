"""
Data models for Garmin workouts.

This module defines dataclasses representing workout structures including
steps, repeat groups, segments, and complete workouts.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from .constants import (
    EndConditionType,
    IntensityType,
    SportType,
    StepType,
    TargetType,
)


@dataclass
class EndCondition:
    """Defines how a workout step ends.

    Attributes:
        condition_type: Type of end condition (time, distance, lap button, etc.)
        value: Numeric value for the condition (seconds for time, meters for distance)
    """

    condition_type: EndConditionType = EndConditionType.LAP_BUTTON
    value: Optional[float] = None

    @classmethod
    def time(cls, seconds: float) -> "EndCondition":
        """Create a time-based end condition."""
        return cls(condition_type=EndConditionType.TIME, value=seconds)

    @classmethod
    def time_minutes(cls, minutes: float) -> "EndCondition":
        """Create a time-based end condition from minutes."""
        return cls(condition_type=EndConditionType.TIME, value=minutes * 60)

    @classmethod
    def distance(cls, meters: float) -> "EndCondition":
        """Create a distance-based end condition."""
        return cls(condition_type=EndConditionType.DISTANCE, value=meters)

    @classmethod
    def distance_km(cls, kilometers: float) -> "EndCondition":
        """Create a distance-based end condition from kilometers."""
        return cls(condition_type=EndConditionType.DISTANCE, value=kilometers * 1000)

    @classmethod
    def distance_miles(cls, miles: float) -> "EndCondition":
        """Create a distance-based end condition from miles."""
        return cls(condition_type=EndConditionType.DISTANCE, value=miles * 1609.344)

    @classmethod
    def lap_button(cls) -> "EndCondition":
        """Create a lap button end condition."""
        return cls(condition_type=EndConditionType.LAP_BUTTON)

    @classmethod
    def iterations(cls, count: int) -> "EndCondition":
        """Create an iterations end condition for repeat groups."""
        return cls(condition_type=EndConditionType.ITERATIONS, value=float(count))

    @classmethod
    def reps(cls, count: int) -> "EndCondition":
        """Create a reps end condition for strength exercises."""
        return cls(condition_type=EndConditionType.REPS, value=float(count))


@dataclass
class Target:
    """Defines the target metric for a workout step.

    Attributes:
        target_type: Type of target (power zone, HR zone, pace zone, etc.)
        value_low: Lower bound of target range (percentage or absolute)
        value_high: Upper bound of target range (percentage or absolute)
        zone_number: Predefined zone number (1-7 typically)
    """

    target_type: TargetType = TargetType.NO_TARGET
    value_low: Optional[float] = None
    value_high: Optional[float] = None
    zone_number: Optional[int] = None

    @classmethod
    def no_target(cls) -> "Target":
        """Create a no-target specification."""
        return cls(target_type=TargetType.NO_TARGET)

    @classmethod
    def power_zone(
        cls,
        low_percent: float,
        high_percent: float,
    ) -> "Target":
        """Create a power zone target with percentage of FTP.

        Args:
            low_percent: Lower bound as percentage of FTP (e.g., 88 for 88%)
            high_percent: Upper bound as percentage of FTP (e.g., 93 for 93%)
        """
        return cls(
            target_type=TargetType.POWER_ZONE,
            value_low=low_percent,
            value_high=high_percent,
        )

    @classmethod
    def heart_rate_zone(
        cls,
        low_percent: float,
        high_percent: float,
    ) -> "Target":
        """Create a heart rate zone target with percentage of max HR.

        Args:
            low_percent: Lower bound as percentage of max HR
            high_percent: Upper bound as percentage of max HR
        """
        return cls(
            target_type=TargetType.HEART_RATE_ZONE,
            value_low=low_percent,
            value_high=high_percent,
        )

    @classmethod
    def cadence_zone(cls, low_rpm: int, high_rpm: int) -> "Target":
        """Create a cadence zone target.

        Args:
            low_rpm: Lower bound RPM
            high_rpm: Upper bound RPM
        """
        return cls(
            target_type=TargetType.CADENCE_ZONE,
            value_low=float(low_rpm),
            value_high=float(high_rpm),
        )

    @classmethod
    def pace_zone(
        cls,
        low_pace_per_km: float,
        high_pace_per_km: float,
    ) -> "Target":
        """Create a pace zone target.

        Args:
            low_pace_per_km: Lower bound in seconds per kilometer
            high_pace_per_km: Upper bound in seconds per kilometer
        """
        return cls(
            target_type=TargetType.PACE_ZONE,
            value_low=low_pace_per_km,
            value_high=high_pace_per_km,
        )


@dataclass
class WorkoutStep:
    """A single executable step within a workout.

    Attributes:
        step_type: Type of step (warmup, interval, recovery, etc.)
        end_condition: How the step ends
        target: Target metric for the step
        description: Optional description text
        step_order: Order within parent (set automatically during serialization)
        intensity: Intensity level for the step
        exercise_name: Name of the exercise (e.g., "BARBELL_DEADLIFT")
        exercise_category: Category of the exercise (e.g., "DEADLIFT", "CORE")
        weight_value: Target weight value for strength exercises
        weight_unit: Unit for weight (e.g., "pound", "kilogram")
    """

    step_type: StepType = StepType.OTHER
    end_condition: EndCondition = field(default_factory=EndCondition.lap_button)
    target: Target = field(default_factory=Target.no_target)
    description: Optional[str] = None
    step_order: Optional[int] = None
    intensity: IntensityType = IntensityType.ACTIVE
    exercise_name: Optional[str] = None
    exercise_category: Optional[str] = None
    weight_value: Optional[float] = None
    weight_unit: Optional[str] = None

    def __post_init__(self) -> None:
        """Set default intensity based on step type."""
        if self.intensity == IntensityType.ACTIVE:
            intensity_map = {
                StepType.WARMUP: IntensityType.WARMUP,
                StepType.COOLDOWN: IntensityType.COOLDOWN,
                StepType.RECOVERY: IntensityType.RECOVERY,
                StepType.REST: IntensityType.REST,
                StepType.INTERVAL: IntensityType.INTERVAL,
            }
            self.intensity = intensity_map.get(self.step_type, IntensityType.ACTIVE)


@dataclass
class RepeatGroup:
    """A group of steps that repeat multiple times.

    Attributes:
        iterations: Number of times to repeat the steps
        steps: List of steps within the repeat group
        step_order: Order within parent workout (set during serialization)
        smart_repeat: When True, skip the last rest/recovery step in the final iteration
    """

    iterations: int = 1
    steps: List[WorkoutStep] = field(default_factory=list)
    step_order: Optional[int] = None
    smart_repeat: bool = False

    def add_step(self, step: WorkoutStep) -> "RepeatGroup":
        """Add a step to the repeat group."""
        self.steps.append(step)
        return self


# Type alias for workout segment children
WorkoutStepOrRepeat = Union[WorkoutStep, RepeatGroup]


@dataclass
class WorkoutSegment:
    """A segment of steps grouped by sport type.

    Used for multi-sport workouts where different segments have different sports.

    Attributes:
        sport_type: Sport type for this segment
        steps: List of steps and repeat groups in this segment
    """

    sport_type: SportType
    steps: List[WorkoutStepOrRepeat] = field(default_factory=list)

    def add_step(self, step: WorkoutStepOrRepeat) -> "WorkoutSegment":
        """Add a step or repeat group to the segment."""
        self.steps.append(step)
        return self


@dataclass
class Workout:
    """A complete workout definition.

    Attributes:
        name: Name of the workout
        sport_type: Primary sport type
        description: Optional description
        steps: List of steps and repeat groups
        workout_id: Garmin workout ID (populated after creation)
        owner_id: Owner user ID
        segments: Optional segments for multi-sport workouts
    """

    name: str
    sport_type: SportType = SportType.CYCLING
    description: Optional[str] = None
    steps: List[WorkoutStepOrRepeat] = field(default_factory=list)
    workout_id: Optional[int] = None
    owner_id: Optional[int] = None
    segments: Optional[List[WorkoutSegment]] = None

    def add_step(self, step: WorkoutStepOrRepeat) -> "Workout":
        """Add a step or repeat group to the workout."""
        self.steps.append(step)
        return self

    def __str__(self) -> str:
        """Return human-readable workout summary."""
        step_count = len(self.steps)
        total_steps = step_count
        for step in self.steps:
            if isinstance(step, RepeatGroup):
                total_steps += len(step.steps) * step.iterations - 1

        parts = [f"Workout: {self.name}"]
        parts.append(f"Sport: {self.sport_type.key}")
        if self.description:
            parts.append(f"Description: {self.description}")
        parts.append(f"Steps: {step_count} ({total_steps} total with repeats)")
        if self.workout_id:
            parts.append(f"ID: {self.workout_id}")

        return " | ".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        """Convert workout to dictionary representation.

        This is a basic dict conversion. For API format, use WorkoutSerializer.
        """
        return {
            "name": self.name,
            "sport_type": self.sport_type.key,
            "description": self.description,
            "workout_id": self.workout_id,
            "step_count": len(self.steps),
        }
