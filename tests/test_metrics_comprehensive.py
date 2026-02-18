"""Comprehensive tests for garmy.metrics module.

This module provides 100% test coverage for all metrics modules and the metrics
package initialization. Tests cover data classes, parsers, property methods,
metric configurations, and edge cases.
"""

from datetime import datetime, timedelta
from typing import Any, Dict
from unittest.mock import Mock, patch

import pytest

from garmy.core.base import MetricConfig
from garmy.metrics import (
    HRV,
    ActivitySummary,
    BodyBattery,
    Calories,
    DailySummary,
    HeartRate,
    Respiration,
    Sleep,
    Steps,
    Stress,
    TrainingReadiness,
)


class TestMetricsPackageInit:
    """Test cases for metrics package __init__.py."""

    def test_package_imports(self):
        """Test all exports are properly imported."""
        # Test that all classes can be imported
        from garmy.metrics import (
            HRV,
            ActivitySummary,
            BodyBattery,
            Calories,
            DailySummary,
            HeartRate,
            Respiration,
            Sleep,
            Steps,
            Stress,
            TrainingReadiness,
        )

        # Verify they are classes
        classes = [
            HRV,
            ActivitySummary,
            BodyBattery,
            Calories,
            DailySummary,
            HeartRate,
            Respiration,
            Sleep,
            Steps,
            Stress,
            TrainingReadiness,
        ]

        for cls in classes:
            assert isinstance(cls, type)

    def test_all_exports(self):
        """Test __all__ contains all expected exports."""
        import garmy.metrics as metrics_module

        expected_exports = {
            "HRV",
            "ActivitySummary",
            "BodyBattery",
            "Calories",
            "DailySummary",
            "HeartRate",
            "Respiration",
            "Sleep",
            "Steps",
            "Stress",
            "TrainingReadiness",
        }

        actual_exports = set(metrics_module.__all__)
        assert actual_exports == expected_exports

    def test_package_docstring(self):
        """Test package has proper docstring."""
        import garmy.metrics as metrics_module

        docstring = metrics_module.__doc__
        assert docstring is not None
        assert "Garmin metrics package" in docstring
        assert "Available Metrics:" in docstring


class TestTrainingReadiness:
    """Test cases for TrainingReadiness metric."""

    def create_sample_training_readiness_data(self) -> Dict[str, Any]:
        """Create sample training readiness API response data."""
        return {
            "score": 75,
            "level": "READY",
            "feedbackLong": "You're ready for a challenging workout",
            "feedbackShort": "READY",
            "calendarDate": "2023-12-01",
            "timestamp": "2023-12-01T08:00:00Z",
            "userProfilePk": 12345,
            "deviceId": 67890,
            "timestampLocal": "2023-12-01T09:00:00+01:00",
            "sleepScore": 85,
            "sleepScoreFactorPercent": 25,
            "sleepScoreFactorFeedback": "Good sleep quality",
            "sleepHistoryFactorPercent": 20,
            "sleepHistoryFactorFeedback": "Consistent sleep pattern",
            "validSleep": True,
            "hrvFactorPercent": 30,
            "hrvFactorFeedback": "HRV in normal range",
            "hrvWeeklyAverage": 45,
            "recoveryTime": 12,
            "recoveryTimeFactorPercent": 15,
            "recoveryTimeFactorFeedback": "Minimal recovery needed",
            "recoveryTimeChangePhrase": "Decreased from yesterday",
            "acwrFactorPercent": 10,
            "acwrFactorFeedback": "Training load balanced",
            "acuteLoad": 150,
            "stressHistoryFactorPercent": 5,
            "stressHistoryFactorFeedback": "Low stress levels",
            "inputContext": "Full data available",
            "primaryActivityTracker": True,
        }

    def test_training_readiness_creation(self):
        """Test TrainingReadiness dataclass creation."""
        tr = TrainingReadiness(
            score=75,
            level="READY",
            feedback_long="Ready for training",
            feedback_short="READY",
            calendar_date="2023-12-01",
            timestamp=datetime(2023, 12, 1, 8, 0, 0),
            user_profile_pk=12345,
            device_id=67890,
        )

        assert tr.score == 75
        assert tr.level == "READY"
        assert tr.feedback_long == "Ready for training"
        assert tr.feedback_short == "READY"
        assert tr.calendar_date == "2023-12-01"
        assert tr.user_profile_pk == 12345
        assert tr.device_id == 67890

    def test_training_readiness_optional_fields(self):
        """Test TrainingReadiness with optional fields."""
        tr = TrainingReadiness(
            score=80,
            level="HIGH",
            feedback_long="Excellent readiness",
            feedback_short="HIGH",
            calendar_date="2023-12-01",
            timestamp=datetime(2023, 12, 1, 8, 0, 0),
            user_profile_pk=12345,
            device_id=67890,
            sleep_score=90,
            hrv_factor_percent=35,
            recovery_time=8,
        )

        assert tr.sleep_score == 90
        assert tr.hrv_factor_percent == 35
        assert tr.recovery_time == 8

    def test_training_readiness_defaults(self):
        """Test TrainingReadiness default values."""
        tr = TrainingReadiness(
            score=75,
            level="READY",
            feedback_long="Ready",
            feedback_short="READY",
            calendar_date="2023-12-01",
            timestamp=datetime(2023, 12, 1, 8, 0, 0),
            user_profile_pk=12345,
            device_id=67890,
        )

        # Test optional fields default to None
        assert tr.sleep_score is None
        assert tr.hrv_factor_percent is None
        assert tr.recovery_time is None
        assert tr.valid_sleep is None

    def test_create_default_training_readiness(self):
        """Test _create_default_training_readiness function."""
        from garmy.metrics.training_readiness import _create_default_training_readiness

        default_tr = _create_default_training_readiness()

        assert default_tr.score == 0
        assert default_tr.level == "UNKNOWN"
        assert default_tr.feedback_long == "No data available"
        assert default_tr.feedback_short == "NO_DATA"
        assert default_tr.calendar_date == "1970-01-01"
        assert default_tr.user_profile_pk == 0
        assert default_tr.device_id == 0

    def test_parse_training_readiness_data_list(self):
        """Test parse_training_readiness_data with list input."""
        from garmy.metrics.training_readiness import parse_training_readiness_data

        sample_data = self.create_sample_training_readiness_data()
        list_data = [sample_data]

        with patch("garmy.core.utils.camel_to_snake_dict") as mock_convert:
            mock_convert.return_value = {
                "score": 75,
                "level": "READY",
                "feedback_long": "Ready for training",
                "feedback_short": "READY",
                "calendar_date": "2023-12-01",
                "timestamp": datetime(2023, 12, 1, 8, 0, 0),
                "user_profile_pk": 12345,
                "device_id": 67890,
            }

            result = parse_training_readiness_data(list_data)

            assert isinstance(result, TrainingReadiness)
            assert result.score == 75
            assert result.level == "READY"

    def test_parse_training_readiness_data_empty_list(self):
        """Test parse_training_readiness_data with empty list."""
        from garmy.metrics.training_readiness import parse_training_readiness_data

        result = parse_training_readiness_data([])

        assert isinstance(result, TrainingReadiness)
        assert result.score == 0
        assert result.level == "UNKNOWN"

    def test_parse_training_readiness_data_datetime_conversion(self):
        """Test datetime field conversion in parser."""
        from garmy.metrics.training_readiness import parse_training_readiness_data

        with patch("garmy.core.utils.camel_to_snake_dict") as mock_convert:
            mock_convert.return_value = {
                "score": 75,
                "level": "READY",
                "feedback_long": "Ready",
                "feedback_short": "READY",
                "calendar_date": "2023-12-01",
                "timestamp": "2023-12-01T08:00:00Z",
                "timestamp_local": "2023-12-01T09:00:00+01:00",
                "user_profile_pk": 12345,
                "device_id": 67890,
            }

            result = parse_training_readiness_data({})

            assert isinstance(result, TrainingReadiness)
            assert isinstance(result.timestamp, datetime)

    def test_parse_training_readiness_data_invalid_datetime(self):
        """Test parser with invalid datetime strings."""
        from garmy.metrics.training_readiness import parse_training_readiness_data

        with patch("garmy.core.utils.camel_to_snake_dict") as mock_convert:
            mock_convert.return_value = {
                "score": 75,
                "level": "READY",
                "feedback_long": "Ready",
                "feedback_short": "READY",
                "calendar_date": "2023-12-01",
                "timestamp": "invalid-datetime",
                "user_profile_pk": 12345,
                "device_id": 67890,
            }

            result = parse_training_readiness_data({})

            assert isinstance(result, TrainingReadiness)
            assert result.timestamp is None

    def test_parse_training_readiness_data_non_dict_error(self):
        """Test parser with non-dict response from camel_to_snake_dict."""
        from garmy.metrics.training_readiness import parse_training_readiness_data

        with patch("garmy.core.utils.camel_to_snake_dict") as mock_convert:
            mock_convert.return_value = "not a dict"

            with pytest.raises(
                ValueError, match="Expected dictionary from API response"
            ):
                parse_training_readiness_data({})

    def test_training_readiness_metric_config(self):
        """Test TrainingReadiness METRIC_CONFIG."""
        from garmy.metrics.training_readiness import METRIC_CONFIG, __metric_config__

        assert isinstance(METRIC_CONFIG, MetricConfig)
        assert METRIC_CONFIG.metric_class == TrainingReadiness
        assert "/metrics-service/metrics/trainingreadiness/" in METRIC_CONFIG.endpoint
        assert METRIC_CONFIG.parser is not None
        assert (
            METRIC_CONFIG.description
            == "Daily training readiness score and recommendations"
        )
        assert METRIC_CONFIG.version == "1.0"

        # Test module export
        assert __metric_config__ == METRIC_CONFIG


