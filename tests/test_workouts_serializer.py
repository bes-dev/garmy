"""Tests for garmy.workouts.serializer module."""

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
from garmy.workouts.serializer import WorkoutSerializer


class TestWorkoutSerializerToApiFormat:
    """Test cases for WorkoutSerializer.to_api_format."""

    def test_basic_workout(self):
        """Test serializing a basic workout."""
        workout = Workout(
            name="Test Workout",
            sport_type=SportType.CYCLING,
            description="Test description",
        )
        warmup = WorkoutStep(
            step_type=StepType.WARMUP,
            end_condition=EndCondition.time_minutes(10),
        )
        workout.add_step(warmup)

        result = WorkoutSerializer.to_api_format(workout)

        assert result["workoutName"] == "Test Workout"
        assert result["description"] == "Test description"
        # Note: We only use sportTypeKey (not ID) because Garmin's IDs are inconsistent
        assert result["sportType"]["sportTypeKey"] == "cycling"
        assert len(result["workoutSegments"]) == 1
        assert len(result["workoutSegments"][0]["workoutSteps"]) == 1

    def test_step_serialization(self):
        """Test step serialization details."""
        workout = Workout(name="Test")
        step = WorkoutStep(
            step_type=StepType.INTERVAL,
            end_condition=EndCondition.time(300),
            target=Target.power_zone(88, 93),
            description="Main set",
        )
        workout.add_step(step)

        result = WorkoutSerializer.to_api_format(workout)
        step_data = result["workoutSegments"][0]["workoutSteps"][0]

        assert step_data["type"] == "ExecutableStepDTO"
        assert step_data["stepOrder"] == 1
        assert step_data["stepType"]["stepTypeId"] == 3  # INTERVAL
        assert step_data["stepType"]["stepTypeKey"] == "interval"
        assert step_data["endCondition"]["conditionTypeId"] == 2  # TIME
        # endConditionValue is at step level (not inside endCondition)
        assert step_data["endConditionValue"] == 300
        # Garmin uses workoutTargetTypeId (not targetTypeId)
        assert step_data["targetType"]["workoutTargetTypeId"] == 2  # POWER_ZONE
        assert step_data["targetType"]["targetValueOne"] == 88
        assert step_data["targetType"]["targetValueTwo"] == 93
        assert step_data["description"] == "Main set"

    def test_repeat_group_serialization(self):
        """Test repeat group serialization."""
        workout = Workout(name="Test")
        repeat = RepeatGroup(iterations=3)
        repeat.add_step(
            WorkoutStep(
                step_type=StepType.INTERVAL,
                end_condition=EndCondition.time_minutes(5),
            )
        )
        repeat.add_step(
            WorkoutStep(
                step_type=StepType.RECOVERY,
                end_condition=EndCondition.time_minutes(2),
            )
        )
        workout.add_step(repeat)

        result = WorkoutSerializer.to_api_format(workout)
        repeat_data = result["workoutSegments"][0]["workoutSteps"][0]

        assert repeat_data["type"] == "RepeatGroupDTO"
        assert repeat_data["stepOrder"] == 1
        # Garmin uses numberOfIterations for repeat groups
        assert repeat_data["numberOfIterations"] == 3
        assert repeat_data["endConditionValue"] == 3.0
        assert len(repeat_data["workoutSteps"]) == 2

    def test_step_ordering(self):
        """Test steps have correct ordering."""
        workout = Workout(name="Test")
        workout.add_step(WorkoutStep(step_type=StepType.WARMUP))
        workout.add_step(WorkoutStep(step_type=StepType.INTERVAL))
        workout.add_step(WorkoutStep(step_type=StepType.COOLDOWN))

        result = WorkoutSerializer.to_api_format(workout)
        steps = result["workoutSegments"][0]["workoutSteps"]

        assert steps[0]["stepOrder"] == 1
        assert steps[1]["stepOrder"] == 2
        assert steps[2]["stepOrder"] == 3

    def test_workout_with_id(self):
        """Test serializing workout with existing ID."""
        workout = Workout(
            name="Test",
            workout_id=12345,
            owner_id=67890,
        )

        result = WorkoutSerializer.to_api_format(workout)

        assert result["workoutId"] == 12345
        assert result["ownerId"] == 67890

    def test_no_target_serialization(self):
        """Test step with no target."""
        workout = Workout(name="Test")
        step = WorkoutStep(
            step_type=StepType.REST,
            target=Target.no_target(),
        )
        workout.add_step(step)

        result = WorkoutSerializer.to_api_format(workout)
        step_data = result["workoutSegments"][0]["workoutSteps"][0]

        # Garmin uses workoutTargetTypeId (not targetTypeId)
        assert step_data["targetType"]["workoutTargetTypeId"] == 1  # NO_TARGET

    def test_lap_button_serialization(self):
        """Test step with lap button end condition."""
        workout = Workout(name="Test")
        step = WorkoutStep(
            step_type=StepType.WARMUP,
            end_condition=EndCondition.lap_button(),
        )
        workout.add_step(step)

        result = WorkoutSerializer.to_api_format(workout)
        step_data = result["workoutSegments"][0]["workoutSteps"][0]

        assert step_data["endCondition"]["conditionTypeId"] == 1  # LAP_BUTTON
        assert "conditionValue" not in step_data["endCondition"]


