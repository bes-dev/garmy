"""Tests for garmy.workouts.constants module."""

import pytest

from garmy.workouts.constants import (
    EndConditionType,
    IntensityType,
    SportType,
    StepType,
    TargetType,
)


class TestSportType:
    """Test cases for SportType enum."""

    def test_sport_type_values(self):
        """Test SportType has correct id and key values."""
        assert SportType.RUNNING.id == 1
        assert SportType.RUNNING.key == "running"

        assert SportType.CYCLING.id == 2
        assert SportType.CYCLING.key == "cycling"

        assert SportType.STRENGTH.id == 5
        assert SportType.STRENGTH.key == "strength_training"

        # Verify other key sport types per Garmin API (IDs verified via testing)
        assert SportType.WALKING.id == 12
        assert SportType.SWIMMING.id == 4
        assert SportType.CARDIO.id == 6
        assert SportType.YOGA.id == 7

    def test_sport_type_from_id(self):
        """Test SportType.from_id lookup."""
        assert SportType.from_id(1) == SportType.RUNNING
        assert SportType.from_id(2) == SportType.CYCLING
        assert SportType.from_id(4) == SportType.SWIMMING

    def test_sport_type_from_id_unknown(self):
        """Test SportType.from_id returns OTHER for unknown IDs."""
        assert SportType.from_id(9999) == SportType.OTHER

    def test_sport_type_from_key(self):
        """Test SportType.from_key lookup."""
        assert SportType.from_key("running") == SportType.RUNNING
        assert SportType.from_key("cycling") == SportType.CYCLING
        assert SportType.from_key("RUNNING") == SportType.RUNNING  # Case insensitive

    def test_sport_type_from_key_unknown(self):
        """Test SportType.from_key returns OTHER for unknown keys."""
        assert SportType.from_key("unknown_sport") == SportType.OTHER


class TestStepType:
    """Test cases for StepType enum."""

    def test_step_type_values(self):
        """Test StepType values."""
        assert StepType.WARMUP.value == "warmup"
        assert StepType.COOLDOWN.value == "cooldown"
        assert StepType.INTERVAL.value == "interval"
        assert StepType.RECOVERY.value == "recovery"
        assert StepType.REST.value == "rest"
        assert StepType.REPEAT.value == "repeat"

    def test_step_type_type_id(self):
        """Test StepType.type_id property."""
        assert StepType.WARMUP.type_id == 1
        assert StepType.COOLDOWN.type_id == 2
        assert StepType.INTERVAL.type_id == 3
        assert StepType.RECOVERY.type_id == 4
        assert StepType.REST.type_id == 5
        assert StepType.REPEAT.type_id == 6

    def test_step_type_from_type_id(self):
        """Test StepType.from_type_id lookup."""
        assert StepType.from_type_id(1) == StepType.WARMUP
        assert StepType.from_type_id(3) == StepType.INTERVAL
        assert StepType.from_type_id(6) == StepType.REPEAT

    def test_step_type_from_type_id_unknown(self):
        """Test StepType.from_type_id returns OTHER for unknown IDs."""
        assert StepType.from_type_id(9999) == StepType.OTHER


class TestEndConditionType:
    """Test cases for EndConditionType enum."""

    def test_end_condition_type_values(self):
        """Test EndConditionType values."""
        assert EndConditionType.LAP_BUTTON.value == "lap.button"
        assert EndConditionType.TIME.value == "time"
        assert EndConditionType.DISTANCE.value == "distance"
        assert EndConditionType.ITERATIONS.value == "iterations"

    def test_end_condition_type_condition_type_id(self):
        """Test EndConditionType.condition_type_id property."""
        assert EndConditionType.LAP_BUTTON.condition_type_id == 1
        assert EndConditionType.TIME.condition_type_id == 2
        assert EndConditionType.DISTANCE.condition_type_id == 3
        assert EndConditionType.ITERATIONS.condition_type_id == 7

    def test_end_condition_type_from_condition_type_id(self):
        """Test EndConditionType.from_condition_type_id lookup."""
        assert EndConditionType.from_condition_type_id(1) == EndConditionType.LAP_BUTTON
        assert EndConditionType.from_condition_type_id(2) == EndConditionType.TIME
        assert EndConditionType.from_condition_type_id(3) == EndConditionType.DISTANCE

    def test_end_condition_type_from_condition_type_id_unknown(self):
        """Test EndConditionType.from_condition_type_id returns LAP_BUTTON for unknown."""
        assert (
            EndConditionType.from_condition_type_id(9999) == EndConditionType.LAP_BUTTON
        )


class TestTargetType:
    """Test cases for TargetType enum."""

    def test_target_type_values(self):
        """Test TargetType values."""
        assert TargetType.NO_TARGET.value == "no.target"
        assert TargetType.POWER_ZONE.value == "power.zone"
        assert TargetType.HEART_RATE_ZONE.value == "heart.rate.zone"
        assert TargetType.CADENCE_ZONE.value == "cadence.zone"

    def test_target_type_target_type_id(self):
        """Test TargetType.target_type_id property."""
        assert TargetType.NO_TARGET.target_type_id == 1
        assert TargetType.POWER_ZONE.target_type_id == 2
        assert TargetType.HEART_RATE_ZONE.target_type_id == 4

    def test_target_type_from_target_type_id(self):
        """Test TargetType.from_target_type_id lookup."""
        assert TargetType.from_target_type_id(1) == TargetType.NO_TARGET
        assert TargetType.from_target_type_id(2) == TargetType.POWER_ZONE

    def test_target_type_from_target_type_id_unknown(self):
        """Test TargetType.from_target_type_id returns NO_TARGET for unknown."""
        assert TargetType.from_target_type_id(9999) == TargetType.NO_TARGET


class TestIntensityType:
    """Test cases for IntensityType enum."""

    def test_intensity_type_values(self):
        """Test IntensityType values."""
        assert IntensityType.ACTIVE.value == "active"
        assert IntensityType.REST.value == "rest"
        assert IntensityType.WARMUP.value == "warmup"
        assert IntensityType.COOLDOWN.value == "cooldown"

    def test_intensity_type_intensity_type_id(self):
        """Test IntensityType.intensity_type_id property."""
        assert IntensityType.ACTIVE.intensity_type_id == 1
        assert IntensityType.REST.intensity_type_id == 2
        assert IntensityType.WARMUP.intensity_type_id == 3

    def test_intensity_type_from_intensity_type_id(self):
        """Test IntensityType.from_intensity_type_id lookup."""
        assert IntensityType.from_intensity_type_id(1) == IntensityType.ACTIVE
        assert IntensityType.from_intensity_type_id(3) == IntensityType.WARMUP

    def test_intensity_type_from_intensity_type_id_unknown(self):
        """Test IntensityType.from_intensity_type_id returns ACTIVE for unknown."""
        assert IntensityType.from_intensity_type_id(9999) == IntensityType.ACTIVE
