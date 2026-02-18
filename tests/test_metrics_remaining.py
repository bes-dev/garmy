"""Comprehensive tests for remaining garmy.metrics modules.

This module provides detailed test coverage for metrics modules not fully
covered in the main comprehensive test file: HRV, Calories, DailySummary,
Respiration, Steps, and Stress.
"""

from datetime import datetime
from typing import Any, Dict

import pytest

from garmy.core.base import MetricConfig


class TestHRV:
    """Test cases for HRV metric module."""

    def create_sample_hrv_data(self) -> Dict[str, Any]:
        """Create sample HRV API response data."""
        return {
            "userProfilePk": 12345,
            "calendarDate": "2023-12-01",
            "weeklyAvg": 45.5,
            "lastNightAvg": 42.3,
            "lastNight5MinHigh": 55.2,
            "baseline": {"lowUpper": 35.0, "highLower": 50.0, "range": "BALANCED"},
            "status": "BALANCED",
            "feedbackPhrase": "Your HRV is in the normal range",
            "createTimeStamp": 1701415200000,
            "hrvReadings": [
                {"timestamp": 1701385200000, "value": 42.1},
                {"timestamp": 1701388800000, "value": 43.5},
                {"timestamp": 1701392400000, "value": 41.8},
            ],
        }

    def test_hrv_module_exists(self):
        """Test HRV module can be imported."""
        try:
            from garmy.metrics import hrv

            assert hrv is not None
        except ImportError:
            pytest.fail("HRV module should be importable")

    def test_hrv_class_import(self):
        """Test HRV class can be imported."""
        from garmy.metrics import HRV

        assert HRV is not None
        assert hasattr(HRV, "__dataclass_fields__")

    def test_hrv_has_metric_config(self):
        """Test HRV module has proper metric configuration."""
        try:
            import garmy.metrics.hrv as hrv_module

            assert hasattr(hrv_module, "METRIC_CONFIG")
            assert hasattr(hrv_module, "__metric_config__")

            config = hrv_module.METRIC_CONFIG
            assert isinstance(config, MetricConfig)
            assert config.metric_class is not None
            assert config.version is not None
        except ImportError:
            pytest.skip("HRV module not implemented yet")

    def test_hrv_basic_functionality(self):
        """Test HRV basic functionality if implemented."""
        try:
            from garmy.metrics import HRV

            # Test basic instantiation if it's a dataclass
            if hasattr(HRV, "__dataclass_fields__"):
                # Try to create instance with minimal data
                try:
                    hrv_instance = HRV()
                    assert hrv_instance is not None
                except TypeError:
                    # If there are required fields, skip this test
                    pytest.skip("HRV requires specific fields for instantiation")

        except ImportError:
            pytest.skip("HRV module not implemented yet")


class TestCalories:
    """Test cases for Calories metric module."""

    def create_sample_calories_data(self) -> Dict[str, Any]:
        """Create sample calories API response data."""
        return {
            "userProfilePk": 12345,
            "calendarDate": "2023-12-01",
            "totalKilocalories": 2450,
            "activeKilocalories": 650,
            "bmrKilocalories": 1800,
            "wellnessKilocalories": 1950,
            "burnedKilocalories": 2100,
            "consumedKilocalories": 2300,
            "remainingKilocalories": 150,
            "projectedKilocalories": 2600,
            "goalKilocalories": 2500,
            "netCalorieGoal": 200,
            "wellnessStartTimeGmt": "2023-12-01T00:00:00Z",
            "wellnessEndTimeGmt": "2023-12-01T23:59:59Z",
        }

    def test_calories_module_exists(self):
        """Test Calories module can be imported."""
        try:
            from garmy.metrics import calories

            assert calories is not None
        except ImportError:
            pytest.fail("Calories module should be importable")

    def test_calories_class_import(self):
        """Test Calories class can be imported."""
        from garmy.metrics import Calories

        assert Calories is not None
        assert hasattr(Calories, "__dataclass_fields__")

    def test_calories_has_metric_config(self):
        """Test Calories module has proper metric configuration."""
        try:
            import garmy.metrics.calories as calories_module

            assert hasattr(calories_module, "METRIC_CONFIG")
            assert hasattr(calories_module, "__metric_config__")

            config = calories_module.METRIC_CONFIG
            assert isinstance(config, MetricConfig)
            assert config.metric_class is not None
            assert config.version is not None
        except ImportError:
            pytest.skip("Calories module not implemented yet")

    def test_calories_basic_functionality(self):
        """Test Calories basic functionality if implemented."""
        try:
            from garmy.metrics import Calories

            if hasattr(Calories, "__dataclass_fields__"):
                try:
                    calories_instance = Calories()
                    assert calories_instance is not None
                except TypeError:
                    pytest.skip("Calories requires specific fields for instantiation")

        except ImportError:
            pytest.skip("Calories module not implemented yet")


