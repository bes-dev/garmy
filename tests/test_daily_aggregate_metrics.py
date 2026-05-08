"""Tests for PR 2 daily aggregate metrics: IntensityMinutes, Floors, RestingHeartRate."""

import pytest

from garmy.core.base import MetricConfig
from garmy.localdb.extractors import DataExtractor
from garmy.localdb.models import MetricType
from garmy.metrics.floors import Floors, parse_floors_data
from garmy.metrics.intensity_minutes import IntensityMinutes, parse_intensity_minutes_data
from garmy.metrics.resting_heart_rate import RestingHeartRate, parse_resting_heart_rate_data


# ---------------------------------------------------------------------------
# IntensityMinutes
# ---------------------------------------------------------------------------


class TestIntensityMinutesParsing:
    """Test IntensityMinutes API response parsing."""

    def create_sample_response(self, **overrides):
        """Create a realistic intensity minutes API response matching actual Garmin API."""
        response = {
            "calendarDate": "2026-03-23",
            "moderateMinutes": 52,
            "vigorousMinutes": 36,
            "weeklyTotal": 124,
            "weekGoal": 150,
            "startDayMinutes": 0,
            "endDayMinutes": 124,
            "weeklyModerate": 52,
            "weeklyVigorous": 36,
            "imValuesArray": [
                [1774276200000, 6],
                [1774277100000, 21],
                [1774278000000, 20],
            ],
        }
        response.update(overrides)
        return response

    def test_parse_full_response(self):
        data = self.create_sample_response()
        result = parse_intensity_minutes_data(data)

        assert isinstance(result, IntensityMinutes)
        assert result.calendar_date == "2026-03-23"
        assert result.moderate_minutes == 52
        assert result.vigorous_minutes == 36
        assert result.weekly_total == 124
        assert result.week_goal == 150
        assert len(result.im_values_array) == 3

    def test_parse_empty_response(self):
        data = {"calendarDate": "2026-03-24"}
        result = parse_intensity_minutes_data(data)

        assert result.calendar_date == "2026-03-24"
        assert result.moderate_minutes is None
        assert result.vigorous_minutes is None
        assert result.weekly_total is None
        assert result.week_goal is None
        assert result.im_values_array == []

    def test_parse_zero_values(self):
        data = self.create_sample_response(
            moderateMinutes=0, vigorousMinutes=0, weeklyTotal=0
        )
        result = parse_intensity_minutes_data(data)

        assert result.moderate_minutes == 0
        assert result.vigorous_minutes == 0
        assert result.weekly_total == 0

    def test_daily_total_property(self):
        """Test daily_total computes sum of timeseries values."""
        im = IntensityMinutes(
            im_values_array=[[1774276200000, 6], [1774277100000, 21], [1774278000000, 20]]
        )
        assert im.daily_total == 47

    def test_daily_total_empty_array(self):
        """Test daily_total returns None when no readings."""
        im = IntensityMinutes(im_values_array=[])
        assert im.daily_total is None

    def test_daily_total_skips_none_values(self):
        """Test daily_total skips None values in array."""
        im = IntensityMinutes(
            im_values_array=[[1774276200000, 6], [1774277100000, None], [1774278000000, 20]]
        )
        assert im.daily_total == 26

    def test_parse_invalid_data_raises(self):
        with pytest.raises(ValueError, match="Expected dictionary"):
            parse_intensity_minutes_data("not a dict")


class TestIntensityMinutesMetricConfig:
    """Test IntensityMinutes metric configuration."""

    def test_metric_config_exists(self):
        from garmy.metrics.intensity_minutes import __metric_config__

        assert __metric_config__ is not None
        assert __metric_config__.endpoint == "/wellness-service/wellness/daily/im/{date}"
        assert __metric_config__.metric_class is IntensityMinutes
        assert __metric_config__.parser is parse_intensity_minutes_data
        assert isinstance(__metric_config__, MetricConfig)

    def test_importable_from_package(self):
        from garmy.metrics import IntensityMinutes as IMImport

        assert IMImport is IntensityMinutes


class TestIntensityMinutesExtraction:
    """Test IntensityMinutes data extraction for daily_health_metrics."""

    def test_extract_intensity_minutes(self):
        im = IntensityMinutes(
            calendar_date="2026-03-23",
            moderate_minutes=52,
            vigorous_minutes=36,
            weekly_total=124,
            week_goal=150,
            im_values_array=[[1774276200000, 6], [1774277100000, 21], [1774278000000, 20]],
        )

        extractor = DataExtractor()
        result = extractor.extract_metric_data(im, MetricType.INTENSITY_MINUTES)

        assert result["moderate_intensity_minutes"] == 52
        assert result["vigorous_intensity_minutes"] == 36
        # intensity_minutes_total is the daily sum from timeseries, not weekly_total
        assert result["intensity_minutes_total"] == 47  # 6 + 21 + 20
        assert result["intensity_minutes_goal"] == 150

    def test_extract_intensity_minutes_none_values(self):
        im = IntensityMinutes()
        extractor = DataExtractor()
        result = extractor.extract_metric_data(im, MetricType.INTENSITY_MINUTES)

        assert result["moderate_intensity_minutes"] is None
        assert result["vigorous_intensity_minutes"] is None
        assert result["intensity_minutes_total"] is None
        assert result["intensity_minutes_goal"] is None


