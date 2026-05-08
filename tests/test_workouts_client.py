"""Tests for garmy.workouts.client module."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from garmy.workouts.client import WorkoutClient
from garmy.workouts.constants import SportType, StepType
from garmy.workouts.models import (
    EndCondition,
    RepeatGroup,
    Workout,
    WorkoutStep,
)


class TestWorkoutClient:
    """Test cases for WorkoutClient class."""

    @pytest.fixture
    def mock_api_client(self):
        """Create a mock API client."""
        client = MagicMock()
        client.connectapi = MagicMock()
        client.request = MagicMock()
        return client

    @pytest.fixture
    def workout_client(self, mock_api_client):
        """Create a WorkoutClient with mocked API client."""
        return WorkoutClient(mock_api_client)

    def test_workout_client_initialization(self, mock_api_client):
        """Test WorkoutClient initialization."""
        client = WorkoutClient(mock_api_client)
        assert client.api_client is mock_api_client

    def test_workout_headers(self, workout_client):
        """Test workout headers are correctly defined."""
        assert "Referer" in workout_client.WORKOUT_HEADERS
        assert "nk" in workout_client.WORKOUT_HEADERS
        assert "workouts" in workout_client.WORKOUT_HEADERS["Referer"]

    def test_list_workouts_empty(self, workout_client, mock_api_client):
        """Test list_workouts returns empty list when no workouts."""
        mock_api_client.connectapi.return_value = []

        result = workout_client.list_workouts()

        assert result == []
        mock_api_client.connectapi.assert_called_once()

    def test_list_workouts_with_results(self, workout_client, mock_api_client):
        """Test list_workouts returns parsed workouts."""
        mock_api_client.connectapi.return_value = [
            {
                "workoutId": 1,
                "workoutName": "Workout 1",
                "sportType": {"sportTypeId": 2, "sportTypeKey": "cycling"},
                "workoutSegments": [],
            },
            {
                "workoutId": 2,
                "workoutName": "Workout 2",
                "sportType": {"sportTypeId": 1, "sportTypeKey": "running"},
                "workoutSegments": [],
            },
        ]

        result = workout_client.list_workouts()

        assert len(result) == 2
        assert result[0].name == "Workout 1"
        assert result[0].workout_id == 1
        assert result[1].name == "Workout 2"
        assert result[1].sport_type == SportType.RUNNING

    def test_list_workouts_parameters(self, workout_client, mock_api_client):
        """Test list_workouts passes correct parameters."""
        mock_api_client.connectapi.return_value = []

        workout_client.list_workouts(
            limit=50,
            start=10,
            my_workouts_only=False,
            order_by="UPDATE_DATE",
            order_seq="DESC",
        )

        call_args = mock_api_client.connectapi.call_args
        endpoint = call_args[0][0]

        assert "limit=50" in endpoint
        assert "start=10" in endpoint
        assert "myWorkoutsOnly=false" in endpoint
        assert "orderBy=UPDATE_DATE" in endpoint
        assert "orderSeq=DESC" in endpoint

    def test_list_workouts_none_response(self, workout_client, mock_api_client):
        """Test list_workouts handles None response."""
        mock_api_client.connectapi.return_value = None

        result = workout_client.list_workouts()

        assert result == []

    def test_get_workout(self, workout_client, mock_api_client):
        """Test get_workout returns parsed workout."""
        mock_api_client.connectapi.return_value = {
            "workoutId": 12345,
            "workoutName": "Test Workout",
            "sportType": {"sportTypeId": 2, "sportTypeKey": "cycling"},
            "description": "Test description",
            "workoutSegments": [],
        }

        result = workout_client.get_workout(12345)

        assert result is not None
        assert result.workout_id == 12345
        assert result.name == "Test Workout"
        assert result.description == "Test description"
        mock_api_client.connectapi.assert_called_once()
        assert (
            "/workout-service/workout/12345"
            in mock_api_client.connectapi.call_args[0][0]
        )

    def test_get_workout_not_found(self, workout_client, mock_api_client):
        """Test get_workout returns None when not found."""
        mock_api_client.connectapi.return_value = None

        result = workout_client.get_workout(99999)

        assert result is None

    def test_create_workout(self, workout_client, mock_api_client):
        """Test create_workout creates and returns workout with ID."""
        workout = Workout(name="New Workout", sport_type=SportType.CYCLING)
        workout.add_step(WorkoutStep(step_type=StepType.WARMUP))

        mock_api_client.connectapi.return_value = {
            "workoutId": 12345,
            "workoutName": "New Workout",
            "sportType": {"sportTypeId": 2, "sportTypeKey": "cycling"},
            "workoutSegments": [
                {
                    "segmentOrder": 1,
                    "sportType": {"sportTypeId": 2},
                    "workoutSteps": [
                        {
                            "type": "ExecutableStepDTO",
                            "stepType": {"stepTypeId": 1},
                            "endCondition": {"conditionTypeId": 1},
                            "targetType": {"targetTypeId": 1},
                            "intensityType": {"intensityTypeId": 3},
                        }
                    ],
                }
            ],
        }

        result = workout_client.create_workout(workout)

        assert result.workout_id == 12345
        call_args = mock_api_client.connectapi.call_args
        assert call_args[1]["method"] == "POST"
        assert "json" in call_args[1]

    def test_create_workout_raw(self, workout_client, mock_api_client):
        """Test create_workout_raw with raw API format."""
        raw_data = {
            "workoutName": "Raw Workout",
            "sportType": {"sportTypeId": 2, "sportTypeKey": "cycling"},
            "workoutSegments": [],
        }

        mock_api_client.connectapi.return_value = {
            "workoutId": 12345,
            **raw_data,
        }

        result = workout_client.create_workout_raw(raw_data)

        assert result["workoutId"] == 12345
        assert result["workoutName"] == "Raw Workout"

    def test_update_workout(self, workout_client, mock_api_client):
        """Test update_workout updates existing workout."""
        workout = Workout(
            name="Updated Workout", sport_type=SportType.CYCLING, workout_id=12345
        )

        mock_api_client.connectapi.return_value = {
            "workoutId": 12345,
            "workoutName": "Updated Workout",
            "sportType": {"sportTypeId": 2, "sportTypeKey": "cycling"},
            "workoutSegments": [],
        }

        result = workout_client.update_workout(workout)

        assert result.name == "Updated Workout"
        call_args = mock_api_client.connectapi.call_args
        assert "/workout-service/workout/12345" in call_args[0][0]
        assert call_args[1]["method"] == "PUT"

    def test_update_workout_without_id(self, workout_client):
        """Test update_workout raises error without workout_id."""
        workout = Workout(name="No ID Workout")

        with pytest.raises(ValueError, match="workout_id must be set"):
            workout_client.update_workout(workout)

    def test_delete_workout(self, workout_client, mock_api_client):
        """Test delete_workout deletes workout."""
        mock_api_client.connectapi.return_value = None

        result = workout_client.delete_workout(12345)

        assert result is True
        call_args = mock_api_client.connectapi.call_args
        assert "/workout-service/workout/12345" in call_args[0][0]
        assert call_args[1]["method"] == "DELETE"

    def test_schedule_workout(self, workout_client, mock_api_client):
        """Test schedule_workout schedules workout for date."""
        mock_api_client.connectapi.return_value = None

        result = workout_client.schedule_workout(12345, "2024-01-15")

        assert result is True
        call_args = mock_api_client.connectapi.call_args
        assert "/workout-service/schedule/12345" in call_args[0][0]
        assert call_args[1]["method"] == "POST"
        assert call_args[1]["json"]["date"] == "2024-01-15"

    def test_unschedule_workout(self, workout_client, mock_api_client):
        """Test unschedule_workout removes scheduled workout."""
        mock_api_client.connectapi.return_value = None

        result = workout_client.unschedule_workout(12345, "2024-01-15")

        assert result is True
        call_args = mock_api_client.connectapi.call_args
        assert "/workout-service/schedule/12345" in call_args[0][0]
        assert call_args[1]["method"] == "DELETE"

    def test_download_fit(self, workout_client, mock_api_client):
        """Test download_fit returns FIT file bytes."""
        mock_response = Mock()
        mock_response.content = b"FIT file content"
        mock_api_client.request.return_value = mock_response

        result = workout_client.download_fit(12345)

        assert result == b"FIT file content"
        call_args = mock_api_client.request.call_args
        assert call_args[0][0] == "GET"
        assert "/workout-service/workout/FIT/12345" in call_args[0][2]

    def test_duplicate_workout(self, workout_client, mock_api_client):
        """Test duplicate_workout creates copy of workout."""
        # Mock get_workout response
        mock_api_client.connectapi.side_effect = [
            # First call: get_workout
            {
                "workoutId": 12345,
                "workoutName": "Original Workout",
                "sportType": {"sportTypeId": 2, "sportTypeKey": "cycling"},
                "description": "Original description",
                "workoutSegments": [
                    {
                        "segmentOrder": 1,
                        "sportType": {"sportTypeId": 2},
                        "workoutSteps": [
                            {
                                "type": "ExecutableStepDTO",
                                "stepType": {"stepTypeId": 1},
                                "endCondition": {"conditionTypeId": 1},
                                "targetType": {"targetTypeId": 1},
                                "intensityType": {"intensityTypeId": 3},
                            }
                        ],
                    }
                ],
            },
            # Second call: create_workout
            {
                "workoutId": 67890,
                "workoutName": "Original Workout (Copy)",
                "sportType": {"sportTypeId": 2, "sportTypeKey": "cycling"},
                "workoutSegments": [],
            },
        ]

        result = workout_client.duplicate_workout(12345)

        assert result.workout_id == 67890
        assert "(Copy)" in result.name

    def test_duplicate_workout_with_new_name(self, workout_client, mock_api_client):
        """Test duplicate_workout with custom name."""
        mock_api_client.connectapi.side_effect = [
            {
                "workoutId": 12345,
                "workoutName": "Original",
                "sportType": {"sportTypeId": 2, "sportTypeKey": "cycling"},
                "workoutSegments": [],
            },
            {
                "workoutId": 67890,
                "workoutName": "Custom Name",
                "sportType": {"sportTypeId": 2, "sportTypeKey": "cycling"},
                "workoutSegments": [],
            },
        ]

        result = workout_client.duplicate_workout(12345, new_name="Custom Name")

        # Verify the create call used the custom name
        create_call = mock_api_client.connectapi.call_args_list[1]
        assert create_call[1]["json"]["workoutName"] == "Custom Name"

    def test_duplicate_workout_not_found(self, workout_client, mock_api_client):
        """Test duplicate_workout raises error when workout not found."""
        mock_api_client.connectapi.return_value = None

        with pytest.raises(ValueError, match="not found"):
            workout_client.duplicate_workout(99999)


class TestWorkoutClientIntegration:
    """Integration tests for WorkoutClient with real serialization."""

    @pytest.fixture
    def mock_api_client(self):
        """Create a mock API client."""
        return MagicMock()

    @pytest.fixture
    def workout_client(self, mock_api_client):
        """Create a WorkoutClient with mocked API client."""
        return WorkoutClient(mock_api_client)

    def test_create_complex_workout(self, workout_client, mock_api_client):
        """Test creating a complex workout with repeats."""
        workout = Workout(
            name="Complex Workout",
            sport_type=SportType.CYCLING,
            description="Test",
        )
        workout.add_step(
            WorkoutStep(
                step_type=StepType.WARMUP,
                end_condition=EndCondition.time_minutes(10),
            )
        )

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

        workout.add_step(
            WorkoutStep(
                step_type=StepType.COOLDOWN,
                end_condition=EndCondition.time_minutes(10),
            )
        )

        mock_api_client.connectapi.return_value = {
            "workoutId": 12345,
            "workoutName": "Complex Workout",
            "sportType": {"sportTypeId": 2, "sportTypeKey": "cycling"},
            "workoutSegments": [],
        }

        result = workout_client.create_workout(workout)

        # Verify the payload structure
        call_args = mock_api_client.connectapi.call_args
        payload = call_args[1]["json"]

        assert payload["workoutName"] == "Complex Workout"
        assert len(payload["workoutSegments"][0]["workoutSteps"]) == 3

        # Verify repeat group structure
        repeat_step = payload["workoutSegments"][0]["workoutSteps"][1]
        assert repeat_step["type"] == "RepeatGroupDTO"
        assert len(repeat_step["workoutSteps"]) == 2
