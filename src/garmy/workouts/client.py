"""
Workout client for Garmin Connect workout API operations.

This module provides the WorkoutClient class for CRUD operations on
Garmin Connect workouts.
"""

from typing import TYPE_CHECKING, Any, ClassVar, Dict, List, Optional, Union, cast

if TYPE_CHECKING:
    from ..core.client import APIClient

from .models import Workout
from .serializer import WorkoutSerializer


class WorkoutClient:
    """Client for Garmin Connect workout API operations.

    Provides methods for listing, creating, updating, and deleting workouts
    in Garmin Connect. Also supports scheduling workouts and downloading FIT files.

    Example:
        >>> from garmy import AuthClient, APIClient
        >>> auth = AuthClient()
        >>> api = APIClient(auth_client=auth)
        >>> auth.login("email", "password")
        >>>
        >>> # List workouts
        >>> workouts = api.workouts.list_workouts()
        >>>
        >>> # Create a workout
        >>> from garmy.workouts import WorkoutBuilder, SportType
        >>> workout = WorkoutBuilder("My Workout", SportType.CYCLING).build()
        >>> result = api.workouts.create_workout(workout)
    """

    # Headers required for workout API calls
    WORKOUT_HEADERS: ClassVar[Dict[str, str]] = {
        "Referer": "https://connect.garmin.com/modern/workouts",
        "nk": "NT",
    }

    def __init__(self, api_client: "APIClient") -> None:
        """Initialize the workout client.

        Args:
            api_client: The APIClient instance for making API requests.
        """
        self.api_client = api_client

    def list_workouts(
        self,
        limit: int = 20,
        start: int = 0,
        my_workouts_only: bool = True,
        order_by: str = "WORKOUT_NAME",
        order_seq: str = "ASC",
    ) -> List[Workout]:
        """List workouts from Garmin Connect.

        Args:
            limit: Maximum number of workouts to return. Default 20.
            start: Starting offset for pagination. Default 0.
            my_workouts_only: If True, only return user's own workouts.
            order_by: Field to order by (WORKOUT_NAME, UPDATE_DATE, etc.)
            order_seq: Order sequence (ASC or DESC).

        Returns:
            List of Workout objects.
        """
        params = {
            "start": start,
            "limit": limit,
            "myWorkoutsOnly": str(my_workouts_only).lower(),
            "orderBy": order_by,
            "orderSeq": order_seq,
        }

        endpoint = "/workout-service/workouts"
        query = "&".join(f"{k}={v}" for k, v in params.items())

        response = self.api_client.connectapi(
            f"{endpoint}?{query}",
            headers=self.WORKOUT_HEADERS,
        )

        if response is None:
            return []

        # API returns a list of workout dicts (cast needed as connectapi type hint is incomplete)
        raw_data = cast("List[Dict[str, Any]]", response)
        return [WorkoutSerializer.from_api_format(w) for w in raw_data]

    def get_workout(self, workout_id: Union[int, str]) -> Optional[Workout]:
        """Get a specific workout by ID.

        Args:
            workout_id: The Garmin workout ID.

        Returns:
            Workout object if found, None otherwise.
        """
        endpoint = f"/workout-service/workout/{workout_id}"

        raw_data = self.api_client.connectapi(
            endpoint,
            headers=self.WORKOUT_HEADERS,
        )

        if not raw_data or not isinstance(raw_data, dict):
            return None

        return WorkoutSerializer.from_api_format(raw_data)

    def create_workout(self, workout: Workout) -> Workout:
        """Create a new workout in Garmin Connect.

        Args:
            workout: The Workout object to create.

        Returns:
            The created Workout with workout_id populated.

        Raises:
            APIError: If the creation fails.
        """
        endpoint = "/workout-service/workout"
        payload = WorkoutSerializer.to_api_format(workout)

        raw_data = self.api_client.connectapi(
            endpoint,
            method="POST",
            json=payload,
            headers=self.WORKOUT_HEADERS,
        )

        if not raw_data or not isinstance(raw_data, dict):
            # Return original workout if response is unexpected
            return workout

        return WorkoutSerializer.from_api_format(raw_data)

    def create_workout_raw(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a workout using raw API format.

        For advanced users who want direct control over the API payload.

        Args:
            data: Dictionary in Garmin API format.

        Returns:
            Raw API response dictionary.
        """
        endpoint = "/workout-service/workout"

        result = self.api_client.connectapi(
            endpoint,
            method="POST",
            json=data,
            headers=self.WORKOUT_HEADERS,
        )

        if isinstance(result, dict):
            return result
        return {}

    def update_workout(self, workout: Workout) -> Workout:
        """Update an existing workout in Garmin Connect.

        Args:
            workout: The Workout object with workout_id set.

        Returns:
            The updated Workout object.

        Raises:
            ValueError: If workout_id is not set.
            APIError: If the update fails.
        """
        if not workout.workout_id:
            raise ValueError("workout_id must be set for update")

        endpoint = f"/workout-service/workout/{workout.workout_id}"
        payload = WorkoutSerializer.to_api_format(workout)

        raw_data = self.api_client.connectapi(
            endpoint,
            method="PUT",
            json=payload,
            headers=self.WORKOUT_HEADERS,
        )

        if not raw_data or not isinstance(raw_data, dict):
            return workout

        return WorkoutSerializer.from_api_format(raw_data)

    def delete_workout(self, workout_id: Union[int, str]) -> bool:
        """Delete a workout from Garmin Connect.

        Args:
            workout_id: The Garmin workout ID to delete.

        Returns:
            True if deletion was successful.

        Raises:
            APIError: If the deletion fails.
        """
        endpoint = f"/workout-service/workout/{workout_id}"

        self.api_client.connectapi(
            endpoint,
            method="DELETE",
            headers=self.WORKOUT_HEADERS,
        )

        return True

    def schedule_workout(
        self,
        workout_id: Union[int, str],
        date: str,
    ) -> bool:
        """Schedule a workout for a specific date.

        Args:
            workout_id: The Garmin workout ID to schedule.
            date: Date in YYYY-MM-DD format.

        Returns:
            True if scheduling was successful.

        Raises:
            APIError: If the scheduling fails.
        """
        endpoint = f"/workout-service/schedule/{workout_id}"
        payload = {"date": date}

        self.api_client.connectapi(
            endpoint,
            method="POST",
            json=payload,
            headers=self.WORKOUT_HEADERS,
        )

        return True

    def unschedule_workout(
        self,
        workout_id: Union[int, str],
        date: str,
    ) -> bool:
        """Remove a scheduled workout from a specific date.

        Args:
            workout_id: The Garmin workout ID to unschedule.
            date: Date in YYYY-MM-DD format.

        Returns:
            True if unscheduling was successful.

        Raises:
            APIError: If the unscheduling fails.
        """
        endpoint = f"/workout-service/schedule/{workout_id}"
        payload = {"date": date}

        self.api_client.connectapi(
            endpoint,
            method="DELETE",
            json=payload,
            headers=self.WORKOUT_HEADERS,
        )

        return True

    def download_fit(self, workout_id: Union[int, str]) -> bytes:
        """Download workout as FIT file.

        Args:
            workout_id: The Garmin workout ID.

        Returns:
            FIT file contents as bytes.

        Raises:
            APIError: If the download fails.
        """
        endpoint = f"/workout-service/workout/FIT/{workout_id}"

        response = self.api_client.request(
            "GET",
            "connectapi",
            endpoint,
            api=True,
            headers=self.WORKOUT_HEADERS,
        )

        return response.content

    def duplicate_workout(
        self,
        workout_id: Union[int, str],
        new_name: Optional[str] = None,
    ) -> Workout:
        """Duplicate an existing workout.

        Args:
            workout_id: The workout ID to duplicate.
            new_name: Optional new name for the duplicated workout.

        Returns:
            The newly created duplicate Workout.
        """
        original = self.get_workout(workout_id)
        if not original:
            raise ValueError(f"Workout {workout_id} not found")

        # Create a copy without the ID
        duplicate = Workout(
            name=new_name or f"{original.name} (Copy)",
            sport_type=original.sport_type,
            description=original.description,
            steps=original.steps,
        )

        return self.create_workout(duplicate)
