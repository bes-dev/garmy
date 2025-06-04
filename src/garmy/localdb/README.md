# Garmy LocalDB Module

Local database functionality for automatic Garmin Connect data synchronization and storage.

## Features

- **Multi-user Support**: Store data for multiple Garmin Connect accounts
- **Crash Recovery**: Automatic resume of interrupted synchronizations
- **Data Integrity**: SHA256 checksums and SQLite transactions
- **CLI Monitoring**: Real-time progress tracking with Rich UI
- **Cross-platform**: SQLite-based storage works everywhere

## Installation

```bash
pip install garmy[localdb]
```

## Quick Start

### 1. Set up a user

```bash
garmy-localdb setup-user your-email@example.com --name "Your Name"
```

### 2. Start data synchronization

```bash
# Sync last 30 days of all metrics
garmy-localdb sync user_id 2023-11-01 2023-11-30

# Sync specific metrics only
garmy-localdb sync user_id 2023-11-01 2023-11-30 --metrics sleep heart_rate steps
```

### 3. Monitor progress

```bash
# Show all active syncs
garmy-localdb status

# Show specific sync
garmy-localdb status <sync_id>
```

### 4. Query local data

```bash
# Query as table
garmy-localdb query user_id sleep

# Query as JSON
garmy-localdb query user_id heart_rate --format json --start-date 2023-11-01
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `setup-user` | Add new user with Garmin authentication |
| `list-users` | Show configured users |
| `sync` | Start background data synchronization |
| `status` | Show sync progress and status |
| `pause/resume/stop` | Control running sync operations |
| `query` | Query locally stored data |
| `stats` | Database statistics |
| `remove-user` | Remove user and all data |

## Programmatic Usage

```python
from garmy.localdb import LocalDBClient, LocalDBConfig, SyncConfig
from datetime import date

# Initialize client
config = LocalDBConfig.default()
with LocalDBClient(config) as client:
    # Add user
    user = UserConfig("user_id", "email@example.com")
    client.add_user(user)
    
    # Start sync
    sync_config = SyncConfig(
        user_id="user_id",
        start_date=date(2023, 11, 1),
        end_date=date(2023, 11, 30),
        metrics=["sleep", "heart_rate"]
    )
    sync_id = await client.start_sync(sync_config)
    
    # Query data
    sleep_data = client.get_metric_data("user_id", "sleep", "2023-11-15")
```

## Database Structure

SQLite tables:
- `users` - User configurations
- `metric_data` - Metric data with checksums
- `sync_status` - Sync operation status
- `sync_checkpoints` - Crash recovery checkpoints

## Configuration

Default database location: `~/.garmy/localdb/garmin_data.db`

SQLite configuration:
- WAL journal mode for better concurrency
- Foreign key constraints enabled
- Automatic checksum verification
- Configurable page size and cache

## Error Handling

- **Automatic retries** with exponential backoff
- **Checkpoint-based recovery** for interrupted syncs
- **Data integrity verification** with SHA256 checksums
- **User-level locking** for concurrent access safety

## Metrics Supported

All 11 Garmin Connect metrics:
- Sleep analysis (stages, SpO2, respiration)
- Heart rate (daily summaries, continuous data)
- Body Battery energy levels
- Stress measurements
- HRV (heart rate variability)
- Respiration data
- Training readiness
- Activities and workouts
- Steps and movement
- Calories burned
- Daily health summaries

## Performance

- **SQLite WAL mode** for concurrent reads
- **Batch processing** for efficient API usage
- **Configurable batch sizes** (default: 50 days)
- **Multi-threaded synchronization** 
- **Incremental updates** (only new/changed data)

## Examples

See `examples/localdb_demo.py` for complete usage examples.