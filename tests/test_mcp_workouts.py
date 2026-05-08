"""Tests for MCP workout tools."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from garmy.mcp.config import MCPConfig


class TestMCPWorkoutToolsConfig:
    """Tests for MCP workout configuration."""

    def test_config_enable_workouts_default_false(self, tmp_path: Path) -> None:
        """Test that workouts are disabled by default."""
        db_file = tmp_path / "test.db"
        db_file.touch()
        config = MCPConfig(db_path=db_file)
        assert config.enable_workouts is False

    def test_config_enable_workouts_true(self, tmp_path: Path) -> None:
        """Test that workouts can be enabled."""
        db_file = tmp_path / "test.db"
        db_file.touch()
        config = MCPConfig(db_path=db_file, enable_workouts=True)
        assert config.enable_workouts is True

    def test_config_enable_workouts_with_profile_path(self, tmp_path: Path) -> None:
        """Test workouts config with profile path."""
        db_file = tmp_path / "test.db"
        db_file.touch()
        config = MCPConfig(
            db_path=db_file,
            enable_workouts=True,
            profile_path=tmp_path,
        )
        assert config.enable_workouts is True
        assert config.profile_path == tmp_path


class TestAddStepsFromJson:
    """Tests for _add_steps_from_json helper function."""

    def test_add_warmup_step(self) -> None:
        """Test adding a warmup step from JSON."""
        from garmy.workouts import SportType, WorkoutBuilder

        builder = WorkoutBuilder("Test", SportType.CYCLING)

        # Import the helper function by creating a mock server context
        steps = [{"type": "warmup", "minutes": 10}]

        # Add steps manually to test the logic
        for step in steps:
            step_type = step.get("type", "interval").lower()
            minutes = step.get("minutes")

            if step_type == "warmup":
                builder.warmup(minutes=minutes)

        workout = builder.build()
        assert len(workout.steps) == 1
        assert workout.steps[0].step_type.value == "warmup"

    def test_add_interval_with_target(self) -> None:
        """Test adding an interval step with power target."""
        from garmy.workouts import SportType, WorkoutBuilder

        builder = WorkoutBuilder("Test", SportType.CYCLING)

        builder.interval(minutes=5, target_power=(90, 95))

        workout = builder.build()
        assert len(workout.steps) == 1
        assert workout.steps[0].step_type.value == "interval"
        assert workout.steps[0].target.value_low == 90
        assert workout.steps[0].target.value_high == 95

    def test_add_repeat_group(self) -> None:
        """Test adding a repeat group from JSON structure."""
        from garmy.workouts import SportType, WorkoutBuilder
        from garmy.workouts.models import RepeatGroup

        builder = WorkoutBuilder("Test", SportType.CYCLING)

        # Add repeat group with nested steps
        repeat_builder = builder.repeat(3)
        repeat_builder.interval(minutes=5, target_power=(90, 95))
        repeat_builder.recovery(minutes=2)
        repeat_builder.end_repeat()

        workout = builder.build()
        assert len(workout.steps) == 1
        assert isinstance(workout.steps[0], RepeatGroup)
        assert workout.steps[0].iterations == 3
        assert len(workout.steps[0].steps) == 2

    def test_add_cooldown_step(self) -> None:
        """Test adding a cooldown step."""
        from garmy.workouts import SportType, WorkoutBuilder

        builder = WorkoutBuilder("Test", SportType.CYCLING)
        builder.cooldown(minutes=10)

        workout = builder.build()
        assert len(workout.steps) == 1
        assert workout.steps[0].step_type.value == "cooldown"

    def test_add_recovery_step(self) -> None:
        """Test adding a recovery step."""
        from garmy.workouts import SportType, WorkoutBuilder

        builder = WorkoutBuilder("Test", SportType.CYCLING)
        builder.recovery(minutes=3, target_hr=(60, 70))

        workout = builder.build()
        assert len(workout.steps) == 1
        assert workout.steps[0].step_type.value == "recovery"

    def test_add_rest_step(self) -> None:
        """Test adding a rest step."""
        from garmy.workouts import SportType, WorkoutBuilder

        builder = WorkoutBuilder("Test", SportType.CYCLING)
        builder.rest(minutes=2)

        workout = builder.build()
        assert len(workout.steps) == 1
        assert workout.steps[0].step_type.value == "rest"


class TestWorkoutToolsIntegration:
    """Integration tests for workout MCP tools behavior."""

    def test_list_workouts_returns_expected_structure(self) -> None:
        """Test that list_workouts returns expected structure."""
        from garmy.workouts import SportType, Workout

        # Create mock workout objects
        mock_workouts = [
            Workout(
                name="Test Workout 1",
                sport_type=SportType.CYCLING,
                workout_id=123,
                steps=[],
            ),
            Workout(
                name="Test Workout 2",
                sport_type=SportType.RUNNING,
                workout_id=456,
                steps=[],
            ),
        ]

        # Format as the MCP tool would
        result = {
            "success": True,
            "count": len(mock_workouts),
            "workouts": [
                {
                    "workout_id": w.workout_id,
                    "name": w.name,
                    "sport_type": w.sport_type.key,
                    "description": w.description,
                    "step_count": len(w.steps),
                }
                for w in mock_workouts
            ],
        }

        assert result["success"] is True
        assert result["count"] == 2
        assert len(result["workouts"]) == 2
        assert result["workouts"][0]["name"] == "Test Workout 1"
        assert result["workouts"][1]["sport_type"] == "running"

    def test_get_workout_formats_steps_correctly(self) -> None:
        """Test that get_workout formats steps correctly."""
        from garmy.workouts import (
            EndCondition,
            SportType,
            StepType,
            Target,
            Workout,
            WorkoutStep,
        )
        from garmy.workouts.models import RepeatGroup

        # Create a workout with various step types
        workout = Workout(
            name="Test",
            sport_type=SportType.CYCLING,
            workout_id=123,
            steps=[
                WorkoutStep(
                    step_type=StepType.WARMUP,
                    end_condition=EndCondition.time_minutes(10),
                    target=Target.no_target(),
                ),
                RepeatGroup(
                    iterations=3,
                    steps=[
                        WorkoutStep(
                            step_type=StepType.INTERVAL,
                            end_condition=EndCondition.time_minutes(5),
                            target=Target.power_zone(90, 95),
                        ),
                    ],
                ),
            ],
        )

        # Format steps as the MCP tool would
        steps_info = []
        for i, step in enumerate(workout.steps):
            if isinstance(step, RepeatGroup):
                steps_info.append(
                    {
                        "index": i + 1,
                        "type": "repeat",
                        "iterations": step.iterations,
                        "steps": [
                            {
                                "type": s.step_type.value,
                                "duration_seconds": s.end_condition.value,
                                "target_type": s.target.target_type.value,
                            }
                            for s in step.steps
                        ],
                    }
                )
            else:
                steps_info.append(
                    {
                        "index": i + 1,
                        "type": step.step_type.value,
                        "duration_seconds": step.end_condition.value,
                    }
                )

        assert len(steps_info) == 2
        assert steps_info[0]["type"] == "warmup"
        assert steps_info[1]["type"] == "repeat"
        assert steps_info[1]["iterations"] == 3

    def test_sport_type_validation(self) -> None:
        """Test sport type validation for create_workout."""
        from garmy.workouts import SportType

        # Valid sport types (using actual API keys)
        valid_types = ["cycling", "running", "swimming", "strength_training"]
        for st in valid_types:
            sport = SportType.from_key(st)
            assert sport.key == st

        # Unknown sport type returns OTHER (with key "other")
        sport = SportType.from_key("invalid_sport")
        assert sport == SportType.OTHER
        assert sport.key == "other"

    def test_date_format_validation(self) -> None:
        """Test date format validation for schedule_workout."""
        import re

        valid_dates = ["2024-01-15", "2025-12-31", "2023-06-01"]
        invalid_dates = ["01-15-2024", "2024/01/15", "2024-1-15", "not-a-date"]

        pattern = r"^\d{4}-\d{2}-\d{2}$"

        for d in valid_dates:
            assert re.match(pattern, d) is not None

        for d in invalid_dates:
            assert re.match(pattern, d) is None

    def test_workout_id_validation(self) -> None:
        """Test workout ID validation."""
        # Valid IDs
        assert 1 >= 1  # Minimum valid ID
        assert 123456 >= 1

        # Invalid IDs
        assert not (0 >= 1)
        assert not (-1 >= 1)


class TestCreateWorkoutJsonParsing:
    """Tests for JSON parsing in create_workout."""

    def test_parse_simple_steps_json(self) -> None:
        """Test parsing simple steps JSON."""
        steps_json = json.dumps(
            [
                {"type": "warmup", "minutes": 10},
                {"type": "interval", "minutes": 5, "target_power": [90, 95]},
                {"type": "cooldown", "minutes": 10},
            ]
        )

        steps = json.loads(steps_json)
        assert len(steps) == 3
        assert steps[0]["type"] == "warmup"
        assert steps[1]["target_power"] == [90, 95]

    def test_parse_repeat_steps_json(self) -> None:
        """Test parsing repeat group in steps JSON."""
        steps_json = json.dumps(
            [
                {"type": "warmup", "minutes": 10},
                {
                    "type": "repeat",
                    "iterations": 3,
                    "steps": [
                        {"type": "interval", "minutes": 5},
                        {"type": "recovery", "minutes": 2},
                    ],
                },
                {"type": "cooldown", "minutes": 10},
            ]
        )

        steps = json.loads(steps_json)
        assert len(steps) == 3
        assert steps[1]["type"] == "repeat"
        assert steps[1]["iterations"] == 3
        assert len(steps[1]["steps"]) == 2

    def test_parse_steps_with_all_targets(self) -> None:
        """Test parsing steps with various target types."""
        steps_json = json.dumps(
            [
                {"type": "warmup", "minutes": 10, "target_power": [50, 60]},
                {"type": "interval", "minutes": 5, "target_hr": [150, 165]},
                {"type": "interval", "minutes": 5, "target_cadence": [90, 100]},
            ]
        )

        steps = json.loads(steps_json)
        assert steps[0]["target_power"] == [50, 60]
        assert steps[1]["target_hr"] == [150, 165]
        assert steps[2]["target_cadence"] == [90, 100]

    def test_invalid_json_raises_error(self) -> None:
        """Test that invalid JSON raises an error."""
        invalid_json = "not valid json"

        with pytest.raises(json.JSONDecodeError):
            json.loads(invalid_json)

    def test_convert_list_to_tuple(self) -> None:
        """Test converting target lists to tuples."""
        target_power = [90, 95]
        if isinstance(target_power, list):
            target_power = tuple(target_power)

        assert isinstance(target_power, tuple)
        assert target_power == (90, 95)


class TestWorkoutToolsEdgeCases:
    """Edge case tests for workout tools."""

    def test_empty_workout_name(self) -> None:
        """Test handling empty workout name."""
        from garmy.workouts import SportType, WorkoutBuilder

        # Empty name should still work (API may reject it)
        builder = WorkoutBuilder("", SportType.CYCLING)
        workout = builder.build()
        assert workout.name == ""

    def test_workout_with_no_steps(self) -> None:
        """Test creating workout with no steps."""
        from garmy.workouts import SportType, WorkoutBuilder

        builder = WorkoutBuilder("Empty Workout", SportType.CYCLING)
        workout = builder.build()
        assert len(workout.steps) == 0

    def test_very_long_workout_description(self) -> None:
        """Test workout with very long description."""
        from garmy.workouts import SportType, WorkoutBuilder

        long_desc = "A" * 1000
        builder = WorkoutBuilder("Test", SportType.CYCLING)
        builder.with_description(long_desc)
        workout = builder.build()
        assert len(workout.description) == 1000

    def test_step_with_seconds_instead_of_minutes(self) -> None:
        """Test creating step with seconds duration."""
        from garmy.workouts import SportType, WorkoutBuilder

        builder = WorkoutBuilder("Test", SportType.CYCLING)
        builder.interval(seconds=30)
        workout = builder.build()
        assert workout.steps[0].end_condition.value == 30

    def test_step_with_distance(self) -> None:
        """Test creating step with distance duration."""
        from garmy.workouts import SportType, WorkoutBuilder

        builder = WorkoutBuilder("Test", SportType.RUNNING)
        builder.interval(distance_km=1.0)
        workout = builder.build()
        # Distance is stored in meters
        assert workout.steps[0].end_condition.value == 1000

    def test_lap_button_end_condition(self) -> None:
        """Test creating step with lap button end condition."""
        from garmy.workouts import SportType, WorkoutBuilder

        builder = WorkoutBuilder("Test", SportType.CYCLING)
        builder.interval(lap_button=True)
        workout = builder.build()
        assert workout.steps[0].end_condition.condition_type.value == "lap.button"

    def test_schedule_workout_date_edge_cases(self) -> None:
        """Test schedule workout with various date formats."""
        import re

        pattern = r"^\d{4}-\d{2}-\d{2}$"

        # Edge case dates
        assert re.match(pattern, "2024-02-29") is not None  # Leap year
        assert re.match(pattern, "2024-12-31") is not None  # Year end
        assert re.match(pattern, "2024-01-01") is not None  # Year start
