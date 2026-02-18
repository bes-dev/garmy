
from datetime import date, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from garmy.localdb.db import HealthDB
from garmy.localdb.models import Base, TimeSeries, Activity, DailyHealthMetric, SyncStatus, MetricType


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    """Fixture for temporary database path."""
    return tmp_path / "test_health.db"


@pytest.fixture
def health_db(db_path: Path) -> HealthDB:
    """Fixture for HealthDB instance."""
    db = HealthDB(db_path)
    yield db
    db.engine.dispose()


def test_initialization(health_db: HealthDB, db_path: Path):
    """Test database initialization."""
    assert db_path.exists()
    assert health_db.engine is not None
    assert health_db.SessionLocal is not None

def test_get_session(health_db: HealthDB):
    """Test getting a database session."""
    with health_db.get_session() as session:
        assert session is not None

def test_get_schema_info(health_db: HealthDB, db_path: Path):
    """Test getting schema information."""
    schema_info = health_db.get_schema_info()
    assert set(schema_info["tables"]) == {"timeseries", "activities", "daily_health_metrics", "sync_status"}
    assert schema_info["db_path"] == str(db_path)

def test_validate_schema(health_db: HealthDB):
    """Test schema validation."""
    assert health_db.validate_schema()

def test_store_timeseries_batch(health_db: HealthDB):
    """Test storing a batch of timeseries data."""
    user_id = 1
    metric_type = MetricType.HEART_RATE
    data = [
        (datetime(2023, 1, 1, 12, 0, 0), 80, {}),
        (datetime(2023, 1, 1, 12, 1, 0), 82, {}),
    ]
    health_db.store_timeseries_batch(user_id, metric_type, data)
    with health_db.get_session() as session:
        timeseries = session.query(TimeSeries).all()
        assert len(timeseries) == 2
        assert timeseries[0].user_id == user_id
        assert timeseries[0].metric_type == metric_type.value

def test_store_activity(health_db: HealthDB):
    """Test storing activity data."""
    user_id = 1
    activity_data = {
        "activity_id": "12345",
        "activity_date": date(2023, 1, 1),
        "activity_name": "Running",
    }
    health_db.store_activity(user_id, activity_data)
    with health_db.get_session() as session:
        activity = session.query(Activity).first()
        assert activity is not None
        assert activity.user_id == user_id
        assert activity.activity_id == "12345"

def test_store_health_metric(health_db: HealthDB):
    """Test storing daily health metric data."""
    user_id = 1
    metric_date = date(2023, 1, 1)
    health_db.store_health_metric(user_id, metric_date, total_steps=1000)
    with health_db.get_session() as session:
        metric = session.query(DailyHealthMetric).first()
        assert metric is not None
        assert metric.user_id == user_id
        assert metric.metric_date == metric_date
        assert metric.total_steps == 1000

def test_create_and_get_sync_status(health_db: HealthDB):
    """Test creating and getting sync status."""
    user_id = 1
    sync_date = date(2023, 1, 1)
    metric_type = MetricType.HEART_RATE
    health_db.create_sync_status(user_id, sync_date, metric_type)
    status = health_db.get_sync_status(user_id, sync_date, metric_type)
    assert status == "pending"

def test_update_sync_status(health_db: HealthDB):
    """Test updating sync status."""
    user_id = 1
    sync_date = date(2023, 1, 1)
    metric_type = MetricType.HEART_RATE
    health_db.create_sync_status(user_id, sync_date, metric_type)
    health_db.update_sync_status(
        user_id, sync_date, metric_type, "success"
    )
    status = health_db.get_sync_status(user_id, sync_date, metric_type)
    assert status == "success"

def test_get_pending_metrics(health_db: HealthDB):
    """Test getting pending metrics."""
    user_id = 1
    sync_date = date(2023, 1, 1)
    health_db.create_sync_status(
        user_id, sync_date, MetricType.HEART_RATE, "pending"
    )
    health_db.create_sync_status(
        user_id, sync_date, MetricType.STEPS, "success"
    )
    pending_metrics = health_db.get_pending_metrics(user_id, sync_date)
    assert len(pending_metrics) == 1
    assert pending_metrics[0] == MetricType.HEART_RATE.value

