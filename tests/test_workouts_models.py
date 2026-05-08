"""Tests for garmy.workouts.models module."""

import pytest

from garmy.workouts.constants import (
    EndConditionType,
    IntensityType,
    SportType,
    StepType,
    TargetType,
)
from garmy.workouts.models import (
    EndCondition,
    RepeatGroup,
    Target,
    Workout,
    WorkoutStep,
)


class TestEndCondition:
    """Test cases for EndCondition dataclass."""

    def test_end_condition_default(self):
        """Test EndCondition defaults to lap button."""
        condition = EndCondition()
        assert condition.condition_type == EndConditionType.LAP_BUTTON
        assert condition.value is None

    def test_end_condition_time(self):
        """Test EndCondition.time factory method."""
        condition = EndCondition.time(300)
        assert condition.condition_type == EndConditionType.TIME
        assert condition.value == 300

    def test_end_condition_time_minutes(self):
        """Test EndCondition.time_minutes factory method."""
        condition = EndCondition.time_minutes(5)
        assert condition.condition_type == EndConditionType.TIME
        assert condition.value == 300  # 5 minutes = 300 seconds

    def test_end_condition_distance(self):
        """Test EndCondition.distance factory method."""
        condition = EndCondition.distance(1000)
        assert condition.condition_type == EndConditionType.DISTANCE
        assert condition.value == 1000

    def test_end_condition_distance_km(self):
        """Test EndCondition.distance_km factory method."""
        condition = EndCondition.distance_km(5)
        assert condition.condition_type == EndConditionType.DISTANCE
        assert condition.value == 5000  # 5 km = 5000 meters

    def test_end_condition_distance_miles(self):
        """Test EndCondition.distance_miles factory method."""
        condition = EndCondition.distance_miles(1)
        assert condition.condition_type == EndConditionType.DISTANCE
        assert condition.value == pytest.approx(1609.344, rel=0.01)

    def test_end_condition_lap_button(self):
        """Test EndCondition.lap_button factory method."""
        condition = EndCondition.lap_button()
        assert condition.condition_type == EndConditionType.LAP_BUTTON
        assert condition.value is None

    def test_end_condition_iterations(self):
        """Test EndCondition.iterations factory method."""
        condition = EndCondition.iterations(3)
        assert condition.condition_type == EndConditionType.ITERATIONS
        assert condition.value == 3.0

    def test_end_condition_reps(self):
        """Test EndCondition.reps factory method."""
        condition = EndCondition.reps(10)
        assert condition.condition_type == EndConditionType.REPS
        assert condition.value == 10.0


class TestTarget:
    """Test cases for Target dataclass."""

    def test_target_default(self):
        """Test Target defaults to no target."""
        target = Target()
        assert target.target_type == TargetType.NO_TARGET
        assert target.value_low is None
        assert target.value_high is None
        assert target.zone_number is None

    def test_target_no_target(self):
        """Test Target.no_target factory method."""
        target = Target.no_target()
        assert target.target_type == TargetType.NO_TARGET

    def test_target_power_zone(self):
        """Test Target.power_zone factory method."""
        target = Target.power_zone(88, 93)
        assert target.target_type == TargetType.POWER_ZONE
        assert target.value_low == 88
        assert target.value_high == 93

    def test_target_heart_rate_zone(self):
        """Test Target.heart_rate_zone factory method."""
        target = Target.heart_rate_zone(70, 80)
        assert target.target_type == TargetType.HEART_RATE_ZONE
        assert target.value_low == 70
        assert target.value_high == 80

    def test_target_cadence_zone(self):
        """Test Target.cadence_zone factory method."""
        target = Target.cadence_zone(85, 95)
        assert target.target_type == TargetType.CADENCE_ZONE
        assert target.value_low == 85
        assert target.value_high == 95

    def test_target_pace_zone(self):
        """Test Target.pace_zone factory method."""
        target = Target.pace_zone(240, 270)  # 4:00-4:30 min/km
        assert target.target_type == TargetType.PACE_ZONE
        assert target.value_low == 240
        assert target.value_high == 270