class TestWorkoutSerializerFromApiFormat:
    """Test cases for WorkoutSerializer.from_api_format."""

    def test_basic_workout_parsing(self):
        """Test parsing a basic workout from API format."""
        api_data = {
            "workoutId": 12345,
            "workoutName": "Test Workout",
            "description": "Test description",
            "sportType": {
                "sportTypeId": 2,
                "sportTypeKey": "cycling",
            },
            "ownerId": 67890,
            "workoutSegments": [
                {
                    "segmentOrder": 1,
                    "sportType": {"sportTypeId": 2, "sportTypeKey": "cycling"},
                    "workoutSteps": [],
                }
            ],
        }

        workout = WorkoutSerializer.from_api_format(api_data)

        assert workout.workout_id == 12345
        assert workout.name == "Test Workout"
        assert workout.description == "Test description"
        assert workout.sport_type == SportType.CYCLING
        assert workout.owner_id == 67890

    def test_step_parsing(self):
        """Test parsing steps from API format."""
        api_data = {
            "workoutName": "Test",
            "sportType": {"sportTypeId": 2, "sportTypeKey": "cycling"},
            "workoutSegments": [
                {
                    "segmentOrder": 1,
                    "sportType": {"sportTypeId": 2, "sportTypeKey": "cycling"},
                    "workoutSteps": [
                        {
                            "type": "ExecutableStepDTO",
                            "stepOrder": 1,
                            "stepType": {
                                "stepTypeId": 1,
                                "stepTypeKey": "warmup",
                            },
                            "intensityType": {
                                "intensityTypeId": 3,
                                "intensityTypeKey": "warmup",
                            },
                            "endCondition": {
                                "conditionTypeId": 2,
                                "conditionTypeKey": "time",
                                "conditionValue": 600,
                            },
                            "targetType": {
                                "targetTypeId": 2,
                                "targetTypeKey": "power.zone",
                                "targetValueLow": 50,
                                "targetValueHigh": 60,
                            },
                            "description": "Easy warmup",
                        }
                    ],
                }
            ],
        }

        workout = WorkoutSerializer.from_api_format(api_data)

        assert len(workout.steps) == 1
        step = workout.steps[0]
        assert step.step_type == StepType.WARMUP
        assert step.end_condition.condition_type == EndConditionType.TIME
        assert step.end_condition.value == 600
        assert step.target.target_type == TargetType.POWER_ZONE
        assert step.target.value_low == 50
        assert step.target.value_high == 60
        assert step.description == "Easy warmup"

    def test_repeat_group_parsing(self):
        """Test parsing repeat groups from API format."""
        api_data = {
            "workoutName": "Test",
            "sportType": {"sportTypeId": 2, "sportTypeKey": "cycling"},
            "workoutSegments": [
                {
                    "segmentOrder": 1,
                    "sportType": {"sportTypeId": 2, "sportTypeKey": "cycling"},
                    "workoutSteps": [
                        {
                            "type": "RepeatGroupDTO",
                            "stepOrder": 1,
                            "endCondition": {
                                "conditionTypeId": 7,
                                "conditionTypeKey": "iterations",
                                "conditionValue": 3,
                            },
                            "workoutSteps": [
                                {
                                    "type": "ExecutableStepDTO",
                                    "stepOrder": 1,
                                    "stepType": {
                                        "stepTypeId": 3,
                                        "stepTypeKey": "interval",
                                    },
                                    "intensityType": {
                                        "intensityTypeId": 6,
                                        "intensityTypeKey": "interval",
                                    },
                                    "endCondition": {
                                        "conditionTypeId": 2,
                                        "conditionValue": 300,
                                    },
                                    "targetType": {"targetTypeId": 1},
                                },
                                {
                                    "type": "ExecutableStepDTO",
                                    "stepOrder": 2,
                                    "stepType": {
                                        "stepTypeId": 4,
                                        "stepTypeKey": "recovery",
                                    },
                                    "intensityType": {
                                        "intensityTypeId": 5,
                                        "intensityTypeKey": "recovery",
                                    },
                                    "endCondition": {
                                        "conditionTypeId": 2,
                                        "conditionValue": 120,
                                    },
                                    "targetType": {"targetTypeId": 1},
                                },
                            ],
                        }
                    ],
                }
            ],
        }

        workout = WorkoutSerializer.from_api_format(api_data)

        assert len(workout.steps) == 1
        repeat = workout.steps[0]
        assert isinstance(repeat, RepeatGroup)
        assert repeat.iterations == 3
        assert len(repeat.steps) == 2
        assert repeat.steps[0].step_type == StepType.INTERVAL
        assert repeat.steps[1].step_type == StepType.RECOVERY

    def test_unknown_sport_type(self):
        """Test parsing with unknown sport type defaults to OTHER."""
        api_data = {
            "workoutName": "Test",
            "sportType": {"sportTypeId": 9999, "sportTypeKey": "unknown"},
            "workoutSegments": [],
        }

        workout = WorkoutSerializer.from_api_format(api_data)

        assert workout.sport_type == SportType.OTHER

    def test_missing_fields(self):
        """Test parsing with missing optional fields."""
        api_data = {
            "workoutName": "Test",
            "sportType": {"sportTypeId": 2},
            "workoutSegments": [],
        }

        workout = WorkoutSerializer.from_api_format(api_data)

        assert workout.name == "Test"
        assert workout.description is None
        assert workout.workout_id is None


