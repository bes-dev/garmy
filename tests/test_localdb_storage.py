"""Tests for local database storage functionality."""

import pytest
import tempfile
import shutil
from datetime import datetime, date
from pathlib import Path
from unittest.mock import patch

from garmy.localdb.config import LocalDBConfig, UserConfig
from garmy.localdb.storage import LocalDataStore
from garmy.localdb.exceptions import (
    LocalDBError,
    UserNotFoundError,
    DataIntegrityError,
)


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
    )


@pytest.fixture
def storage(db_config):
    """Create test storage instance."""
    store = LocalDataStore(db_config)
    store.open()
    yield store
    store.close()


@pytest.fixture
def test_user():
    """Create test user configuration."""
    return UserConfig(
        user_id="test_user",
        email="test@example.com",
        display_name="Test User",
        created_at=datetime.now(),
    )


class TestLocalDataStore:
    """Test local data storage functionality."""
    
    def test_open_close_database(self, db_config):
        """Test opening and closing database."""
        storage = LocalDataStore(db_config)
        
        # Database should not be open initially
        assert storage._db is None
        
        # Open database
        storage.open()
        assert storage._db is not None
        
        # Close database
        storage.close()
        assert storage._db is None
    
    def test_context_manager(self, db_config):
        """Test using storage as context manager."""
        with LocalDataStore(db_config) as storage:
            assert storage._db is not None
        # Database should be closed after context
    
    def test_add_user(self, storage, test_user):
        """Test adding a new user."""
        storage.add_user(test_user)
        
        # User should be in cache
        assert test_user.user_id in storage._users_cache
        
        # User should be retrievable
        retrieved_user = storage.get_user(test_user.user_id)
        assert retrieved_user.email == test_user.email
    
    def test_add_duplicate_user(self, storage, test_user):
        """Test adding duplicate user raises error."""
        storage.add_user(test_user)
        
        with pytest.raises(LocalDBError, match="already exists"):
            storage.add_user(test_user)
    
    def test_get_nonexistent_user(self, storage):
        """Test getting non-existent user raises error."""
        with pytest.raises(UserNotFoundError):
            storage.get_user("nonexistent")
    
    def test_update_user(self, storage, test_user):
        """Test updating user configuration."""
        storage.add_user(test_user)
        
        # Update user
        test_user.display_name = "Updated Name"
        test_user.last_sync = datetime.now()
        storage.update_user(test_user)
        
        # Verify update
        retrieved_user = storage.get_user(test_user.user_id)
        assert retrieved_user.display_name == "Updated Name"
        assert retrieved_user.last_sync is not None
    
    def test_list_users(self, storage):
        """Test listing users."""
        # Initially empty
        assert len(storage.list_users()) == 0
        
        # Add users
        user1 = UserConfig("user1", "user1@example.com")
        user2 = UserConfig("user2", "user2@example.com")
        
        storage.add_user(user1)
        storage.add_user(user2)
        
        users = storage.list_users()
        assert len(users) == 2
        assert any(u.user_id == "user1" for u in users)
        assert any(u.user_id == "user2" for u in users)
    
    def test_remove_user(self, storage, test_user):
        """Test removing user and their data."""
        storage.add_user(test_user)
        
        # Add some data for the user
        test_data = {"test": "data"}
        storage.store_metric_data(test_user.user_id, "sleep", "2023-12-01", test_data)
        
        # Remove user
        storage.remove_user(test_user.user_id)
        
        # User should be gone
        with pytest.raises(UserNotFoundError):
            storage.get_user(test_user.user_id)
        
        # Data should be gone (user not found error expected)
        with pytest.raises(UserNotFoundError):
            storage.get_metric_data(test_user.user_id, "sleep", "2023-12-01")
    
    def test_store_and_get_metric_data(self, storage, test_user):
        """Test storing and retrieving metric data."""
        storage.add_user(test_user)
        
        test_data = {
            "sleep_start": "2023-12-01T22:00:00",
            "sleep_end": "2023-12-02T06:30:00",
            "deep_sleep_minutes": 120,
            "light_sleep_minutes": 180,
        }
        
        # Store data
        storage.store_metric_data(test_user.user_id, "sleep", "2023-12-01", test_data)
        
        # Retrieve data
        retrieved_data = storage.get_metric_data(test_user.user_id, "sleep", "2023-12-01")
        assert retrieved_data == test_data
    
    def test_store_metric_data_with_date_object(self, storage, test_user):
        """Test storing data with date object."""
        storage.add_user(test_user)
        
        test_data = {"steps": 10000}
        test_date = date(2023, 12, 1)
        
        storage.store_metric_data(test_user.user_id, "steps", test_date, test_data)
        
        # Should be retrievable with string date
        retrieved_data = storage.get_metric_data(test_user.user_id, "steps", "2023-12-01")
        assert retrieved_data == test_data
    
    def test_get_nonexistent_metric_data(self, storage, test_user):
        """Test getting non-existent metric data returns None."""
        storage.add_user(test_user)
        
        data = storage.get_metric_data(test_user.user_id, "sleep", "2023-12-01")
        assert data is None
    
    def test_list_metric_dates(self, storage, test_user):
        """Test listing available dates for a metric."""
        storage.add_user(test_user)
        
        # Store data for multiple dates
        dates = ["2023-12-01", "2023-12-02", "2023-12-03"]
        for date_str in dates:
            storage.store_metric_data(test_user.user_id, "sleep", date_str, {"test": date_str})
        
        # Get available dates
        available_dates = storage.list_metric_dates(test_user.user_id, "sleep")
        assert sorted(available_dates) == sorted(dates)
    
    def test_list_metric_dates_with_range(self, storage, test_user):
        """Test listing dates with start/end range."""
        storage.add_user(test_user)
        
        # Store data for multiple dates
        dates = ["2023-12-01", "2023-12-02", "2023-12-03", "2023-12-04"]
        for date_str in dates:
            storage.store_metric_data(test_user.user_id, "sleep", date_str, {"test": date_str})
        
        # Get dates in range
        available_dates = storage.list_metric_dates(
            test_user.user_id, "sleep", "2023-12-02", "2023-12-03"
        )
        assert sorted(available_dates) == ["2023-12-02", "2023-12-03"]
    
    def test_list_user_metrics(self, storage, test_user):
        """Test listing available metrics for a user."""
        storage.add_user(test_user)
        
        # Store data for different metrics
        metrics = ["sleep", "heart_rate", "steps"]
        for metric in metrics:
            storage.store_metric_data(test_user.user_id, metric, "2023-12-01", {"test": metric})
        
        # Get available metrics
        available_metrics = storage.list_user_metrics(test_user.user_id)
        assert sorted(available_metrics) == sorted(metrics)
    
    def test_sync_status_operations(self, storage, test_user):
        """Test sync status storage and retrieval."""
        storage.add_user(test_user)
        
        sync_id = "test_sync_123"
        status_data = {
            "status": "running",
            "progress": 50,
            "started_at": datetime.now().isoformat(),
        }
        
        # Store status
        storage.store_sync_status(test_user.user_id, sync_id, status_data)
        
        # Retrieve status
        retrieved_status = storage.get_sync_status(test_user.user_id, sync_id)
        assert retrieved_status == status_data
        
        # Non-existent status
        assert storage.get_sync_status(test_user.user_id, "nonexistent") is None
    
    def test_sync_checkpoint_operations(self, storage, test_user):
        """Test sync checkpoint storage and retrieval."""
        storage.add_user(test_user)
        
        sync_id = "test_sync_123"
        checkpoint_data = {
            "completed_metrics": ["sleep", "heart_rate"],
            "current_date": "2023-12-01",
            "failed_attempts": {},
        }
        
        # Store checkpoint
        storage.store_sync_checkpoint(test_user.user_id, sync_id, checkpoint_data)
        
        # Retrieve checkpoint
        retrieved_checkpoint = storage.get_sync_checkpoint(test_user.user_id, sync_id)
        assert retrieved_checkpoint["checkpoint"] == checkpoint_data
        assert "timestamp" in retrieved_checkpoint
        assert "sync_id" in retrieved_checkpoint
    
    def test_cleanup_sync_data(self, storage, test_user):
        """Test cleaning up sync data."""
        storage.add_user(test_user)
        
        sync_id = "test_sync_123"
        
        # Store sync data
        storage.store_sync_status(test_user.user_id, sync_id, {"status": "completed"})
        storage.store_sync_checkpoint(test_user.user_id, sync_id, {"test": "data"})
        
        # Verify data exists
        assert storage.get_sync_status(test_user.user_id, sync_id) is not None
        assert storage.get_sync_checkpoint(test_user.user_id, sync_id) is not None
        
        # Clean up
        storage.cleanup_sync_data(test_user.user_id, sync_id)
        
        # Verify data is gone
        assert storage.get_sync_status(test_user.user_id, sync_id) is None
        assert storage.get_sync_checkpoint(test_user.user_id, sync_id) is None
    
    def test_database_stats(self, storage, test_user):
        """Test getting database statistics."""
        storage.add_user(test_user)
        
        # Add some data
        storage.store_metric_data(test_user.user_id, "sleep", "2023-12-01", {"test": "data"})
        storage.store_metric_data(test_user.user_id, "heart_rate", "2023-12-01", {"test": "data"})
        
        stats = storage.get_database_stats()
        
        assert stats["users_count"] == 1
        assert stats["compression_enabled"] is True
        assert test_user.user_id in stats["user_data_counts"]
        assert stats["user_data_counts"][test_user.user_id] == 2
    
    def test_data_integrity_verification(self, storage, test_user):
        """Test data integrity with checksums."""
        storage.add_user(test_user)
        
        test_data = {"important": "data", "value": 123}
        
        # Store data (should include checksum)
        storage.store_metric_data(test_user.user_id, "test", "2023-12-01", test_data)
        
        # Retrieve should work normally
        retrieved_data = storage.get_metric_data(test_user.user_id, "test", "2023-12-01")
        assert retrieved_data == test_data
    
    def test_generate_sync_id(self):
        """Test sync ID generation."""
        sync_id1 = LocalDataStore.generate_sync_id()
        sync_id2 = LocalDataStore.generate_sync_id()
        
        # Should be different
        assert sync_id1 != sync_id2
        
        # Should be valid UUIDs
        import uuid
        uuid.UUID(sync_id1)  # Should not raise
        uuid.UUID(sync_id2)  # Should not raise
    
    @patch('sqlite3.connect')
    def test_database_open_failure(self, mock_connect, db_config):
        """Test handling database open failure."""
        mock_connect.side_effect = Exception("Database error")
        
        storage = LocalDataStore(db_config)
        
        with pytest.raises(LocalDBError, match="Failed to open database"):
            storage.open()
    
    def test_transaction_operations(self, storage, test_user):
        """Test transaction-based operations."""
        storage.add_user(test_user)
        
        # Test successful transaction
        with storage.transaction(test_user.user_id) as batch:
            # This would normally add operations to the batch
            # For this test, we just verify the transaction context works
            pass
        
        # Test transaction with exception
        try:
            with storage.transaction(test_user.user_id) as batch:
                raise ValueError("Test exception")
        except ValueError:
            pass  # Expected
    
    def test_concurrent_user_operations(self, storage):
        """Test that multiple users can be handled concurrently."""
        user1 = UserConfig("user1", "user1@example.com")
        user2 = UserConfig("user2", "user2@example.com")
        
        storage.add_user(user1)
        storage.add_user(user2)
        
        # Store data for both users
        storage.store_metric_data("user1", "sleep", "2023-12-01", {"user": "1"})
        storage.store_metric_data("user2", "sleep", "2023-12-01", {"user": "2"})
        
        # Verify isolation
        user1_data = storage.get_metric_data("user1", "sleep", "2023-12-01")
        user2_data = storage.get_metric_data("user2", "sleep", "2023-12-01")
        
        assert user1_data["user"] == "1"
        assert user2_data["user"] == "2"