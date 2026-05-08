"""
Garmy Workouts Module.

This module provides functionality for creating, managing, and scheduling
workouts in Garmin Connect.

Example:
    >>> from garmy import AuthClient, APIClient
    >>> from garmy.workouts import WorkoutBuilder, SportType
    >>>
    >>> # Authenticate
    >>> auth = AuthClient()
    >>> api = APIClient(auth_client=auth)
    >>> auth.login("email", "password")
    >>>
    >>> # Create a workout using the fluent builder
    >>> workout = (
    ...     WorkoutBuilder("Sweet Spot 2x20", SportType.CYCLING)
    ...     .with_description("Endurance builder workout")
    ...     .warmup(minutes=15, target_power=(50, 65))
    ...     .repeat(2)
    ...         .interval(minutes=20, target_power=(88, 93))
    ...         .recovery(minutes=5, target_power=(40, 50))
    ...     .end_repeat()
    ...     .cooldown(minutes=10, target_power=(40, 55))
    ...     .build()
    ... )
    >>>
    >>> # Create the workout in Garmin Connect
    >>> result = api.workouts.create_workout(workout)
    >>> print(f"Created workout: {result.workout_id}")
    >>>
    >>> # List existing workouts
    >>> workouts = api.workouts.list_workouts(limit=10)
    >>> for w in workouts:
    ...     print(f"{w.name} ({w.sport_type.key})")
"""

from .builder import RepeatBuilder, WorkoutBuilder
from .client import WorkoutClient
from .constants import (
    EndConditionType,
    IntensityType,
    SportType,
    StepType,
    TargetType,
)
from .exercises import (
    ExerciseMatcher,
    MatchResult,
    get_matcher,
    resolve_exercise,
    search_exercises,
)
from .models import (
    EndCondition,
    RepeatGroup,
    Target,
    Workout,
    WorkoutSegment,
    WorkoutStep,
)
from .serializer import WorkoutSerializer

__all__ = [
    "EndCondition",
    "EndConditionType",
    "ExerciseMatcher",
    "IntensityType",
    "MatchResult",
    "RepeatBuilder",
    "RepeatGroup",
    "SportType",
    "StepType",
    "Target",
    "TargetType",
    "Workout",
    "WorkoutBuilder",
    "WorkoutClient",
    "WorkoutSegment",
    "WorkoutSerializer",
    "WorkoutStep",
    "get_matcher",
    "resolve_exercise",
    "search_exercises",
]