class TestSmartRepeatSerialization:
    """Test cases for smart_repeat (skip last rest) feature."""

    def test_serialize_smart_repeat_true(self):
        """Test serialization with smart_repeat=True produces correct API fields."""
        workout = Workout(name="Test")
        repeat = RepeatGroup(iterations=3, smart_repeat=True)
        repeat.add_step(
            WorkoutStep(
                step_type=StepType.INTERVAL,
                end_condition=EndCondition.time_minutes(5),
            )
        )
        repeat.add_step(
            WorkoutStep(
                step_type=StepType.REST,
                end_condition=EndCondition.time_minutes(1),
            )
        )
        workout.add_step(repeat)

        result = WorkoutSerializer.to_api_format(workout)
        repeat_data = result["workoutSegments"][0]["workoutSteps"][0]

        assert repeat_data["skipLastRestStep"] is True
        assert repeat_data["smartRepeat"] is False

    def test_serialize_smart_repeat_false_default(self):
        """Test serialization with smart_repeat=False (default) produces correct API fields."""
        workout = Workout(name="Test")
        repeat = RepeatGroup(iterations=3)
        repeat.add_step(
            WorkoutStep(
                step_type=StepType.INTERVAL,
                end_condition=EndCondition.time_minutes(5),
            )
        )
        workout.add_step(repeat)

        result = WorkoutSerializer.to_api_format(workout)
        repeat_data = result["workoutSegments"][0]["workoutSteps"][0]

        assert repeat_data["skipLastRestStep"] is False
        assert repeat_data["smartRepeat"] is False

    def test_parse_skip_last_rest_step_true(self):
        """Test parsing API response with skipLastRestStep=true."""
        api_data = {
            "workoutName": "Test",
            "sportType": {"sportTypeId": 2, "sportTypeKey": "cycling"},
            "workoutSegments": [
                {
                    "segmentOrder": 1,
                    "sportType": {"sportTypeId": 2, "sportTypeKey": "cycling"},
                    "workoutSteps": [
                        {
                            "type": "RepeatGroupDTO",
                            "stepOrder": 1,
                            "numberOfIterations": 3,
                            "skipLastRestStep": True,
                            "smartRepeat": False,
                            "endCondition": {
                                "conditionTypeId": 7,
                                "conditionTypeKey": "iterations",
                            },
                            "endConditionValue": 3.0,
                            "workoutSteps": [
                                {
                                    "type": "ExecutableStepDTO",
                                    "stepOrder": 1,
                                    "stepType": {
                                        "stepTypeId": 3,
                                        "stepTypeKey": "interval",
                                    },
                                    "intensityType": {
                                        "intensityTypeId": 6,
                                        "intensityTypeKey": "interval",
                                    },
                                    "endCondition": {
                                        "conditionTypeId": 2,
                                        "conditionValue": 300,
                                    },
                                    "targetType": {"targetTypeId": 1},
                                },
                            ],
                        }
                    ],
                }
            ],
        }

        workout = WorkoutSerializer.from_api_format(api_data)

        repeat = workout.steps[0]
        assert isinstance(repeat, RepeatGroup)
        assert repeat.smart_repeat is True

    def test_parse_skip_last_rest_step_missing(self):
        """Test parsing API response without skipLastRestStep defaults to False."""
        api_data = {
            "workoutName": "Test",
            "sportType": {"sportTypeId": 2, "sportTypeKey": "cycling"},
            "workoutSegments": [
                {
                    "segmentOrder": 1,
                    "sportType": {"sportTypeId": 2, "sportTypeKey": "cycling"},
                    "workoutSteps": [
                        {
                            "type": "RepeatGroupDTO",
                            "stepOrder": 1,
                            "numberOfIterations": 2,
                            "endCondition": {
                                "conditionTypeId": 7,
                                "conditionTypeKey": "iterations",
                            },
                            "workoutSteps": [
                                {
                                    "type": "ExecutableStepDTO",
                                    "stepOrder": 1,
                                    "stepType": {
                                        "stepTypeId": 3,
                                        "stepTypeKey": "interval",
                                    },
                                    "intensityType": {
                                        "intensityTypeId": 6,
                                        "intensityTypeKey": "interval",
                                    },
                                    "endCondition": {
                                        "conditionTypeId": 2,
                                        "conditionValue": 300,
                                    },
                                    "targetType": {"targetTypeId": 1},
                                },
                            ],
                        }
                    ],
                }
            ],
        }

        workout = WorkoutSerializer.from_api_format(api_data)

        repeat = workout.steps[0]
        assert isinstance(repeat, RepeatGroup)
        assert repeat.smart_repeat is False

    def test_smart_repeat_round_trip(self):
        """Test smart_repeat=True survives serialization round trip."""
        original = Workout(name="Smart Repeat Test")
        repeat = RepeatGroup(iterations=3, smart_repeat=True)
        repeat.add_step(
            WorkoutStep(
                step_type=StepType.INTERVAL,
                end_condition=EndCondition.time_minutes(5),
            )
        )
        repeat.add_step(
            WorkoutStep(
                step_type=StepType.REST,
                end_condition=EndCondition.time_minutes(1),
            )
        )
        original.add_step(repeat)

        api_format = WorkoutSerializer.to_api_format(original)
        restored = WorkoutSerializer.from_api_format(api_format)

        restored_repeat = restored.steps[0]
        assert isinstance(restored_repeat, RepeatGroup)
        assert restored_repeat.smart_repeat is True
        assert restored_repeat.iterations == 3


