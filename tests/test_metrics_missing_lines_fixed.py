"""Tests specifically targeting missing lines in metrics modules.

This module contains tests designed to hit exact missing lines identified
in the coverage report to achieve 100% coverage.
"""

from datetime import datetime

import pytest


class TestCaloriesMissingLines:
    """Tests for missing lines in calories.py module."""

    def test_calories_date_property_line_88(self):
        """Test line 88: datetime.strptime(self.calendar_date, "%Y-%m-%d")."""
        from garmy.metrics.calories import Calories

        calories = Calories(calendar_date="2023-12-01")

        # This should trigger line 88
        date_result = calories.date
        assert isinstance(date_result, datetime)
        assert date_result.year == 2023
        assert date_result.month == 12
        assert date_result.day == 1

    def test_calories_activity_efficiency_lines_93_95(self):
        """Test lines 93-95: activity efficiency calculation and zero case."""
        from garmy.metrics.calories import Calories

        # Test normal case (line 94)
        calories1 = Calories(total_kilocalories=2500, active_kilocalories=800)
        efficiency = calories1.activity_efficiency
        assert efficiency == (800 / 2500) * 100

        # Test zero case (line 95)
        calories2 = Calories(total_kilocalories=0, active_kilocalories=800)
        efficiency_zero = calories2.activity_efficiency
        assert efficiency_zero == 0.0

    def test_calories_bmr_percentage_lines_100_102(self):
        """Test lines 100-102: BMR percentage calculation and zero case."""
        from garmy.metrics.calories import Calories

        # Test normal case (line 101)
        calories1 = Calories(total_kilocalories=2500, bmr_kilocalories=1700)
        bmr_pct = calories1.bmr_percentage
        assert bmr_pct == (1700 / 2500) * 100

        # Test zero case (line 102)
        calories2 = Calories(total_kilocalories=0, bmr_kilocalories=1700)
        bmr_pct_zero = calories2.bmr_percentage
        assert bmr_pct_zero == 0.0

    def test_calories_total_burned_line_107(self):
        """Test line 107: burned_kilocalories or total_kilocalories."""
        from garmy.metrics.calories import Calories

        # Test with burned_kilocalories available
        calories1 = Calories(total_kilocalories=2500, burned_kilocalories=2200)
        assert calories1.total_burned == 2200

        # Test with burned_kilocalories as None (should fall back to total_kilocalories)
        calories2 = Calories(total_kilocalories=2500, burned_kilocalories=None)
        assert calories2.total_burned == 2500

    def test_calories_calorie_balance_lines_112_117(self):
        """Test lines 112-117: calorie balance calculation."""
        from garmy.metrics.calories import Calories

        # Test with both values available (lines 113-116)
        calories1 = Calories(consumed_kilocalories=2300, burned_kilocalories=2200)
        balance = calories1.calorie_balance
        assert balance == 100  # 2300 - 2200

        # Test with consumed_kilocalories None (line 117)
        calories2 = Calories(consumed_kilocalories=None, burned_kilocalories=2200)
        balance_none = calories2.calorie_balance
        assert balance_none is None

        # Test with burned_kilocalories None (line 117)
        calories3 = Calories(consumed_kilocalories=2300, burned_kilocalories=None)
        balance_none2 = calories3.calorie_balance
        assert balance_none2 is None

    def test_calories_goal_progress_lines_122_124(self):
        """Test lines 122-124: goal progress calculation."""
        from garmy.metrics.calories import Calories

        # Test with valid goal (line 123)
        calories1 = Calories(total_kilocalories=2500, net_calorie_goal=2400)
        progress = calories1.goal_progress
        assert progress == (2500 / 2400) * 100

        # Test with zero goal (line 124)
        calories2 = Calories(total_kilocalories=2500, net_calorie_goal=0)
        progress_none = calories2.goal_progress
        assert progress_none is None

        # Test with None goal (line 124)
        calories3 = Calories(total_kilocalories=2500, net_calorie_goal=None)
        progress_none2 = calories3.goal_progress
        assert progress_none2 is None