class TestIntensityMinutesTimeseriesExtraction:
    """Test IntensityMinutes timeseries extraction for localdb storage."""

    def test_extract_timeseries(self):
        """Test timeseries extraction from imValuesArray."""
        im = IntensityMinutes(
            im_values_array=[
                [1774276200000, 6],
                [1774277100000, 21],
                [1774278000000, 20],
            ],
        )

        extractor = DataExtractor()
        timeseries = extractor.extract_timeseries_data(im, MetricType.INTENSITY_MINUTES)

        assert len(timeseries) == 3
        ts, value, meta = timeseries[0]
        assert ts == 1774276200000
        assert value == 6
        assert meta == {}

    def test_extract_timeseries_skips_none_values(self):
        """Test that readings with None value are skipped."""
        im = IntensityMinutes(
            im_values_array=[
                [1774276200000, None],
                [1774277100000, 21],
            ],
        )

        extractor = DataExtractor()
        timeseries = extractor.extract_timeseries_data(im, MetricType.INTENSITY_MINUTES)

        assert len(timeseries) == 1
        assert timeseries[0][1] == 21

    def test_extract_timeseries_empty_array(self):
        """Test timeseries extraction with no readings."""
        im = IntensityMinutes(im_values_array=[])
        extractor = DataExtractor()
        timeseries = extractor.extract_timeseries_data(im, MetricType.INTENSITY_MINUTES)

        assert timeseries == []


# ---------------------------------------------------------------------------
# Floors
# ---------------------------------------------------------------------------


class TestFloorsParsing:
    """Test Floors API response parsing."""

    def create_sample_response(self, **overrides):
        """Create a realistic floors chart API response."""
        response = {
            "startTimestampGMT": "2026-03-24T00:00:00.0",
            "endTimestampGMT": "2026-03-25T00:00:00.0",
            "floorValuesArray": [
                [1711238400000, 3, 1],
                [1711242000000, 2, 0],
                [1711245600000, 0, 2],
                [1711249200000, 5, 3],
            ],
        }
        response.update(overrides)
        return response

    def test_parse_full_response(self):
        data = self.create_sample_response()
        result = parse_floors_data(data)

        assert isinstance(result, Floors)
        assert result.calendar_date == "2026-03-24"
        assert result.floors_ascended == 10  # 3 + 2 + 0 + 5
        assert result.floors_descended == 6  # 1 + 0 + 2 + 3

    def test_parse_empty_array(self):
        data = {"floorValuesArray": []}
        result = parse_floors_data(data)

        assert result.floors_ascended is None
        assert result.floors_descended is None

    def test_parse_missing_array(self):
        data = {}
        result = parse_floors_data(data)

        assert result.floors_ascended is None
        assert result.floors_descended is None

    def test_parse_none_values_in_array(self):
        """Test that None values in array entries are handled gracefully."""
        data = {
            "floorValuesArray": [
                [1711238400000, 3, None],
                [1711242000000, None, 2],
                [1711245600000, 1, 1],
            ],
        }
        result = parse_floors_data(data)

        assert result.floors_ascended == 4  # 3 + 0 + 1
        assert result.floors_descended == 3  # 0 + 2 + 1

    def test_parse_malformed_entries_skipped(self):
        """Test that entries with fewer than 3 elements are skipped."""
        data = {
            "floorValuesArray": [
                [1711238400000, 3, 1],
                [1711242000000],  # malformed
                [1711245600000, 2, 0],
            ],
        }
        result = parse_floors_data(data)

        assert result.floors_ascended == 5  # 3 + 2
        assert result.floors_descended == 1

    def test_parse_string_values_in_array(self):
        """Test that string values in array entries are cast to int."""
        data = {
            "floorValuesArray": [
                [1711238400000, "3", "1"],
                [1711242000000, "2", "0"],
            ],
        }
        result = parse_floors_data(data)

        assert result.floors_ascended == 5
        assert result.floors_descended == 1

    def test_parse_invalid_data_raises(self):
        with pytest.raises(ValueError, match="Expected dictionary"):
            parse_floors_data("not a dict")

    def test_calendar_date_from_timestamp(self):
        """Test date extraction from startTimestampGMT."""
        data = {
            "startTimestampGMT": "2026-03-24T00:00:00.0",
            "floorValuesArray": [[1711238400000, 1, 0]],
        }
        result = parse_floors_data(data)
        assert result.calendar_date == "2026-03-24"