class TestWorkoutStep:
    """Test cases for WorkoutStep dataclass."""

    def test_workout_step_default(self):
        """Test WorkoutStep default values."""
        step = WorkoutStep()
        assert step.step_type == StepType.OTHER
        assert step.end_condition.condition_type == EndConditionType.LAP_BUTTON
        assert step.target.target_type == TargetType.NO_TARGET
        assert step.description is None
        assert step.step_order is None

    def test_workout_step_with_values(self):
        """Test WorkoutStep with custom values."""
        step = WorkoutStep(
            step_type=StepType.INTERVAL,
            end_condition=EndCondition.time_minutes(5),
            target=Target.power_zone(90, 95),
            description="Hard interval",
        )
        assert step.step_type == StepType.INTERVAL
        assert step.end_condition.value == 300
        assert step.target.value_low == 90
        assert step.description == "Hard interval"

    def test_workout_step_intensity_auto_set(self):
        """Test WorkoutStep auto-sets intensity based on step type."""
        warmup = WorkoutStep(step_type=StepType.WARMUP)
        assert warmup.intensity == IntensityType.WARMUP

        cooldown = WorkoutStep(step_type=StepType.COOLDOWN)
        assert cooldown.intensity == IntensityType.COOLDOWN

        recovery = WorkoutStep(step_type=StepType.RECOVERY)
        assert recovery.intensity == IntensityType.RECOVERY


class TestRepeatGroup:
    """Test cases for RepeatGroup dataclass."""

    def test_repeat_group_default(self):
        """Test RepeatGroup default values."""
        group = RepeatGroup()
        assert group.iterations == 1
        assert group.steps == []
        assert group.step_order is None

    def test_repeat_group_with_iterations(self):
        """Test RepeatGroup with custom iterations."""
        group = RepeatGroup(iterations=5)
        assert group.iterations == 5

    def test_repeat_group_add_step(self):
        """Test RepeatGroup.add_step method."""
        group = RepeatGroup(iterations=3)
        step = WorkoutStep(step_type=StepType.INTERVAL)

        result = group.add_step(step)

        assert result is group  # Returns self for chaining
        assert len(group.steps) == 1
        assert group.steps[0] == step

    def test_repeat_group_multiple_steps(self):
        """Test RepeatGroup with multiple steps."""
        group = RepeatGroup(iterations=2)
        interval = WorkoutStep(step_type=StepType.INTERVAL)
        recovery = WorkoutStep(step_type=StepType.RECOVERY)

        group.add_step(interval).add_step(recovery)

        assert len(group.steps) == 2
        assert group.steps[0].step_type == StepType.INTERVAL
        assert group.steps[1].step_type == StepType.RECOVERY


class TestWorkout:
    """Test cases for Workout dataclass."""

    def test_workout_default(self):
        """Test Workout default values."""
        workout = Workout(name="Test Workout")
        assert workout.name == "Test Workout"
        assert workout.sport_type == SportType.CYCLING
        assert workout.description is None
        assert workout.steps == []
        assert workout.workout_id is None
        assert workout.owner_id is None

    def test_workout_with_values(self):
        """Test Workout with custom values."""
        workout = Workout(
            name="My Workout",
            sport_type=SportType.RUNNING,
            description="A great workout",
            workout_id=12345,
        )
        assert workout.name == "My Workout"
        assert workout.sport_type == SportType.RUNNING
        assert workout.description == "A great workout"
        assert workout.workout_id == 12345

    def test_workout_add_step(self):
        """Test Workout.add_step method."""
        workout = Workout(name="Test")
        step = WorkoutStep(step_type=StepType.WARMUP)

        result = workout.add_step(step)

        assert result is workout  # Returns self for chaining
        assert len(workout.steps) == 1
        assert workout.steps[0] == step

    def test_workout_str(self):
        """Test Workout string representation."""
        workout = Workout(
            name="Test Workout",
            sport_type=SportType.CYCLING,
            description="Test description",
        )
        workout.add_step(WorkoutStep(step_type=StepType.WARMUP))
        workout.add_step(WorkoutStep(step_type=StepType.INTERVAL))

        result = str(workout)

        assert "Test Workout" in result
        assert "cycling" in result

    def test_workout_to_dict(self):
        """Test Workout.to_dict method."""
        workout = Workout(
            name="Test Workout",
            sport_type=SportType.RUNNING,
            description="Test",
            workout_id=123,
        )

        result = workout.to_dict()

        assert result["name"] == "Test Workout"
        assert result["sport_type"] == "running"
        assert result["description"] == "Test"
        assert result["workout_id"] == 123

    def test_workout_with_repeat_group(self):
        """Test Workout with repeat groups affects step count calculation."""
        workout = Workout(name="Test")
        workout.add_step(WorkoutStep(step_type=StepType.WARMUP))

        repeat = RepeatGroup(iterations=3)
        repeat.add_step(WorkoutStep(step_type=StepType.INTERVAL))
        repeat.add_step(WorkoutStep(step_type=StepType.RECOVERY))
        workout.add_step(repeat)

        workout.add_step(WorkoutStep(step_type=StepType.COOLDOWN))

        # 3 top-level items: warmup, repeat, cooldown
        assert len(workout.steps) == 3