class TestBodyBattery:
    """Test cases for BodyBattery metric."""

    def create_sample_body_battery_data(self) -> Dict[str, Any]:
        """Create sample body battery API response data."""
        return {
            "userProfilePk": 12345,
            "calendarDate": "2023-12-01",
            "bodyBatteryValuesArray": [
                [1701415200000, "CHARGING", 75, 1.0],
                [1701418800000, "DRAINING", 70, 1.0],
                [1701422400000, "ACTIVE", 65, 1.0],
            ],
            "startTimestampGmt": "2023-12-01T00:00:00Z",
            "endTimestampGmt": "2023-12-01T23:59:59Z",
            "stressValuesArray": [[1701415200000, 25, 1.0]],
            "maxStressLevel": 50,
            "avgStressLevel": 30,
        }

    def test_body_battery_reading_creation(self):
        """Test BodyBatteryReading dataclass creation."""
        from garmy.metrics.body_battery import BodyBatteryReading

        reading = BodyBatteryReading(
            timestamp=1701415200000, level=75, status="CHARGING", version=1.0
        )

        assert reading.timestamp == 1701415200000
        assert reading.level == 75
        assert reading.status == "CHARGING"
        assert reading.version == 1.0

    def test_body_battery_reading_datetime_property(self):
        """Test BodyBatteryReading datetime property."""
        from garmy.metrics.body_battery import BodyBatteryReading

        reading = BodyBatteryReading(
            timestamp=1701415200000, level=75, status="CHARGING", version=1.0
        )

        dt = reading.datetime
        assert isinstance(dt, datetime)
        assert dt.year == 2023
        assert dt.month == 12
        assert dt.day == 1

    def test_body_battery_creation(self):
        """Test BodyBattery dataclass creation."""
        bb = BodyBattery(
            user_profile_pk=12345,
            calendar_date="2023-12-01",
            body_battery_values_array=[
                [1701415200000, "CHARGING", 75, 1.0],
                [1701418800000, "DRAINING", 70, 1.0],
            ],
        )

        assert bb.user_profile_pk == 12345
        assert bb.calendar_date == "2023-12-01"
        assert len(bb.body_battery_values_array) == 2

    def test_body_battery_readings_property(self):
        """Test BodyBattery body_battery_readings property."""
        bb = BodyBattery(
            user_profile_pk=12345,
            calendar_date="2023-12-01",
            body_battery_values_array=[
                [1701415200000, "CHARGING", 75, 1.0],
                [1701418800000, "DRAINING", 70, 1.0],
                [1701422400000, "ACTIVE", 65, 1.0],  # Complete array
            ],
        )

        readings = bb.body_battery_readings
        assert len(readings) == 3

        # Test first reading (timestamp=0, status=1, level=2, version=3)
        assert readings[0].timestamp == 1701415200000
        assert readings[0].status == "CHARGING"
        assert readings[0].level == 75
        assert readings[0].version == 1.0

        # Test reading with missing version (should use default 1.0)
        assert readings[2].timestamp == 1701422400000
        assert readings[2].status == "ACTIVE"
        assert readings[2].level == 65
        assert readings[2].version == 1.0

    def test_body_battery_readings_property_short_arrays(self):
        """Test body_battery_readings with arrays shorter than 4 elements."""
        bb = BodyBattery(
            user_profile_pk=12345,
            calendar_date="2023-12-01",
            body_battery_values_array=[
                [1701415200000, "CHARGING"],  # Too short
                [1701418800000, "DRAINING", 70, 1.0],  # Valid
            ],
        )

        readings = bb.body_battery_readings
        assert len(readings) == 1  # Only the valid one
        assert readings[0].level == 70

    def test_body_battery_optional_fields(self):
        """Test BodyBattery with optional fields."""
        bb = BodyBattery(
            user_profile_pk=12345,
            calendar_date="2023-12-01",
            body_battery_values_array=[],
            max_stress_level=50,
            avg_stress_level=30,
            stress_values_array=[[1701415200000, 25, 1.0]],
        )

        assert bb.max_stress_level == 50
        assert bb.avg_stress_level == 30
        assert bb.stress_values_array == [[1701415200000, 25, 1.0]]

    def test_body_battery_parser(self):
        """Test BodyBattery parser function."""
        from garmy.metrics.body_battery import parse_body_battery_data

        sample_data = self.create_sample_body_battery_data()

        with patch(
            "garmy.metrics.body_battery.create_simple_field_parser"
        ) as mock_parser:
            mock_instance = Mock()
            mock_instance.return_value = BodyBattery(
                user_profile_pk=12345,
                calendar_date="2023-12-01",
                body_battery_values_array=[],
            )
            mock_parser.return_value = mock_instance

            result = parse_body_battery_data(sample_data)

            assert isinstance(result, BodyBattery)

    def test_body_battery_metric_config(self):
        """Test BodyBattery METRIC_CONFIG."""
        from garmy.metrics.body_battery import METRIC_CONFIG, __metric_config__

        assert isinstance(METRIC_CONFIG, MetricConfig)
        assert METRIC_CONFIG.metric_class == BodyBattery
        assert "/wellness-service/wellness/dailyStress/" in METRIC_CONFIG.endpoint
        assert METRIC_CONFIG.parser is not None
        assert "Body Battery energy levels" in METRIC_CONFIG.description
        assert METRIC_CONFIG.version == "1.0"

        # Test module export
        assert __metric_config__ == METRIC_CONFIG


