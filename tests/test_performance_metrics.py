"""Tests for PR3 performance metrics: TrainingStatus, EnduranceScore."""

import pytest

from garmy.core.base import MetricConfig
from garmy.localdb.extractors import DataExtractor
from garmy.localdb.models import MetricType, PerformanceMetric
from garmy.metrics.endurance_score import (
    CLASSIFICATION_MAP,
    EnduranceScore,
    parse_endurance_score_data,
)
from garmy.metrics.training_status import (
    STATUS_MAP,
    TrainingStatus,
    parse_training_status_data,
)


# ---------------------------------------------------------------------------
# TrainingStatus
# ---------------------------------------------------------------------------


class TestTrainingStatusParsing:
    """Test TrainingStatus API response parsing with actual API structure."""

    def create_sample_response(self, **overrides):
        """Create a realistic training status API response matching actual Garmin API."""
        response = {
            "userId": 123456,
            "mostRecentTrainingStatus": {
                "latestTrainingStatusData": {
                    "3456789": {
                        "calendarDate": "2026-03-24",
                        "deviceId": "3456789",
                        "trainingStatus": 4,
                        "trainingStatusFeedbackPhrase": "MAINTAINING_1",
                        "trainingPaused": False,
                        "acuteTrainingLoadDTO": {
                            "acwrPercent": 38,
                            "acwrStatus": "OPTIMAL",
                            "dailyTrainingLoadAcute": 345.0,
                            "dailyTrainingLoadChronic": 375.0,
                            "dailyAcuteChronicWorkloadRatio": 0.92,
                        },
                    }
                }
            },
            "mostRecentTrainingLoadBalance": {},
            "heatAltitudeAcclimationDTO": None,
        }
        response.update(overrides)
        return response

    def test_parse_full_response(self):
        data = self.create_sample_response()
        result = parse_training_status_data(data)

        assert isinstance(result, TrainingStatus)
        assert result.calendar_date == "2026-03-24"
        assert result.training_status == 4
        assert result.training_status_feedback == "MAINTAINING_1"
        assert result.acute_load == 345.0
        assert result.chronic_load == 375.0
        assert result.load_balance == 0.92
        assert result.load_type == "OPTIMAL"

    def test_parse_empty_response(self):
        data = {}
        result = parse_training_status_data(data)

        assert result.calendar_date == ""
        assert result.acute_load is None
        assert result.chronic_load is None
        assert result.load_balance is None
        assert result.load_type is None
        assert result.training_status is None
        assert result.training_status_feedback is None

    def test_parse_missing_training_status(self):
        """Test parsing when mostRecentTrainingStatus is missing."""
        data = {"userId": 123456}
        result = parse_training_status_data(data)

        assert result.training_status is None
        assert result.acute_load is None

    def test_parse_empty_device_map(self):
        """Test parsing when device map is empty."""
        data = {
            "mostRecentTrainingStatus": {
                "latestTrainingStatusData": {}
            }
        }
        result = parse_training_status_data(data)

        assert result.training_status is None

    def test_parse_no_load_dto(self):
        """Test parsing when acuteTrainingLoadDTO is missing."""
        data = {
            "mostRecentTrainingStatus": {
                "latestTrainingStatusData": {
                    "3456789": {
                        "calendarDate": "2026-03-24",
                        "trainingStatus": 5,
                        "trainingStatusFeedbackPhrase": "PRODUCTIVE_1",
                    }
                }
            }
        }
        result = parse_training_status_data(data)

        assert result.training_status == 5
        assert result.training_status_feedback == "PRODUCTIVE_1"
        assert result.acute_load is None
        assert result.chronic_load is None

    def test_parse_invalid_data_raises(self):
        with pytest.raises(ValueError, match="Expected dictionary"):
            parse_training_status_data("not a dict")

    def test_status_label_property(self):
        ts = TrainingStatus(training_status=4)
        assert ts.status_label == "MAINTAINING"

    def test_status_label_productive(self):
        ts = TrainingStatus(training_status=5)
        assert ts.status_label == "PRODUCTIVE"

    def test_status_label_none(self):
        ts = TrainingStatus()
        assert ts.status_label is None

    def test_status_label_unknown(self):
        ts = TrainingStatus(training_status=99)
        assert ts.status_label == "UNKNOWN_99"

    def test_status_map_has_expected_statuses(self):
        """Verify STATUS_MAP contains all known statuses from Garmin."""
        expected = {
            "DETRAINING",
            "RECOVERY",
            "MAINTAINING",
            "PRODUCTIVE",
            "OVERREACHING",
        }
        actual_labels = set(STATUS_MAP.values())
        assert expected.issubset(actual_labels)


