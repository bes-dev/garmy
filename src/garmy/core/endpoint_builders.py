"""
Endpoint Builders for Garmin Connect API.

========================================

This module provides base classes and utilities for building API endpoints
with common patterns like user ID resolution, date formatting, and error handling.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Union

if TYPE_CHECKING:
    from datetime import date

from .exceptions import EndpointBuilderError
from .utils import format_date


class BaseEndpointBuilder(ABC):
    """Base class for API endpoint builders.

    Provides common functionality for building endpoints that require
    user ID resolution, date formatting, and consistent error handling.
    """

    @abstractmethod
    def get_endpoint_name(self) -> str:
        """Get the name of the endpoint for error messages."""
        pass

    @abstractmethod
    def build_endpoint_url(self, user_id: str, date_str: str, **kwargs: Any) -> str:
        """Build the final endpoint URL with user ID and date."""
        pass

    def get_user_id(self, api_client: Any) -> str:
        """Get user ID from API client with robust error handling.

        Args:
            api_client: API client instance

        Returns:
            User ID string

        Raises:
            EndpointBuilderError: If user ID cannot be determined
        """
        if not api_client:
            raise EndpointBuilderError(
                f"API client required for {self.get_endpoint_name()} endpoint"
            )

        try:
            # Try primary method: profile settings
            profile = api_client.connectapi("/userprofile-service/userprofile/settings")
            if isinstance(profile, dict) and "displayName" in profile:
                user_id = str(profile["displayName"])
                if user_id:
                    return user_id

            # Fallback: try social profile
            social_profile = api_client.get_user_profile()
            user_id = str(
                social_profile.get("userProfileId")
                or social_profile.get("id")
                or social_profile.get("userId")
                or social_profile.get("profileId", "")
            )

            if not user_id:
                raise EndpointBuilderError(
                    f"Unable to determine user ID for {self.get_endpoint_name()} endpoint"
                )

            return user_id

        except (SystemExit, KeyboardInterrupt, GeneratorExit):
            raise
        except (KeyError, AttributeError, TypeError) as e:
            raise EndpointBuilderError(
                f"Unable to determine user ID for {self.get_endpoint_name()} endpoint: "
                f"API response structure changed: {e}"
            ) from e
        except Exception as e:
            raise EndpointBuilderError(
                f"Unable to determine user ID for {self.get_endpoint_name()} endpoint: {e}"
            ) from e

    def build(
        self,
        date_input: Union["date", str, None] = None,
        api_client: Any = None,
        **kwargs: Any,
    ) -> str:
        """Build the complete endpoint URL.

        Args:
            date_input: Date for the request
            api_client: API client instance
            **kwargs: Additional parameters for endpoint building

        Returns:
            Complete endpoint URL

        Raises:
            EndpointBuilderError: If endpoint building fails
        """
        user_id = self.get_user_id(api_client)
        date_str = format_date(date_input)
        return self.build_endpoint_url(user_id, date_str, **kwargs)


class UserSummaryEndpointBuilder(BaseEndpointBuilder):
    """Builder for user summary service endpoints."""

    def __init__(self, endpoint_name: str, service_path: str):
        """Initialize with endpoint details.

        Args:
            endpoint_name: Name for error messages (e.g., "calories")
            service_path: Service path after user ID (e.g., "?calendarDate={date}")
        """
        self.endpoint_name = endpoint_name
        self.service_path = service_path

    def get_endpoint_name(self) -> str:
        """Get the name of this endpoint."""
        return self.endpoint_name

    def build_endpoint_url(self, user_id: str, date_str: str, **kwargs: Any) -> str:
        """Build user summary service URL."""
        return (
            f"/usersummary-service/usersummary/daily/{user_id}?calendarDate={date_str}"
        )


class WellnessEndpointBuilder(BaseEndpointBuilder):
    """Builder for wellness service endpoints."""

    def __init__(self, endpoint_name: str, wellness_type: str):
        """Initialize with endpoint details.

        Args:
            endpoint_name: Name for error messages (e.g., "heart rate")
            wellness_type: Type of wellness data (e.g., "heartRate")
        """
        self.endpoint_name = endpoint_name
        self.wellness_type = wellness_type

    def get_endpoint_name(self) -> str:
        """Get the name of this endpoint."""
        return self.endpoint_name

    def build_endpoint_url(self, user_id: str, date_str: str, **kwargs: Any) -> str:
        """Build wellness service URL."""
        # Use the wellness_type for the URL path
        if self.wellness_type == "heartRate":
            return (
                f"/wellness-service/wellness/dailyHeartRate/{user_id}?date={date_str}"
            )
        elif self.wellness_type == "respiration":
            return (
                f"/wellness-service/wellness/dailyRespiration/{user_id}?date={date_str}"
            )
        else:
            return (
                f"/wellness-service/wellness/daily{self.wellness_type.capitalize()}/"
                f"{user_id}?date={date_str}"
            )


class SleepEndpointBuilder(BaseEndpointBuilder):
    """Builder for sleep service endpoints."""

    def get_endpoint_name(self) -> str:
        """Get the name of this endpoint."""
        return "sleep"

    def build_endpoint_url(self, user_id: str, date_str: str, **kwargs: Any) -> str:
        """Build sleep service URL."""
        return (
            f"/wellness-service/wellness/dailySleepData/{user_id}"
            f"?date={date_str}&nonSleepBufferMinutes=60"
        )


# Endpoint builder functions for metric modules
# These functions provide a simple interface for metrics to build their endpoints
def build_sleep_endpoint(
    date_input: Union["date", str, None] = None, api_client: Any = None, **kwargs: Any
) -> str:
    """Build sleep endpoint URL."""
    builder = SleepEndpointBuilder()
    return builder.build(date_input, api_client, **kwargs)


def build_heart_rate_endpoint(
    date_input: Union["date", str, None] = None, api_client: Any = None, **kwargs: Any
) -> str:
    """Build heart rate endpoint URL."""
    builder = WellnessEndpointBuilder("heart rate", "heartRate")
    return builder.build(date_input, api_client, **kwargs)


def build_respiration_endpoint(
    date_input: Union["date", str, None] = None, api_client: Any = None, **kwargs: Any
) -> str:
    """Build respiration endpoint URL."""
    builder = WellnessEndpointBuilder("respiration", "respiration")
    return builder.build(date_input, api_client, **kwargs)


def build_calories_endpoint(
    date_input: Union["date", str, None] = None, api_client: Any = None, **kwargs: Any
) -> str:
    """Build calories endpoint URL."""
    builder = UserSummaryEndpointBuilder("calories", "")
    return builder.build(date_input, api_client, **kwargs)


def build_daily_summary_endpoint(
    date_input: Union["date", str, None] = None, api_client: Any = None, **kwargs: Any
) -> str:
    """Build daily summary endpoint URL."""
    builder = UserSummaryEndpointBuilder("daily summary", "")
    return builder.build(date_input, api_client, **kwargs)