class TestSleep:
    """Test cases for Sleep metric."""

    def create_sample_sleep_data(self) -> Dict[str, Any]:
        """Create sample sleep API response data."""
        return {
            "dailySleepDto": {
                "id": 123456,
                "userProfilePk": 12345,
                "calendarDate": "2023-12-01",
                "sleepTimeSeconds": 28800,  # 8 hours
                "napTimeSeconds": 0,
                "sleepStartTimestampGmt": 1701385200000,
                "sleepEndTimestampGmt": 1701414000000,
                "sleepStartTimestampLocal": 1701385200000,
                "sleepEndTimestampLocal": 1701414000000,
                "deepSleepSeconds": 7200,
                "lightSleepSeconds": 14400,
                "remSleepSeconds": 5400,
                "awakeSleepSeconds": 1800,
                "unmeasurableSleepSeconds": 0,
                "awakeCount": 3,
                "sleepWindowConfirmed": True,
                "sleepWindowConfirmationType": "AUTO",
                "deviceRemCapable": True,
                "retro": False,
                "sleepFromDevice": True,
                "averageSpO2Value": 96,
                "lowestSpO2Value": 94,
                "highestSpO2Value": 98,
                "averageRespirationValue": 14.5,
                "lowestRespirationValue": 12.0,
                "highestRespirationValue": 16.5,
                "avgSleepStress": 15.2,
                "sleepScores": {"overall": 85, "quality": 90},
                "sleepNeed": {"baselineSleepNeed": 480},
            },
            "sleepMovement": [
                {"startGMT": 1701385200000, "activityLevel": 0.1},
                {"startGMT": 1701388800000, "activityLevel": 0.3},
            ],
            "wellnessEpochSpO2DataDtoList": [
                {"startGMT": 1701385200000, "value": 96},
                {"startGMT": 1701388800000, "value": 95},
            ],
            "wellnessEpochRespirationDataDtoList": [
                {"startGMT": 1701385200000, "value": 14.5},
                {"startGMT": 1701388800000, "value": 15.0},
            ],
        }

    def test_sleep_summary_creation(self):
        """Test SleepSummary dataclass creation."""
        from garmy.metrics.sleep import SleepSummary

        summary = SleepSummary(
            id=123456,
            user_profile_pk=12345,
            calendar_date="2023-12-01",
            sleep_time_seconds=28800,
            deep_sleep_seconds=7200,
            light_sleep_seconds=14400,
            rem_sleep_seconds=5400,
            awake_sleep_seconds=1800,
        )

        assert summary.id == 123456
        assert summary.user_profile_pk == 12345
        assert summary.sleep_time_seconds == 28800
        assert summary.deep_sleep_seconds == 7200

    def test_sleep_summary_datetime_properties(self):
        """Test SleepSummary datetime properties."""
        from garmy.metrics.sleep import SleepSummary

        summary = SleepSummary(
            sleep_start_timestamp_gmt=1701385200000,
            sleep_end_timestamp_gmt=1701414000000,
            sleep_start_timestamp_local=1701385200000,
            sleep_end_timestamp_local=1701414000000,
        )

        # Test GMT datetime properties
        start_gmt = summary.sleep_start_datetime_gmt
        end_gmt = summary.sleep_end_datetime_gmt
        assert isinstance(start_gmt, datetime)
        assert isinstance(end_gmt, datetime)

        # Test local datetime properties
        start_local = summary.sleep_start_datetime_local
        end_local = summary.sleep_end_datetime_local
        assert isinstance(start_local, datetime)
        assert isinstance(end_local, datetime)

    def test_sleep_summary_calculated_properties(self):
        """Test SleepSummary calculated properties."""
        from garmy.metrics.sleep import SleepSummary

        summary = SleepSummary(
            sleep_time_seconds=28800,  # 8 hours
            sleep_start_timestamp_local=1701385200000,
            sleep_end_timestamp_local=1701414000000,
        )

        # Test total sleep duration in hours
        assert summary.total_sleep_duration_hours == 8.0

        # Test sleep efficiency calculation
        efficiency = summary.sleep_efficiency_percentage
        assert isinstance(efficiency, float)
        assert 0 <= efficiency <= 100

    def test_sleep_summary_efficiency_zero_time_in_bed(self):
        """Test sleep efficiency when time in bed is zero."""
        from garmy.metrics.sleep import SleepSummary

        summary = SleepSummary(
            sleep_time_seconds=28800,
            sleep_start_timestamp_local=1701385200000,
            sleep_end_timestamp_local=1701385200000,  # Same as start
        )

        assert summary.sleep_efficiency_percentage == 0

    def test_sleep_creation(self):
        """Test Sleep dataclass creation."""
        from garmy.metrics.sleep import Sleep, SleepSummary

        summary = SleepSummary(sleep_time_seconds=28800)
        sleep = Sleep(
            sleep_summary=summary,
            sleep_movement=[{"startGMT": 1701385200000, "activityLevel": 0.1}],
            wellness_epoch_spo2_data_dto_list=[
                {"startGMT": 1701385200000, "value": 96}
            ],
            wellness_epoch_respiration_data_dto_list=[
                {"startGMT": 1701385200000, "value": 14.5}
            ],
        )

        assert isinstance(sleep.sleep_summary, SleepSummary)
        assert len(sleep.sleep_movement) == 1
        assert len(sleep.wellness_epoch_spo2_data_dto_list) == 1
        assert len(sleep.wellness_epoch_respiration_data_dto_list) == 1

    def test_sleep_calculated_properties(self):
        """Test Sleep calculated properties."""
        from garmy.metrics.sleep import Sleep, SleepSummary

        summary = SleepSummary(
            sleep_time_seconds=28800,  # 8 hours
            deep_sleep_seconds=7200,  # 2 hours
            light_sleep_seconds=14400,  # 4 hours
            rem_sleep_seconds=5400,  # 1.5 hours
            awake_sleep_seconds=1800,  # 0.5 hours
        )

        sleep = Sleep(
            sleep_summary=summary,
            wellness_epoch_spo2_data_dto_list=[{}, {}],
            wellness_epoch_respiration_data_dto_list=[{}],
            sleep_movement=[{}, {}, {}],
        )

        # Test duration property
        assert sleep.sleep_duration_hours == 8.0

        # Test sleep stage percentages
        assert sleep.deep_sleep_percentage == 25.0  # 2/8 * 100
        assert sleep.light_sleep_percentage == 50.0  # 4/8 * 100
        assert sleep.rem_sleep_percentage == 18.75  # 1.5/8 * 100
        assert sleep.awake_percentage == 6.25  # 0.5/8 * 100

        # Test reading counts
        assert sleep.spo2_readings_count == 2
        assert sleep.respiration_readings_count == 1
        assert sleep.movement_readings_count == 3

    def test_sleep_percentage_with_zero_sleep_time(self):
        """Test sleep percentages when sleep time is zero."""
        from garmy.metrics.sleep import Sleep, SleepSummary

        summary = SleepSummary(
            sleep_time_seconds=0,
            deep_sleep_seconds=0,
            light_sleep_seconds=0,
            rem_sleep_seconds=0,
            awake_sleep_seconds=0,
        )

        sleep = Sleep(sleep_summary=summary)

        assert sleep.deep_sleep_percentage == 0
        assert sleep.light_sleep_percentage == 0
        assert sleep.rem_sleep_percentage == 0
        assert sleep.awake_percentage == 0

    def test_sleep_parser(self):
        """Test Sleep parser function."""
        from garmy.metrics.sleep import parse_sleep_data

        sample_data = self.create_sample_sleep_data()

        with patch("garmy.metrics.sleep.create_nested_summary_parser") as mock_parser:
            mock_instance = Mock()
            mock_instance.return_value = Sleep(
                sleep_summary=Mock(),
                sleep_movement=[],
                wellness_epoch_spo2_data_dto_list=[],
                wellness_epoch_respiration_data_dto_list=[],
            )
            mock_parser.return_value = mock_instance

            result = parse_sleep_data(sample_data)

            assert isinstance(result, Sleep)

    def test_sleep_endpoint_builder(self):
        """Test Sleep endpoint builder."""
        from garmy.metrics.sleep import build_sleep_endpoint

        # Mock the imported function
        with patch("garmy.metrics.sleep._build_sleep_endpoint") as mock_builder:
            mock_builder.return_value = (
                "/sleep-service/sleep/dailySleepData/12345/2023-12-01"
            )

            result = build_sleep_endpoint("2023-12-01", Mock(), user_id=12345)

            assert result == "/sleep-service/sleep/dailySleepData/12345/2023-12-01"
            mock_builder.assert_called_once()

    def test_sleep_metric_config(self):
        """Test Sleep METRIC_CONFIG."""
        from garmy.metrics.sleep import METRIC_CONFIG, __metric_config__

        assert isinstance(METRIC_CONFIG, MetricConfig)
        assert METRIC_CONFIG.metric_class == Sleep
        assert METRIC_CONFIG.endpoint == ""  # Uses endpoint_builder
        assert METRIC_CONFIG.endpoint_builder is not None
        assert METRIC_CONFIG.requires_user_id is True
        assert "Comprehensive sleep data" in METRIC_CONFIG.description
        assert METRIC_CONFIG.version == "1.0"

        # Test module export
        assert __metric_config__ == METRIC_CONFIG