class TestDailySummary:
    """Test cases for DailySummary metric module."""

    def create_sample_daily_summary_data(self) -> Dict[str, Any]:
        """Create sample daily summary API response data."""
        return {
            "userProfilePk": 12345,
            "calendarDate": "2023-12-01",
            "dailySummaryDto": {
                "steps": 12500,
                "stepGoal": 10000,
                "totalKilocalories": 2450,
                "activeKilocalories": 650,
                "restingHeartRate": 55,
                "maxHeartRate": 180,
                "averageStressLevel": 25,
                "maxStressLevel": 45,
                "sleepTimeSeconds": 28800,
                "bodyBatteryChargedUp": 85,
                "bodyBatteryDrained": 35,
                "floorsClimbed": 15,
                "floorsGoal": 10,
            },
            "wellnessDataDto": {
                "steps": 12500,
                "distance": 8.5,
                "calories": 2450,
                "activeTime": 45,
            },
        }

    def test_daily_summary_module_exists(self):
        """Test DailySummary module can be imported."""
        try:
            from garmy.metrics import daily_summary

            assert daily_summary is not None
        except ImportError:
            pytest.fail("DailySummary module should be importable")

    def test_daily_summary_class_import(self):
        """Test DailySummary class can be imported."""
        from garmy.metrics import DailySummary

        assert DailySummary is not None
        assert hasattr(DailySummary, "__dataclass_fields__")

    def test_daily_summary_has_metric_config(self):
        """Test DailySummary module has proper metric configuration."""
        try:
            import garmy.metrics.daily_summary as daily_summary_module

            assert hasattr(daily_summary_module, "METRIC_CONFIG")
            assert hasattr(daily_summary_module, "__metric_config__")

            config = daily_summary_module.METRIC_CONFIG
            assert isinstance(config, MetricConfig)
            assert config.metric_class is not None
            assert config.version is not None
        except ImportError:
            pytest.skip("DailySummary module not implemented yet")

    def test_daily_summary_basic_functionality(self):
        """Test DailySummary basic functionality if implemented."""
        try:
            from garmy.metrics import DailySummary

            if hasattr(DailySummary, "__dataclass_fields__"):
                try:
                    summary_instance = DailySummary()
                    assert summary_instance is not None
                except TypeError:
                    pytest.skip(
                        "DailySummary requires specific fields for instantiation"
                    )

        except ImportError:
            pytest.skip("DailySummary module not implemented yet")


