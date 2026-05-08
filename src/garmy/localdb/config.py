"""Configuration for localdb module."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class SyncConfig:
    """Sync operation configuration."""

    # Retry settings
    max_retries: int = 3
    retry_exponential_base: int = 2

    # Rate limiting
    rate_limit_delay: float = 0.5

    # Progress reporting
    progress_reporter: str = "logging"  # logging, tqdm, rich, json, silent
    progress_show_details: bool = True
    progress_log_interval: int = 50  # For logging reporter

    # Activities API (handled by iterator)
    activities_batch_size: int = 50

    # Timeseries validation
    min_timeseries_fields: int = 2

    # Sync range limits
    max_sync_days: int = 3650  # ~10 years maximum sync range


@dataclass
class DatabaseConfig:
    """Database configuration."""

    # Connection settings
    timeout: float = 30.0
    enable_wal_mode: bool = True

    # Timestamp conversion
    ms_per_second: int = 1000
    seconds_per_day: int = 24 * 60 * 60


@dataclass
class LocalDBConfig:
    """Complete localdb configuration."""

    sync: SyncConfig = field(default_factory=SyncConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