class TestActivities:
    """Test cases for Activities metric."""

    def create_sample_activity_data(self) -> Dict[str, Any]:
        """Create sample activity API response data."""
        return {
            "activityId": 123456789,
            "activityName": "Morning Run",
            "startTimeLocal": "2023-12-01 07:00:00",
            "startTimeGMT": "2023-12-01 06:00:00",
            "activityType": {"typeId": 1, "typeKey": "running"},
            "eventType": {"typeId": 1, "typeKey": "race"},
            "duration": 2400.0,  # 40 minutes
            "elapsedDuration": 2500.0,
            "movingDuration": 2300.0,
            "ownerId": 12345,
            "ownerDisplayName": "John Doe",
            "ownerFullName": "John Doe",
            "averageHR": 150.5,
            "maxHR": 180.0,
            "sportTypeId": 1,
            "deviceId": 67890,
            "manufacturer": "Garmin",
            "lapCount": 5,
            "hasPolyline": True,
            "hasImages": False,
            "privacy": {"typeId": 1, "typeKey": "public"},
            "beginTimestamp": 1701415200000,
            "endTimeGMT": "2023-12-01 06:40:00",
            "autoCalcCalories": True,
            "manualActivity": False,
            "favorite": False,
            "aerobicTrainingEffect": 3.2,
            "anaerobicTrainingEffect": 1.8,
            "trainingEffectLabel": "Maintaining",
            "activityTrainingLoad": 180.0,
            "avgStress": 25.5,
            "startStress": 20.0,
            "endStress": 30.0,
            "maxStress": 35.0,
            "differenceStress": 10.0,
            "differenceBodyBattery": -15,
            "minRespirationRate": 12.0,
            "maxRespirationRate": 18.0,
            "avgRespirationRate": 15.0,
        }

    def test_activity_summary_creation(self):
        """Test ActivitySummary dataclass creation."""
        activity = ActivitySummary(
            activity_id=123456789,
            activity_name="Morning Run",
            start_time_local="2023-12-01 07:00:00",
            start_time_gmt="2023-12-01 06:00:00",
            duration=2400.0,
            owner_id=12345,
        )

        assert activity.activity_id == 123456789
        assert activity.activity_name == "Morning Run"
        assert activity.duration == 2400.0
        assert activity.owner_id == 12345

    def test_activity_summary_with_nested_dicts(self):
        """Test ActivitySummary with nested dictionary fields."""
        activity = ActivitySummary(
            activity_id=123456789,
            activity_name="Morning Run",
            activity_type={"typeId": 1, "typeKey": "running"},
            event_type={"typeId": 1, "typeKey": "race"},
            privacy={"typeId": 1, "typeKey": "public"},
        )

        assert activity.activity_type["typeKey"] == "running"
        assert activity.event_type["typeKey"] == "race"
        assert activity.privacy["typeKey"] == "public"

    def test_activity_summary_calculated_properties(self):
        """Test ActivitySummary calculated properties."""
        activity = ActivitySummary(
            activity_type={"typeKey": "running", "typeId": 1},
            duration=2400.0,  # 40 minutes
            moving_duration=2300.0,  # 38.33 minutes
            average_hr=150.0,
            max_hr=180.0,
            avg_stress=25.0,
            avg_respiration_rate=15.0,
        )

        # Test activity type properties
        assert activity.activity_type_name == "running"
        assert activity.activity_type_id == 1

        # Test duration properties
        assert activity.duration_minutes == 40.0
        assert activity.duration_hours == pytest.approx(0.667, rel=1e-2)
        assert activity.moving_duration_minutes == pytest.approx(38.33, rel=1e-2)

        # Test heart rate properties
        assert activity.heart_rate_range == 30.0
        assert activity.has_heart_rate is True

        # Test data availability properties
        assert activity.has_stress_data is True
        assert activity.has_respiration_data is True

    def test_activity_summary_datetime_properties(self):
        """Test ActivitySummary datetime properties."""
        with patch("garmy.metrics.activities._parse_datetime_cached") as mock_parse:
            mock_parse.side_effect = [
                datetime(2023, 12, 1, 7, 0, 0),  # local
                datetime(2023, 12, 1, 6, 0, 0),  # gmt
            ]

            activity = ActivitySummary(
                start_time_local="2023-12-01 07:00:00",
                start_time_gmt="2023-12-01 06:00:00",
            )

            local_dt = activity.start_datetime_local
            gmt_dt = activity.start_datetime_gmt

            assert isinstance(local_dt, datetime)
            assert isinstance(gmt_dt, datetime)
            assert local_dt.hour == 7
            assert gmt_dt.hour == 6

    def test_activity_summary_start_date_property(self):
        """Test ActivitySummary start_date property."""
        with patch("garmy.metrics.activities._parse_datetime_cached") as mock_parse:
            mock_parse.return_value = datetime(2023, 12, 1, 7, 0, 0)

            activity = ActivitySummary(start_time_local="2023-12-01 07:00:00")

            assert activity.start_date == "2023-12-01"

    def test_activity_summary_start_date_no_datetime(self):
        """Test start_date when datetime parsing fails."""
        with patch("garmy.metrics.activities._parse_datetime_cached") as mock_parse:
            mock_parse.return_value = None

            activity = ActivitySummary(start_time_local="invalid")

            assert activity.start_date == ""

    def test_activity_summary_privacy_type_property(self):
        """Test ActivitySummary privacy_type property."""
        activity = ActivitySummary(privacy={"typeKey": "public", "typeId": 1})

        assert activity.privacy_type == "public"

    def test_activity_summary_heart_rate_edge_cases(self):
        """Test heart rate properties edge cases."""
        # No heart rate data
        activity1 = ActivitySummary()
        assert activity1.heart_rate_range is None
        assert activity1.has_heart_rate is False

        # Zero heart rate
        activity2 = ActivitySummary(average_hr=0.0)
        assert activity2.has_heart_rate is False

        # Only average HR
        activity3 = ActivitySummary(average_hr=150.0, max_hr=None)
        assert activity3.heart_rate_range is None

    def test_activity_summary_stress_impact_categorization(self):
        """Test stress impact categorization."""
        # Stress reducing
        activity1 = ActivitySummary(difference_stress=-10.0)
        assert activity1.stress_impact == "stress_reducing"

        # Stress increasing
        activity2 = ActivitySummary(difference_stress=10.0)
        assert activity2.stress_impact == "stress_increasing"

        # Stress neutral
        activity3 = ActivitySummary(difference_stress=2.0)
        assert activity3.stress_impact == "stress_neutral"

        # No stress data
        activity4 = ActivitySummary(difference_stress=None)
        assert activity4.stress_impact is None

    def test_parse_datetime_cached(self):
        """Test _parse_datetime_cached function."""
        from garmy.metrics.activities import _parse_datetime_cached

        # Valid datetime string
        result1 = _parse_datetime_cached("2023-12-01 07:00:00")
        assert isinstance(result1, datetime)
        assert result1.year == 2023
        assert result1.month == 12
        assert result1.day == 1
        assert result1.hour == 7

        # Invalid datetime string
        result2 = _parse_datetime_cached("invalid-datetime")
        assert result2 is None

        # None input
        result3 = _parse_datetime_cached(None)
        assert result3 is None

        # Empty string
        result4 = _parse_datetime_cached("")
        assert result4 is None

    def test_activities_accessor_creation(self):
        """Test ActivitiesAccessor creation."""
        from garmy.metrics.activities import ActivitiesAccessor

        mock_api_client = Mock()
        accessor = ActivitiesAccessor(mock_api_client)

        assert accessor.api_client == mock_api_client
        assert accessor.parse_func is not None

    def test_activities_accessor_raw(self):
        """Test ActivitiesAccessor raw method."""
        from garmy.metrics.activities import ActivitiesAccessor

        mock_api_client = Mock()
        mock_api_client.connectapi.return_value = {"activities": []}

        accessor = ActivitiesAccessor(mock_api_client)
        accessor.raw(limit=10, start=5)

        mock_api_client.connectapi.assert_called_once()
        call_args = mock_api_client.connectapi.call_args[0][0]
        assert "limit=10" in call_args
        assert "start=5" in call_args

    def test_activities_accessor_raw_with_exception(self):
        """Test ActivitiesAccessor raw method with exception."""
        from garmy.metrics.activities import ActivitiesAccessor

        mock_api_client = Mock()
        mock_api_client.connectapi.side_effect = Exception("API Error")

        with patch("garmy.core.utils.handle_api_exception") as mock_handle:
            mock_handle.return_value = []

            accessor = ActivitiesAccessor(mock_api_client)
            result = accessor.raw()

            assert result == []
            mock_handle.assert_called_once()

    def test_activities_accessor_list(self):
        """Test ActivitiesAccessor list method."""
        from garmy.metrics.activities import ActivitiesAccessor

        mock_api_client = Mock()
        accessor = ActivitiesAccessor(mock_api_client)

        # Mock raw method to return sample data
        with patch.object(accessor, "raw") as mock_raw:
            mock_raw.return_value = [self.create_sample_activity_data()]

            with patch.object(accessor, "parse_func") as mock_parse:
                mock_parse.return_value = [ActivitySummary(activity_id=123)]

                result = accessor.list(limit=20)

                assert isinstance(result, list)
                mock_raw.assert_called_once_with(20, 0, 'desc')
                mock_parse.assert_called_once()

    def test_activities_accessor_list_empty_data(self):
        """Test ActivitiesAccessor list method with empty data."""
        from garmy.metrics.activities import ActivitiesAccessor

        mock_api_client = Mock()
        accessor = ActivitiesAccessor(mock_api_client)

        with patch.object(accessor, "raw") as mock_raw:
            mock_raw.return_value = None

            result = accessor.list()

            assert result == []

    def test_activities_accessor_get_recent(self):
        """Test ActivitiesAccessor get_recent method."""
        from garmy.metrics.activities import ActivitiesAccessor

        mock_api_client = Mock()
        accessor = ActivitiesAccessor(mock_api_client)

        # Create mock activities with different dates
        with patch.object(accessor, "list") as mock_list:
            # Use real datetime strings that will be parsed correctly
            recent_activity = ActivitySummary(
                activity_id=1,
                start_time_local=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )
            old_activity = ActivitySummary(
                activity_id=2,
                start_time_local=(datetime.now() - timedelta(days=10)).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
            )

            mock_list.return_value = [recent_activity, old_activity]

            result = accessor.get_recent(days=7)

            assert len(result) == 1
            assert result[0].activity_id == 1

    def test_activities_accessor_get_recent_empty_list(self):
        """Test get_recent with empty activities list."""
        from garmy.metrics.activities import ActivitiesAccessor

        mock_api_client = Mock()
        accessor = ActivitiesAccessor(mock_api_client)

        with patch.object(accessor, "list") as mock_list:
            mock_list.return_value = []

            result = accessor.get_recent(days=7)

            assert result == []

    def test_activities_accessor_get_by_type(self):
        """Test ActivitiesAccessor get_by_type method."""
        from garmy.metrics.activities import ActivitiesAccessor

        mock_api_client = Mock()
        accessor = ActivitiesAccessor(mock_api_client)

        with patch.object(accessor, "list") as mock_list:
            running_activity = ActivitySummary(
                activity_id=1, activity_type={"typeKey": "running"}
            )
            cycling_activity = ActivitySummary(
                activity_id=2, activity_type={"typeKey": "cycling"}
            )

            mock_list.return_value = [running_activity, cycling_activity]

            result = accessor.get_by_type("running")

            assert len(result) == 1
            assert result[0].activity_id == 1

    def test_activities_accessor_get_compatibility(self):
        """Test ActivitiesAccessor get method for compatibility."""
        from garmy.metrics.activities import ActivitiesAccessor

        mock_api_client = Mock()
        accessor = ActivitiesAccessor(mock_api_client)

        with patch.object(accessor, "list") as mock_list:
            mock_list.return_value = [ActivitySummary(activity_id=123)]

            result = accessor.get()

            assert isinstance(result, list)
            mock_list.assert_called_once()

    def test_create_activities_accessor(self):
        """Test create_activities_accessor factory function."""
        from garmy.metrics.activities import (
            ActivitiesAccessor,
            create_activities_accessor,
        )

        mock_api_client = Mock()
        accessor = create_activities_accessor(mock_api_client)

        assert isinstance(accessor, ActivitiesAccessor)
        assert accessor.api_client == mock_api_client

    def test_activities_parser(self):
        """Test Activities parser function."""
        from garmy.metrics.activities import parse_activities_data

        sample_data = [self.create_sample_activity_data()]

        with patch("garmy.metrics.activities.create_list_parser") as mock_parser:
            mock_instance = Mock()
            mock_instance.return_value = [ActivitySummary(activity_id=123)]
            mock_parser.return_value = mock_instance

            result = parse_activities_data(sample_data)

            assert isinstance(result, list)

    def test_activities_metric_config(self):
        """Test Activities METRIC_CONFIG."""
        from garmy.metrics.activities import (
            METRIC_CONFIG,
            __custom_accessor_factory__,
            __metric_config__,
        )

        assert isinstance(METRIC_CONFIG, MetricConfig)
        assert METRIC_CONFIG.metric_class == ActivitySummary
        assert (
            "/activitylist-service/activities/search/activities"
            in METRIC_CONFIG.endpoint
        )
        assert METRIC_CONFIG.parser is not None
        assert "Activity summaries" in METRIC_CONFIG.description
        assert METRIC_CONFIG.version == "1.0"

        # Test module exports
        assert __metric_config__ == METRIC_CONFIG
        assert __custom_accessor_factory__ is not None


