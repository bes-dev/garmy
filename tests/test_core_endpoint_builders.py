"""Comprehensive tests for garmy.core.endpoint_builders module.

This module provides 100% test coverage for endpoint builders.
"""

from datetime import date
from unittest.mock import Mock, patch

import pytest

from garmy.core.endpoint_builders import (
    BaseEndpointBuilder,
    SleepEndpointBuilder,
    UserSummaryEndpointBuilder,
    WellnessEndpointBuilder,
    build_calories_endpoint,
    build_daily_summary_endpoint,
    build_heart_rate_endpoint,
    build_respiration_endpoint,
    build_sleep_endpoint,
)
from garmy.core.exceptions import EndpointBuilderError


class TestBaseEndpointBuilder:
    """Test cases for BaseEndpointBuilder abstract class."""

    def test_base_endpoint_builder_is_abstract(self):
        """Test BaseEndpointBuilder cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseEndpointBuilder()

    def test_base_endpoint_builder_abstract_methods(self):
        """Test BaseEndpointBuilder has required abstract methods."""
        # Should have abstract methods
        assert hasattr(BaseEndpointBuilder, "get_endpoint_name")
        assert hasattr(BaseEndpointBuilder, "build_endpoint_url")

    def test_get_user_id_no_api_client(self):
        """Test get_user_id raises error when no API client."""

        class TestBuilder(BaseEndpointBuilder):
            def get_endpoint_name(self):
                return "test"

            def build_endpoint_url(self, user_id, date_str, **kwargs):
                return f"/test/{user_id}/{date_str}"

        builder = TestBuilder()

        with pytest.raises(EndpointBuilderError, match="API client required"):
            builder.get_user_id(None)

    def test_get_user_id_profile_settings_success(self):
        """Test get_user_id success with profile settings."""

        class TestBuilder(BaseEndpointBuilder):
            def get_endpoint_name(self):
                return "test"

            def build_endpoint_url(self, user_id, date_str, **kwargs):
                return f"/test/{user_id}/{date_str}"

        builder = TestBuilder()

        # Mock API client
        mock_api_client = Mock()
        mock_api_client.connectapi.return_value = {"displayName": "test_user_123"}

        result = builder.get_user_id(mock_api_client)

        assert result == "test_user_123"
        mock_api_client.connectapi.assert_called_once_with(
            "/userprofile-service/userprofile/settings"
        )

    def test_get_user_id_profile_settings_empty_display_name(self):
        """Test get_user_id fallback when display name is empty."""

        class TestBuilder(BaseEndpointBuilder):
            def get_endpoint_name(self):
                return "test"

            def build_endpoint_url(self, user_id, date_str, **kwargs):
                return f"/test/{user_id}/{date_str}"

        builder = TestBuilder()

        # Mock API client with empty display name
        mock_api_client = Mock()
        mock_api_client.connectapi.return_value = {"displayName": ""}
        mock_api_client.get_user_profile.return_value = {
            "userProfileId": "fallback_user"
        }

        result = builder.get_user_id(mock_api_client)

        assert result == "fallback_user"

    def test_get_user_id_social_profile_fallback(self):
        """Test get_user_id fallback to social profile."""

        class TestBuilder(BaseEndpointBuilder):
            def get_endpoint_name(self):
                return "test"

            def build_endpoint_url(self, user_id, date_str, **kwargs):
                return f"/test/{user_id}/{date_str}"

        builder = TestBuilder()

        # Mock API client - profile settings fails, social profile succeeds
        mock_api_client = Mock()
        mock_api_client.connectapi.return_value = {}  # No displayName
        mock_api_client.get_user_profile.return_value = {
            "userProfileId": "social_user_123"
        }

        result = builder.get_user_id(mock_api_client)

        assert result == "social_user_123"

    def test_get_user_id_social_profile_multiple_fields(self):
        """Test get_user_id tries multiple fields in social profile."""

        class TestBuilder(BaseEndpointBuilder):
            def get_endpoint_name(self):
                return "test"

            def build_endpoint_url(self, user_id, date_str, **kwargs):
                return f"/test/{user_id}/{date_str}"

        builder = TestBuilder()

        # Mock API client - test different field priorities
        mock_api_client = Mock()
        mock_api_client.connectapi.return_value = {}

        # Test userProfileId priority
        mock_api_client.get_user_profile.return_value = {
            "userProfileId": "profile_id",
            "id": "other_id",
            "userId": "user_id",
            "profileId": "profile_id_field",
        }

        result = builder.get_user_id(mock_api_client)
        assert result == "profile_id"

        # Test id fallback
        mock_api_client.get_user_profile.return_value = {
            "id": "other_id",
            "userId": "user_id",
            "profileId": "profile_id_field",
        }

        result = builder.get_user_id(mock_api_client)
        assert result == "other_id"

    def test_get_user_id_no_valid_user_id(self):
        """Test get_user_id raises error when no valid user ID found."""

        class TestBuilder(BaseEndpointBuilder):
            def get_endpoint_name(self):
                return "test"

            def build_endpoint_url(self, user_id, date_str, **kwargs):
                return f"/test/{user_id}/{date_str}"

        builder = TestBuilder()

        # Mock API client with no valid user ID
        mock_api_client = Mock()
        mock_api_client.connectapi.return_value = {}
        mock_api_client.get_user_profile.return_value = {}

        with pytest.raises(EndpointBuilderError, match="Unable to determine user ID"):
            builder.get_user_id(mock_api_client)

    def test_get_user_id_key_error(self):
        """Test get_user_id handles KeyError."""

        class TestBuilder(BaseEndpointBuilder):
            def get_endpoint_name(self):
                return "test"

            def build_endpoint_url(self, user_id, date_str, **kwargs):
                return f"/test/{user_id}/{date_str}"

        builder = TestBuilder()

        # Mock API client that raises KeyError
        mock_api_client = Mock()
        mock_api_client.connectapi.side_effect = KeyError("Missing key")

        with pytest.raises(
            EndpointBuilderError, match="API response structure changed"
        ):
            builder.get_user_id(mock_api_client)

    def test_get_user_id_attribute_error(self):
        """Test get_user_id handles AttributeError."""

        class TestBuilder(BaseEndpointBuilder):
            def get_endpoint_name(self):
                return "test"

            def build_endpoint_url(self, user_id, date_str, **kwargs):
                return f"/test/{user_id}/{date_str}"

        builder = TestBuilder()

        # Mock API client that raises AttributeError
        mock_api_client = Mock()
        mock_api_client.connectapi.side_effect = AttributeError("No attribute")

        with pytest.raises(
            EndpointBuilderError, match="API response structure changed"
        ):
            builder.get_user_id(mock_api_client)

    def test_get_user_id_general_exception(self):
        """Test get_user_id handles general exceptions."""

        class TestBuilder(BaseEndpointBuilder):
            def get_endpoint_name(self):
                return "test"

            def build_endpoint_url(self, user_id, date_str, **kwargs):
                return f"/test/{user_id}/{date_str}"

        builder = TestBuilder()

        # Mock API client that raises general exception
        mock_api_client = Mock()
        mock_api_client.connectapi.side_effect = ValueError("General error")

        with pytest.raises(
            EndpointBuilderError,
            match="Unable to determine user ID for test endpoint: General error",
        ):
            builder.get_user_id(mock_api_client)

    def test_get_user_id_system_exit_propagated(self):
        """Test get_user_id propagates SystemExit."""

        class TestBuilder(BaseEndpointBuilder):
            def get_endpoint_name(self):
                return "test"

            def build_endpoint_url(self, user_id, date_str, **kwargs):
                return f"/test/{user_id}/{date_str}"

        builder = TestBuilder()

        # Mock API client that raises SystemExit
        mock_api_client = Mock()
        mock_api_client.connectapi.side_effect = SystemExit("Exit")

        with pytest.raises(SystemExit):
            builder.get_user_id(mock_api_client)

    @patch("garmy.core.endpoint_builders.format_date")
    def test_build_method_success(self, mock_format_date):
        """Test build method success."""

        class TestBuilder(BaseEndpointBuilder):
            def get_endpoint_name(self):
                return "test"

            def build_endpoint_url(self, user_id, date_str, **kwargs):
                return f"/test/{user_id}/{date_str}"

        builder = TestBuilder()
        mock_format_date.return_value = "2023-12-01"

        # Mock successful user ID retrieval
        with patch.object(builder, "get_user_id", return_value="test_user"):
            result = builder.build(date.today(), Mock())

        assert result == "/test/test_user/2023-12-01"

    @patch("garmy.core.endpoint_builders.format_date")
    def test_build_method_with_kwargs(self, mock_format_date):
        """Test build method with additional kwargs."""

        class TestBuilder(BaseEndpointBuilder):
            def get_endpoint_name(self):
                return "test"

            def build_endpoint_url(self, user_id, date_str, **kwargs):
                extra = kwargs.get("extra", "")
                return f"/test/{user_id}/{date_str}{extra}"

        builder = TestBuilder()
        mock_format_date.return_value = "2023-12-01"

        # Mock successful user ID retrieval
        with patch.object(builder, "get_user_id", return_value="test_user"):
            result = builder.build(date.today(), Mock(), extra="/extra")

        assert result == "/test/test_user/2023-12-01/extra"


class TestUserSummaryEndpointBuilder:
    """Test cases for UserSummaryEndpointBuilder."""

    def test_user_summary_endpoint_builder_initialization(self):
        """Test UserSummaryEndpointBuilder initialization."""
        builder = UserSummaryEndpointBuilder("calories", "/path")

        assert builder.endpoint_name == "calories"
        assert builder.service_path == "/path"

    def test_get_endpoint_name(self):
        """Test get_endpoint_name method."""
        builder = UserSummaryEndpointBuilder("test_metric", "/path")

        assert builder.get_endpoint_name() == "test_metric"

    def test_build_endpoint_url(self):
        """Test build_endpoint_url method."""
        builder = UserSummaryEndpointBuilder("calories", "/path")

        result = builder.build_endpoint_url("user123", "2023-12-01")

        expected = (
            "/usersummary-service/usersummary/daily/user123?calendarDate=2023-12-01"
        )
        assert result == expected

    def test_build_endpoint_url_with_kwargs(self):
        """Test build_endpoint_url ignores kwargs."""
        builder = UserSummaryEndpointBuilder("calories", "/path")

        result = builder.build_endpoint_url("user123", "2023-12-01", extra="ignored")

        expected = (
            "/usersummary-service/usersummary/daily/user123?calendarDate=2023-12-01"
        )
        assert result == expected


class TestWellnessEndpointBuilder:
    """Test cases for WellnessEndpointBuilder."""

    def test_wellness_endpoint_builder_initialization(self):
        """Test WellnessEndpointBuilder initialization."""
        builder = WellnessEndpointBuilder("heart rate", "heartRate")

        assert builder.endpoint_name == "heart rate"
        assert builder.wellness_type == "heartRate"

    def test_get_endpoint_name(self):
        """Test get_endpoint_name method."""
        builder = WellnessEndpointBuilder("test_metric", "testType")

        assert builder.get_endpoint_name() == "test_metric"

    def test_build_endpoint_url_heart_rate(self):
        """Test build_endpoint_url for heart rate."""
        builder = WellnessEndpointBuilder("heart rate", "heartRate")

        result = builder.build_endpoint_url("user123", "2023-12-01")

        expected = "/wellness-service/wellness/dailyHeartRate/user123?date=2023-12-01"
        assert result == expected

    def test_build_endpoint_url_respiration(self):
        """Test build_endpoint_url for respiration."""
        builder = WellnessEndpointBuilder("respiration", "respiration")

        result = builder.build_endpoint_url("user123", "2023-12-01")

        expected = "/wellness-service/wellness/dailyRespiration/user123?date=2023-12-01"
        assert result == expected

    def test_build_endpoint_url_generic_wellness(self):
        """Test build_endpoint_url for generic wellness type."""
        builder = WellnessEndpointBuilder("stress", "stress")

        result = builder.build_endpoint_url("user123", "2023-12-01")

        expected = "/wellness-service/wellness/dailyStress/user123?date=2023-12-01"
        assert result == expected

    def test_build_endpoint_url_capitalization(self):
        """Test build_endpoint_url capitalizes wellness type."""
        builder = WellnessEndpointBuilder("custom metric", "customType")

        result = builder.build_endpoint_url("user123", "2023-12-01")

        expected = "/wellness-service/wellness/dailyCustomtype/user123?date=2023-12-01"
        assert result == expected

    def test_build_endpoint_url_with_kwargs(self):
        """Test build_endpoint_url ignores kwargs."""
        builder = WellnessEndpointBuilder("heart rate", "heartRate")

        result = builder.build_endpoint_url("user123", "2023-12-01", extra="ignored")

        expected = "/wellness-service/wellness/dailyHeartRate/user123?date=2023-12-01"
        assert result == expected


class TestSleepEndpointBuilder:
    """Test cases for SleepEndpointBuilder."""

    def test_sleep_endpoint_builder_initialization(self):
        """Test SleepEndpointBuilder can be instantiated."""
        builder = SleepEndpointBuilder()

        assert isinstance(builder, SleepEndpointBuilder)
        assert isinstance(builder, BaseEndpointBuilder)

    def test_get_endpoint_name(self):
        """Test get_endpoint_name method."""
        builder = SleepEndpointBuilder()

        assert builder.get_endpoint_name() == "sleep"

    def test_build_endpoint_url(self):
        """Test build_endpoint_url method."""
        builder = SleepEndpointBuilder()

        result = builder.build_endpoint_url("user123", "2023-12-01")

        expected = (
            "/wellness-service/wellness/dailySleepData/user123?"
            "date=2023-12-01&nonSleepBufferMinutes=60"
        )
        assert result == expected

    def test_build_endpoint_url_with_kwargs(self):
        """Test build_endpoint_url ignores kwargs."""
        builder = SleepEndpointBuilder()

        result = builder.build_endpoint_url("user123", "2023-12-01", extra="ignored")

        expected = (
            "/wellness-service/wellness/dailySleepData/user123?"
            "date=2023-12-01&nonSleepBufferMinutes=60"
        )
        assert result == expected


class TestEndpointBuilderFunctions:
    """Test cases for endpoint builder convenience functions."""

    @patch("garmy.core.endpoint_builders.SleepEndpointBuilder")
    def test_build_sleep_endpoint(self, mock_sleep_builder):
        """Test build_sleep_endpoint function."""
        mock_builder_instance = Mock()
        mock_sleep_builder.return_value = mock_builder_instance
        mock_builder_instance.build.return_value = "/sleep/endpoint"

        result = build_sleep_endpoint("2023-12-01", Mock(), extra="param")

        assert result == "/sleep/endpoint"
        mock_sleep_builder.assert_called_once()
        mock_builder_instance.build.assert_called_once_with(
            "2023-12-01", mock_builder_instance.build.call_args[0][1], extra="param"
        )

    @patch("garmy.core.endpoint_builders.WellnessEndpointBuilder")
    def test_build_heart_rate_endpoint(self, mock_wellness_builder):
        """Test build_heart_rate_endpoint function."""
        mock_builder_instance = Mock()
        mock_wellness_builder.return_value = mock_builder_instance
        mock_builder_instance.build.return_value = "/heart-rate/endpoint"

        result = build_heart_rate_endpoint("2023-12-01", Mock())

        assert result == "/heart-rate/endpoint"
        mock_wellness_builder.assert_called_once_with("heart rate", "heartRate")

    @patch("garmy.core.endpoint_builders.WellnessEndpointBuilder")
    def test_build_respiration_endpoint(self, mock_wellness_builder):
        """Test build_respiration_endpoint function."""
        mock_builder_instance = Mock()
        mock_wellness_builder.return_value = mock_builder_instance
        mock_builder_instance.build.return_value = "/respiration/endpoint"

        result = build_respiration_endpoint("2023-12-01", Mock())

        assert result == "/respiration/endpoint"
        mock_wellness_builder.assert_called_once_with("respiration", "respiration")

    @patch("garmy.core.endpoint_builders.UserSummaryEndpointBuilder")
    def test_build_calories_endpoint(self, mock_summary_builder):
        """Test build_calories_endpoint function."""
        mock_builder_instance = Mock()
        mock_summary_builder.return_value = mock_builder_instance
        mock_builder_instance.build.return_value = "/calories/endpoint"

        result = build_calories_endpoint("2023-12-01", Mock())

        assert result == "/calories/endpoint"
        mock_summary_builder.assert_called_once_with("calories", "")

    @patch("garmy.core.endpoint_builders.UserSummaryEndpointBuilder")
    def test_build_daily_summary_endpoint(self, mock_summary_builder):
        """Test build_daily_summary_endpoint function."""
        mock_builder_instance = Mock()
        mock_summary_builder.return_value = mock_builder_instance
        mock_builder_instance.build.return_value = "/daily-summary/endpoint"

        result = build_daily_summary_endpoint("2023-12-01", Mock())

        assert result == "/daily-summary/endpoint"
        mock_summary_builder.assert_called_once_with("daily summary", "")

    def test_build_sleep_endpoint_no_params(self):
        """Test build_sleep_endpoint with no parameters."""
        with patch("garmy.core.endpoint_builders.SleepEndpointBuilder") as mock_builder:
            mock_instance = Mock()
            mock_builder.return_value = mock_instance
            mock_instance.build.return_value = "/sleep/default"

            result = build_sleep_endpoint()

            assert result == "/sleep/default"
            mock_instance.build.assert_called_once_with(None, None)

    def test_build_heart_rate_endpoint_with_kwargs(self):
        """Test build_heart_rate_endpoint with kwargs."""
        with patch(
            "garmy.core.endpoint_builders.WellnessEndpointBuilder"
        ) as mock_builder:
            mock_instance = Mock()
            mock_builder.return_value = mock_instance
            mock_instance.build.return_value = "/hr/endpoint"

            result = build_heart_rate_endpoint(
                date_input="2023-12-01", api_client=Mock(), extra="test"
            )

            assert result == "/hr/endpoint"
            mock_instance.build.assert_called_once()


class TestEndpointBuilderErrorHandling:
    """Test cases for error handling in endpoint builders."""

    def test_endpoint_builder_error_creation(self):
        """Test EndpointBuilderError can be created."""
        error = EndpointBuilderError("Test error message")

        assert isinstance(error, Exception)
        assert str(error) == "Test error message"

    def test_endpoint_builder_error_with_cause(self):
        """Test EndpointBuilderError with cause."""
        original_error = ValueError("Original error")
        try:
            raise original_error
        except ValueError as e:
            error = EndpointBuilderError("Wrapper error")
            error.__cause__ = e

        assert isinstance(error, Exception)
        assert str(error) == "Wrapper error"
        assert error.__cause__ == original_error

    def test_base_endpoint_builder_error_propagation(self):
        """Test BaseEndpointBuilder error propagation."""

        class FailingBuilder(BaseEndpointBuilder):
            def get_endpoint_name(self):
                return "failing"

            def build_endpoint_url(self, user_id, date_str, **kwargs):
                raise ValueError("Build failed")

        builder = FailingBuilder()

        with patch.object(builder, "get_user_id", return_value="user123"), patch(
            "garmy.core.endpoint_builders.format_date", return_value="2023-12-01"
        ), pytest.raises(ValueError, match="Build failed"):
            builder.build(date.today(), Mock())


class TestEndpointBuilderIntegration:
    """Test cases for endpoint builder integration scenarios."""

    def test_user_summary_builder_full_integration(self):
        """Test UserSummaryEndpointBuilder full integration."""
        builder = UserSummaryEndpointBuilder("calories", "/path")

        # Mock API client
        mock_api_client = Mock()
        mock_api_client.connectapi.return_value = {"displayName": "test_user"}

        with patch(
            "garmy.core.endpoint_builders.format_date", return_value="2023-12-01"
        ):
            result = builder.build(date.today(), mock_api_client)

        expected = (
            "/usersummary-service/usersummary/daily/test_user?calendarDate=2023-12-01"
        )
        assert result == expected

    def test_wellness_builder_full_integration(self):
        """Test WellnessEndpointBuilder full integration."""
        builder = WellnessEndpointBuilder("heart rate", "heartRate")

        # Mock API client
        mock_api_client = Mock()
        mock_api_client.connectapi.return_value = {"displayName": "wellness_user"}

        with patch(
            "garmy.core.endpoint_builders.format_date", return_value="2023-12-01"
        ):
            result = builder.build(date.today(), mock_api_client)

        expected = (
            "/wellness-service/wellness/dailyHeartRate/wellness_user?date=2023-12-01"
        )
        assert result == expected

    def test_sleep_builder_full_integration(self):
        """Test SleepEndpointBuilder full integration."""
        builder = SleepEndpointBuilder()

        # Mock API client
        mock_api_client = Mock()
        mock_api_client.connectapi.return_value = {"displayName": "sleep_user"}

        with patch(
            "garmy.core.endpoint_builders.format_date", return_value="2023-12-01"
        ):
            result = builder.build(date.today(), mock_api_client)

        expected = (
            "/wellness-service/wellness/dailySleepData/sleep_user?"
            "date=2023-12-01&nonSleepBufferMinutes=60"
        )
        assert result == expected

    def test_builder_functions_integration(self):
        """Test convenience functions work with real builders."""
        mock_api_client = Mock()
        mock_api_client.connectapi.return_value = {"displayName": "integration_user"}

        with patch(
            "garmy.core.endpoint_builders.format_date", return_value="2023-12-01"
        ):
            # Test each convenience function
            sleep_result = build_sleep_endpoint("2023-12-01", mock_api_client)
            hr_result = build_heart_rate_endpoint("2023-12-01", mock_api_client)
            resp_result = build_respiration_endpoint("2023-12-01", mock_api_client)
            cal_result = build_calories_endpoint("2023-12-01", mock_api_client)
            summary_result = build_daily_summary_endpoint("2023-12-01", mock_api_client)

        # All should return valid endpoint strings
        assert "/wellness-service/wellness/dailySleepData/" in sleep_result
        assert "/wellness-service/wellness/dailyHeartRate/" in hr_result
        assert "/wellness-service/wellness/dailyRespiration/" in resp_result
        assert "/usersummary-service/usersummary/daily/" in cal_result
        assert "/usersummary-service/usersummary/daily/" in summary_result