class TestStepsMissingLines:
    """Tests for missing lines in steps.py module."""

    def test_steps_properties_lines_51_61(self):
        """Test missing lines in DailySteps properties."""
        from garmy.metrics.steps import DailySteps

        # Test distance conversion properties
        daily_step = DailySteps(
            calendar_date="2023-12-01",
            total_steps=12000,
            step_goal=10000,
            total_distance=8500,  # meters
        )

        # Test distance_km property (line 51)
        distance_km = daily_step.distance_km
        assert distance_km == 8.5

        # Test distance_miles property (line 56)
        distance_miles = daily_step.distance_miles
        assert abs(distance_miles - 5.28) < 0.1  # approximate check

        # Test date property (line 61)
        date_obj = daily_step.date
        assert date_obj.year == 2023
        assert date_obj.month == 12
        assert date_obj.day == 1

    def test_steps_aggregations_basic_usage(self):
        """Test Steps aggregations to cover missing lines."""
        from garmy.metrics.steps import DailySteps, Steps, StepsAggregations

        # Create Steps with aggregations and daily data
        steps = Steps(
            daily_steps=[
                DailySteps(
                    calendar_date="2023-12-01",
                    total_steps=12000,
                    step_goal=10000,
                    total_distance=8500,
                )
            ],
            aggregations=StepsAggregations(daily_average=11000, weekly_total=77000),
        )

        # Test weekly_total property (lines 162-166)
        weekly_total = steps.weekly_total
        assert weekly_total == 77000

        # Test total_distance_km property (line 171)
        total_distance = steps.total_distance_km
        assert total_distance == 8.5

    def test_steps_build_endpoint_lines_76_89(self):
        """Test the build_steps_endpoint function."""
        from datetime import date

        from garmy.metrics.steps import build_steps_endpoint

        # Test with None date (lines 76-77)
        endpoint1 = build_steps_endpoint()
        assert "/usersummary-service/stats/daily/" in endpoint1
        assert "statsType=STEPS" in endpoint1

        # Test with string date (lines 78-79)
        endpoint2 = build_steps_endpoint("2023-12-01")
        assert "/usersummary-service/stats/daily/" in endpoint2
        assert (
            "2023-12-01" in endpoint2 or "2023-11-25" in endpoint2
        )  # Could be start or end date

        # Test with date object (lines 80-81)
        test_date = date(2023, 12, 1)
        endpoint3 = build_steps_endpoint(test_date)
        assert "/usersummary-service/stats/daily/" in endpoint3


class TestStressMissingLines:
    """Tests for missing lines in stress.py module."""

    def test_stress_reading_properties_lines_52_66(self):
        """Test missing lines in StressReading properties."""
        from garmy.metrics.stress import StressReading

        # Test stress reading with various stress levels
        reading1 = StressReading(timestamp=1701415200000, stress_level=-1)
        assert reading1.stress_category == "Rest"  # line 58

        reading2 = StressReading(timestamp=1701415200000, stress_level=20)
        assert reading2.stress_category == "Low"  # line 60

        reading3 = StressReading(timestamp=1701415200000, stress_level=40)
        assert reading3.stress_category == "Medium"  # line 62

        reading4 = StressReading(timestamp=1701415200000, stress_level=60)
        assert reading4.stress_category == "High"  # line 64

        reading5 = StressReading(timestamp=1701415200000, stress_level=80)
        assert reading5.stress_category == "Very High"  # line 66

        # Test datetime property (line 52)
        datetime_obj = reading1.datetime
        assert datetime_obj is not None

    def test_stress_readings_property_lines_126_145(self):
        """Test missing lines in stress readings property."""
        from garmy.metrics.stress import Stress

        stress = Stress(
            user_profile_pk=12345,
            calendar_date="2023-12-01",
            max_stress_level=65,
            avg_stress_level=32,
            stress_values_array=[
                [1701415200000, 25],
                [1701418800000, 35],
                [1701422400000, 40],
            ],
        )

        # Test stress_readings property (lines 126-132)
        readings = stress.stress_readings
        assert len(readings) == 3
        assert readings[0].stress_level == 25
        assert readings[1].stress_level == 35
        assert readings[2].stress_level == 40


