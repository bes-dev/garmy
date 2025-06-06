"""LocalDB - Efficient Garmin data storage with analytics.

A modern, SQLAlchemy-based local database for Garmin data that automatically
generates tables from metrics dataclasses, ensuring consistency and enabling
powerful analytics.

Key Features:
- Auto-generated SQLAlchemy models from metrics dataclasses
- Efficient analytics queries with proper indexing
- Type-safe data storage and retrieval
- Async synchronization with progress tracking
- CLI interface for data management
- No data structure duplication

Example:
    >>> from garmy.localdb import LocalDBClient
    >>> 
    >>> with LocalDBClient('~/.garmy/data.db') as client:
    ...     # Add user
    ...     client.add_user('user123', 'user@example.com')
    ...     
    ...     # Sync data
    ...     await client.sync_user_data('user123', ['steps', 'sleep'], start_date, end_date)
    ...     
    ...     # Get analytics
    ...     analytics = client.get_steps_analytics('user123', days=30)
    ...     print(f"Average steps: {analytics['averages']['daily_steps']}")
"""

from .client import LocalDBClient
from .storage import LocalDataStore
from .sync import SyncManager, SyncProgress
from .models import User, StepsData, HeartRateData, SleepData, BodyBatteryData
from .config import LocalDBConfig

# Compatibility aliases
LocalDB = LocalDBClient
LocalDataStore = LocalDataStore

__all__ = [
    # Main classes
    'LocalDBClient',
    'LocalDataStore', 
    'SyncManager',
    'SyncProgress',
    'LocalDBConfig',
    
    # Models
    'User',
    'StepsData',
    'HeartRateData', 
    'SleepData',
    'BodyBatteryData',
    
    # Compatibility
    'LocalDB',
]

__version__ = '2.0.0'