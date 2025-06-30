# Garmy 🏃‍♂️

[![PyPI version](https://badge.fury.io/py/garmy.svg)](https://badge.fury.io/py/garmy)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Tests](https://github.com/bes-dev/garmy/workflows/Tests/badge.svg)](https://github.com/bes-dev/garmy/actions)

An AI-powered Python library for Garmin Connect API designed specifically for health data analysis and AI agent integration. Build intelligent health assistants and data analysis tools with seamless access to Garmin's comprehensive fitness metrics.

**Inspired by [garth](https://github.com/matin/garth)** - This project was heavily inspired by the excellent garth library, building upon its foundation with enhanced modularity, type safety, and AI integration capabilities.

## 🎯 Key Features

- **🤖 AI-First Design**: Built specifically for AI health agents and intelligent assistants
- **🏥 Health Analytics**: Advanced data analysis capabilities for fitness and wellness insights
- **📊 Rich Metrics**: Complete access to sleep, heart rate, stress, training readiness, and more
- **💾 Local Database**: Built-in SQLite database for local health data storage and sync
- **🖥️ CLI Tools**: Command-line interfaces for data synchronization and MCP server management
- **🤖 MCP Server**: Model Context Protocol server for AI assistant integration (Claude Desktop)
- **⚡ High Performance**: Optimized for high-performance AI applications
- **🛡️ Type Safe**: Full type hints and runtime validation for reliable AI workflows
- **🔄 Auto-Discovery**: Automatic metric registration and API endpoint discovery

## 📦 Installation

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

### Development Installation
```bash
git clone https://github.com/bes-dev/garmy.git
cd garmy
pip install -e ".[dev]"
```

## 🚀 Quick Start

### Basic API Usage

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

# Get sleep data for specific date
sleep_data = api_client.metrics.get('sleep').get('2023-12-01')
print(f"Sleep Score: {sleep_data[0].overall_sleep_score}")
```

### Local Database & CLI Tools

```bash
# Sync recent health data to local database
garmy-sync sync --last-days 7

# Check sync status
garmy-sync status

# Start MCP server for AI assistants
garmy-mcp server --database health.db

# Show database info
garmy-mcp info --database health.db

# Get configuration examples
garmy-mcp config
```

### AI Assistant Integration (Claude Desktop)

Add to your Claude Desktop configuration (`~/.claude_desktop_config.json`):

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

Now ask Claude: *"What health data do I have available? Analyze my sleep patterns over the last month."*

## 📊 Available Health Metrics

Garmy provides access to a comprehensive set of Garmin Connect metrics:

| Metric | Description | Example Usage |
|--------|-------------|---------------|
| `sleep` | Sleep tracking data including stages and scores | `api_client.metrics.get('sleep').get()` |
| `heart_rate` | Daily heart rate statistics | `api_client.metrics.get('heart_rate').get()` |
| `stress` | Stress level measurements | `api_client.metrics.get('stress').get()` |
| `steps` | Daily step counts and goals | `api_client.metrics.get('steps').list(days=7)` |
| `training_readiness` | Training readiness scores and factors | `api_client.metrics.get('training_readiness').get()` |
| `body_battery` | Body battery energy levels | `api_client.metrics.get('body_battery').get()` |
| `activities` | Activity summaries and details | `api_client.metrics.get('activities').list(days=30)` |

## 🧑‍💻 Architecture Overview

Garmy consists of three main modules:

### 🔌 **Core Library**
- **Garmin Connect API**: Type-safe access to all health metrics
- **High Performance**: Optimized concurrent operations
- **Auto-Discovery**: Automatic endpoint and metric detection

### 💾 **LocalDB Module** 
- **SQLite Storage**: Local database for health data persistence
- **Data Sync**: Robust synchronization with conflict resolution
- **CLI Tools**: `garmy-sync` for data management

### 🤖 **MCP Server Module**
- **AI Integration**: Model Context Protocol server for AI assistants
- **Secure Access**: Read-only database access with query validation
- **Claude Desktop**: Native integration with Claude Desktop
- **CLI Tools**: `garmy-mcp` for server management

## 📚 Documentation

### 📖 Getting Started
- **[Quick Start Guide](docs/quick-start.md)** - Get up and running in minutes
- **[Basic Examples](examples/README.md)** - Simple usage patterns

### 🏗️ Core Features  
- **[Available Metrics](#-available-health-metrics)** - All supported health metrics in this README

### 💾 Local Database
- **[LocalDB Guide](docs/localdb-guide.md)** - Complete local storage guide
- **[Database Schema](docs/database-schema.md)** - Schema and table structure

### 🤖 AI Integration
- **[MCP Usage Example](docs/mcp-example.md)** - Complete walkthrough from sync to AI analysis
- **[MCP Server Guide](docs/mcp-server-guide.md)** - AI assistant integration
- **[Claude Desktop Setup](docs/claude-desktop-integration.md)** - Step-by-step Claude integration

### 🔬 Advanced Usage
- **[Examples Directory](examples/)** - Comprehensive usage examples

## 🎯 Use Cases

### For AI Developers
```python
# Build AI health monitoring agents
from garmy import APIClient, AuthClient

def health_agent():
    auth_client = AuthClient()
    api_client = APIClient(auth_client=auth_client)
    
    # Login and get metrics
    auth_client.login(email, password)
    sleep_data = api_client.metrics.get('sleep').get()
    readiness_data = api_client.metrics.get('training_readiness').get()
    
    # AI analysis logic here
    return analyze_health_trends(sleep_data, readiness_data)
```

### For Data Analysts
```bash
# Local database analysis workflow
garmy-sync sync --last-days 90  # Sync 3 months of data
garmy-mcp server --database health.db  # Start MCP server
# Use Claude Desktop or Python to analyze trends, correlations, patterns
```

### For Health Researchers  
```python
# Large-scale health data collection
from garmy.localdb import SyncManager

sync_manager = SyncManager(db_path="research_data.db")
sync_manager.initialize(email, password)

# Collect comprehensive health dataset
stats = sync_manager.sync_range(
    user_id=1,
    start_date=date(2023, 1, 1),
    end_date=date.today(),
    metrics=[MetricType.SLEEP, MetricType.HRV, MetricType.STRESS]
)
```

## 🛡️ Security & Privacy

- **🔒 Local Data**: All health data stored locally in SQLite
- **🔐 Read-Only MCP**: AI assistants have read-only database access
- **🛡️ Query Validation**: SQL injection prevention and query limits
- **🔑 Secure Auth**: OAuth token management with automatic refresh
- **🚫 No Data Sharing**: Health data never leaves your local environment

## 🧪 Examples

Check out the `examples/` directory for comprehensive usage examples:

```bash
# Basic authentication and metrics
python examples/basic_usage.py

# Local database operations
python examples/localdb_demo.py

# MCP server configuration
python examples/mcp_server_example.py

# AI health analytics
python examples/ai_health_analytics.py
```

## 🔧 Development

### Running Tests
```bash
# Install development dependencies
make install-dev

# Run all tests
make test

# Run specific test modules
make test-core      # Core functionality
make test-localdb   # LocalDB module
make test-mcp       # MCP server

# Check code quality
make lint
make quick-check
```

### Adding Custom Metrics
```python
from dataclasses import dataclass
from garmy.core.base import BaseMetric

@dataclass
class CustomMetric(BaseMetric):
    endpoint_path = "/usersummary-service/stats/custom/{date}"
    
    custom_field: int
    timestamp: str
    
    def validate(self) -> bool:
        return self.custom_field > 0
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](docs/contributing.md) for details.

### Development Setup
```bash
git clone https://github.com/bes-dev/garmy.git
cd garmy
make install-dev
make ci  # Run quality checks
```

## 🙏 Acknowledgments

Garmy was heavily inspired by the excellent [garth](https://github.com/matin/garth) library by [Matin Tamizi](https://github.com/matin). We're grateful for the foundational work that made this project possible. Garmy builds upon garth's concepts with:

- Enhanced modularity and extensibility
- Full type safety with mypy compliance
- Auto-discovery system for metrics
- Local database integration
- MCP server for AI assistants
- Modern Python architecture and testing practices

Special thanks to the garth project and its contributors for pioneering accessible Garmin Connect API access.

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## 👨‍💻 Author

**bes-dev** - [GitHub Profile](https://github.com/bes-dev)

## 🔗 Links

- **[Documentation](docs/)** - Complete documentation
- **[PyPI Package](https://pypi.org/project/garmy/)** - Install via pip
- **[GitHub Issues](https://github.com/bes-dev/garmy/issues)** - Bug reports and feature requests
- **[Examples](examples/)** - Usage examples and tutorials

---

*Garmy makes Garmin Connect data accessible with modern Python practices, type safety, and AI assistant integration for building intelligent health applications.*