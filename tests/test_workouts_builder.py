"""Tests for garmy.workouts.builder module."""

import pytest

from garmy.workouts.builder import RepeatBuilder, WorkoutBuilder
from garmy.workouts.constants import (
    EndConditionType,
    SportType,
    StepType,
    TargetType,
)
from garmy.workouts.models import RepeatGroup, Workout, WorkoutStep


class TestWorkoutBuilder:
    """Test cases for WorkoutBuilder class."""

    def test_builder_initialization(self):
        """Test WorkoutBuilder initialization."""
        builder = WorkoutBuilder("Test Workout", SportType.CYCLING)

        assert builder._name == "Test Workout"
        assert builder._sport_type == SportType.CYCLING
        assert builder._description is None
        assert builder._steps == []

    def test_builder_default_sport_type(self):
        """Test WorkoutBuilder defaults to cycling."""
        builder = WorkoutBuilder("Test")
        assert builder._sport_type == SportType.CYCLING

    def test_with_description(self):
        """Test with_description method."""
        builder = WorkoutBuilder("Test")
        result = builder.with_description("A great workout")

        assert result is builder  # Returns self for chaining
        assert builder._description == "A great workout"

    def test_warmup_with_time(self):
        """Test warmup method with time."""
        builder = WorkoutBuilder("Test")
        result = builder.warmup(minutes=10)

        assert result is builder
        assert len(builder._steps) == 1

        step = builder._steps[0]
        assert step.step_type == StepType.WARMUP
        assert step.end_condition.condition_type == EndConditionType.TIME
        assert step.end_condition.value == 600  # 10 minutes

    def test_warmup_with_target_power(self):
        """Test warmup with power target."""
        builder = WorkoutBuilder("Test")
        builder.warmup(minutes=10, target_power=(50, 60))

        step = builder._steps[0]
        assert step.target.target_type == TargetType.POWER_ZONE
        assert step.target.value_low == 50
        assert step.target.value_high == 60

    def test_interval_with_target_hr(self):
        """Test interval with heart rate target."""
        builder = WorkoutBuilder("Test")
        builder.interval(minutes=5, target_hr=(75, 85))

        step = builder._steps[0]
        assert step.step_type == StepType.INTERVAL
        assert step.target.target_type == TargetType.HEART_RATE_ZONE
        assert step.target.value_low == 75
        assert step.target.value_high == 85

    def test_interval_with_cadence(self):
        """Test interval with cadence target."""
        builder = WorkoutBuilder("Test")
        builder.interval(minutes=5, target_cadence=(85, 95))

        step = builder._steps[0]
        assert step.target.target_type == TargetType.CADENCE_ZONE
        assert step.target.value_low == 85
        assert step.target.value_high == 95

    def test_recovery(self):
        """Test recovery method."""
        builder = WorkoutBuilder("Test")
        builder.recovery(minutes=2)

        step = builder._steps[0]
        assert step.step_type == StepType.RECOVERY
        assert step.end_condition.value == 120

    def test_rest(self):
        """Test rest method."""
        builder = WorkoutBuilder("Test")
        builder.rest(seconds=30)

        step = builder._steps[0]
        assert step.step_type == StepType.REST
        assert step.end_condition.value == 30

    def test_cooldown(self):
        """Test cooldown method."""
        builder = WorkoutBuilder("Test")
        builder.cooldown(minutes=10)

        step = builder._steps[0]
        assert step.step_type == StepType.COOLDOWN

    def test_lap_button_end_condition(self):
        """Test step with lap button end condition."""
        builder = WorkoutBuilder("Test")
        builder.warmup(lap_button=True)

        step = builder._steps[0]
        assert step.end_condition.condition_type == EndConditionType.LAP_BUTTON

    def test_distance_km(self):
        """Test step with distance in km."""
        builder = WorkoutBuilder("Test")
        builder.interval(distance_km=5)

        step = builder._steps[0]
        assert step.end_condition.condition_type == EndConditionType.DISTANCE
        assert step.end_condition.value == 5000

    def test_distance_miles(self):
        """Test step with distance in miles."""
        builder = WorkoutBuilder("Test")
        builder.interval(distance_miles=1)

        step = builder._steps[0]
        assert step.end_condition.condition_type == EndConditionType.DISTANCE
        assert step.end_condition.value == pytest.approx(1609.344, rel=0.01)

    def test_step_description(self):
        """Test step with description."""
        builder = WorkoutBuilder("Test")
        builder.interval(minutes=5, description="Push hard!")

        step = builder._steps[0]
        assert step.description == "Push hard!"

    def test_generic_step_method(self):
        """Test generic step method."""
        builder = WorkoutBuilder("Test")
        builder.step(StepType.INTERVAL, minutes=5, target_power=(90, 95))

        step = builder._steps[0]
        assert step.step_type == StepType.INTERVAL
        assert step.target.value_low == 90

    def test_add_step(self):
        """Test add_step method with pre-built step."""
        builder = WorkoutBuilder("Test")
        step = WorkoutStep(step_type=StepType.WARMUP)

        result = builder.add_step(step)

        assert result is builder
        assert builder._steps[0] is step

    def test_build(self):
        """Test build method creates Workout object."""
        workout = (
            WorkoutBuilder("Test Workout", SportType.RUNNING)
            .with_description("My description")
            .warmup(minutes=10)
            .interval(minutes=20)
            .cooldown(minutes=10)
            .build()
        )

        assert isinstance(workout, Workout)
        assert workout.name == "Test Workout"
        assert workout.sport_type == SportType.RUNNING
        assert workout.description == "My description"
        assert len(workout.steps) == 3

    def test_full_workout_chain(self):
        """Test full workout building with chained methods."""
        workout = (
            WorkoutBuilder("Sweet Spot 2x20", SportType.CYCLING)
            .with_description("Sweet spot training")
            .warmup(minutes=15, target_power=(50, 65))
            .interval(minutes=20, target_power=(88, 93))
            .recovery(minutes=5, target_power=(40, 50))
            .interval(minutes=20, target_power=(88, 93))
            .cooldown(minutes=10, target_power=(40, 55))
            .build()
        )

        assert workout.name == "Sweet Spot 2x20"
        assert len(workout.steps) == 5
        assert workout.steps[0].step_type == StepType.WARMUP
        assert workout.steps[1].step_type == StepType.INTERVAL
        assert workout.steps[4].step_type == StepType.COOLDOWN


