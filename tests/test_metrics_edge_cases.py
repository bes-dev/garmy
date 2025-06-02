"""Edge case tests for garmy.metrics module.

This module provides tests for edge cases, error conditions, and specific
implementation details to ensure 100% test coverage of the metrics module.
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from garmy.core.base import MetricConfig
from garmy.core.exceptions import ValidationError


class TestTrainingReadinessEdgeCases:
    """Edge case tests for TrainingReadiness module."""

    def test_parse_training_readiness_field_filtering(self):
        """Test field filtering in training readiness parser."""
        from garmy.metrics.training_readiness import (
            TrainingReadiness,
            parse_training_readiness_data,
        )

        with patch("garmy.core.utils.camel_to_snake_dict") as mock_convert:
            mock_convert.return_value = {
                "score": 75,
                "level": "READY",
                "feedback_long": "Ready",
                "feedback_short": "READY",
                "calendar_date": "2023-12-01",
                "timestamp": "2023-12-01T08:00:00Z",
                "user_profile_pk": 12345,
                "device_id": 67890,
                "unknown_field": "should_be_filtered",
                "another_unknown": 123,
            }

            result = parse_training_readiness_data({})

            assert isinstance(result, TrainingReadiness)
            assert result.score == 75
            # Unknown fields should be filtered out
            assert not hasattr(result, "unknown_field")
            assert not hasattr(result, "another_unknown")

    def test_parse_training_readiness_datetime_edge_cases(self):
        """Test datetime parsing edge cases."""
        from garmy.metrics.training_readiness import parse_training_readiness_data

        # Test with various datetime formats
        test_cases = [
            "2023-12-01T08:00:00Z",
            "2023-12-01T08:00:00.000Z",
            "2023-12-01T08:00:00+00:00",
            "invalid-datetime",
            None,
            123456789,  # Non-string value
        ]

        for timestamp_value in test_cases:
            with patch("garmy.core.utils.camel_to_snake_dict") as mock_convert:
                mock_convert.return_value = {
                    "score": 75,
                    "level": "READY",
                    "feedback_long": "Ready",
                    "feedback_short": "READY",
                    "calendar_date": "2023-12-01",
                    "timestamp": timestamp_value,
                    "user_profile_pk": 12345,
                    "device_id": 67890,
                }

                result = parse_training_readiness_data({})

                # Should not raise exception, but timestamp might be None
                from garmy.metrics.training_readiness import TrainingReadiness

                assert isinstance(result, TrainingReadiness)
                if timestamp_value == "invalid-datetime":
                    assert result.timestamp is None
                elif timestamp_value in [None, 123456789]:
                    # Non-string values are passed through as-is
                    assert result.timestamp == timestamp_value
                else:
                    # Valid datetime strings should parse correctly
                    assert isinstance(result.timestamp, datetime)

    def test_training_readiness_with_all_optional_fields(self):
        """Test TrainingReadiness with all possible optional fields."""
        from garmy.metrics.training_readiness import TrainingReadiness

        tr = TrainingReadiness(
            score=85,
            level="HIGH",
            feedback_long="Excellent readiness",
            feedback_short="HIGH",
            calendar_date="2023-12-01",
            timestamp=datetime(2023, 12, 1, 8, 0, 0),
            user_profile_pk=12345,
            device_id=67890,
            timestamp_local=datetime(2023, 12, 1, 9, 0, 0),
            sleep_score=90,
            sleep_score_factor_percent=30,
            sleep_score_factor_feedback="Excellent sleep",
            sleep_history_factor_percent=25,
            sleep_history_factor_feedback="Consistent pattern",
            valid_sleep=True,
            hrv_factor_percent=35,
            hrv_factor_feedback="HRV excellent",
            hrv_weekly_average=50,
            recovery_time=6,
            recovery_time_factor_percent=10,
            recovery_time_factor_feedback="Quick recovery",
            recovery_time_change_phrase="Improved from yesterday",
            acwr_factor_percent=15,
            acwr_factor_feedback="Balanced load",
            acute_load=120,
            stress_history_factor_percent=5,
            stress_history_factor_feedback="Low stress",
            input_context="All sensors active",
            primary_activity_tracker=True,
        )

        # Verify all fields are set correctly
        assert tr.score == 85
        assert tr.sleep_score == 90
        assert tr.hrv_weekly_average == 50
        assert tr.recovery_time == 6
        assert tr.acute_load == 120
        assert tr.primary_activity_tracker is True


class TestBodyBatteryEdgeCases:
    """Edge case tests for BodyBattery module."""

    def test_body_battery_readings_malformed_data(self):
        """Test BodyBattery readings with various malformed data."""
        from garmy.metrics.body_battery import BodyBattery

        bb = BodyBattery(
            user_profile_pk=12345,
            calendar_date="2023-12-01",
            body_battery_values_array=[
                [],  # Empty array
                [1701415200000],  # Missing fields
                [1701418800000, "CHARGING"],  # Missing level
                [1701422400000, "DRAINING", 70],  # Missing version
                [1701425600000, "ACTIVE", 65, 1.0],  # Complete
                [1701429200000, "UNKNOWN", 60, 1.0, "extra"],  # Extra fields
            ],
        )

        readings = bb.body_battery_readings

        # Should only process arrays with at least 4 elements
        assert len(readings) == 2  # Only the last 2 arrays with 4+ elements

        # Test that missing version defaults to 1.0
        assert readings[0].version == 1.0
        assert readings[1].version == 1.0

    def test_body_battery_with_stress_data(self):
        """Test BodyBattery with all optional stress-related fields."""
        from garmy.metrics.body_battery import BodyBattery

        bb = BodyBattery(
            user_profile_pk=12345,
            calendar_date="2023-12-01",
            body_battery_values_array=[],
            start_timestamp_gmt=datetime(2023, 12, 1, 0, 0, 0),
            end_timestamp_gmt=datetime(2023, 12, 1, 23, 59, 59),
            max_stress_level=55,
            avg_stress_level=30,
            stress_chart_value_offset=10,
            stress_chart_y_axis_origin=0,
            stress_value_descriptors_dto_list=[{"key": "timestamp", "index": 0}],
            stress_values_array=[[1701415200000, 25, 1.0]],
            body_battery_value_descriptors_dto_list=[{"key": "timestamp", "index": 0}],
        )

        assert bb.max_stress_level == 55
        assert bb.avg_stress_level == 30
        assert bb.stress_chart_value_offset == 10
        assert len(bb.stress_values_array) == 1
        assert len(bb.stress_value_descriptors_dto_list) == 1
        assert len(bb.body_battery_value_descriptors_dto_list) == 1


class TestSleepEdgeCases:
    """Edge case tests for Sleep module."""

    def test_sleep_summary_with_extreme_values(self):
        """Test SleepSummary with extreme values."""
        from garmy.metrics.sleep import SleepSummary

        # Test with very long sleep
        summary = SleepSummary(
            sleep_time_seconds=43200,  # 12 hours
            deep_sleep_seconds=21600,  # 6 hours (50%)
            light_sleep_seconds=14400,  # 4 hours
            rem_sleep_seconds=7200,  # 2 hours
            awake_sleep_seconds=0,  # No awake time
            sleep_start_timestamp_local=1701385200000,
            sleep_end_timestamp_local=1701428400000,  # 12 hours later
        )

        assert summary.total_sleep_duration_hours == 12.0
        efficiency = summary.sleep_efficiency_percentage
        assert 0 <= efficiency <= 100

    def test_sleep_summary_with_no_sleep(self):
        """Test SleepSummary with zero sleep time."""
        from garmy.metrics.sleep import SleepSummary

        summary = SleepSummary(
            sleep_time_seconds=0,
            deep_sleep_seconds=0,
            light_sleep_seconds=0,
            rem_sleep_seconds=0,
            awake_sleep_seconds=0,
        )

        assert summary.total_sleep_duration_hours == 0.0
        assert summary.sleep_efficiency_percentage == 0

    def test_sleep_with_extensive_raw_data(self):
        """Test Sleep with extensive raw data lists."""
        from garmy.metrics.sleep import Sleep, SleepSummary

        summary = SleepSummary(sleep_time_seconds=28800)

        # Create large lists to test counting
        large_spo2_list = [{"timestamp": i, "value": 95 + (i % 5)} for i in range(100)]
        large_respiration_list = [
            {"timestamp": i, "value": 14.0 + (i % 3)} for i in range(50)
        ]
        large_movement_list = [
            {"timestamp": i, "activity": 0.1 * (i % 10)} for i in range(200)
        ]

        sleep = Sleep(
            sleep_summary=summary,
            wellness_epoch_spo2_data_dto_list=large_spo2_list,
            wellness_epoch_respiration_data_dto_list=large_respiration_list,
            sleep_movement=large_movement_list,
        )

        assert sleep.spo2_readings_count == 100
        assert sleep.respiration_readings_count == 50
        assert sleep.movement_readings_count == 200

    def test_sleep_endpoint_builder_parameters(self):
        """Test Sleep endpoint builder with various parameters."""
        from garmy.metrics.sleep import build_sleep_endpoint

        with patch("garmy.metrics.sleep._build_sleep_endpoint") as mock_builder:
            mock_builder.return_value = "/test/endpoint"

            # Test with different parameter combinations
            test_cases = [
                ("2023-12-01", None, {}),
                (None, Mock(), {"user_id": 12345}),
                ("2023-12-01", Mock(), {"user_id": 12345, "extra": "param"}),
            ]

            for date_input, api_client, kwargs in test_cases:
                result = build_sleep_endpoint(date_input, api_client, **kwargs)
                assert result == "/test/endpoint"
                mock_builder.assert_called_with(date_input, api_client, **kwargs)


class TestActivitiesEdgeCases:
    """Edge case tests for Activities module."""

    def test_activity_summary_edge_case_properties(self):
        """Test ActivitySummary properties with edge case values."""
        from garmy.metrics.activities import ActivitySummary

        # Test with missing/empty nested dicts
        activity = ActivitySummary(
            activity_type={},  # Empty dict
            event_type={"typeId": 1},  # Missing typeKey
            privacy={"typeKey": "private"},  # Missing typeId
            duration=0,  # Zero duration
            average_hr=None,
            max_hr=150.0,  # Only max HR
            difference_stress=0.0,  # Exactly zero stress difference
        )

        # Test property methods handle missing keys gracefully
        assert activity.activity_type_name == "unknown"
        assert activity.activity_type_id == 0
        assert activity.privacy_type == "private"

        # Test duration properties with zero
        assert activity.duration_minutes == 0.0
        assert activity.duration_hours == 0.0

        # Test heart rate properties
        assert activity.heart_rate_range is None  # Missing average HR
        assert activity.has_heart_rate is False

        # Test stress impact with exactly zero
        assert activity.stress_impact == "stress_neutral"

    def test_activity_summary_with_very_large_values(self):
        """Test ActivitySummary with very large values."""
        from garmy.metrics.activities import ActivitySummary

        activity = ActivitySummary(
            duration=86400.0,  # 24 hours in seconds
            moving_duration=82800.0,  # 23 hours
            average_hr=200.0,
            max_hr=220.0,
            difference_stress=100.0,  # Very high stress change
            difference_body_battery=-50,  # Large battery drain
        )

        assert activity.duration_hours == 24.0
        assert activity.moving_duration_minutes == 1380.0  # 23 * 60
        assert activity.heart_rate_range == 20.0
        assert activity.stress_impact == "stress_increasing"

    def test_parse_datetime_cached_performance(self):
        """Test datetime caching performance and edge cases."""
        from garmy.metrics.activities import _parse_datetime_cached

        # Test caching by calling same value multiple times
        test_datetime = "2023-12-01 07:00:00"

        result1 = _parse_datetime_cached(test_datetime)
        result2 = _parse_datetime_cached(test_datetime)
        result3 = _parse_datetime_cached(test_datetime)

        # Should return same datetime object due to caching
        assert result1 == result2 == result3
        assert isinstance(result1, datetime)

    def test_activities_accessor_error_handling(self):
        """Test ActivitiesAccessor error handling."""
        from garmy.metrics.activities import ActivitiesAccessor

        mock_api_client = Mock()
        accessor = ActivitiesAccessor(mock_api_client)

        # Test with different exception types
        test_exceptions = [
            SystemExit("System exit"),
            KeyboardInterrupt("Keyboard interrupt"),
            GeneratorExit("Generator exit"),
            ValueError("Regular exception"),
        ]

        for exception in test_exceptions:
            mock_api_client.connectapi.side_effect = exception

            if isinstance(exception, (SystemExit, KeyboardInterrupt, GeneratorExit)):
                # These should be re-raised
                with pytest.raises(type(exception)):
                    accessor.raw()
            else:
                # Other exceptions should be handled
                with patch("garmy.core.utils.handle_api_exception") as mock_handle:
                    mock_handle.return_value = []
                    result = accessor.raw()
                    assert result == []

    def test_activities_accessor_get_recent_edge_cases(self):
        """Test get_recent method edge cases."""
        from garmy.metrics.activities import ActivitiesAccessor, ActivitySummary

        mock_api_client = Mock()
        accessor = ActivitiesAccessor(mock_api_client)

        # Test with activities that have None datetime
        with patch.object(accessor, "list") as mock_list:
            # Create activity and mock its datetime property to return None
            activity_with_none_datetime = ActivitySummary(activity_id=1)

            # Mock the property method to return None
            with patch.object(
                type(activity_with_none_datetime),
                "start_datetime_local",
                new_callable=lambda: property(lambda self: None),
            ):
                mock_list.return_value = [activity_with_none_datetime]

                result = accessor.get_recent(days=7)

                # Should filter out activities with None datetime
                assert result == []

    def test_activities_accessor_get_by_type_case_insensitive(self):
        """Test get_by_type is case insensitive."""
        from garmy.metrics.activities import ActivitiesAccessor, ActivitySummary

        mock_api_client = Mock()
        accessor = ActivitiesAccessor(mock_api_client)

        with patch.object(accessor, "list") as mock_list:
            activities = [
                ActivitySummary(activity_id=1, activity_type={"typeKey": "Running"}),
                ActivitySummary(activity_id=2, activity_type={"typeKey": "CYCLING"}),
                ActivitySummary(activity_id=3, activity_type={"typeKey": "swimming"}),
            ]

            mock_list.return_value = activities

            # Test case insensitive matching
            result = accessor.get_by_type("running")
            assert len(result) == 1
            assert result[0].activity_id == 1

            result = accessor.get_by_type("SWIMMING")
            assert len(result) == 1
            assert result[0].activity_id == 3


class TestHeartRateEdgeCases:
    """Edge case tests for HeartRate module."""

    def test_heart_rate_summary_with_extreme_values(self):
        """Test HeartRateSummary with extreme heart rate values."""
        from garmy.metrics.heart_rate import HeartRateSummary

        summary = HeartRateSummary(
            max_heart_rate=250,  # Very high
            min_heart_rate=30,  # Very low
            resting_heart_rate=35,
            last_seven_days_avg_resting_heart_rate=38,
        )

        assert summary.heart_rate_range == 220

    def test_heart_rate_average_with_mixed_data(self):
        """Test heart rate average calculation with mixed valid/invalid data."""
        from garmy.metrics.heart_rate import HeartRate, HeartRateSummary

        summary = HeartRateSummary()
        hr = HeartRate(
            heart_rate_summary=summary,
            heart_rate_values_array=[
                [1701415200000, 60],  # Valid
                [1701415500000, 0],  # Zero (but should count)
                [1701415800000, None],  # None (invalid)
                [1701416100000],  # Missing value (invalid)
                [1701416400000, 70],  # Valid
                [],  # Empty array (invalid)
                [1701416700000, 80, "extra"],  # Extra data (valid)
            ],
        )

        # Should calculate average of: 60, 0, 70, 80 = 210/4 = 52.5
        assert hr.average_heart_rate == 52.5

    def test_heart_rate_endpoint_builder_edge_cases(self):
        """Test HeartRate endpoint builder edge cases."""
        from garmy.metrics.heart_rate import build_heart_rate_endpoint

        with patch(
            "garmy.metrics.heart_rate._build_heart_rate_endpoint"
        ) as mock_builder:
            mock_builder.return_value = "/test/endpoint"

            # Test with None values
            result = build_heart_rate_endpoint(None, None)
            assert result == "/test/endpoint"

            # Test with extra kwargs
            result = build_heart_rate_endpoint(
                "2023-12-01", Mock(), user_id=12345, extra_param="test", another=123
            )
            assert result == "/test/endpoint"


class TestMetricConfigValidation:
    """Test MetricConfig validation and edge cases."""

    def test_metric_config_post_init_validation(self):
        """Test MetricConfig __post_init__ validation."""
        from garmy.metrics.training_readiness import TrainingReadiness

        # Test valid config
        config = MetricConfig(metric_class=TrainingReadiness, endpoint="/test/endpoint")
        assert config.metric_class == TrainingReadiness

        # Test with endpoint_builder instead of endpoint
        mock_builder = Mock()
        config2 = MetricConfig(
            metric_class=TrainingReadiness, endpoint="", endpoint_builder=mock_builder
        )
        assert config2.endpoint_builder == mock_builder

    def test_metric_config_validation_errors(self):
        """Test MetricConfig validation errors."""
        from garmy.metrics.training_readiness import TrainingReadiness

        # Test missing both endpoint and endpoint_builder
        with pytest.raises(
            ValidationError,
            match="Either endpoint or endpoint_builder must be provided",
        ):
            MetricConfig(
                metric_class=TrainingReadiness, endpoint="", endpoint_builder=None
            )

        # Test non-dataclass metric_class
        with pytest.raises(ValidationError, match="must be a dataclass"):
            MetricConfig(metric_class=str, endpoint="/test/endpoint")  # Not a dataclass

    def test_metric_config_optional_fields(self):
        """Test MetricConfig with all optional fields."""
        from garmy.metrics.training_readiness import TrainingReadiness

        mock_parser = Mock()
        mock_builder = Mock()

        config = MetricConfig(
            metric_class=TrainingReadiness,
            endpoint="/test/endpoint",
            parser=mock_parser,
            endpoint_builder=mock_builder,
            requires_user_id=True,
            description="Test metric",
            version="2.0",
            deprecated=True,
        )

        assert config.parser == mock_parser
        assert config.endpoint_builder == mock_builder
        assert config.requires_user_id is True
        assert config.description == "Test metric"
        assert config.version == "2.0"
        assert config.deprecated is True


class TestModuleImportsAndStructure:
    """Test module imports and structure edge cases."""

    def test_import_all_metric_classes_directly(self):
        """Test importing all metric classes directly."""
        from garmy.metrics.activities import ActivitySummary
        from garmy.metrics.body_battery import BodyBattery
        from garmy.metrics.heart_rate import HeartRate
        from garmy.metrics.sleep import Sleep
        from garmy.metrics.training_readiness import TrainingReadiness

        classes = [TrainingReadiness, BodyBattery, Sleep, ActivitySummary, HeartRate]

        for cls in classes:
            assert hasattr(cls, "__dataclass_fields__")
            assert cls.__module__.startswith("garmy.metrics.")

    def test_metric_module_attributes(self):
        """Test metric modules have expected attributes."""
        import garmy.metrics.activities as act_module
        import garmy.metrics.body_battery as bb_module
        import garmy.metrics.training_readiness as tr_module

        # Test training_readiness specific attributes
        assert hasattr(tr_module, "parse_training_readiness_data")
        assert hasattr(tr_module, "_create_default_training_readiness")

        # Test body_battery specific attributes
        assert hasattr(bb_module, "BodyBatteryReading")
        assert hasattr(bb_module, "parse_body_battery_data")

        # Test activities specific attributes
        assert hasattr(act_module, "ActivitiesAccessor")
        assert hasattr(act_module, "create_activities_accessor")
        assert hasattr(act_module, "_parse_datetime_cached")

    def test_custom_accessor_factory_attribute(self):
        """Test activities module has custom accessor factory."""
        import garmy.metrics.activities as act_module

        assert hasattr(act_module, "__custom_accessor_factory__")
        assert callable(act_module.__custom_accessor_factory__)

        # Test factory function works
        mock_api_client = Mock()
        accessor = act_module.__custom_accessor_factory__(mock_api_client)
        assert accessor.api_client == mock_api_client


if __name__ == "__main__":
    pytest.main([__file__])