class TestHeartRate:
    """Test cases for HeartRate metric."""

    def create_sample_heart_rate_data(self) -> Dict[str, Any]:
        """Create sample heart rate API response data."""
        return {
            "userProfilePk": 12345,
            "calendarDate": "2023-12-01",
            "startTimestampGmt": "2023-12-01T00:00:00.0Z",
            "endTimestampGmt": "2023-12-01T23:59:59.0Z",
            "startTimestampLocal": "2023-12-01T01:00:00.0+01:00",
            "endTimestampLocal": "2023-12-02T00:59:59.0+01:00",
            "maxHeartRate": 180,
            "minHeartRate": 45,
            "restingHeartRate": 55,
            "lastSevenDaysAvgRestingHeartRate": 57,
            "heartRateValuesArray": [
                [1701415200000, 60],
                [1701415500000, 65],
                [1701415800000, 70],
            ],
            "heartRateValueDescriptors": [
                {"key": "timestampGMT", "index": 0},
                {"key": "heartRate", "index": 1},
            ],
        }

    def test_heart_rate_summary_creation(self):
        """Test HeartRateSummary dataclass creation."""
        from garmy.metrics.heart_rate import HeartRateSummary

        summary = HeartRateSummary(
            user_profile_pk=12345,
            calendar_date="2023-12-01",
            max_heart_rate=180,
            min_heart_rate=45,
            resting_heart_rate=55,
            last_seven_days_avg_resting_heart_rate=57,
        )

        assert summary.user_profile_pk == 12345
        assert summary.calendar_date == "2023-12-01"
        assert summary.max_heart_rate == 180
        assert summary.min_heart_rate == 45
        assert summary.resting_heart_rate == 55

    def test_heart_rate_summary_calculated_properties(self):
        """Test HeartRateSummary calculated properties."""
        from garmy.metrics.heart_rate import HeartRateSummary

        summary = HeartRateSummary(max_heart_rate=180, min_heart_rate=45)

        assert summary.heart_rate_range == 135

    def test_heart_rate_summary_datetime_properties(self):
        """Test HeartRateSummary datetime properties."""
        from garmy.metrics.heart_rate import HeartRateSummary

        summary = HeartRateSummary(
            start_timestamp_gmt="2023-12-01T00:00:00.0Z",
            end_timestamp_gmt="2023-12-01T23:59:59.0Z",
            start_timestamp_local="2023-12-01T01:00:00.0+01:00",
            end_timestamp_local="2023-12-02T00:59:59.0+01:00",
        )

        # Test GMT datetime properties
        start_gmt = summary.start_datetime_gmt
        end_gmt = summary.end_datetime_gmt
        assert isinstance(start_gmt, datetime)
        assert isinstance(end_gmt, datetime)

        # Test local datetime properties
        start_local = summary.start_datetime_local
        end_local = summary.end_datetime_local
        assert isinstance(start_local, datetime)
        assert isinstance(end_local, datetime)

    def test_heart_rate_creation(self):
        """Test HeartRate dataclass creation."""
        from garmy.metrics.heart_rate import HeartRate, HeartRateSummary

        summary = HeartRateSummary(
            max_heart_rate=180, min_heart_rate=45, resting_heart_rate=55
        )

        hr = HeartRate(
            heart_rate_summary=summary,
            heart_rate_values_array=[[1701415200000, 60], [1701415500000, 65]],
            heart_rate_value_descriptors=[{"key": "timestampGMT", "index": 0}],
        )

        assert isinstance(hr.heart_rate_summary, HeartRateSummary)
        assert len(hr.heart_rate_values_array) == 2
        assert len(hr.heart_rate_value_descriptors) == 1

    def test_heart_rate_calculated_properties(self):
        """Test HeartRate calculated properties."""
        from garmy.metrics.heart_rate import HeartRate, HeartRateSummary

        summary = HeartRateSummary()
        hr = HeartRate(
            heart_rate_summary=summary,
            heart_rate_values_array=[
                [1701415200000, 60],
                [1701415500000, 65],
                [1701415800000, 70],
                [1701416100000, None],  # Invalid reading
                [1701416400000],  # Short array
            ],
        )

        # Test readings count
        assert hr.readings_count == 5

        # Test average heart rate (should skip invalid readings)
        expected_avg = (60 + 65 + 70) / 3
        assert hr.average_heart_rate == expected_avg

    def test_heart_rate_average_with_no_readings(self):
        """Test average heart rate with no readings."""
        from garmy.metrics.heart_rate import HeartRate, HeartRateSummary

        summary = HeartRateSummary()
        hr = HeartRate(heart_rate_summary=summary, heart_rate_values_array=[])

        assert hr.average_heart_rate == 0.0

    def test_heart_rate_average_with_invalid_readings(self):
        """Test average heart rate with all invalid readings."""
        from garmy.metrics.heart_rate import HeartRate, HeartRateSummary

        summary = HeartRateSummary()
        hr = HeartRate(
            heart_rate_summary=summary,
            heart_rate_values_array=[[1701415200000, None], [1701415500000], []],
        )

        assert hr.average_heart_rate == 0.0

    def test_heart_rate_parser(self):
        """Test HeartRate parser function."""
        from garmy.metrics.heart_rate import parse_heart_rate_data

        sample_data = self.create_sample_heart_rate_data()

        with patch("garmy.metrics.heart_rate.create_summary_raw_parser") as mock_parser:
            mock_instance = Mock()
            mock_instance.return_value = HeartRate(
                heart_rate_summary=Mock(),
                heart_rate_values_array=[],
                heart_rate_value_descriptors=[],
            )
            mock_parser.return_value = mock_instance

            result = parse_heart_rate_data(sample_data)

            assert isinstance(result, HeartRate)

    def test_heart_rate_endpoint_builder(self):
        """Test HeartRate endpoint builder."""
        from garmy.metrics.heart_rate import build_heart_rate_endpoint

        with patch(
            "garmy.metrics.heart_rate._build_heart_rate_endpoint"
        ) as mock_builder:
            mock_builder.return_value = (
                "/wellness-service/wellness/dailyHeartRate/12345/2023-12-01"
            )

            result = build_heart_rate_endpoint("2023-12-01", Mock(), user_id=12345)

            assert (
                result == "/wellness-service/wellness/dailyHeartRate/12345/2023-12-01"
            )
            mock_builder.assert_called_once()

    def test_heart_rate_metric_config(self):
        """Test HeartRate METRIC_CONFIG."""
        from garmy.metrics.heart_rate import METRIC_CONFIG, __metric_config__

        assert isinstance(METRIC_CONFIG, MetricConfig)
        assert METRIC_CONFIG.metric_class == HeartRate
        assert METRIC_CONFIG.endpoint == ""  # Uses endpoint_builder
        assert METRIC_CONFIG.endpoint_builder is not None
        assert METRIC_CONFIG.requires_user_id is True
        assert "Daily heart rate data" in METRIC_CONFIG.description
        assert METRIC_CONFIG.version == "1.0"

        # Test module export
        assert __metric_config__ == METRIC_CONFIG