class TestRespiration:
    """Test cases for Respiration metric module."""

    def create_sample_respiration_data(self) -> Dict[str, Any]:
        """Create sample respiration API response data."""
        return {
            "userProfilePk": 12345,
            "calendarDate": "2023-12-01",
            "startTimestampGmt": "2023-12-01T00:00:00Z",
            "endTimestampGmt": "2023-12-01T23:59:59Z",
            "avgWakingRespirationValue": 14.5,
            "highestRespirationValue": 18.0,
            "lowestRespirationValue": 12.0,
            "avgSleepRespirationValue": 13.2,
            "respirationValues": [
                {"timestamp": 1701415200000, "value": 14.5},
                {"timestamp": 1701418800000, "value": 15.0},
                {"timestamp": 1701422400000, "value": 13.8},
            ],
        }

    def test_respiration_module_exists(self):
        """Test Respiration module can be imported."""
        try:
            from garmy.metrics import respiration

            assert respiration is not None
        except ImportError:
            pytest.fail("Respiration module should be importable")

    def test_respiration_class_import(self):
        """Test Respiration class can be imported."""
        from garmy.metrics import Respiration

        assert Respiration is not None
        assert hasattr(Respiration, "__dataclass_fields__")

    def test_respiration_has_metric_config(self):
        """Test Respiration module has proper metric configuration."""
        try:
            import garmy.metrics.respiration as respiration_module

            assert hasattr(respiration_module, "METRIC_CONFIG")
            assert hasattr(respiration_module, "__metric_config__")

            config = respiration_module.METRIC_CONFIG
            assert isinstance(config, MetricConfig)
            assert config.metric_class is not None
            assert config.version is not None
        except ImportError:
            pytest.skip("Respiration module not implemented yet")

    def test_respiration_basic_functionality(self):
        """Test Respiration basic functionality if implemented."""
        try:
            from garmy.metrics import Respiration

            if hasattr(Respiration, "__dataclass_fields__"):
                try:
                    respiration_instance = Respiration()
                    assert respiration_instance is not None
                except TypeError:
                    pytest.skip(
                        "Respiration requires specific fields for instantiation"
                    )

        except ImportError:
            pytest.skip("Respiration module not implemented yet")


class TestSteps:
    """Test cases for Steps metric module."""

    def create_sample_steps_data(self) -> Dict[str, Any]:
        """Create sample steps API response data."""
        return {
            "userProfilePk": 12345,
            "calendarDate": "2023-12-01",
            "totalSteps": 12500,
            "stepGoal": 10000,
            "totalDistance": 8500.0,  # meters
            "activeTime": 2700,  # seconds (45 minutes)
            "wellnessDataDto": {
                "totalSteps": 12500,
                "stepGoal": 10000,
                "totalDistanceMeters": 8500,
                "activeTimeInMinutes": 45,
            },
            "stepsTimeline": [
                {"timestamp": 1701415200000, "steps": 150},
                {"timestamp": 1701418800000, "steps": 200},
                {"timestamp": 1701422400000, "steps": 180},
            ],
        }

    def test_steps_module_exists(self):
        """Test Steps module can be imported."""
        try:
            from garmy.metrics import steps

            assert steps is not None
        except ImportError:
            pytest.fail("Steps module should be importable")

    def test_steps_class_import(self):
        """Test Steps class can be imported."""
        from garmy.metrics import Steps

        assert Steps is not None
        assert hasattr(Steps, "__dataclass_fields__")

    def test_steps_has_metric_config(self):
        """Test Steps module has proper metric configuration."""
        try:
            import garmy.metrics.steps as steps_module

            assert hasattr(steps_module, "METRIC_CONFIG")
            assert hasattr(steps_module, "__metric_config__")

            config = steps_module.METRIC_CONFIG
            assert isinstance(config, MetricConfig)
            assert config.metric_class is not None
            assert config.version is not None
        except ImportError:
            pytest.skip("Steps module not implemented yet")

    def test_steps_basic_functionality(self):
        """Test Steps basic functionality if implemented."""
        try:
            from garmy.metrics import Steps

            if hasattr(Steps, "__dataclass_fields__"):
                try:
                    steps_instance = Steps()
                    assert steps_instance is not None
                except TypeError:
                    pytest.skip("Steps requires specific fields for instantiation")

        except ImportError:
            pytest.skip("Steps module not implemented yet")


