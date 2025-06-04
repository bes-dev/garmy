"""Main client for local database operations."""

import asyncio
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ..auth.client import AuthClient
from ..core.client import APIClient
from .config import LocalDBConfig, SyncConfig, UserConfig
from .exceptions import LocalDBError, UserNotFoundError
from .storage import LocalDataStore
from .sync import SyncManager, SyncProgress


class LocalDBClient:
    """Main client for local database operations."""
    
    def __init__(self, config: Optional[LocalDBConfig] = None) -> None:
        self.config = config or LocalDBConfig.default()
        self._storage: Optional[LocalDataStore] = None
        self._sync_manager: Optional[SyncManager] = None
        self._api_clients: Dict[str, APIClient] = {}
    
    def __enter__(self) -> "LocalDBClient":
        """Context manager entry."""
        self.open()
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()
    
    def open(self) -> None:
        """Open the local database."""
        if self._storage is None:
            self._storage = LocalDataStore(self.config)
            self._storage.open()
    
    def close(self) -> None:
        """Close the local database."""
        if self._storage is not None:
            self._storage.close()
            self._storage = None
        self._api_clients.clear()
    
    @property
    def storage(self) -> LocalDataStore:
        """Get storage instance."""
        if self._storage is None:
            raise LocalDBError("Database not open. Call open() first.")
        return self._storage
    
    def _get_sync_manager(self, user_id: str) -> SyncManager:
        """Get sync manager for user."""
        if self._sync_manager is None:
            api_client = self._get_api_client(user_id)
            self._sync_manager = SyncManager(api_client, self.storage)
        return self._sync_manager
    
    def _get_api_client(self, user_id: str) -> APIClient:
        """Get API client for user."""
        if user_id not in self._api_clients:
            user_config = self.storage.get_user(user_id)
            
            # Create auth client with user's token path
            auth_client = AuthClient()
            if user_config.auth_token_path:
                # Load tokens from user's path
                pass  # Auth client will handle token loading
            
            self._api_clients[user_id] = APIClient(auth_client=auth_client)
        
        return self._api_clients[user_id]
    
    # User management
    def add_user(self, user_config: UserConfig) -> None:
        """Add a new user."""
        self.storage.add_user(user_config)
    
    def get_user(self, user_id: str) -> UserConfig:
        """Get user configuration."""
        return self.storage.get_user(user_id)
    
    def update_user(self, user_config: UserConfig) -> None:
        """Update user configuration."""
        self.storage.update_user(user_config)
    
    def list_users(self) -> List[UserConfig]:
        """List all users."""
        return self.storage.list_users()
    
    def remove_user(self, user_id: str) -> None:
        """Remove user and all their data."""
        # Clean up API client
        if user_id in self._api_clients:
            del self._api_clients[user_id]
        
        self.storage.remove_user(user_id)
    
    # Data operations
    def store_metric_data(
        self,
        user_id: str,
        metric_type: str,
        data_date: Union[str, date],
        data: Dict[str, Any],
    ) -> None:
        """Store metric data."""
        self.storage.store_metric_data(user_id, metric_type, data_date, data)
    
    def get_metric_data(
        self,
        user_id: str,
        metric_type: str,
        data_date: Union[str, date],
    ) -> Optional[Dict[str, Any]]:
        """Get metric data."""
        return self.storage.get_metric_data(user_id, metric_type, data_date)
    
    def list_metric_dates(
        self,
        user_id: str,
        metric_type: str,
        start_date: Optional[Union[str, date]] = None,
        end_date: Optional[Union[str, date]] = None,
    ) -> List[str]:
        """List available dates for a metric."""
        return self.storage.list_metric_dates(user_id, metric_type, start_date, end_date)
    
    def list_user_metrics(self, user_id: str) -> List[str]:
        """List available metrics for a user."""
        return self.storage.list_user_metrics(user_id)
    
    # Sync operations
    async def start_sync(self, config: SyncConfig, resume: bool = True) -> str:
        """Start data synchronization."""
        sync_manager = self._get_sync_manager(config.user_id)
        return await sync_manager.start_sync(config, resume)
    
    async def pause_sync(self, sync_id: str) -> None:
        """Pause a sync operation."""
        if self._sync_manager:
            await self._sync_manager.pause_sync(sync_id)
    
    async def resume_sync(self, sync_id: str) -> None:
        """Resume a sync operation."""
        if self._sync_manager:
            await self._sync_manager.resume_sync(sync_id)
    
    async def stop_sync(self, sync_id: str) -> None:
        """Stop a sync operation."""
        if self._sync_manager:
            await self._sync_manager.stop_sync(sync_id)
    
    def get_sync_progress(self, sync_id: str) -> Optional[SyncProgress]:
        """Get sync progress."""
        if self._sync_manager:
            return self._sync_manager.get_sync_progress(sync_id)
        return None
    
    def list_active_syncs(self) -> List[SyncProgress]:
        """List active sync operations."""
        if self._sync_manager:
            return self._sync_manager.list_active_syncs()
        return []
    
    # Database operations
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        return self.storage.get_database_stats()
    
    def backup_database(self, backup_path: Path) -> None:
        """Create a backup of the database."""
        # This would implement database backup functionality
        # For LevelDB, this could involve creating a snapshot
        raise NotImplementedError("Database backup not yet implemented")
    
    def restore_database(self, backup_path: Path) -> None:
        """Restore database from backup."""
        # This would implement database restore functionality
        raise NotImplementedError("Database restore not yet implemented")
    
    def compact_database(self) -> None:
        """Compact the database to reclaim space."""
        # LevelDB compaction - would need to implement with plyvel
        raise NotImplementedError("Database compaction not yet implemented")
    
    # Utility methods
    def validate_data_integrity(self, user_id: str) -> Dict[str, Any]:
        """Validate data integrity for a user."""
        report = {
            "user_id": user_id,
            "total_records": 0,
            "corrupted_records": 0,
            "missing_checksums": 0,
            "errors": [],
        }
        
        try:
            metrics = self.list_user_metrics(user_id)
            
            for metric in metrics:
                dates = self.list_metric_dates(user_id, metric)
                
                for date_str in dates:
                    report["total_records"] += 1
                    
                    try:
                        data = self.get_metric_data(user_id, metric, date_str)
                        if data is None:
                            report["corrupted_records"] += 1
                            report["errors"].append(f"Missing data for {metric}:{date_str}")
                    except Exception as e:
                        report["corrupted_records"] += 1
                        report["errors"].append(f"Error reading {metric}:{date_str}: {e}")
        
        except Exception as e:
            report["errors"].append(f"Validation error: {e}")
        
        return report