class TestRespirationMissingLines:
    """Tests for missing lines in respiration.py module."""

    def test_respiration_summary_properties_lines_71_96(self):
        """Test missing lines in RespirationSummary properties."""
        from garmy.metrics.respiration import RespirationSummary

        resp_summary = RespirationSummary(
            highest_respiration_value=18,
            lowest_respiration_value=12,
            avg_waking_respiration_value=15,
            avg_sleep_respiration_value=13,
            sleep_start_timestamp_gmt="2023-12-01T22:00:00Z",
            sleep_end_timestamp_gmt="2023-12-02T06:00:00Z",
            sleep_start_timestamp_local="2023-12-01T22:00:00",
            sleep_end_timestamp_local="2023-12-02T06:00:00",
        )

        # Test respiration_range property (line 71)
        resp_range = resp_summary.respiration_range
        assert resp_range == 6  # 18 - 12

        # Test waking_vs_sleep_difference property (line 76)
        waking_sleep_diff = resp_summary.waking_vs_sleep_difference
        assert waking_sleep_diff == 2  # 15 - 13

        # Test datetime properties (lines 81, 86, 91, 96)
        sleep_start_gmt = resp_summary.sleep_start_datetime_gmt
        sleep_end_gmt = resp_summary.sleep_end_datetime_gmt
        sleep_start_local = resp_summary.sleep_start_datetime_local
        sleep_end_local = resp_summary.sleep_end_datetime_local

        assert sleep_start_gmt is not None
        assert sleep_end_gmt is not None
        assert sleep_start_local is not None
        assert sleep_end_local is not None

    def test_respiration_count_properties_lines_142_158(self):
        """Test missing lines in Respiration count properties."""
        from garmy.metrics.respiration import Respiration, RespirationSummary

        respiration = Respiration(
            respiration_summary=RespirationSummary(),
            respiration_values_array=[
                [1701415200000, 14],
                [1701418800000, -1],  # Invalid reading
                [1701422400000, 16],
                [1701425600000, 15],
            ],
            respiration_averages_values_array=[
                [1701415200000, 14, 16, 12],
                [1701418800000, 15, 17, 13],
            ],
        )

        # Test readings_count property (line 142)
        readings_count = respiration.readings_count
        assert readings_count == 4

        # Test valid_readings_count property (lines 147-153)
        valid_count = respiration.valid_readings_count
        assert valid_count == 3  # Excludes the -1 reading

        # Test averages_count property (line 158)
        averages_count = respiration.averages_count
        assert averages_count == 2


class TestHRVMissingLines:
    """Tests for missing lines in hrv.py module."""

    def test_hrv_reading_properties_lines_57_62(self):
        """Test missing lines in HRVReading properties."""
        from garmy.metrics.hrv import HRVReading

        reading = HRVReading(
            hrv_value=45,
            reading_time_gmt="2023-12-01T06:00:00Z",
            reading_time_local="2023-12-01T07:00:00",
        )

        # Test datetime_gmt property (line 57)
        datetime_gmt = reading.datetime_gmt
        assert datetime_gmt is not None

        # Test datetime_local property (line 62)
        datetime_local = reading.datetime_local
        assert datetime_local is not None

    def test_hrv_summary_date_property_line_43(self):
        """Test missing line in HRVSummary date property."""
        from garmy.metrics.hrv import HRVBaseline, HRVSummary

        baseline = HRVBaseline(
            low_upper=35, balanced_low=30, balanced_upper=50, marker_value=42.5
        )

        summary = HRVSummary(
            calendar_date="2023-12-01",
            weekly_avg=45,
            last_night_avg=42,
            last_night_5_min_high=55,
            baseline=baseline,
            status="BALANCED",
            feedback_phrase="Your HRV is in normal range",
            create_time_stamp="2023-12-01T08:00:00Z",
        )

        # Test date property (line 43)
        date_obj = summary.date
        assert date_obj.year == 2023
        assert date_obj.month == 12
        assert date_obj.day == 1

    def test_hrv_parser_lines_68_109(self):
        """Test missing lines in parse_hrv_data function."""
        from garmy.metrics.hrv import parse_hrv_data

        # Test with sample data
        sample_data = {
            "userProfilePk": 12345,
            "hrvSummary": {
                "calendarDate": "2023-12-01",
                "weeklyAvg": 45,
                "lastNightAvg": 42,
                "lastNight5MinHigh": 55,
                "baseline": {
                    "lowUpper": 35,
                    "balancedLow": 30,
                    "balancedUpper": 50,
                    "markerValue": 42.5,
                },
                "status": "BALANCED",
                "feedbackPhrase": "Your HRV is normal",
                "createTimeStamp": "2023-12-01T08:00:00Z",
            },
            "hrvReadings": [
                {
                    "hrvValue": 42,
                    "readingTimeGmt": "2023-12-01T06:00:00Z",
                    "readingTimeLocal": "2023-12-01T07:00:00",
                }
            ],
        }

        # This should trigger the parser lines 68-109
        hrv = parse_hrv_data(sample_data)
        assert hrv.user_profile_pk == 12345
        assert hrv.hrv_summary.calendar_date == "2023-12-01"
        assert len(hrv.hrv_readings) == 1