class TestFloorsMetricConfig:
    """Test Floors metric configuration."""

    def test_metric_config_exists(self):
        from garmy.metrics.floors import __metric_config__

        assert __metric_config__ is not None
        assert (
            __metric_config__.endpoint
            == "/wellness-service/wellness/floorsChartData/daily/{date}"
        )
        assert __metric_config__.metric_class is Floors
        assert __metric_config__.parser is parse_floors_data
        assert isinstance(__metric_config__, MetricConfig)

    def test_importable_from_package(self):
        from garmy.metrics import Floors as FloorsImport

        assert FloorsImport is Floors


class TestFloorsExtraction:
    """Test Floors data extraction for daily_health_metrics."""

    def test_extract_floors(self):
        floors = Floors(
            calendar_date="2026-03-24",
            floors_ascended=10,
            floors_descended=6,
        )

        extractor = DataExtractor()
        result = extractor.extract_metric_data(floors, MetricType.FLOORS)

        assert result["floors_ascended"] == 10
        assert result["floors_descended"] == 6

    def test_extract_floors_none_values(self):
        floors = Floors()
        extractor = DataExtractor()
        result = extractor.extract_metric_data(floors, MetricType.FLOORS)

        assert result["floors_ascended"] is None
        assert result["floors_descended"] is None


# ---------------------------------------------------------------------------
# RestingHeartRate
# ---------------------------------------------------------------------------


class TestRestingHeartRateParsing:
    """Test RestingHeartRate API response parsing."""

    def create_sample_response(self, **overrides):
        """Create a realistic user stats API response."""
        response = {
            "allMetrics": {
                "metricsMap": {
                    "WELLNESS_RESTING_HEART_RATE": [
                        {
                            "calendarDate": "2026-03-24",
                            "value": 52.0,
                        }
                    ]
                }
            }
        }
        # Apply overrides to the nested structure
        for key, val in overrides.items():
            response[key] = val
        return response

    def test_parse_full_response(self):
        data = self.create_sample_response()
        result = parse_resting_heart_rate_data(data)

        assert isinstance(result, RestingHeartRate)
        assert result.calendar_date == "2026-03-24"
        assert result.value == 52

    def test_parse_empty_metrics_map(self):
        data = {"allMetrics": {"metricsMap": {}}}
        result = parse_resting_heart_rate_data(data)

        assert result.calendar_date == ""
        assert result.value is None

    def test_parse_missing_all_metrics(self):
        data = {}
        result = parse_resting_heart_rate_data(data)

        assert result.calendar_date == ""
        assert result.value is None

    def test_parse_empty_rhr_list(self):
        data = {
            "allMetrics": {
                "metricsMap": {
                    "WELLNESS_RESTING_HEART_RATE": []
                }
            }
        }
        result = parse_resting_heart_rate_data(data)

        assert result.value is None

    def test_parse_null_value(self):
        data = {
            "allMetrics": {
                "metricsMap": {
                    "WELLNESS_RESTING_HEART_RATE": [
                        {"calendarDate": "2026-03-24", "value": None}
                    ]
                }
            }
        }
        result = parse_resting_heart_rate_data(data)

        assert result.value is None

    def test_parse_float_value_converted_to_int(self):
        data = {
            "allMetrics": {
                "metricsMap": {
                    "WELLNESS_RESTING_HEART_RATE": [
                        {"calendarDate": "2026-03-24", "value": 55.0}
                    ]
                }
            }
        }
        result = parse_resting_heart_rate_data(data)

        assert result.value == 55
        assert isinstance(result.value, int)

    def test_parse_invalid_data_raises(self):
        with pytest.raises(ValueError, match="Expected dictionary"):
            parse_resting_heart_rate_data("not a dict")


class TestRestingHeartRateMetricConfig:
    """Test RestingHeartRate metric configuration."""

    def test_metric_config_exists(self):
        from garmy.metrics.resting_heart_rate import __metric_config__

        assert __metric_config__ is not None
        assert __metric_config__.metric_class is RestingHeartRate
        assert __metric_config__.parser is parse_resting_heart_rate_data
        assert __metric_config__.endpoint_builder is not None
        assert __metric_config__.requires_user_id is True
        assert isinstance(__metric_config__, MetricConfig)

    def test_importable_from_package(self):
        from garmy.metrics import RestingHeartRate as RHRImport

        assert RHRImport is RestingHeartRate


class TestRestingHeartRateExtraction:
    """Test RestingHeartRate data extraction for daily_health_metrics."""

    def test_extract_resting_heart_rate(self):
        rhr = RestingHeartRate(
            calendar_date="2026-03-24",
            value=52,
        )

        extractor = DataExtractor()
        result = extractor.extract_metric_data(rhr, MetricType.RESTING_HEART_RATE)

        assert result["dedicated_resting_heart_rate"] == 52

    def test_extract_resting_heart_rate_none(self):
        rhr = RestingHeartRate()
        extractor = DataExtractor()
        result = extractor.extract_metric_data(rhr, MetricType.RESTING_HEART_RATE)

        assert result["dedicated_resting_heart_rate"] is None