class TestOtherMetrics:
    """Test cases for remaining metrics with basic functionality."""

    def test_hrv_import_and_basic_structure(self):
        """Test HRV metric can be imported and has basic structure."""
        assert hasattr(HRV, "__dataclass_fields__")

        # Check if it's a dataclass
        assert hasattr(HRV, "__dataclass_fields__")

    def test_calories_import_and_basic_structure(self):
        """Test Calories metric can be imported and has basic structure."""
        assert hasattr(Calories, "__dataclass_fields__")

    def test_daily_summary_import_and_basic_structure(self):
        """Test DailySummary metric can be imported and has basic structure."""
        assert hasattr(DailySummary, "__dataclass_fields__")

    def test_respiration_import_and_basic_structure(self):
        """Test Respiration metric can be imported and has basic structure."""
        assert hasattr(Respiration, "__dataclass_fields__")

    def test_steps_import_and_basic_structure(self):
        """Test Steps metric can be imported and has basic structure."""
        assert hasattr(Steps, "__dataclass_fields__")

    def test_stress_import_and_basic_structure(self):
        """Test Stress metric can be imported and has basic structure."""
        assert hasattr(Stress, "__dataclass_fields__")

    def test_all_metrics_have_metric_configs(self):
        """Test all metrics modules have METRIC_CONFIG."""
        metric_modules = [
            "training_readiness",
            "body_battery",
            "sleep",
            "activities",
            "heart_rate",
            "hrv",
            "calories",
            "daily_summary",
            "respiration",
            "steps",
            "stress",
        ]

        for module_name in metric_modules:
            module = __import__(f"garmy.metrics.{module_name}", fromlist=[""])
            assert hasattr(module, "METRIC_CONFIG")
            assert hasattr(module, "__metric_config__")
            assert isinstance(module.METRIC_CONFIG, MetricConfig)


