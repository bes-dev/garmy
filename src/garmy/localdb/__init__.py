"""Local database module for Garmin data storage and synchronization."""

from .client import LocalDBClient
from .config import LocalDBConfig, SyncConfig, UserConfig
from .exceptions import (
    LocalDBError,
    SyncError,
    DataIntegrityError,
    UserNotFoundError,
    SyncInterruptedError,
)
from .storage import LocalDataStore
from .sync import SyncManager, SyncStatus, SyncProgress
from .cli import LocalDBCLI

__all__ = [
    "LocalDBClient",
    "LocalDBConfig",
    "SyncConfig",
    "UserConfig",
    "LocalDBError",
    "SyncError",
    "DataIntegrityError",
    "UserNotFoundError",
    "SyncInterruptedError",
    "LocalDataStore",
    "SyncManager",
    "SyncStatus",
    "SyncProgress",
    "LocalDBCLI",
]