class TestTrainingStatusMetricConfig:
    """Test TrainingStatus metric configuration."""

    def test_metric_config_exists(self):
        from garmy.metrics.training_status import __metric_config__

        assert __metric_config__ is not None
        assert (
            __metric_config__.endpoint
            == "/metrics-service/metrics/trainingstatus/aggregated/{date}"
        )
        assert __metric_config__.metric_class is TrainingStatus
        assert __metric_config__.parser is parse_training_status_data
        assert isinstance(__metric_config__, MetricConfig)

    def test_importable_from_package(self):
        from garmy.metrics import TrainingStatus as Imported

        assert Imported is TrainingStatus


class TestTrainingStatusExtraction:
    """Test TrainingStatus data extraction for performance_metrics table."""

    def test_extract_training_status(self):
        ts = TrainingStatus(
            calendar_date="2026-03-24",
            acute_load=345.0,
            chronic_load=375.0,
            load_balance=0.92,
            load_type="OPTIMAL",
            training_status=4,
            training_status_feedback="MAINTAINING_1",
        )

        extractor = DataExtractor()
        result = extractor.extract_metric_data(ts, MetricType.TRAINING_STATUS)

        assert result["acute_load"] == 345.0
        assert result["chronic_load"] == 375.0
        assert result["load_balance"] == 0.92
        assert result["load_type"] == "OPTIMAL"
        assert result["training_status"] == 4
        assert result["training_status_feedback"] == "MAINTAINING_1"

    def test_extract_training_status_none_values(self):
        ts = TrainingStatus()
        extractor = DataExtractor()
        result = extractor.extract_metric_data(ts, MetricType.TRAINING_STATUS)

        assert result["acute_load"] is None
        assert result["chronic_load"] is None
        assert result["load_balance"] is None
        assert result["load_type"] is None
        assert result["training_status"] is None
        assert result["training_status_feedback"] is None


# ---------------------------------------------------------------------------
# EnduranceScore
# ---------------------------------------------------------------------------


class TestEnduranceScoreParsing:
    """Test EnduranceScore API response parsing with actual API structure."""

    def create_sample_response(self, **overrides):
        """Create a realistic endurance score API response (flat dict)."""
        response = {
            "userProfilePK": 123456,
            "deviceId": "3456789",
            "calendarDate": "2026-03-24",
            "overallScore": 4508,
            "classification": 1,
            "feedbackPhrase": "20",
            "primaryTrainingDevice": True,
            "gaugeLowerLimit": 0,
            "gaugeUpperLimit": 10000,
            "classificationLowerLimitIntermediate": 3846,
            "classificationLowerLimitTrained": 5246,
            "classificationLowerLimitWellTrained": 6616,
            "classificationLowerLimitExpert": 7776,
            "classificationLowerLimitSuperior": 8396,
            "classificationLowerLimitElite": 9016,
            "contributors": [
                {"activityTypeId": 13, "contribution": 66.09},
                {"group": 1, "contribution": 22.3},
            ],
        }
        response.update(overrides)
        return response

    def test_parse_full_response(self):
        data = self.create_sample_response()
        result = parse_endurance_score_data(data)

        assert isinstance(result, EnduranceScore)
        assert result.calendar_date == "2026-03-24"
        assert result.endurance_score == 4508.0
        assert result.endurance_score_classification == 1

    def test_parse_empty_response(self):
        data = {}
        result = parse_endurance_score_data(data)

        assert result.calendar_date == ""
        assert result.endurance_score is None
        assert result.endurance_score_classification is None

    def test_parse_missing_classification(self):
        data = {"calendarDate": "2026-03-24", "overallScore": 5000}
        result = parse_endurance_score_data(data)

        assert result.endurance_score == 5000.0
        assert result.endurance_score_classification is None

    def test_parse_invalid_data_raises(self):
        with pytest.raises(ValueError, match="Expected dictionary"):
            parse_endurance_score_data("not a dict")

    def test_classification_label_property(self):
        es = EnduranceScore(endurance_score_classification=1)
        assert es.classification_label == "RECREATIONAL"

    def test_classification_label_elite(self):
        es = EnduranceScore(endurance_score_classification=7)
        assert es.classification_label == "ELITE"

    def test_classification_label_none(self):
        es = EnduranceScore()
        assert es.classification_label is None

    def test_classification_label_unknown(self):
        es = EnduranceScore(endurance_score_classification=99)
        assert es.classification_label == "UNKNOWN_99"

    def test_classification_map_has_expected_levels(self):
        """Verify CLASSIFICATION_MAP has all levels from API field names."""
        expected = {
            "RECREATIONAL",
            "INTERMEDIATE",
            "TRAINED",
            "WELL_TRAINED",
            "EXPERT",
            "SUPERIOR",
            "ELITE",
        }
        assert set(CLASSIFICATION_MAP.values()) == expected


