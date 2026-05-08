"""
Fluent builder API for creating Garmin workouts.

This module provides an intuitive, chainable API for constructing workouts
without needing to manually create all the underlying model objects.

Example:
    >>> workout = (
    ...     WorkoutBuilder("Sweet Spot 2x20", SportType.CYCLING)
    ...     .with_description("Endurance builder")
    ...     .warmup(minutes=15, target_power=(50, 65))
    ...     .repeat(2)
    ...         .interval(minutes=20, target_power=(88, 93))
    ...         .recovery(minutes=5)
    ...     .end_repeat()
    ...     .cooldown(minutes=10)
    ...     .build()
    ... )
"""

from typing import List, Optional, Tuple

from .constants import SportType, StepType
from .models import (
    EndCondition,
    RepeatGroup,
    Target,
    Workout,
    WorkoutStep,
    WorkoutStepOrRepeat,
)


class RepeatBuilder:
    """Builder for repeat group steps.

    Created via WorkoutBuilder.repeat() and returns to parent via end_repeat().
    """

    def __init__(
        self, parent: "WorkoutBuilder", iterations: int, smart_repeat: bool = False
    ) -> None:
        """Initialize repeat builder.

        Args:
            parent: The parent WorkoutBuilder to return to.
            iterations: Number of times to repeat the steps.
            smart_repeat: When True, skip the last rest/recovery step in the final iteration.
        """
        self._parent = parent
        self._iterations = iterations
        self._smart_repeat = smart_repeat
        self._steps: List[WorkoutStep] = []

    def _create_step(
        self,
        step_type: StepType,
        minutes: Optional[float] = None,
        seconds: Optional[float] = None,
        distance_km: Optional[float] = None,
        distance_miles: Optional[float] = None,
        target_power: Optional[Tuple[float, float]] = None,
        target_hr: Optional[Tuple[float, float]] = None,
        target_cadence: Optional[Tuple[int, int]] = None,
        description: Optional[str] = None,
        lap_button: bool = False,
        reps: Optional[int] = None,
        exercise_name: Optional[str] = None,
        exercise_category: Optional[str] = None,
        weight_value: Optional[float] = None,
        weight_unit: Optional[str] = None,
    ) -> WorkoutStep:
        """Create a workout step with the given parameters."""
        # Determine end condition
        if lap_button:
            end_condition = EndCondition.lap_button()
        elif reps is not None:
            end_condition = EndCondition.reps(reps)
        elif minutes is not None:
            end_condition = EndCondition.time_minutes(minutes)
        elif seconds is not None:
            end_condition = EndCondition.time(seconds)
        elif distance_km is not None:
            end_condition = EndCondition.distance_km(distance_km)
        elif distance_miles is not None:
            end_condition = EndCondition.distance_miles(distance_miles)
        else:
            end_condition = EndCondition.lap_button()

        # Determine target
        if target_power is not None:
            target = Target.power_zone(target_power[0], target_power[1])
        elif target_hr is not None:
            target = Target.heart_rate_zone(target_hr[0], target_hr[1])
        elif target_cadence is not None:
            target = Target.cadence_zone(target_cadence[0], target_cadence[1])
        else:
            target = Target.no_target()

        return WorkoutStep(
            step_type=step_type,
            end_condition=end_condition,
            target=target,
            description=description,
            exercise_name=exercise_name,
            exercise_category=exercise_category,
            weight_value=weight_value,
            weight_unit=weight_unit,
        )

    def interval(
        self,
        minutes: Optional[float] = None,
        seconds: Optional[float] = None,
        distance_km: Optional[float] = None,
        distance_miles: Optional[float] = None,
        target_power: Optional[Tuple[float, float]] = None,
        target_hr: Optional[Tuple[float, float]] = None,
        target_cadence: Optional[Tuple[int, int]] = None,
        description: Optional[str] = None,
        lap_button: bool = False,
        reps: Optional[int] = None,
        exercise_name: Optional[str] = None,
        exercise_category: Optional[str] = None,
        weight_value: Optional[float] = None,
        weight_unit: Optional[str] = None,
    ) -> "RepeatBuilder":
        """Add an interval step to the repeat group."""
        step = self._create_step(
            StepType.INTERVAL,
            minutes=minutes,
            seconds=seconds,
            distance_km=distance_km,
            distance_miles=distance_miles,
            target_power=target_power,
            target_hr=target_hr,
            target_cadence=target_cadence,
            description=description,
            lap_button=lap_button,
            reps=reps,
            exercise_name=exercise_name,
            exercise_category=exercise_category,
            weight_value=weight_value,
            weight_unit=weight_unit,
        )
        self._steps.append(step)
        return self

    def recovery(
        self,
        minutes: Optional[float] = None,
        seconds: Optional[float] = None,
        distance_km: Optional[float] = None,
        distance_miles: Optional[float] = None,
        target_power: Optional[Tuple[float, float]] = None,
        target_hr: Optional[Tuple[float, float]] = None,
        target_cadence: Optional[Tuple[int, int]] = None,
        description: Optional[str] = None,
        lap_button: bool = False,
        reps: Optional[int] = None,
        exercise_name: Optional[str] = None,
        exercise_category: Optional[str] = None,
        weight_value: Optional[float] = None,
        weight_unit: Optional[str] = None,
    ) -> "RepeatBuilder":
        """Add a recovery step to the repeat group."""
        step = self._create_step(
            StepType.RECOVERY,
            minutes=minutes,
            seconds=seconds,
            distance_km=distance_km,
            distance_miles=distance_miles,
            target_power=target_power,
            target_hr=target_hr,
            target_cadence=target_cadence,
            description=description,
            lap_button=lap_button,
            reps=reps,
            exercise_name=exercise_name,
            exercise_category=exercise_category,
            weight_value=weight_value,
            weight_unit=weight_unit,
        )
        self._steps.append(step)
        return self

    def rest(
        self,
        minutes: Optional[float] = None,
        seconds: Optional[float] = None,
        description: Optional[str] = None,
        lap_button: bool = False,
    ) -> "RepeatBuilder":
        """Add a rest step to the repeat group."""
        step = self._create_step(
            StepType.REST,
            minutes=minutes,
            seconds=seconds,
            description=description,
            lap_button=lap_button,
        )
        self._steps.append(step)
        return self

    def step(
        self,
        step_type: StepType,
        minutes: Optional[float] = None,
        seconds: Optional[float] = None,
        distance_km: Optional[float] = None,
        distance_miles: Optional[float] = None,
        target_power: Optional[Tuple[float, float]] = None,
        target_hr: Optional[Tuple[float, float]] = None,
        target_cadence: Optional[Tuple[int, int]] = None,
        description: Optional[str] = None,
        lap_button: bool = False,
        reps: Optional[int] = None,
        exercise_name: Optional[str] = None,
        exercise_category: Optional[str] = None,
        weight_value: Optional[float] = None,
        weight_unit: Optional[str] = None,
    ) -> "RepeatBuilder":
        """Add a generic step to the repeat group."""
        step = self._create_step(
            step_type,
            minutes=minutes,
            seconds=seconds,
            distance_km=distance_km,
            distance_miles=distance_miles,
            target_power=target_power,
            target_hr=target_hr,
            target_cadence=target_cadence,
            description=description,
            lap_button=lap_button,
            reps=reps,
            exercise_name=exercise_name,
            exercise_category=exercise_category,
            weight_value=weight_value,
            weight_unit=weight_unit,
        )
        self._steps.append(step)
        return self

    def end_repeat(self) -> "WorkoutBuilder":
        """Finish the repeat group and return to the parent builder."""
        repeat_group = RepeatGroup(
            iterations=self._iterations,
            steps=self._steps,
            smart_repeat=self._smart_repeat,
        )
        self._parent._steps.append(repeat_group)
        return self._parent