class TestRepeatBuilder:
    """Test cases for RepeatBuilder class."""

    def test_repeat_builder_initialization(self):
        """Test RepeatBuilder initialization."""
        parent = WorkoutBuilder("Test")
        repeat_builder = RepeatBuilder(parent, 3)

        assert repeat_builder._parent is parent
        assert repeat_builder._iterations == 3
        assert repeat_builder._steps == []

    def test_repeat_interval(self):
        """Test adding interval to repeat group."""
        parent = WorkoutBuilder("Test")
        repeat_builder = parent.repeat(3)

        result = repeat_builder.interval(minutes=5)

        assert result is repeat_builder  # Returns self for chaining
        assert len(repeat_builder._steps) == 1
        assert repeat_builder._steps[0].step_type == StepType.INTERVAL

    def test_repeat_recovery(self):
        """Test adding recovery to repeat group."""
        parent = WorkoutBuilder("Test")
        repeat_builder = parent.repeat(3)

        repeat_builder.recovery(minutes=2)

        assert len(repeat_builder._steps) == 1
        assert repeat_builder._steps[0].step_type == StepType.RECOVERY

    def test_repeat_rest(self):
        """Test adding rest to repeat group."""
        parent = WorkoutBuilder("Test")
        repeat_builder = parent.repeat(3)

        repeat_builder.rest(seconds=30)

        assert len(repeat_builder._steps) == 1
        assert repeat_builder._steps[0].step_type == StepType.REST

    def test_repeat_generic_step(self):
        """Test adding generic step to repeat group."""
        parent = WorkoutBuilder("Test")
        repeat_builder = parent.repeat(3)

        repeat_builder.step(StepType.INTERVAL, minutes=5)

        assert repeat_builder._steps[0].step_type == StepType.INTERVAL

    def test_end_repeat_returns_parent(self):
        """Test end_repeat returns parent builder."""
        parent = WorkoutBuilder("Test")
        repeat_builder = parent.repeat(3)
        repeat_builder.interval(minutes=5)

        result = repeat_builder.end_repeat()

        assert result is parent

    def test_end_repeat_adds_repeat_group(self):
        """Test end_repeat adds RepeatGroup to parent."""
        parent = WorkoutBuilder("Test")
        parent.repeat(3).interval(minutes=5).recovery(minutes=2).end_repeat()

        assert len(parent._steps) == 1
        assert isinstance(parent._steps[0], RepeatGroup)
        assert parent._steps[0].iterations == 3
        assert len(parent._steps[0].steps) == 2

    def test_repeat_with_targets(self):
        """Test repeat steps with targets."""
        parent = WorkoutBuilder("Test")
        parent.repeat(3).interval(minutes=5, target_power=(90, 95)).recovery(
            minutes=2, target_hr=(50, 60)
        ).end_repeat()

        repeat_group = parent._steps[0]
        assert repeat_group.steps[0].target.target_type == TargetType.POWER_ZONE
        assert repeat_group.steps[1].target.target_type == TargetType.HEART_RATE_ZONE

    def test_full_workout_with_repeat(self):
        """Test building full workout with repeat group."""
        workout = (
            WorkoutBuilder("VO2max Intervals", SportType.CYCLING)
            .warmup(minutes=15)
            .repeat(5)
            .interval(minutes=3, target_power=(105, 120))
            .recovery(minutes=3, target_power=(40, 50))
            .end_repeat()
            .cooldown(minutes=10)
            .build()
        )

        assert len(workout.steps) == 3  # warmup, repeat, cooldown
        assert isinstance(workout.steps[1], RepeatGroup)
        assert workout.steps[1].iterations == 5
        assert len(workout.steps[1].steps) == 2


class TestWorkoutBuilderIntegration:
    """Integration tests for workout building."""

    def test_complex_workout(self):
        """Test building a complex workout with multiple elements."""
        workout = (
            WorkoutBuilder("Race Prep", SportType.RUNNING)
            .with_description("Pre-race sharpening workout")
            .warmup(minutes=15, target_hr=(60, 70))
            .repeat(3)
            .interval(distance_km=1, target_hr=(85, 90), description="Fast km")
            .recovery(minutes=2, target_hr=(60, 65))
            .end_repeat()
            .rest(minutes=5)
            .repeat(6)
            .interval(seconds=30, target_hr=(90, 95), description="Strides")
            .recovery(seconds=90)
            .end_repeat()
            .cooldown(minutes=10, target_hr=(55, 65))
            .build()
        )

        assert workout.name == "Race Prep"
        assert workout.sport_type == SportType.RUNNING
        assert len(workout.steps) == 5  # warmup, repeat, rest, repeat, cooldown

        # First repeat group
        first_repeat = workout.steps[1]
        assert isinstance(first_repeat, RepeatGroup)
        assert first_repeat.iterations == 3
        assert first_repeat.steps[0].description == "Fast km"

        # Second repeat group
        second_repeat = workout.steps[3]
        assert isinstance(second_repeat, RepeatGroup)
        assert second_repeat.iterations == 6
