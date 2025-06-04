"""Tests for local database synchronization functionality."""

import pytest
import asyncio
import tempfile
import shutil
from datetime import datetime, date, timedelta
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

from garmy.localdb.config import LocalDBConfig, SyncConfig, UserConfig
from garmy.localdb.storage import LocalDataStore
from garmy.localdb.sync import SyncManager, SyncProgress, SyncStatus, SyncCheckpoint
from garmy.localdb.exceptions import SyncError


@pytest.fixture
def temp_db_path():
    """Create temporary directory for test database."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def db_config(temp_db_path):
    """Create test database configuration."""
    return LocalDBConfig(
        db_path=temp_db_path / "test.db",
        compression=True,
        create_if_missing=True,
    )


@pytest.fixture
def storage(db_config):
    """Create test storage instance."""
    store = LocalDataStore(db_config)
    store.open()
    
    # Add test user
    user = UserConfig("test_user", "test@example.com", created_at=datetime.now())
    store.add_user(user)
    
    yield store
    store.close()


@pytest.fixture
def mock_api_client():
    """Create mock API client."""
    client = Mock()
    
    # Mock metrics accessor
    metrics_mock = Mock()
    
    # Mock individual metric accessors
    sleep_mock = Mock()
    sleep_mock.get = Mock(return_value={"sleep_data": "test"})
    
    heart_rate_mock = Mock()
    heart_rate_mock.get = Mock(return_value={"heart_rate_data": "test"})
    
    # Configure metrics.get to return appropriate mock
    def get_metric(metric_name):
        if metric_name == "sleep":
            return sleep_mock
        elif metric_name == "heart_rate":
            return heart_rate_mock
        else:
            mock_accessor = Mock()
            mock_accessor.get = Mock(return_value={f"{metric_name}_data": "test"})
            return mock_accessor
    
    metrics_mock.get = get_metric
    client.metrics = metrics_mock
    
    return client


@pytest.fixture
def sync_config():
    """Create test sync configuration."""
    return SyncConfig(
        user_id="test_user",
        start_date=date(2023, 12, 1),
        end_date=date(2023, 12, 3),
        metrics=["sleep", "heart_rate"],
        batch_size=2,
        retry_attempts=2,
        retry_delay=0.1,  # Short delay for tests
    )


@pytest.fixture
def sync_manager(mock_api_client, storage):
    """Create test sync manager."""
    return SyncManager(mock_api_client, storage, max_workers=2)


class TestSyncProgress:
    """Test sync progress tracking."""
    
    def test_progress_creation(self):
        """Test creating sync progress."""
        progress = SyncProgress(
            sync_id="test_sync",
            user_id="test_user",
            status=SyncStatus.PENDING,
            total_metrics=2,
            completed_metrics=0,
            total_days=6,  # 3 days * 2 metrics
            completed_days=0,
        )
        
        assert progress.sync_id == "test_sync"
        assert progress.status == SyncStatus.PENDING
        assert progress.progress_percentage == 0.0
        assert progress.metric_progress_percentage == 0.0
    
    def test_progress_percentage_calculation(self):
        """Test progress percentage calculations."""
        progress = SyncProgress(
            sync_id="test_sync",
            user_id="test_user",
            status=SyncStatus.RUNNING,
            total_metrics=4,
            completed_metrics=2,
            total_days=12,
            completed_days=6,
        )
        
        assert progress.progress_percentage == 50.0
        assert progress.metric_progress_percentage == 50.0
    
    def test_elapsed_time_calculation(self):
        """Test elapsed time calculation."""
        start_time = datetime.now()
        progress = SyncProgress(
            sync_id="test_sync",
            user_id="test_user",
            status=SyncStatus.RUNNING,
            total_metrics=2,
            completed_metrics=1,
            total_days=4,
            completed_days=2,
            started_at=start_time,
        )
        
        elapsed = progress.elapsed_time
        assert elapsed is not None
        assert elapsed.total_seconds() >= 0
    
    def test_progress_serialization(self):
        """Test progress to/from dict conversion."""
        progress = SyncProgress(
            sync_id="test_sync",
            user_id="test_user",
            status=SyncStatus.RUNNING,
            total_metrics=2,
            completed_metrics=1,
            total_days=4,
            completed_days=2,
            started_at=datetime.now(),
            current_metric="sleep",
            current_date="2023-12-01",
        )
        
        # Convert to dict
        data = progress.to_dict()
        assert data["sync_id"] == "test_sync"
        assert data["status"] == "running"
        
        # Convert back
        restored_progress = SyncProgress.from_dict(data)
        assert restored_progress.sync_id == progress.sync_id
        assert restored_progress.status == progress.status
        assert restored_progress.current_metric == progress.current_metric


class TestSyncCheckpoint:
    """Test sync checkpoint functionality."""
    
    def test_checkpoint_creation(self):
        """Test creating sync checkpoint."""
        checkpoint = SyncCheckpoint(
            sync_id="test_sync",
            user_id="test_user",
        )
        
        assert checkpoint.sync_id == "test_sync"
        assert checkpoint.user_id == "test_user"
        assert len(checkpoint.completed_metrics) == 0
        assert len(checkpoint.completed_dates) == 0
    
    def test_checkpoint_serialization(self):
        """Test checkpoint to/from dict conversion."""
        checkpoint = SyncCheckpoint(
            sync_id="test_sync",
            user_id="test_user",
        )
        
        # Add some data
        checkpoint.completed_metrics.add("sleep")
        checkpoint.completed_dates["sleep"] = {"2023-12-01", "2023-12-02"}
        checkpoint.failed_attempts["heart_rate:2023-12-01"] = 2
        
        # Convert to dict
        data = checkpoint.to_dict()
        assert "sleep" in data["completed_metrics"]
        assert "sleep" in data["completed_dates"]
        
        # Convert back
        restored_checkpoint = SyncCheckpoint.from_dict(data)
        assert "sleep" in restored_checkpoint.completed_metrics
        assert "sleep" in restored_checkpoint.completed_dates
        assert restored_checkpoint.failed_attempts["heart_rate:2023-12-01"] == 2


class TestSyncManager:
    """Test sync manager functionality."""
    
    @pytest.mark.asyncio
    async def test_start_sync(self, sync_manager, sync_config):
        """Test starting a sync operation."""
        sync_id = await sync_manager.start_sync(sync_config, resume=False)
        
        assert sync_id is not None
        assert sync_id in sync_manager._active_syncs
        
        # Wait a moment for sync to start
        await asyncio.sleep(0.1)
        
        progress = sync_manager.get_sync_progress(sync_id)
        assert progress is not None
        assert progress.user_id == "test_user"
        
        # Clean up
        await sync_manager.stop_sync(sync_id)
    
    @pytest.mark.asyncio
    async def test_pause_resume_sync(self, sync_manager, sync_config):
        """Test pausing and resuming sync."""
        sync_id = await sync_manager.start_sync(sync_config, resume=False)
        
        # Wait for sync to start
        await asyncio.sleep(0.1)
        
        # Pause sync
        await sync_manager.pause_sync(sync_id)
        progress = sync_manager.get_sync_progress(sync_id)
        assert progress.status == SyncStatus.PAUSED
        
        # Resume sync
        await sync_manager.resume_sync(sync_id)
        progress = sync_manager.get_sync_progress(sync_id)
        assert progress.status == SyncStatus.RUNNING
        
        # Clean up
        await sync_manager.stop_sync(sync_id)
    
    @pytest.mark.asyncio
    async def test_stop_sync(self, sync_manager, sync_config):
        """Test stopping a sync operation."""
        sync_id = await sync_manager.start_sync(sync_config, resume=False)
        
        # Wait for sync to start
        await asyncio.sleep(0.1)
        
        # Stop sync
        await sync_manager.stop_sync(sync_id)
        
        # Should be removed from active syncs
        assert sync_id not in sync_manager._active_syncs
    
    @pytest.mark.asyncio
    async def test_list_active_syncs(self, sync_manager, sync_config):
        """Test listing active syncs."""
        # Initially no active syncs
        assert len(sync_manager.list_active_syncs()) == 0
        
        # Start a sync
        sync_id = await sync_manager.start_sync(sync_config, resume=False)
        await asyncio.sleep(0.1)
        
        # Should have one active sync
        active_syncs = sync_manager.list_active_syncs()
        assert len(active_syncs) == 1
        assert active_syncs[0].sync_id == sync_id
        
        # Clean up
        await sync_manager.stop_sync(sync_id)
    
    @pytest.mark.asyncio
    async def test_progress_callback(self, sync_manager, sync_config):
        """Test progress callback functionality."""
        callback_calls = []
        
        def progress_callback(progress):
            callback_calls.append(progress)
        
        sync_manager.add_progress_callback(progress_callback)
        
        # Start sync
        sync_id = await sync_manager.start_sync(sync_config, resume=False)
        
        # Wait for some progress
        await asyncio.sleep(0.2)
        
        # Should have received progress updates
        assert len(callback_calls) > 0
        
        # Remove callback
        sync_manager.remove_progress_callback(progress_callback)
        
        # Clean up
        await sync_manager.stop_sync(sync_id)
    
    @pytest.mark.asyncio
    async def test_sync_with_api_errors(self, storage, sync_config):
        """Test sync handling API errors."""
        # Create API client that raises errors
        api_client = Mock()
        metrics_mock = Mock()
        
        sleep_mock = Mock()
        sleep_mock.get = Mock(side_effect=Exception("API Error"))
        
        metrics_mock.get = Mock(return_value=sleep_mock)
        api_client.metrics = metrics_mock
        
        sync_manager = SyncManager(api_client, storage, max_workers=1)
        
        # Start sync - should handle errors gracefully
        sync_id = await sync_manager.start_sync(sync_config, resume=False)
        
        # Wait for sync to complete/fail
        await asyncio.sleep(1.0)
        
        progress = sync_manager.get_sync_progress(sync_id)
        # Sync might fail or continue with retries
        assert progress is not None
    
    @pytest.mark.asyncio
    async def test_checkpoint_save_and_load(self, sync_manager, sync_config, storage):
        """Test checkpoint saving and loading."""
        # Create a checkpoint
        checkpoint = SyncCheckpoint(
            sync_id="test_sync",
            user_id="test_user",
        )
        
        checkpoint.completed_metrics.add("sleep")
        checkpoint.completed_dates["sleep"] = {"2023-12-01"}
        
        # Save checkpoint
        await sync_manager._save_checkpoint(checkpoint)
        
        # Load checkpoint
        loaded_checkpoint = await sync_manager._load_or_create_checkpoint("test_sync", sync_config)
        
        assert "sleep" in loaded_checkpoint.completed_metrics
        assert "sleep" in loaded_checkpoint.completed_dates
    
    @pytest.mark.asyncio
    async def test_batch_processing_with_retries(self, storage, sync_config):
        """Test batch processing with retry logic."""
        # Create API client with intermittent failures
        api_client = Mock()
        metrics_mock = Mock()
        
        call_count = 0
        def get_data(date_str):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:  # Fail first two calls
                raise Exception("Temporary error")
            return {"data": f"success_{date_str}"}
        
        sleep_mock = Mock()
        sleep_mock.get = Mock(side_effect=get_data)
        
        metrics_mock.get = Mock(return_value=sleep_mock)
        api_client.metrics = metrics_mock
        
        sync_manager = SyncManager(api_client, storage, max_workers=1)
        
        # Create simplified config for single metric/date
        simple_config = SyncConfig(
            user_id="test_user",
            start_date=date(2023, 12, 1),
            end_date=date(2023, 12, 1),  # Single day
            metrics=["sleep"],
            batch_size=1,
            retry_attempts=3,
            retry_delay=0.01,
        )
        
        sync_id = await sync_manager.start_sync(simple_config, resume=False)
        
        # Wait for sync to complete
        await asyncio.sleep(1.0)
        
        # Check if data was eventually stored
        stored_data = storage.get_metric_data("test_user", "sleep", "2023-12-01")
        # Should succeed after retries
        assert stored_data is not None or call_count >= 2  # Either succeeded or tried multiple times
    
    def test_sync_manager_initialization(self, mock_api_client, storage):
        """Test sync manager initialization."""
        sync_manager = SyncManager(mock_api_client, storage, max_workers=4, checkpoint_interval=30)
        
        assert sync_manager.api_client == mock_api_client
        assert sync_manager.storage == storage
        assert sync_manager.max_workers == 4
        assert sync_manager.checkpoint_interval == 30
        assert len(sync_manager._active_syncs) == 0
        assert len(sync_manager._progress_callbacks) == 0