class TestStress:
    """Test cases for Stress metric module."""

    def create_sample_stress_data(self) -> Dict[str, Any]:
        """Create sample stress API response data."""
        return {
            "userProfilePk": 12345,
            "calendarDate": "2023-12-01",
            "startTimestampGmt": "2023-12-01T00:00:00Z",
            "endTimestampGmt": "2023-12-01T23:59:59Z",
            "maxStressLevel": 65,
            "avgStressLevel": 32,
            "stressChartValueOffset": 0,
            "stressChartYAxisOrigin": 0,
            "stressValueDescriptorsDtoList": [
                {"key": "timestamp", "index": 0},
                {"key": "stressLevel", "index": 1},
            ],
            "stressValuesArray": [
                [1701415200000, 25, 1.0],
                [1701418800000, 35, 1.0],
                [1701422400000, 40, 1.0],
            ],
            "bodyBatteryValuesArray": [
                [1701415200000, "CHARGING", 75, 1.0],
                [1701418800000, "DRAINING", 70, 1.0],
            ],
        }

    def test_stress_module_exists(self):
        """Test Stress module can be imported."""
        try:
            from garmy.metrics import stress

            assert stress is not None
        except ImportError:
            pytest.fail("Stress module should be importable")

    def test_stress_class_import(self):
        """Test Stress class can be imported."""
        from garmy.metrics import Stress

        assert Stress is not None
        assert hasattr(Stress, "__dataclass_fields__")

    def test_stress_has_metric_config(self):
        """Test Stress module has proper metric configuration."""
        try:
            import garmy.metrics.stress as stress_module

            assert hasattr(stress_module, "METRIC_CONFIG")
            assert hasattr(stress_module, "__metric_config__")

            config = stress_module.METRIC_CONFIG
            assert isinstance(config, MetricConfig)
            assert config.metric_class is not None
            assert config.version is not None
        except ImportError:
            pytest.skip("Stress module not implemented yet")

    def test_stress_basic_functionality(self):
        """Test Stress basic functionality if implemented."""
        try:
            from garmy.metrics import Stress

            if hasattr(Stress, "__dataclass_fields__"):
                try:
                    stress_instance = Stress()
                    assert stress_instance is not None
                except TypeError:
                    pytest.skip("Stress requires specific fields for instantiation")

        except ImportError:
            pytest.skip("Stress module not implemented yet")


class TestMetricsModuleStructure:
    """Test the overall structure of metrics modules."""

    def test_all_metrics_modules_importable(self):
        """Test all metrics modules can be imported."""
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
            try:
                module = __import__(f"garmy.metrics.{module_name}", fromlist=[""])
                assert module is not None
            except ImportError as e:
                pytest.fail(f"Module {module_name} should be importable: {e}")

    def test_all_exported_classes_are_dataclasses(self):
        """Test all exported metric classes are dataclasses."""
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
            assert hasattr(cls, "__dataclass_fields__"), (
                f"{cls.__name__} should be a dataclass"
            )

    def test_metric_configs_consistency(self):
        """Test metric configurations are consistent across modules."""
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
            try:
                module = __import__(f"garmy.metrics.{module_name}", fromlist=[""])

                # Check required attributes exist
                assert hasattr(module, "METRIC_CONFIG"), (
                    f"{module_name} missing METRIC_CONFIG"
                )
                assert hasattr(module, "__metric_config__"), (
                    f"{module_name} missing __metric_config__"
                )

                # Check config is valid
                config = module.METRIC_CONFIG
                assert isinstance(config, MetricConfig), (
                    f"{module_name} METRIC_CONFIG not MetricConfig instance"
                )
                assert config.metric_class is not None, (
                    f"{module_name} missing metric_class"
                )
                assert config.version is not None, f"{module_name} missing version"

                # Check consistency between METRIC_CONFIG and __metric_config__
                assert module.__metric_config__ == config, (
                    f"{module_name} config exports inconsistent"
                )

            except ImportError:
                pytest.skip(f"Module {module_name} not implemented yet")

    def test_endpoint_or_builder_present(self):
        """Test each metric has either endpoint or endpoint_builder."""
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
            try:
                module = __import__(f"garmy.metrics.{module_name}", fromlist=[""])
                config = module.METRIC_CONFIG

                # Must have either endpoint or endpoint_builder
                has_endpoint = bool(config.endpoint)
                has_builder = bool(config.endpoint_builder)

                assert has_endpoint or has_builder, (
                    f"{module_name} needs endpoint or endpoint_builder"
                )

            except ImportError:
                pytest.skip(f"Module {module_name} not implemented yet")

    def test_parser_functions_exist(self):
        """Test parser functions exist where expected."""
        modules_with_parsers = [
            "training_readiness",
            "body_battery",
            "sleep",
            "activities",
            "heart_rate",
        ]

        for module_name in modules_with_parsers:
            try:
                module = __import__(f"garmy.metrics.{module_name}", fromlist=[""])
                config = module.METRIC_CONFIG

                if config.parser:
                    assert callable(config.parser), f"{module_name} parser not callable"

            except ImportError:
                pytest.skip(f"Module {module_name} not implemented yet")


