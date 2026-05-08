"""Tests for HRV timeseries extraction and expanded daily summary fields."""

from garmy.localdb.extractors import DataExtractor
from garmy.localdb.models import MetricType
from garmy.metrics.hrv import HRV, HRVBaseline, HRVReading, HRVSummary


class TestHRVTimeseriesExtraction:
    """Test HRV timeseries data extraction for localdb storage."""

    def create_sample_hrv_data(self, **overrides):
        """Create a realistic HRV data object for testing."""
        baseline = HRVBaseline(
            low_upper=45,
            balanced_low=50,
            balanced_upper=70,
            marker_value=55.0,
        )
        summary = HRVSummary(
            calendar_date="2026-03-24",
            weekly_avg=58,
            last_night_avg=62,
            last_night_5_min_high=85,
            baseline=baseline,
            status="BALANCED",
            feedback_phrase="Your HRV is balanced",
            create_time_stamp="2026-03-24T06:00:00.0",
        )
        readings = [
            HRVReading(
                hrv_value=55,
                reading_time_gmt="2026-03-24T01:00:00.0",
                reading_time_local="2026-03-23T20:00:00.0",
            ),
            HRVReading(
                hrv_value=62,
                reading_time_gmt="2026-03-24T01:05:00.0",
                reading_time_local="2026-03-23T20:05:00.0",
            ),
            HRVReading(
                hrv_value=70,
                reading_time_gmt="2026-03-24T01:10:00.0",
                reading_time_local="2026-03-23T20:10:00.0",
            ),
        ]

        kwargs = dict(
            user_profile_pk=12345,
            hrv_summary=summary,
            hrv_readings=readings,
        )
        kwargs.update(overrides)
        return HRV(**kwargs)

    def test_extract_hrv_timeseries(self):
        """Test timeseries extraction converts ISO timestamps to unix ms."""
        hrv = self.create_sample_hrv_data()
        extractor = DataExtractor()
        timeseries = extractor.extract_timeseries_data(hrv, MetricType.HRV)

        assert len(timeseries) == 3

        # Verify first reading
        ts, value, meta = timeseries[0]
        assert value == 55
        assert meta == {}
        # Timestamp should be a positive integer (unix ms)
        assert isinstance(ts, int)
        assert ts > 0

    def test_extract_hrv_timeseries_skips_none_values(self):
        """Test that readings with None hrv_value are skipped."""
        hrv = self.create_sample_hrv_data(
            hrv_readings=[
                HRVReading(
                    hrv_value=0,  # zero is valid
                    reading_time_gmt="2026-03-24T01:00:00.0",
                    reading_time_local="2026-03-23T20:00:00.0",
                ),
            ]
        )

        # Manually set one reading's hrv_value to None
        reading_with_none = HRVReading(
            hrv_value=55,
            reading_time_gmt="2026-03-24T01:05:00.0",
            reading_time_local="",
        )
        object.__setattr__(reading_with_none, "hrv_value", None)

        hrv.hrv_readings.append(reading_with_none)

        extractor = DataExtractor()
        timeseries = extractor.extract_timeseries_data(hrv, MetricType.HRV)

        values = [t[1] for t in timeseries]
        assert None not in values

    def test_extract_hrv_timeseries_empty_readings(self):
        """Test timeseries extraction with no readings."""
        hrv = self.create_sample_hrv_data(hrv_readings=[])
        extractor = DataExtractor()
        timeseries = extractor.extract_timeseries_data(hrv, MetricType.HRV)

        assert timeseries == []

    def test_extract_hrv_timeseries_handles_z_suffix(self):
        """Test ISO timestamp with Z suffix is handled correctly."""
        hrv = self.create_sample_hrv_data(
            hrv_readings=[
                HRVReading(
                    hrv_value=60,
                    reading_time_gmt="2026-03-24T01:00:00Z",
                    reading_time_local="2026-03-23T20:00:00Z",
                ),
            ]
        )

        extractor = DataExtractor()
        timeseries = extractor.extract_timeseries_data(hrv, MetricType.HRV)

        assert len(timeseries) == 1
        assert timeseries[0][1] == 60


class TestHRVExpandedDailySummary:
    """Test HRV expanded daily summary extraction with baseline fields."""

    def create_sample_hrv_data(self, **overrides):
        """Create a realistic HRV data object for testing."""
        baseline = HRVBaseline(
            low_upper=45,
            balanced_low=50,
            balanced_upper=70,
            marker_value=55.0,
        )
        summary = HRVSummary(
            calendar_date="2026-03-24",
            weekly_avg=58,
            last_night_avg=62,
            last_night_5_min_high=85,
            baseline=baseline,
            status="BALANCED",
            feedback_phrase="Your HRV is balanced",
            create_time_stamp="2026-03-24T06:00:00.0",
        )
        kwargs = dict(
            user_profile_pk=12345,
            hrv_summary=summary,
            hrv_readings=[],
        )
        kwargs.update(overrides)
        return HRV(**kwargs)

    def test_extract_hrv_summary_with_baseline(self):
        """Test extraction includes baseline fields."""
        hrv = self.create_sample_hrv_data()
        extractor = DataExtractor()
        result = extractor.extract_metric_data(hrv, MetricType.HRV)

        assert result["hrv_weekly_avg"] == 58
        assert result["hrv_last_night_avg"] == 62
        assert result["hrv_status"] == "BALANCED"
        assert result["hrv_last_night_5min_high"] == 85
        assert result["hrv_baseline_low_upper"] == 45
        assert result["hrv_baseline_balanced_low"] == 50
        assert result["hrv_baseline_balanced_upper"] == 70

    def test_extract_hrv_summary_no_summary(self):
        """Test extraction returns empty dict when no summary."""
        hrv = self.create_sample_hrv_data()
        object.__setattr__(hrv, "hrv_summary", None)

        extractor = DataExtractor()
        result = extractor.extract_metric_data(hrv, MetricType.HRV)

        assert result == {}

    def test_extract_hrv_summary_no_baseline(self):
        """Test extraction when baseline is None."""
        hrv = self.create_sample_hrv_data()
        object.__setattr__(hrv.hrv_summary, "baseline", None)

        extractor = DataExtractor()
        result = extractor.extract_metric_data(hrv, MetricType.HRV)

        assert result["hrv_weekly_avg"] == 58
        assert "hrv_baseline_low_upper" not in result