class TestWorkoutSerializerRoundTrip:
    """Test round-trip serialization/deserialization."""

    def test_simple_workout_round_trip(self):
        """Test simple workout survives serialization round trip."""
        original = Workout(
            name="Round Trip Test",
            sport_type=SportType.RUNNING,
            description="Testing round trip",
        )
        original.add_step(
            WorkoutStep(
                step_type=StepType.WARMUP,
                end_condition=EndCondition.time_minutes(10),
                target=Target.heart_rate_zone(60, 70),
            )
        )
        original.add_step(
            WorkoutStep(
                step_type=StepType.INTERVAL,
                end_condition=EndCondition.distance_km(5),
                target=Target.power_zone(85, 90),
            )
        )

        # Serialize and deserialize
        api_format = WorkoutSerializer.to_api_format(original)
        restored = WorkoutSerializer.from_api_format(api_format)

        # Verify
        assert restored.name == original.name
        assert restored.sport_type == original.sport_type
        assert restored.description == original.description
        assert len(restored.steps) == len(original.steps)

        # Check first step
        assert restored.steps[0].step_type == StepType.WARMUP
        assert restored.steps[0].end_condition.value == 600

        # Check second step
        assert restored.steps[1].step_type == StepType.INTERVAL
        assert restored.steps[1].end_condition.value == 5000

    def test_repeat_group_round_trip(self):
        """Test workout with repeat group survives round trip."""
        original = Workout(name="Repeat Test")

        repeat = RepeatGroup(iterations=4)
        repeat.add_step(
            WorkoutStep(
                step_type=StepType.INTERVAL,
                end_condition=EndCondition.time_minutes(3),
            )
        )
        repeat.add_step(
            WorkoutStep(
                step_type=StepType.RECOVERY,
                end_condition=EndCondition.time_minutes(2),
            )
        )
        original.add_step(repeat)

        # Serialize and deserialize
        api_format = WorkoutSerializer.to_api_format(original)
        restored = WorkoutSerializer.from_api_format(api_format)

        # Verify
        assert len(restored.steps) == 1
        restored_repeat = restored.steps[0]
        assert isinstance(restored_repeat, RepeatGroup)
        assert restored_repeat.iterations == 4
        assert len(restored_repeat.steps) == 2