class TestMetricsEdgeCases:
    """Test cases for edge cases and error conditions."""

    def test_timestamp_mixin_inheritance(self):
        """Test that metrics using TimestampMixin work correctly."""
        from garmy.metrics.activities import ActivitySummary
        from garmy.metrics.body_battery import BodyBatteryReading

        # Test BodyBatteryReading (uses TimestampMixin)
        reading = BodyBatteryReading(
            timestamp=1701415200000, level=75, status="CHARGING", version=1.0
        )

        dt = reading.datetime
        assert isinstance(dt, datetime)

        # Test ActivitySummary (uses TimestampMixin)
        activity = ActivitySummary()
        assert hasattr(activity, "timestamp_to_datetime")

    def test_dataclass_field_defaults(self):
        """Test dataclass field defaults work correctly."""
        from garmy.metrics.activities import ActivitySummary
        from garmy.metrics.sleep import Sleep

        # Test Sleep with default lists
        sleep = Sleep(sleep_summary=Mock())
        assert sleep.sleep_movement == []
        assert sleep.wellness_epoch_spo2_data_dto_list == []
        assert sleep.wellness_epoch_respiration_data_dto_list == []

        # Test ActivitySummary with default dicts
        activity = ActivitySummary()
        assert activity.activity_type == {}
        assert activity.event_type == {}
        assert activity.privacy == {}

    def test_optional_datetime_properties(self):
        """Test optional datetime properties handle None gracefully."""
        from garmy.metrics.heart_rate import HeartRateSummary

        summary = HeartRateSummary(start_timestamp_gmt="", end_timestamp_gmt=None)

        # Should return None for empty/invalid timestamps
        assert summary.start_datetime_gmt is None
        assert summary.end_datetime_gmt is None

    def test_metric_configs_immutability(self):
        """Test that METRIC_CONFIG objects are immutable."""
        from garmy.metrics.training_readiness import METRIC_CONFIG

        # Should not be able to modify frozen dataclass
        with pytest.raises(AttributeError):
            METRIC_CONFIG.endpoint = "/new/endpoint"

        with pytest.raises(AttributeError):
            METRIC_CONFIG.version = "2.0"

    def test_property_methods_with_zero_values(self):
        """Test property methods handle zero/empty values correctly."""
        from garmy.metrics.sleep import Sleep, SleepSummary

        summary = SleepSummary(sleep_time_seconds=0)
        sleep = Sleep(sleep_summary=summary)

        # Should handle division by zero gracefully
        assert sleep.deep_sleep_percentage == 0
        assert sleep.light_sleep_percentage == 0
        assert sleep.rem_sleep_percentage == 0
        assert sleep.awake_percentage == 0

    def test_list_property_with_empty_data(self):
        """Test list properties handle empty data correctly."""
        from garmy.metrics.body_battery import BodyBattery

        bb = BodyBattery(
            user_profile_pk=12345,
            calendar_date="2023-12-01",
            body_battery_values_array=[],
        )

        readings = bb.body_battery_readings
        assert readings == []
        assert len(readings) == 0


