"""LocalDB configuration module with comprehensive configuration loading."""

import json
import logging
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Union

from .exceptions import ConfigurationError, ValidationError

logger = logging.getLogger(__name__)


@dataclass
class LocalDBConfig:
    """Configuration for LocalDB operations with validation and loading capabilities."""

    # Database settings
    database_path: str = "garmy_local.db"
    echo_sql: bool = False
    auto_create_tables: bool = True
    backup_before_migration: bool = True

    # Sync settings
    auto_sync: bool = True
    sync_days: int = 30
    batch_size: int = 100
    max_retries: int = 3
    retry_delay: int = 5

    # Performance settings
    connection_pool_size: int = 5
    connection_timeout: int = 30
    query_timeout: int = 60
    cache_size: int = 100

    # Analytics settings
    analytics_cache_ttl: int = 3600  # 1 hour
    analytics_max_days: int = 365

    # Logging settings
    log_level: str = "INFO"
    log_sql_queries: bool = False

    # Security settings
    encrypt_sensitive_data: bool = False
    max_token_age_days: int = 30

    def __post_init__(self):
        """Post-initialization validation and setup."""
        self.validate()
        self._ensure_database_dir()

    @property
    def database_url(self) -> str:
        """Get SQLAlchemy database URL."""
        return f"sqlite:///{self.database_path}"

    @property
    def db_path(self) -> Path:
        """Get database path as Path object."""
        return Path(self.database_path)

    @property
    def db_dir(self) -> Path:
        """Get database directory."""
        return self.db_path.parent

    def validate(self) -> None:
        """Validate configuration settings with comprehensive checks."""
        errors = []

        # Database validation
        if not self.database_path:
            errors.append("database_path cannot be empty")

        # Sync validation
        if self.sync_days < 1 or self.sync_days > 3650:  # Max 10 years
            errors.append("sync_days must be between 1 and 3650")

        if self.batch_size < 1 or self.batch_size > 10000:
            errors.append("batch_size must be between 1 and 10000")

        if self.max_retries < 0 or self.max_retries > 10:
            errors.append("max_retries must be between 0 and 10")

        if self.retry_delay < 0 or self.retry_delay > 300:
            errors.append("retry_delay must be between 0 and 300 seconds")

        # Performance validation
        if self.connection_pool_size < 1 or self.connection_pool_size > 100:
            errors.append("connection_pool_size must be between 1 and 100")

        if self.connection_timeout < 5 or self.connection_timeout > 300:
            errors.append("connection_timeout must be between 5 and 300 seconds")

        if self.query_timeout < 5 or self.query_timeout > 3600:
            errors.append("query_timeout must be between 5 and 3600 seconds")

        if self.cache_size < 0 or self.cache_size > 10000:
            errors.append("cache_size must be between 0 and 10000")

        # Analytics validation
        if self.analytics_cache_ttl < 60 or self.analytics_cache_ttl > 86400:
            errors.append("analytics_cache_ttl must be between 60 and 86400 seconds")

        if self.analytics_max_days < 1 or self.analytics_max_days > 3650:
            errors.append("analytics_max_days must be between 1 and 3650")

        # Logging validation
        valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.log_level.upper() not in valid_log_levels:
            errors.append(f"log_level must be one of {valid_log_levels}")

        # Security validation
        if self.max_token_age_days < 1 or self.max_token_age_days > 365:
            errors.append("max_token_age_days must be between 1 and 365")

        if errors:
            raise ValidationError(f"Configuration validation failed: {'; '.join(errors)}")

    def _ensure_database_dir(self) -> None:
        """Ensure database directory exists."""
        try:
            self.db_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise ConfigurationError(f"Failed to create database directory {self.db_dir}: {e}")

    @classmethod
    def from_file(cls, config_path: Optional[Union[str, Path]] = None) -> "LocalDBConfig":
        """Load configuration from file with comprehensive error handling."""
        config = cls()  # Start with defaults

        if config_path is None:
            # Try default locations
            possible_paths = [
                Path.cwd() / "garmy_localdb.json",
                Path.home() / ".garmy" / "localdb_config.json",
                Path.home() / ".config" / "garmy" / "localdb.json",
            ]

            for path in possible_paths:
                if path.exists():
                    config_path = path
                    break
            else:
                logger.info("No configuration file found, using defaults")
                return config

        config_path = Path(config_path)
        if not config_path.exists():
            raise ConfigurationError(f"Configuration file not found: {config_path}")

        try:
            return cls._load_from_json(config_path)
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration from {config_path}: {e}")

    @classmethod
    def _load_from_json(cls, config_path: Path) -> "LocalDBConfig":
        """Load configuration from JSON file."""
        try:
            with open(config_path, encoding='utf-8') as f:
                data = json.load(f)

            # Filter only valid fields
            valid_fields = {field.name for field in cls.__dataclass_fields__.values()}
            filtered_data = {k: v for k, v in data.items() if k in valid_fields}

            logger.info(f"Loaded configuration from {config_path}")
            return cls(**filtered_data)

        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Invalid JSON in configuration file: {e}")
        except Exception as e:
            raise ConfigurationError(f"Failed to read configuration file: {e}")

    @classmethod
    def from_environment(cls) -> "LocalDBConfig":
        """Load configuration from environment variables."""
        config = cls()  # Start with defaults

        # Environment variable mapping
        env_mapping = {
            'GARMY_DB_PATH': 'database_path',
            'GARMY_ECHO_SQL': 'echo_sql',
            'GARMY_AUTO_SYNC': 'auto_sync',
            'GARMY_SYNC_DAYS': 'sync_days',
            'GARMY_BATCH_SIZE': 'batch_size',
            'GARMY_LOG_LEVEL': 'log_level',
            'GARMY_CACHE_SIZE': 'cache_size',
        }

        updates = {}
        for env_var, config_key in env_mapping.items():
            value = os.getenv(env_var)
            if value is not None:
                # Type conversion based on field type
                field_type = cls.__dataclass_fields__[config_key].type
                try:
                    if field_type == bool:
                        updates[config_key] = value.lower() in ('true', '1', 'yes', 'on')
                    elif field_type == int:
                        updates[config_key] = int(value)
                    elif field_type == float:
                        updates[config_key] = float(value)
                    else:
                        updates[config_key] = value
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid value for {env_var}: {value}, error: {e}")

        if updates:
            # Create new instance with updates
            current_data = asdict(config)
            current_data.update(updates)
            config = cls(**current_data)
            logger.info(f"Updated configuration from environment variables: {list(updates.keys())}")

        return config

    @classmethod
    def default(cls, database_path: str = "garmy_local.db") -> "LocalDBConfig":
        """Create default configuration with specified database path."""
        return cls(database_path=database_path)

    def save_to_file(self, config_path: Union[str, Path]) -> None:
        """Save configuration to file."""
        config_path = Path(config_path)

        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)

            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(asdict(self), f, indent=2, sort_keys=True)

            logger.info(f"Configuration saved to {config_path}")

        except Exception as e:
            raise ConfigurationError(f"Failed to save configuration to {config_path}: {e}")

    def update(self, **kwargs) -> "LocalDBConfig":
        """Create a new configuration with updated values."""
        current_data = asdict(self)
        current_data.update(kwargs)
        return self.__class__(**current_data)

    def get_dict(self) -> Dict[str, Any]:
        """Get configuration as dictionary."""
        return asdict(self)

    def apply_logging_config(self) -> None:
        """Apply logging configuration."""
        logging.basicConfig(
            level=getattr(logging, self.log_level.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        if self.log_sql_queries:
            logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

    def get_summary(self) -> str:
        """Get a human-readable configuration summary."""
        lines = [
            "LocalDB Configuration Summary:",
            f"  Database: {self.database_path}",
            f"  Sync: {self.sync_days} days, batch size {self.batch_size}",
            f"  Cache: {self.cache_size} items, TTL {self.analytics_cache_ttl}s",
            f"  Performance: {self.connection_pool_size} connections, {self.connection_timeout}s timeout",
            f"  Logging: {self.log_level}",
        ]
        return "\n".join(lines)


class ConfigManager:
    """Configuration manager for LocalDB with environment and file support."""

    def __init__(self):
        self._config: Optional[LocalDBConfig] = None

    def get_config(self, config_path: Optional[Union[str, Path]] = None,
                   use_environment: bool = True) -> LocalDBConfig:
        """Get configuration with priority: file > environment > defaults."""
        if self._config is not None:
            return self._config

        try:
            # Try to load from file first
            if config_path or self._has_config_file():
                config = LocalDBConfig.from_file(config_path)
            else:
                config = LocalDBConfig()

            # Apply environment overrides if requested
            if use_environment:
                env_config = LocalDBConfig.from_environment()
                # Merge environment updates
                env_data = asdict(env_config)
                default_data = asdict(LocalDBConfig())

                # Only apply non-default environment values
                env_updates = {k: v for k, v in env_data.items()
                              if v != default_data.get(k)}

                if env_updates:
                    current_data = asdict(config)
                    current_data.update(env_updates)
                    config = LocalDBConfig(**current_data)

            self._config = config
            logger.info("Configuration loaded successfully")
            return config

        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            # Fallback to defaults
            self._config = LocalDBConfig()
            return self._config

    def _has_config_file(self) -> bool:
        """Check if any default config file exists."""
        possible_paths = [
            Path.cwd() / "garmy_localdb.json",
            Path.home() / ".garmy" / "localdb_config.json",
            Path.home() / ".config" / "garmy" / "localdb.json",
        ]
        return any(path.exists() for path in possible_paths)

    def reload_config(self, config_path: Optional[Union[str, Path]] = None) -> LocalDBConfig:
        """Reload configuration, discarding cached version."""
        self._config = None
        return self.get_config(config_path)

    def set_config(self, config: LocalDBConfig) -> None:
        """Set configuration manually."""
        config.validate()  # Ensure it's valid
        self._config = config


# Global configuration manager instance
config_manager = ConfigManager()
