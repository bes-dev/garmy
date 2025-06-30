# Quick Start Guide

Get up and running with Garmy in just a few minutes.

## 🚀 Installation

### Basic Installation
```bash
pip install garmy
```

### With Optional Features
```bash
# For local database functionality
pip install garmy[localdb]

# For MCP server functionality
pip install garmy[mcp]

# For everything
pip install garmy[all]
```

### Development Installation
```bash
git clone https://github.com/bes-dev/garmy.git
cd garmy
pip install -e ".[dev]"
```

## 🎯 Basic Usage

### 1. Simple API Access

```python
from garmy import AuthClient, APIClient

# Create clients
auth_client = AuthClient()
api_client = APIClient(auth_client=auth_client)

# Login
auth_client.login("your_email@garmin.com", "your_password")

# Get today's training readiness
readiness = api_client.metrics.get('training_readiness').get()
print(f"Training Readiness Score: {readiness[0].score}/100")

# Get sleep data
sleep_data = api_client.metrics.get('sleep').get('2023-12-01')
print(f"Sleep Score: {sleep_data[0].overall_sleep_score}")
```

### 2. Local Database Storage

```bash
# Sync recent health data
garmy-sync sync --last-days 7

# Check sync status
garmy-sync status
```

```python
from garmy.localdb import SyncManager
from datetime import date, timedelta

# Initialize sync manager
sync_manager = SyncManager(db_path="my_health.db")
sync_manager.initialize("email@garmin.com", "password")

# Sync data
end_date = date.today()
start_date = end_date - timedelta(days=7)
stats = sync_manager.sync_range(user_id=1, start_date=start_date, end_date=end_date)

print(f"Synced: {stats['completed']} records")
```

### 3. AI Assistant Integration

```bash
# Start MCP server for AI assistants
garmy-mcp server --database health.db

# Get database info
garmy-mcp info --database health.db

# Show configuration examples
garmy-mcp config
```

## 🔧 Configuration

### Environment Variables
```bash
# For MCP server
export GARMY_DB_PATH="/path/to/health.db"

# For API access (optional)
export GARMIN_EMAIL="your_email@garmin.com"
export GARMIN_PASSWORD="your_password"
```

### Claude Desktop Integration
Add to `~/.claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "garmy-localdb": {
      "command": "garmy-mcp",
      "args": ["server", "--database", "/path/to/health.db", "--max-rows", "500"]
    }
  }
}
```

## 📊 Available Health Metrics

| Metric | Description | Example Usage |
|--------|-------------|---------------|
| `sleep` | Sleep tracking data | `api_client.metrics.get('sleep').get()` |
| `heart_rate` | Heart rate statistics | `api_client.metrics.get('heart_rate').get()` |
| `stress` | Stress measurements | `api_client.metrics.get('stress').get()` |
| `steps` | Daily step counts | `api_client.metrics.get('steps').list(days=7)` |
| `training_readiness` | Training readiness | `api_client.metrics.get('training_readiness').get()` |
| `body_battery` | Body battery levels | `api_client.metrics.get('body_battery').get()` |
| `activities` | Workouts and activities | `api_client.metrics.get('activities').list(days=30)` |

## 🔗 Next Steps

- **[LocalDB Guide](localdb-guide.md)** - Learn about local data storage
- **[MCP Server Guide](mcp-server-guide.md)** - Set up AI assistant integration  
- **[API Reference](api-reference.md)** - Explore all available methods
- **[Examples](examples/basic-usage.md)** - See more usage patterns

## 🆘 Getting Help

- **[GitHub Issues](https://github.com/bes-dev/garmy/issues)** - Report bugs or request features
- **[Documentation](README.md)** - Complete documentation index
- **[Contributing](contributing.md)** - Help improve Garmy