class TestEnduranceScoreMetricConfig:
    """Test EnduranceScore metric configuration."""

    def test_metric_config_exists(self):
        from garmy.metrics.endurance_score import __metric_config__

        assert __metric_config__ is not None
        assert __metric_config__.endpoint == "/metrics-service/metrics/endurancescore"
        assert __metric_config__.metric_class is EnduranceScore
        assert __metric_config__.parser is parse_endurance_score_data
        assert isinstance(__metric_config__, MetricConfig)

    def test_has_endpoint_builder(self):
        from garmy.metrics.endurance_score import __metric_config__

        assert __metric_config__.endpoint_builder is not None

    def test_importable_from_package(self):
        from garmy.metrics import EnduranceScore as Imported

        assert Imported is EnduranceScore


class TestEnduranceScoreExtraction:
    """Test EnduranceScore data extraction for performance_metrics table."""

    def test_extract_endurance_score(self):
        es = EnduranceScore(
            calendar_date="2026-03-24",
            endurance_score=4508.0,
            endurance_score_classification=1,
        )

        extractor = DataExtractor()
        result = extractor.extract_metric_data(es, MetricType.ENDURANCE_SCORE)

        assert result["endurance_score"] == 4508.0
        assert result["endurance_score_classification"] == 1

    def test_extract_endurance_score_none_values(self):
        es = EnduranceScore()
        extractor = DataExtractor()
        result = extractor.extract_metric_data(es, MetricType.ENDURANCE_SCORE)

        assert result["endurance_score"] is None
        assert result["endurance_score_classification"] is None


# ---------------------------------------------------------------------------
# Endpoint Builder
# ---------------------------------------------------------------------------


class TestEnduranceScoreEndpointBuilder:
    """Test EnduranceScore endpoint builder."""

    def test_build_endpoint_url(self):
        from garmy.core.endpoint_builders import build_endurance_score_endpoint

        url = build_endurance_score_endpoint("2026-03-24")

        assert "/metrics-service/metrics/endurancescore" in url
        assert "startDate=2026-03-24" in url
        assert "endDate=2026-03-24" in url
        assert "aggregation=daily" in url

    def test_build_from_date_object(self):
        from datetime import date

        from garmy.core.endpoint_builders import build_endurance_score_endpoint

        url = build_endurance_score_endpoint(date(2026, 3, 24))

        assert "startDate=2026-03-24" in url
        assert "endDate=2026-03-24" in url

    def test_no_user_id_in_url(self):
        """Verify endpoint builder does not require API client / user_id."""
        from garmy.core.endpoint_builders import build_endurance_score_endpoint

        url = build_endurance_score_endpoint("2026-03-24", api_client=None)
        assert "endurancescore" in url


# ---------------------------------------------------------------------------
# MetricType Enum
# ---------------------------------------------------------------------------


class TestMetricTypeEntries:
    """Test new MetricType enum entries exist."""

    def test_training_status_enum(self):
        assert MetricType.TRAINING_STATUS.value == "training_status"

    def test_endurance_score_enum(self):
        assert MetricType.ENDURANCE_SCORE.value == "endurance_score"


# ---------------------------------------------------------------------------
# PerformanceMetric Model
# ---------------------------------------------------------------------------


class TestPerformanceMetricModel:
    """Test PerformanceMetric SQLAlchemy model."""

    def test_table_name(self):
        assert PerformanceMetric.__tablename__ == "performance_metrics"

    def test_has_training_load_columns(self):
        columns = {c.name for c in PerformanceMetric.__table__.columns}
        assert "acute_load" in columns
        assert "chronic_load" in columns
        assert "load_balance" in columns
        assert "load_type" in columns

    def test_has_training_status_columns(self):
        columns = {c.name for c in PerformanceMetric.__table__.columns}
        assert "training_status" in columns
        assert "training_status_feedback" in columns

    def test_has_endurance_score_columns(self):
        columns = {c.name for c in PerformanceMetric.__table__.columns}
        assert "endurance_score" in columns
        assert "endurance_score_classification" in columns

    def test_no_vo2_max_columns(self):
        """VO2 Max was removed — verify columns don't exist."""
        columns = {c.name for c in PerformanceMetric.__table__.columns}
        assert "vo2_max_running" not in columns
        assert "vo2_max_cycling" not in columns
        assert "fitness_age" not in columns

    def test_primary_key(self):
        pk_columns = {c.name for c in PerformanceMetric.__table__.primary_key.columns}
        assert pk_columns == {"user_id", "metric_date"}