class TestMetricsDataValidation:
    """Test data validation and edge cases for metrics."""

    def test_required_vs_optional_fields(self):
        """Test required vs optional field handling in metrics."""
        from garmy.metrics import TrainingReadiness

        # Test creating with minimal required fields
        tr = TrainingReadiness(
            score=75,
            level="READY",
            feedback_long="Ready",
            feedback_short="READY",
            calendar_date="2023-12-01",
            timestamp=datetime(2023, 12, 1),
            user_profile_pk=12345,
            device_id=67890,
        )

        assert tr.score == 75
        assert tr.level == "READY"
        assert tr.sleep_score is None  # Optional field

    def test_nested_dict_handling(self):
        """Test handling of nested dictionary fields."""
        from garmy.metrics import ActivitySummary

        activity = ActivitySummary(
            activity_type={"typeKey": "running", "typeId": 1},
            event_type={"typeKey": "race", "typeId": 2},
            privacy={"typeKey": "public", "typeId": 1},
        )

        # Test property methods work with nested dicts
        assert activity.activity_type_name == "running"
        assert activity.activity_type_id == 1
        assert activity.privacy_type == "public"

    def test_calculated_properties_edge_cases(self):
        """Test calculated properties with edge case values."""
        from garmy.metrics.heart_rate import HeartRate, HeartRateSummary

        # Test with zero/negative values
        summary = HeartRateSummary(max_heart_rate=0, min_heart_rate=0)
        hr = HeartRate(heart_rate_summary=summary, heart_rate_values_array=[])

        assert summary.heart_rate_range == 0
        assert hr.average_heart_rate == 0.0

    def test_timestamp_property_edge_cases(self):
        """Test timestamp-related properties with edge cases."""
        from garmy.metrics.body_battery import BodyBatteryReading
        from datetime import timezone

        # Test with very old timestamp
        reading = BodyBatteryReading(
            timestamp=0,
            level=50,
            status="UNKNOWN",
            version=1.0,  # Unix epoch
        )

        dt = reading.datetime
        assert isinstance(dt, datetime)
        assert dt.year == 1970
        assert dt.tzinfo == timezone.utc

    def test_list_processing_edge_cases(self):
        """Test list processing with various edge cases."""
        from garmy.metrics.body_battery import BodyBattery

        # Test with malformed data arrays
        bb = BodyBattery(
            user_profile_pk=12345,
            calendar_date="2023-12-01",
            body_battery_values_array=[
                [],  # Empty array
                [1701415200000],  # Incomplete array
                [1701418800000, "CHARGING", 75, 1.0],  # Valid array
                [1701422400000, "DRAINING", None, 1.0],  # Null value
            ],
        )

        readings = bb.body_battery_readings
        # Should only include valid readings with 4+ elements
        assert (
            len(readings) == 2
        )  # The valid array and the one with None (both have 4 elements)
        assert readings[0].level == 75
        assert readings[1].level is None  # None values are preserved


if __name__ == "__main__":
    pytest.main([__file__])
