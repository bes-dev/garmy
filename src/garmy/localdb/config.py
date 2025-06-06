"""LocalDB configuration module."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class LocalDBConfig:
    """Configuration for LocalDB operations."""
    
    # Database settings
    database_path: str = "garmy_local.db"
    echo_sql: bool = False
    
    # Sync settings
    auto_sync: bool = True
    sync_days: int = 30
    batch_size: int = 100
    
    # Performance settings
    connection_pool_size: int = 5
    connection_timeout: int = 30
    
    @property
    def database_url(self) -> str:
        """Get SQLAlchemy database URL."""
        return f"sqlite:///{self.database_path}"
    
    @property
    def db_path(self) -> str:
        """Alias for database_path for compatibility."""
        return self.database_path
    
    @classmethod
    def from_file(cls, config_path: Optional[str] = None) -> "LocalDBConfig":
        """Load configuration from file."""
        # For now, return default config
        # In future, could load from JSON/YAML file
        return cls()
    
    @classmethod
    def default(cls, database_path: str = "garmy_local.db") -> "LocalDBConfig":
        """Create default configuration with specified database path."""
        return cls(database_path=database_path)
    
    def validate(self) -> None:
        """Validate configuration settings."""
        if self.sync_days < 1:
            raise ValueError("sync_days must be positive")
        if self.batch_size < 1:
            raise ValueError("batch_size must be positive")
        if self.connection_pool_size < 1:
            raise ValueError("connection_pool_size must be positive")