def test_existence_checks(health_db: HealthDB):
    """Test existence check methods."""
    user_id = 1
    activity_id = "12345"
    metric_date = date(2023, 1, 1)
    sync_date = date(2023, 1, 1)
    metric_type = MetricType.HEART_RATE

    assert not health_db.activity_exists(user_id, activity_id)
    assert not health_db.health_metric_exists(user_id, metric_date)
    assert not health_db.sync_status_exists(user_id, sync_date, metric_type)

    health_db.store_activity(user_id, {"activity_id": activity_id, "activity_date": metric_date})
    health_db.store_health_metric(user_id, metric_date)
    health_db.create_sync_status(user_id, sync_date, metric_type)

    assert health_db.activity_exists(user_id, activity_id)
    assert health_db.health_metric_exists(user_id, metric_date)
    assert health_db.sync_status_exists(user_id, sync_date, metric_type)

def test_get_health_metrics(health_db: HealthDB):
    """Test querying health metrics."""
    user_id = 1
    start_date = date(2023, 1, 1)
    end_date = date(2023, 1, 2)
    health_db.store_health_metric(user_id, start_date, total_steps=1000)
    health_db.store_health_metric(user_id, end_date, total_steps=2000)

    metrics = health_db.get_health_metrics(user_id, start_date, end_date)
    assert len(metrics) == 2
    assert metrics[0]["total_steps"] == 1000
    assert metrics[1]["total_steps"] == 2000

def test_get_activities(health_db: HealthDB):
    """Test querying activities."""
    user_id = 1
    start_date = date(2023, 1, 1)
    end_date = date(2023, 1, 2)
    health_db.store_activity(
        user_id, {"activity_id": "1", "activity_date": start_date, "activity_name": "Running"}
    )
    health_db.store_activity(
        user_id, {"activity_id": "2", "activity_date": end_date, "activity_name": "Cycling"}
    )

    activities = health_db.get_activities(user_id, start_date, end_date)
    assert len(activities) == 2
    assert activities[0]["activity_name"] == "Running"
    assert activities[1]["activity_name"] == "Cycling"

def test_get_timeseries(health_db: HealthDB):
    """Test querying timeseries data."""
    user_id = 1
    metric_type = MetricType.HEART_RATE
    start_timestamp = int(datetime(2023, 1, 1, 12, 0, 0).timestamp())
    end_timestamp = int(datetime(2023, 1, 1, 12, 1, 0).timestamp())
    data = [
        (start_timestamp, 80, {}),
        (end_timestamp, 82, {}),
    ]
    health_db.store_timeseries_batch(user_id, metric_type, data)

    timeseries = health_db.get_timeseries(
        user_id, metric_type, start_timestamp, end_timestamp
    )
    assert len(timeseries) == 2
    assert timeseries[0][1] == 80
    assert timeseries[1][1] == 82

@patch('garmy.AuthClient')
@patch('garmy.APIClient')
@patch('garmy.localdb.sync.ActivitiesIterator')
def test_sync_activities_updates_status(mock_activities_iterator, mock_api_client, mock_auth_client, health_db: HealthDB):
    """Test that syncing activities updates their sync_status to 'completed'."""
    from garmy.localdb.sync import SyncManager
    from garmy.localdb.config import LocalDBConfig

    user_id = 1
    sync_date = date(2023, 1, 1)

    # Mock APIClient and ActivitiesIterator behavior
    mock_api_client_instance = mock_api_client.return_value
    mock_api_client_instance.metrics.get.return_value.get.return_value = MagicMock() # For other metrics if any

    mock_activities_iterator_instance = mock_activities_iterator.return_value
    mock_activities_iterator_instance.get_activities_for_date.return_value = [
        MagicMock(activity_id="123", activity_date=sync_date, activity_name="Running"),
        MagicMock(activity_id="456", activity_date=sync_date, activity_name="Walking")
    ]
    mock_activities_iterator_instance.initialize.return_value = None

    # Mock DataExtractor to return some data
    with patch('garmy.localdb.sync.DataExtractor') as MockDataExtractor:
        mock_extractor_instance = MockDataExtractor.return_value
        mock_extractor_instance.extract_metric_data.side_effect = [
            {"activity_id": "123", "activity_date": sync_date, "activity_name": "Running"},
            {"activity_id": "456", "activity_date": sync_date, "activity_name": "Walking"}
        ]

        # Initialize SyncManager
        sync_manager = SyncManager(db_path=health_db.db_path, config=LocalDBConfig())
        sync_manager.api_client = mock_api_client_instance
        sync_manager.activities_iterator = mock_activities_iterator_instance

        # Call sync_range for activities
        sync_manager.sync_range(user_id, sync_date, sync_date, metrics=[MetricType.ACTIVITIES])

        # Assert that the sync status for ACTIVITIES is 'completed'
        status = health_db.get_sync_status(user_id, sync_date, MetricType.ACTIVITIES)
        assert status == 'completed'