class WorkoutBuilder:
    """Fluent builder for creating Garmin workouts.

    Example:
        >>> workout = (
        ...     WorkoutBuilder("My Workout", SportType.CYCLING)
        ...     .warmup(minutes=10)
        ...     .interval(minutes=5, target_power=(90, 95))
        ...     .cooldown(minutes=5)
        ...     .build()
        ... )
    """

    def __init__(
        self,
        name: str,
        sport_type: SportType = SportType.CYCLING,
    ) -> None:
        """Initialize the workout builder.

        Args:
            name: Name of the workout.
            sport_type: Type of sport for the workout.
        """
        self._name = name
        self._sport_type = sport_type
        self._description: Optional[str] = None
        self._steps: List[WorkoutStepOrRepeat] = []

    def with_description(self, description: str) -> "WorkoutBuilder":
        """Set the workout description."""
        self._description = description
        return self

    def _create_step(
        self,
        step_type: StepType,
        minutes: Optional[float] = None,
        seconds: Optional[float] = None,
        distance_km: Optional[float] = None,
        distance_miles: Optional[float] = None,
        target_power: Optional[Tuple[float, float]] = None,
        target_hr: Optional[Tuple[float, float]] = None,
        target_cadence: Optional[Tuple[int, int]] = None,
        description: Optional[str] = None,
        lap_button: bool = False,
        reps: Optional[int] = None,
        exercise_name: Optional[str] = None,
        exercise_category: Optional[str] = None,
        weight_value: Optional[float] = None,
        weight_unit: Optional[str] = None,
    ) -> WorkoutStep:
        """Create a workout step with the given parameters."""
        # Determine end condition
        if lap_button:
            end_condition = EndCondition.lap_button()
        elif reps is not None:
            end_condition = EndCondition.reps(reps)
        elif minutes is not None:
            end_condition = EndCondition.time_minutes(minutes)
        elif seconds is not None:
            end_condition = EndCondition.time(seconds)
        elif distance_km is not None:
            end_condition = EndCondition.distance_km(distance_km)
        elif distance_miles is not None:
            end_condition = EndCondition.distance_miles(distance_miles)
        else:
            end_condition = EndCondition.lap_button()

        # Determine target
        if target_power is not None:
            target = Target.power_zone(target_power[0], target_power[1])
        elif target_hr is not None:
            target = Target.heart_rate_zone(target_hr[0], target_hr[1])
        elif target_cadence is not None:
            target = Target.cadence_zone(target_cadence[0], target_cadence[1])
        else:
            target = Target.no_target()

        return WorkoutStep(
            step_type=step_type,
            end_condition=end_condition,
            target=target,
            description=description,
            exercise_name=exercise_name,
            exercise_category=exercise_category,
            weight_value=weight_value,
            weight_unit=weight_unit,
        )

    def warmup(
        self,
        minutes: Optional[float] = None,
        seconds: Optional[float] = None,
        distance_km: Optional[float] = None,
        distance_miles: Optional[float] = None,
        target_power: Optional[Tuple[float, float]] = None,
        target_hr: Optional[Tuple[float, float]] = None,
        target_cadence: Optional[Tuple[int, int]] = None,
        description: Optional[str] = None,
        lap_button: bool = False,
    ) -> "WorkoutBuilder":
        """Add a warmup step."""
        step = self._create_step(
            StepType.WARMUP,
            minutes=minutes,
            seconds=seconds,
            distance_km=distance_km,
            distance_miles=distance_miles,
            target_power=target_power,
            target_hr=target_hr,
            target_cadence=target_cadence,
            description=description,
            lap_button=lap_button,
        )
        self._steps.append(step)
        return self

    def cooldown(
        self,
        minutes: Optional[float] = None,
        seconds: Optional[float] = None,
        distance_km: Optional[float] = None,
        distance_miles: Optional[float] = None,
        target_power: Optional[Tuple[float, float]] = None,
        target_hr: Optional[Tuple[float, float]] = None,
        target_cadence: Optional[Tuple[int, int]] = None,
        description: Optional[str] = None,
        lap_button: bool = False,
    ) -> "WorkoutBuilder":
        """Add a cooldown step."""
        step = self._create_step(
            StepType.COOLDOWN,
            minutes=minutes,
            seconds=seconds,
            distance_km=distance_km,
            distance_miles=distance_miles,
            target_power=target_power,
            target_hr=target_hr,
            target_cadence=target_cadence,
            description=description,
            lap_button=lap_button,
        )
        self._steps.append(step)
        return self

    def interval(
        self,
        minutes: Optional[float] = None,
        seconds: Optional[float] = None,
        distance_km: Optional[float] = None,
        distance_miles: Optional[float] = None,
        target_power: Optional[Tuple[float, float]] = None,
        target_hr: Optional[Tuple[float, float]] = None,
        target_cadence: Optional[Tuple[int, int]] = None,
        description: Optional[str] = None,
        lap_button: bool = False,
        reps: Optional[int] = None,
        exercise_name: Optional[str] = None,
        exercise_category: Optional[str] = None,
        weight_value: Optional[float] = None,
        weight_unit: Optional[str] = None,
    ) -> "WorkoutBuilder":
        """Add an interval step."""
        step = self._create_step(
            StepType.INTERVAL,
            minutes=minutes,
            seconds=seconds,
            distance_km=distance_km,
            distance_miles=distance_miles,
            target_power=target_power,
            target_hr=target_hr,
            target_cadence=target_cadence,
            description=description,
            lap_button=lap_button,
            reps=reps,
            exercise_name=exercise_name,
            exercise_category=exercise_category,
            weight_value=weight_value,
            weight_unit=weight_unit,
        )
        self._steps.append(step)
        return self

    def recovery(
        self,
        minutes: Optional[float] = None,
        seconds: Optional[float] = None,
        distance_km: Optional[float] = None,
        distance_miles: Optional[float] = None,
        target_power: Optional[Tuple[float, float]] = None,
        target_hr: Optional[Tuple[float, float]] = None,
        target_cadence: Optional[Tuple[int, int]] = None,
        description: Optional[str] = None,
        lap_button: bool = False,
        reps: Optional[int] = None,
        exercise_name: Optional[str] = None,
        exercise_category: Optional[str] = None,
        weight_value: Optional[float] = None,
        weight_unit: Optional[str] = None,
    ) -> "WorkoutBuilder":
        """Add a recovery step."""
        step = self._create_step(
            StepType.RECOVERY,
            minutes=minutes,
            seconds=seconds,
            distance_km=distance_km,
            distance_miles=distance_miles,
            target_power=target_power,
            target_hr=target_hr,
            target_cadence=target_cadence,
            description=description,
            lap_button=lap_button,
            reps=reps,
            exercise_name=exercise_name,
            exercise_category=exercise_category,
            weight_value=weight_value,
            weight_unit=weight_unit,
        )
        self._steps.append(step)
        return self

    def rest(
        self,
        minutes: Optional[float] = None,
        seconds: Optional[float] = None,
        description: Optional[str] = None,
        lap_button: bool = False,
    ) -> "WorkoutBuilder":
        """Add a rest step."""
        step = self._create_step(
            StepType.REST,
            minutes=minutes,
            seconds=seconds,
            description=description,
            lap_button=lap_button,
        )
        self._steps.append(step)
        return self

    def step(
        self,
        step_type: StepType,
        minutes: Optional[float] = None,
        seconds: Optional[float] = None,
        distance_km: Optional[float] = None,
        distance_miles: Optional[float] = None,
        target_power: Optional[Tuple[float, float]] = None,
        target_hr: Optional[Tuple[float, float]] = None,
        target_cadence: Optional[Tuple[int, int]] = None,
        description: Optional[str] = None,
        lap_button: bool = False,
        reps: Optional[int] = None,
        exercise_name: Optional[str] = None,
        exercise_category: Optional[str] = None,
        weight_value: Optional[float] = None,
        weight_unit: Optional[str] = None,
    ) -> "WorkoutBuilder":
        """Add a generic step with the specified type."""
        step = self._create_step(
            step_type,
            minutes=minutes,
            seconds=seconds,
            distance_km=distance_km,
            distance_miles=distance_miles,
            target_power=target_power,
            target_hr=target_hr,
            target_cadence=target_cadence,
            description=description,
            lap_button=lap_button,
            reps=reps,
            exercise_name=exercise_name,
            exercise_category=exercise_category,
            weight_value=weight_value,
            weight_unit=weight_unit,
        )
        self._steps.append(step)
        return self

    def repeat(self, iterations: int, smart_repeat: bool = False) -> RepeatBuilder:
        """Start a repeat group with the specified number of iterations.

        Use end_repeat() on the returned RepeatBuilder to return to this builder.

        Args:
            iterations: Number of times to repeat the steps.
            smart_repeat: When True, skip the last rest/recovery step in the final iteration.

        Example:
            >>> builder.repeat(3).interval(minutes=5).recovery(minutes=2).end_repeat()
        """
        return RepeatBuilder(self, iterations, smart_repeat=smart_repeat)

    def add_step(self, step: WorkoutStepOrRepeat) -> "WorkoutBuilder":
        """Add a pre-built step or repeat group."""
        self._steps.append(step)
        return self

    def build(self) -> Workout:
        """Build and return the Workout object."""
        return Workout(
            name=self._name,
            sport_type=self._sport_type,
            description=self._description,
            steps=self._steps,
        )
