"""Exceptions for local database operations."""

from typing import Optional


class LocalDBError(Exception):
    """Base exception for local database operations."""
    
    def __init__(self, message: str, user_id: Optional[str] = None) -> None:
        self.user_id = user_id
        super().__init__(message)


class SyncError(LocalDBError):
    """Exception raised during data synchronization."""
    
    def __init__(self, message: str, sync_id: Optional[str] = None, user_id: Optional[str] = None) -> None:
        self.sync_id = sync_id
        super().__init__(message, user_id)


class DataIntegrityError(LocalDBError):
    """Exception raised when data integrity is compromised."""
    pass


class UserNotFoundError(LocalDBError):
    """Exception raised when user is not found in the database."""
    pass


class SyncInterruptedError(SyncError):
    """Exception raised when sync is interrupted and needs recovery."""
    
    def __init__(self, message: str, sync_id: str, checkpoint: dict, user_id: Optional[str] = None) -> None:
        self.checkpoint = checkpoint
        super().__init__(message, sync_id, user_id)


class ConfigurationError(LocalDBError):
    """Exception raised for configuration-related errors."""
    pass


class LockError(LocalDBError):
    """Exception raised when database lock operations fail."""
    pass