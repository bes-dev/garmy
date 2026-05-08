"""Tests for SpO2 metric module: dataclass, parser, and timeseries extraction."""

import pytest

from garmy.core.base import MetricConfig
from garmy.localdb.extractors import DataExtractor
from garmy.localdb.models import MetricType
from garmy.metrics.spo2 import SpO2, parse_spo2_data


class TestSpO2Parsing:
    """Test SpO2 API response parsing."""

    def create_sample_spo2_response(self, **overrides):
        """Create a realistic SpO2 API response matching actual Garmin API."""
        response = {
            "calendarDate": "2026-03-24",
            "averageSpO2": 97.0,
            "lowestSpO2": 91,
            "latestSpO2": 100,
            "avgSleepSpO2": 98.0,
            "lastSevenDaysAvgSpO2": 96.14,
            "spO2HourlyAverages": [
                [1711238400000, 99],
                [1711242000000, 97],
                [1711245600000, 96],
            ],
            "continuousReadingDTOList": None,
        }
        response.update(overrides)
        return response

    def test_parse_full_response(self):
        """Test parsing a complete SpO2 API response."""
        data = self.create_sample_spo2_response()
        result = parse_spo2_data(data)

        assert isinstance(result, SpO2)
        assert result.calendar_date == "2026-03-24"
        assert result.average_spo2 == 97.0
        assert result.lowest_spo2 == 91
        assert result.latest_spo2 == 100
        assert result.avg_sleep_spo2 == 98.0
        assert result.last_seven_days_avg_spo2 == 96.14
        assert len(result.spo2_hourly_averages) == 3

    def test_parse_hourly_averages(self):
        """Test hourly average readings are parsed correctly."""
        data = self.create_sample_spo2_response()
        result = parse_spo2_data(data)

        reading = result.spo2_hourly_averages[0]
        assert reading[0] == 1711238400000
        assert reading[1] == 99

    def test_parse_empty_response(self):
        """Test parsing an empty/minimal response."""
        data = {"calendarDate": "2026-03-24"}
        result = parse_spo2_data(data)

        assert result.calendar_date == "2026-03-24"
        assert result.average_spo2 is None
        assert result.lowest_spo2 is None
        assert result.latest_spo2 is None
        assert result.spo2_hourly_averages == []

    def test_readings_count_property(self):
        """Test readings_count property."""
        data = self.create_sample_spo2_response()
        result = parse_spo2_data(data)
        assert result.readings_count == 3

    def test_valid_readings_count_property(self):
        """Test valid_readings_count excludes None values."""
        spo2 = SpO2(
            spo2_hourly_averages=[
                [1711238400000, 99],
                [1711242000000, None],
                [1711245600000, 96],
            ]
        )
        assert spo2.valid_readings_count == 2

    def test_parse_invalid_data_raises(self):
        """Test that non-dict input raises ValueError."""
        with pytest.raises(ValueError, match="Expected dictionary"):
            parse_spo2_data("not a dict")


class TestSpO2MetricConfig:
    """Test SpO2 metric configuration for auto-discovery."""

    def test_metric_config_exists(self):
        """Test that __metric_config__ is exported."""
        from garmy.metrics.spo2 import __metric_config__

        assert __metric_config__ is not None
        assert __metric_config__.endpoint == "/wellness-service/wellness/daily/spo2/{date}"
        assert __metric_config__.metric_class is SpO2
        assert __metric_config__.parser is parse_spo2_data
        assert isinstance(__metric_config__, MetricConfig)

    def test_spo2_importable_from_package(self):
        """Test SpO2 is importable from garmy.metrics."""
        from garmy.metrics import SpO2 as SpO2Import

        assert SpO2Import is SpO2


class TestSpO2TimeseriesExtraction:
    """Test SpO2 timeseries data extraction for localdb storage."""

    def test_extract_spo2_timeseries(self):
        """Test timeseries extraction from SpO2 hourly averages."""
        spo2 = SpO2(
            calendar_date="2026-03-24",
            average_spo2=97.0,
            spo2_hourly_averages=[
                [1711238400000, 99],
                [1711242000000, 97],
                [1711245600000, 96],
            ],
        )

        extractor = DataExtractor()
        timeseries = extractor.extract_timeseries_data(spo2, MetricType.SPO2)

        assert len(timeseries) == 3
        ts, value, meta = timeseries[0]
        assert ts == 1711238400000
        assert value == 99
        assert meta == {}

    def test_extract_spo2_timeseries_skips_none_values(self):
        """Test that readings with None value are skipped."""
        spo2 = SpO2(
            spo2_hourly_averages=[
                [1711238400000, None],
                [1711242000000, 97],
            ],
        )

        extractor = DataExtractor()
        timeseries = extractor.extract_timeseries_data(spo2, MetricType.SPO2)

        assert len(timeseries) == 1
        assert timeseries[0][1] == 97

    def test_extract_spo2_timeseries_empty_readings(self):
        """Test timeseries extraction with no readings."""
        spo2 = SpO2(spo2_hourly_averages=[])
        extractor = DataExtractor()
        timeseries = extractor.extract_timeseries_data(spo2, MetricType.SPO2)

        assert timeseries == []


class TestSpO2DailySummaryExtraction:
    """Test SpO2 daily summary extraction for daily_health_metrics."""

    def test_extract_spo2_summary(self):
        """Test daily summary extraction from SpO2 data."""
        spo2 = SpO2(
            calendar_date="2026-03-24",
            average_spo2=97.0,
            lowest_spo2=91,
        )

        extractor = DataExtractor()
        result = extractor.extract_metric_data(spo2, MetricType.SPO2)

        assert result["average_spo2"] == 97.0
        assert result["lowest_spo2"] == 91

    def test_extract_spo2_summary_none_values(self):
        """Test extraction when fields are None."""
        spo2 = SpO2()
        extractor = DataExtractor()
        result = extractor.extract_metric_data(spo2, MetricType.SPO2)

        assert result["average_spo2"] is None
        assert result["lowest_spo2"] is None
