"""Configuration classes for local database."""

from dataclasses import dataclass, field
from datetime import datetime, date
from pathlib import Path
from typing import List, Optional, Dict, Any
import json
import os


@dataclass
class UserConfig:
    """Configuration for a specific user."""
    
    user_id: str
    email: str
    display_name: Optional[str] = None
    created_at: Optional[datetime] = None
    last_sync: Optional[datetime] = None
    auth_token_path: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "user_id": self.user_id,
            "email": self.email,
            "display_name": self.display_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            "auth_token_path": self.auth_token_path,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserConfig":
        """Create from dictionary."""
        return cls(
            user_id=data["user_id"],
            email=data["email"],
            display_name=data.get("display_name"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            last_sync=datetime.fromisoformat(data["last_sync"]) if data.get("last_sync") else None,
            auth_token_path=data.get("auth_token_path"),
        )


@dataclass
class SyncConfig:
    """Configuration for data synchronization."""
    
    user_id: str
    start_date: date
    end_date: date
    metrics: List[str] = field(default_factory=lambda: [
        "sleep", "heart_rate", "body_battery", "stress", "hrv", 
        "respiration", "training_readiness", "activities", 
        "steps", "calories", "daily_summary"
    ])
    schedule: Optional[str] = None  # "daily", "hourly", "weekly", or cron expression
    batch_size: int = 100  # Number of days to process in one batch
    retry_attempts: int = 3
    retry_delay: int = 300  # seconds
    auto_resume: bool = True
    incremental: bool = True  # Only sync new/changed data
    reverse_chronological: bool = True  # Sync from newest to oldest dates (recommended)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "user_id": self.user_id,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "metrics": self.metrics,
            "schedule": self.schedule,
            "batch_size": self.batch_size,
            "retry_attempts": self.retry_attempts,
            "retry_delay": self.retry_delay,
            "auto_resume": self.auto_resume,
            "incremental": self.incremental,
            "reverse_chronological": self.reverse_chronological,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SyncConfig":
        """Create from dictionary."""
        return cls(
            user_id=data["user_id"],
            start_date=date.fromisoformat(data["start_date"]),
            end_date=date.fromisoformat(data["end_date"]),
            metrics=data.get("metrics", []),
            schedule=data.get("schedule"),
            batch_size=data.get("batch_size", 100),
            retry_attempts=data.get("retry_attempts", 3),
            retry_delay=data.get("retry_delay", 300),
            auto_resume=data.get("auto_resume", True),
            incremental=data.get("incremental", True),
            reverse_chronological=data.get("reverse_chronological", True),
        )


@dataclass
class LocalDBConfig:
    """Configuration for local database."""
    
    db_path: Path
    compression: bool = True  # Use larger page size for compression-like effect
    timeout: float = 30.0  # Connection timeout in seconds
    wal_mode: bool = True  # Use WAL mode for better concurrency
    synchronous_mode: str = "NORMAL"  # FULL, NORMAL, or OFF
    page_size: int = 4096  # Page size in bytes (4KB default, 64KB for compression)
    cache_size: int = 2000  # Number of pages to cache
    temp_store: str = "MEMORY"  # Store temporary tables in memory
    journal_mode: str = "WAL"  # WAL, DELETE, TRUNCATE, PERSIST, MEMORY, OFF
    
    def __post_init__(self) -> None:
        """Ensure db_path is a Path object and create directories."""
        if isinstance(self.db_path, str):
            self.db_path = Path(self.db_path)
        
        # Create parent directories
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    @property
    def config_file(self) -> Path:
        """Path to configuration file."""
        return self.db_path.parent / "config.json"
    
    @property
    def users_file(self) -> Path:
        """Path to users configuration file."""
        return self.db_path.parent / "users.json"
    
    def save_config(self) -> None:
        """Save configuration to file."""
        config_data = {
            "db_path": str(self.db_path),
            "compression": self.compression,
            "timeout": self.timeout,
            "wal_mode": self.wal_mode,
            "synchronous_mode": self.synchronous_mode,
            "page_size": self.page_size,
            "cache_size": self.cache_size,
            "temp_store": self.temp_store,
            "journal_mode": self.journal_mode,
        }
        
        with open(self.config_file, "w") as f:
            json.dump(config_data, f, indent=2)
    
    @classmethod
    def load_config(cls, config_path: Path) -> "LocalDBConfig":
        """Load configuration from file."""
        if not config_path.exists():
            # Return default config if file doesn't exist
            return cls(db_path=config_path.parent / "garmin_data.db")
        
        with open(config_path) as f:
            config_data = json.load(f)
        
        return cls(**config_data)
    
    @classmethod
    def default(cls, base_path: Optional[Path] = None) -> "LocalDBConfig":
        """Create default configuration."""
        if base_path is None:
            base_path = Path.home() / ".garmy" / "localdb"
        
        return cls(db_path=base_path / "garmin_data.db")