"""
Serializer for converting workouts to/from Garmin API JSON format.

This module handles the conversion between Python workout models and the
JSON format expected by the Garmin Connect workout API.
"""

from typing import Any, Dict, List, Optional, Sequence, Union

from .constants import (
    EndConditionType,
    IntensityType,
    SportType,
    StepType,
    TargetType,
)
from .models import (
    EndCondition,
    RepeatGroup,
    Target,
    Workout,
    WorkoutStep,
    WorkoutStepOrRepeat,
)


class WorkoutSerializer:
    """Converts Workout models to/from Garmin API JSON format."""

    @classmethod
    def to_api_format(cls, workout: Workout) -> Dict[str, Any]:
        """Convert a Workout to Garmin API JSON format.

        Args:
            workout: The Workout model to convert.

        Returns:
            Dictionary in Garmin API format ready for POST/PUT.
        """
        # Build workout steps with proper ordering
        workout_steps = cls._serialize_steps(workout.steps)

        # Include both sportTypeId and sportTypeKey for Garmin to properly store the sport type
        # Note: Garmin's IDs are inconsistent, but including the ID helps Garmin store it correctly
        payload: Dict[str, Any] = {
            "workoutName": workout.name,
            "sportType": {
                "sportTypeId": workout.sport_type.id,
                "sportTypeKey": workout.sport_type.key,
            },
            "workoutSegments": [
                {
                    "segmentOrder": 1,
                    "sportType": {
                        "sportTypeId": workout.sport_type.id,
                        "sportTypeKey": workout.sport_type.key,
                    },
                    "workoutSteps": workout_steps,
                }
            ],
        }

        if workout.description:
            payload["description"] = workout.description

        if workout.workout_id:
            payload["workoutId"] = workout.workout_id

        if workout.owner_id:
            payload["ownerId"] = workout.owner_id

        return payload

    @classmethod
    def _serialize_steps(
        cls,
        steps: Sequence[Union[WorkoutStep, RepeatGroup]],
        start_order: int = 1,
    ) -> List[Dict[str, Any]]:
        """Serialize a list of steps with proper ordering.

        Args:
            steps: List of WorkoutStep and RepeatGroup objects.
            start_order: Starting step order number.

        Returns:
            List of serialized step dictionaries.
        """
        result: List[Dict[str, Any]] = []
        current_order = start_order

        for step in steps:
            if isinstance(step, RepeatGroup):
                serialized = cls._serialize_repeat_group(step, current_order)
                result.append(serialized)
            else:
                serialized = cls._serialize_step(step, current_order)
                result.append(serialized)
            current_order += 1

        return result

    @classmethod
    def _serialize_step(cls, step: WorkoutStep, order: int) -> Dict[str, Any]:
        """Serialize a single workout step.

        Args:
            step: The WorkoutStep to serialize.
            order: The step order number.

        Returns:
            Serialized step dictionary.
        """
        result: Dict[str, Any] = {
            "type": "ExecutableStepDTO",
            "stepOrder": order,
            "stepType": {
                "stepTypeId": step.step_type.type_id,
                "stepTypeKey": step.step_type.value,
            },
            "endCondition": {
                "conditionTypeId": step.end_condition.condition_type.condition_type_id,
                "conditionTypeKey": step.end_condition.condition_type.value,
            },
            # Garmin expects endConditionValue at step level, not inside endCondition
            "endConditionValue": step.end_condition.value,
            "targetType": cls._serialize_target(step.target),
            "intensityType": {
                "intensityTypeId": step.intensity.intensity_type_id,
                "intensityTypeKey": step.intensity.value,
            },
        }

        if step.description:
            result["description"] = step.description

        # Add exercise fields for strength training workouts
        if step.exercise_category:
            result["category"] = step.exercise_category

        if step.exercise_name:
            result["exerciseName"] = step.exercise_name

        if step.weight_value is not None:
            # Send weight in its original unit - the Garmin mobile app has a bug
            # where it doesn't convert kg to the user's display preference,
            # so we send in the user's specified unit (default: pound)
            weight_unit = step.weight_unit or "pound"
            result["weightValue"] = step.weight_value
            if weight_unit == "kilogram":
                result["weightUnit"] = {
                    "unitId": 8,
                    "unitKey": "kilogram",
                    "factor": 1000.0,
                }
            else:
                # Default to pound
                result["weightUnit"] = {
                    "unitId": 9,
                    "unitKey": "pound",
                    "factor": 453.59237,
                }

        return result

    @classmethod
    def _serialize_end_condition(cls, end_condition: EndCondition) -> Dict[str, Any]:
        """Serialize an end condition."""
        result: Dict[str, Any] = {
            "conditionTypeId": end_condition.condition_type.condition_type_id,
            "conditionTypeKey": end_condition.condition_type.value,
        }

        if end_condition.value is not None:
            # Garmin uses different value keys for different condition types
            if end_condition.condition_type in (
                EndConditionType.ITERATIONS,
                EndConditionType.REPS,
            ):
                result["conditionValue"] = int(end_condition.value)
            else:
                result["conditionValue"] = end_condition.value

        return result

    @classmethod
    def _serialize_target(cls, target: Target) -> Dict[str, Any]:
        """Serialize a target specification."""
        # Garmin API uses workoutTargetTypeId/Key, not targetTypeId/Key
        result: Dict[str, Any] = {
            "workoutTargetTypeId": target.target_type.target_type_id,
            "workoutTargetTypeKey": target.target_type.value,
        }

        if target.value_low is not None:
            result["targetValueOne"] = target.value_low

        if target.value_high is not None:
            result["targetValueTwo"] = target.value_high

        if target.zone_number is not None:
            result["zoneNumber"] = target.zone_number

        return result

    @classmethod
    def _serialize_repeat_group(cls, repeat: RepeatGroup, order: int) -> Dict[str, Any]:
        """Serialize a repeat group.

        Args:
            repeat: The RepeatGroup to serialize.
            order: The step order number for the repeat group.

        Returns:
            Serialized repeat group dictionary.
        """
        # Serialize child steps with their own ordering starting at 1
        child_steps = cls._serialize_steps(repeat.steps, start_order=1)

        # Garmin API uses numberOfIterations for repeat groups
        return {
            "type": "RepeatGroupDTO",
            "stepOrder": order,
            "stepType": {
                "stepTypeId": StepType.REPEAT.type_id,
                "stepTypeKey": StepType.REPEAT.value,
            },
            "numberOfIterations": repeat.iterations,
            "endCondition": {
                "conditionTypeId": EndConditionType.ITERATIONS.condition_type_id,
                "conditionTypeKey": EndConditionType.ITERATIONS.value,
            },
            "endConditionValue": float(repeat.iterations),
            "smartRepeat": False,
            "skipLastRestStep": repeat.smart_repeat,
            "workoutSteps": child_steps,
        }

    @classmethod
    def from_api_format(cls, data: Dict[str, Any]) -> Workout:
        """Parse Garmin API JSON into a Workout model.

        Args:
            data: Dictionary from Garmin API response.

        Returns:
            Parsed Workout model.
        """
        # Parse sport type - prefer key over ID since Garmin's IDs are inconsistent
        # (e.g., strength_training workouts return sportTypeId=5 but sportTypeKey=strength_training)
        sport_type_data = data.get("sportType", {})
        sport_type_id = sport_type_data.get("sportTypeId")
        sport_type_key = sport_type_data.get("sportTypeKey", "")

        # Prefer key-based lookup since Garmin's IDs don't match their keys
        if sport_type_key:
            sport_type = SportType.from_key(sport_type_key)
            # Fall back to ID if key lookup fails
            if sport_type == SportType.OTHER and sport_type_id is not None:
                sport_type = SportType.from_id(sport_type_id)
        elif sport_type_id is not None:
            sport_type = SportType.from_id(sport_type_id)
        else:
            sport_type = SportType.OTHER

        # Parse steps from segments
        steps: List[WorkoutStepOrRepeat] = []
        segments = data.get("workoutSegments", [])
        if segments:
            first_segment = segments[0]
            workout_steps = first_segment.get("workoutSteps", [])
            steps = cls._parse_steps(workout_steps)

        return Workout(
            name=data.get("workoutName", "Untitled"),
            sport_type=sport_type,
            description=data.get("description"),
            steps=steps,
            workout_id=data.get("workoutId"),
            owner_id=data.get("ownerId"),
        )

    @classmethod
    def _parse_steps(
        cls, steps_data: List[Dict[str, Any]]
    ) -> List[WorkoutStepOrRepeat]:
        """Parse a list of step dictionaries into models.

        Args:
            steps_data: List of step dictionaries from API.

        Returns:
            List of WorkoutStep and RepeatGroup models.
        """
        result: List[WorkoutStepOrRepeat] = []

        for step_data in steps_data:
            step_type_str = step_data.get("type", "")

            if step_type_str == "RepeatGroupDTO":
                result.append(cls._parse_repeat_group(step_data))
            else:
                result.append(cls._parse_step(step_data))

        return result

    @classmethod
    def _parse_step(cls, data: Dict[str, Any]) -> WorkoutStep:
        """Parse a single step dictionary into a WorkoutStep.

        Args:
            data: Step dictionary from API.

        Returns:
            Parsed WorkoutStep model.
        """
        # Parse step type (handle None values)
        step_type_data = data.get("stepType") or {}
        step_type = StepType.from_type_id(step_type_data.get("stepTypeId", 7))

        # Parse end condition (handle None values)
        # Note: Garmin API returns endConditionValue at step level, not inside endCondition
        end_condition_data = data.get("endCondition") or {}
        end_condition_value = data.get("endConditionValue")  # Value is at step level!
        end_condition = cls._parse_end_condition(
            end_condition_data, end_condition_value
        )

        # Parse target (handle None values - Garmin sometimes returns targetType: null)
        target = cls._parse_target(data.get("targetType") or {})

        # Parse intensity (handle None values)
        intensity_data = data.get("intensityType") or {}
        intensity = IntensityType.from_intensity_type_id(
            intensity_data.get("intensityTypeId", 1)
        )

        # Parse exercise info for strength workouts
        exercise_name = data.get("exerciseName")
        exercise_category = data.get("category")

        # Parse weight info
        # Garmin returns weight with unit info - respect the unit from API
        weight_value_raw = data.get("weightValue")
        weight_unit_data = data.get("weightUnit") or {}
        weight_value: Optional[float] = None
        weight_unit: Optional[str] = None

        if weight_value_raw is not None and weight_value_raw > 0:
            # Check what unit Garmin returned
            api_unit = weight_unit_data.get("unitKey", "kilogram")
            if api_unit == "pound":
                # Already in pounds, use as-is
                weight_value = round(weight_value_raw, 1)
                weight_unit = "pound"
            else:
                # Assume kilograms, convert to pounds for consistency
                weight_value = round(weight_value_raw * 2.20462, 1)
                weight_unit = "pound"
        elif weight_value_raw is not None and weight_value_raw < 0:
            # Clean up negative placeholder values from API
            weight_value = None
            weight_unit = None

        return WorkoutStep(
            step_type=step_type,
            end_condition=end_condition,
            target=target,
            description=data.get("description"),
            step_order=data.get("stepOrder"),
            intensity=intensity,
            exercise_name=exercise_name,
            exercise_category=exercise_category,
            weight_value=weight_value,
            weight_unit=weight_unit,
        )

    @classmethod
    def _parse_end_condition(
        cls, data: Dict[str, Any], step_level_value: Optional[float] = None
    ) -> EndCondition:
        """Parse an end condition dictionary.

        Args:
            data: End condition dictionary from API.
            step_level_value: Value from step level (endConditionValue), which Garmin
                             uses instead of putting it inside the endCondition object.
        """
        condition_type = EndConditionType.from_condition_type_id(
            data.get("conditionTypeId", 1)
        )
        # Prefer step-level value (endConditionValue) over nested value (conditionValue)
        value = (
            step_level_value
            if step_level_value is not None
            else data.get("conditionValue")
        )

        return EndCondition(condition_type=condition_type, value=value)

    @classmethod
    def _parse_target(cls, data: Dict[str, Any]) -> Target:
        """Parse a target dictionary."""
        # Handle both field name formats (workoutTargetTypeId and targetTypeId)
        target_type_id = data.get("workoutTargetTypeId") or data.get("targetTypeId", 1)
        target_type = TargetType.from_target_type_id(target_type_id)

        # Handle both value field name formats
        value_low = data.get("targetValueOne") or data.get("targetValueLow")
        value_high = data.get("targetValueTwo") or data.get("targetValueHigh")

        return Target(
            target_type=target_type,
            value_low=value_low,
            value_high=value_high,
            zone_number=data.get("zoneNumber"),
        )

    @classmethod
    def _parse_repeat_group(cls, data: Dict[str, Any]) -> RepeatGroup:
        """Parse a repeat group dictionary.

        Args:
            data: Repeat group dictionary from API.

        Returns:
            Parsed RepeatGroup model.
        """
        # Try different iteration field names (numberOfIterations, endConditionValue, conditionValue)
        iterations = data.get("numberOfIterations")
        if iterations is None:
            iterations = data.get("endConditionValue")
        if iterations is None:
            end_condition = data.get("endCondition") or {}
            iterations = end_condition.get("conditionValue", 1)
        iterations = int(iterations)

        # Parse child steps
        child_steps_data = data.get("workoutSteps", [])
        steps = [
            cls._parse_step(s)
            for s in child_steps_data
            if s.get("type") != "RepeatGroupDTO"
        ]

        smart_repeat = bool(data.get("skipLastRestStep", False))

        return RepeatGroup(
            iterations=iterations,
            steps=steps,
            step_order=data.get("stepOrder"),
            smart_repeat=smart_repeat,
        )