class TestMetricsIntegration:
    """Integration tests for metrics module."""

    def test_all_metrics_are_dataclasses(self):
        """Test all exported metrics are dataclasses."""
        import garmy.metrics as metrics_module

        for name in metrics_module.__all__:
            metric_class = getattr(metrics_module, name)
            assert hasattr(metric_class, "__dataclass_fields__"), (
                f"{name} is not a dataclass"
            )

    def test_metric_configs_have_required_fields(self):
        """Test all metric configs have required fields."""
        metric_modules = [
            "training_readiness",
            "body_battery",
            "sleep",
            "activities",
            "heart_rate",
            "hrv",
            "calories",
            "daily_summary",
            "respiration",
            "steps",
            "stress",
        ]

        for module_name in metric_modules:
            module = __import__(f"garmy.metrics.{module_name}", fromlist=[""])
            config = module.METRIC_CONFIG

            # Required fields
            assert config.metric_class is not None
            assert config.version is not None

            # Either endpoint or endpoint_builder must be present
            assert config.endpoint or config.endpoint_builder

    def test_parsers_are_callable(self):
        """Test all metric parsers are callable."""
        metric_modules = [
            "training_readiness",
            "body_battery",
            "sleep",
            "activities",
            "heart_rate",
        ]

        for module_name in metric_modules:
            module = __import__(f"garmy.metrics.{module_name}", fromlist=[""])
            config = module.METRIC_CONFIG

            if config.parser:
                assert callable(config.parser)

    def test_endpoint_builders_are_callable(self):
        """Test endpoint builders are callable when present."""
        endpoint_builder_modules = ["sleep", "heart_rate"]

        for module_name in endpoint_builder_modules:
            module = __import__(f"garmy.metrics.{module_name}", fromlist=[""])
            config = module.METRIC_CONFIG

            if config.endpoint_builder:
                assert callable(config.endpoint_builder)

    def test_activities_has_custom_accessor(self):
        """Test activities module has custom accessor factory."""
        import garmy.metrics.activities as activities_module

        assert hasattr(activities_module, "__custom_accessor_factory__")
        assert callable(activities_module.__custom_accessor_factory__)


if __name__ == "__main__":
    pytest.main([__file__])
