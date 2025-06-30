# Quick Start Guide

Get up and running with Garmy in minutes.

## 🚀 Installation

### Standard Installation
```bash
pip install garmy
```

### With Optional Features
```bash
# For local database functionality
pip install garmy[localdb]

# For MCP server functionality (AI assistants)
pip install garmy[mcp]

# For everything
pip install garmy[all]
```

## 🔧 Basic Setup

### 1. Basic API Usage

```python
from garmy import AuthClient, APIClient

# Create clients
auth_client = AuthClient()
api_client = APIClient(auth_client=auth_client)

# Login
auth_client.login("your_email@garmin.com", "your_password")

# Get today's training readiness
readiness = api_client.metrics.get('training_readiness').get()
print(f"Training Readiness Score: {readiness.score}/100")

# Get sleep data for specific date
sleep_data = api_client.metrics.get('sleep').get('2023-12-01')
print(f"Sleep Score: {sleep_data.sleep_duration_hours}")
```

### 2. Local Database Setup

```bash
# Sync recent health data to local database
garmy-sync sync --last-days 7

# Check sync status
garmy-sync status
```

### 3. AI Assistant Integration

```bash
# Start MCP server for AI assistants
garmy-mcp server --database health.db

# Show database info
garmy-mcp info --database health.db
```

## 📖 Next Steps

- **[LocalDB Guide](localdb-guide.md)** - Set up local data storage
- **[MCP Server Guide](mcp-server-guide.md)** - Integrate with AI assistants
- **[Database Schema](database-schema.md)** - Understand your data
- **[Examples](../examples/)** - See more examples

## 🆘 Need Help?

- Check the [examples directory](../examples/) for comprehensive usage examples
- Review the [database schema](database-schema.md) to understand available data
- See [Claude Desktop integration](claude-desktop-integration.md) for AI setup