class TestDailySummaryMissingLines:
    """Tests for missing lines in daily_summary.py module."""

    def test_daily_summary_date_property_line_269(self):
        """Test missing line in DailySummary date property."""
        from garmy.metrics.daily_summary import DailySummary

        summary = DailySummary(calendar_date="2023-12-01")

        # Test date property (line 269)
        date_obj = summary.date
        assert date_obj.year == 2023
        assert date_obj.month == 12
        assert date_obj.day == 1

    def test_daily_summary_calculated_properties_lines_275_400(self):
        """Test missing lines in daily summary calculated properties."""
        from garmy.metrics.daily_summary import DailySummary

        summary = DailySummary(
            total_steps=12000,
            daily_step_goal=10000,
            total_distance_meters=8500,
            highly_active_seconds=1800,
            active_seconds=2400,
            sedentary_seconds=72000,
            moderate_intensity_minutes=30,
            vigorous_intensity_minutes=15,
            intensity_minutes_goal=150,
            total_kilocalories=2500,
            active_kilocalories=800,
            bmr_kilocalories=1700,
            max_heart_rate=180,
            min_heart_rate=60,
            resting_heart_rate=65,
            last_seven_days_avg_resting_heart_rate=62,
            max_stress_level=65,
            average_stress_level=32,
            total_stress_duration=28800,
            body_battery_highest_value=95,
            body_battery_lowest_value=25,
            body_battery_charged_value=40,
            body_battery_drained_value=30,
            average_spo2=96,
            lowest_spo2=92,
            highest_respiration_value=18,
            lowest_respiration_value=12,
            sleeping_seconds=28800,
            measurable_asleep_duration=25200,
            duration_in_milliseconds=86400000,
            last_sync_timestamp_gmt="2023-12-01T08:00:00Z",
        )

        # Test distance properties (lines 275, 280)
        assert summary.distance_km == 8.5
        assert abs(summary.distance_miles - 5.28) < 0.1

        # Test step goal progress (lines 285-287)
        assert summary.step_goal_progress == 120.0

        # Test activity time properties (lines 292, 297)
        assert summary.total_active_minutes == 70.0  # (1800 + 2400) / 60
        assert summary.total_sedentary_hours == 20.0  # 72000 / 3600

        # Test intensity minutes progress (lines 302-307)
        expected_progress = ((30 + 15 * 2) / 150) * 100  # 40%
        assert summary.intensity_minutes_progress == expected_progress

        # Test calorie efficiency properties (lines 313-315, 320-322)
        assert summary.activity_efficiency == 32.0  # (800 / 2500) * 100
        assert summary.bmr_percentage == 68.0  # (1700 / 2500) * 100

        # Test heart rate properties (lines 328, 333)
        assert summary.heart_rate_range == 120  # 180 - 60
        assert summary.resting_hr_trend == 3  # 65 - 62

        # Test stress properties (lines 339, 344)
        assert summary.stress_range == 33  # 65 - 32
        assert summary.total_stress_hours == 8.0  # 28800 / 3600

        # Test body battery properties (lines 350, 355)
        assert summary.body_battery_range == 70  # 95 - 25
        assert summary.net_body_battery_change == 10  # 40 - 30

        # Test SpO2 property (line 361)
        assert summary.spo2_range == 4  # 96 - 92

        # Test respiration property (line 367)
        assert summary.respiration_range == 6  # 18 - 12

        # Test sleep properties (lines 373, 378)
        assert summary.sleep_hours == 8.0  # 28800 / 3600
        assert summary.measurable_sleep_hours == 7.0  # 25200 / 3600

        # Test metadata properties (lines 384, 389)
        assert summary.wellness_duration_hours == 24.0  # 86400000 / 3600000
        assert summary.last_sync_datetime_gmt is not None


# Tests for sleep module TYPE_CHECKING line
class TestSleepMissingLines:
    """Tests for missing lines in sleep.py module."""

    def test_sleep_summary_properties_lines_100_130(self):
        """Test missing lines in SleepSummary properties."""
        from garmy.metrics.sleep import SleepSummary

        sleep_summary = SleepSummary(
            sleep_start_timestamp_gmt=1701415200000,
            sleep_end_timestamp_gmt=1701443200000,
            sleep_start_timestamp_local=1701415200000,
            sleep_end_timestamp_local=1701443200000,
            sleep_time_seconds=28800,
        )

        # Test datetime properties (lines 100, 105, 110, 115)
        start_gmt = sleep_summary.sleep_start_datetime_gmt
        end_gmt = sleep_summary.sleep_end_datetime_gmt
        start_local = sleep_summary.sleep_start_datetime_local
        end_local = sleep_summary.sleep_end_datetime_local

        assert start_gmt is not None
        assert end_gmt is not None
        assert start_local is not None
        assert end_local is not None

        # Test sleep duration property (line 120)
        duration_hours = sleep_summary.total_sleep_duration_hours
        assert duration_hours == 8.0  # 28800 seconds = 8 hours

        # Test sleep efficiency property (lines 125-130)
        efficiency = sleep_summary.sleep_efficiency_percentage
        assert efficiency > 0  # Should calculate efficiency


if __name__ == "__main__":
    pytest.main([__file__])
