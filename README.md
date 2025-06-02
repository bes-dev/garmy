# Garmy 🏃‍♂️

[![PyPI version](https://badge.fury.io/py/garmy.svg)](https://badge.fury.io/py/garmy)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Tests](https://github.com/bes-dev/garmy/workflows/Tests/badge.svg)](https://github.com/bes-dev/garmy/actions)

An AI-powered Python library for Garmin Connect API designed specifically for health data analysis and AI agent integration via Model Context Protocol (MCP). Build intelligent health assistants and data analysis tools with seamless access to Garmin's comprehensive fitness metrics.

**Inspired by [garth](https://github.com/matin/garth)** - This project was heavily inspired by the excellent garth library, building upon its foundation with enhanced modularity, type safety, and AI integration capabilities.

## 🎯 Key Features

- **🤖 AI-First Design**: Built specifically for AI health agents and intelligent assistants
- **🔌 MCP Integration**: Native Model Context Protocol support for seamless AI interactions
- **🏥 Health Analytics**: Advanced data analysis capabilities for fitness and wellness insights
- **📊 Rich Metrics**: Complete access to sleep, heart rate, stress, training readiness, and more
- **🗣️ Natural Language**: Query health data using conversational commands
- **⚡ Real-time Processing**: Async/await support for high-performance AI applications
- **🛡️ Type Safe**: Full type hints and runtime validation for reliable AI workflows
- **🔄 Auto-Discovery**: Automatic metric registration and API endpoint discovery

## 📦 Installation

### Standard Installation
```bash
pip install garmy
```

### With MCP Support (Recommended for AI Agents)
```bash
pip install garmy[mcp]
```

### Development Installation
```bash
git clone https://github.com/bes-dev/garmy.git
cd garmy
pip install -e ".[dev,mcp]"
```

## 🚀 Quick Start

### AI Agent Example (Recommended)

```python
from garmy import AuthClient, APIClient
import asyncio

# Create an AI health agent
async def health_agent():
    auth_client = AuthClient()
    api_client = APIClient(auth_client=auth_client)
    
    # Login using environment variables (secure for AI agents)
    await auth_client.login_async(
        email=os.getenv('GARMIN_EMAIL'),
        password=os.getenv('GARMIN_PASSWORD')
    )
    
    # AI agent can now analyze multiple health metrics concurrently
    sleep_task = api_client.metrics.get('sleep').get_async()
    readiness_task = api_client.metrics.get('training_readiness').get_async()
    hrv_task = api_client.metrics.get('hrv').get_async()
    
    sleep_data, readiness_data, hrv_data = await asyncio.gather(
        sleep_task, readiness_task, hrv_task
    )
    
    # AI analysis logic here
    health_score = analyze_health_trends(sleep_data, readiness_data, hrv_data)
    return health_score

# Run AI health agent
health_insights = asyncio.run(health_agent())
```

### Basic Usage

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

# Get multiple days of data
weekly_steps = api_client.metrics['steps'].list(days=7)
```

### Async Usage

```python
import asyncio
from garmy import AuthClient, APIClient

async def main():
    auth_client = AuthClient()
    api_client = APIClient(auth_client=auth_client)
    
    # Login
    await auth_client.login_async("your_email@garmin.com", "your_password")
    
    # Get multiple metrics concurrently
    sleep_task = api_client.metrics.get('sleep').get_async()
    hr_task = api_client.metrics.get('heart_rate').get_async()
    
    sleep_data, hr_data = await asyncio.gather(sleep_task, hr_task)

asyncio.run(main())
```

## 📊 Available Metrics

Garmy provides access to a comprehensive set of Garmin Connect metrics:

| Metric | Description | Example Usage |
|--------|-------------|---------------|
| `sleep` | Sleep tracking data including stages and scores | `api_client.metrics.get('sleep').get()` |
| `heart_rate` | Daily heart rate statistics | `api_client.metrics.get('heart_rate').get()` |
| `stress` | Stress level measurements | `api_client.metrics.get('stress').get()` |
| `steps` | Daily step counts and goals | `api_client.metrics.get('steps').list(days=7)` |
| `training_readiness` | Training readiness scores and factors | `api_client.metrics.get('training_readiness').get()` |
| `body_battery` | Body battery energy levels | `api_client.metrics.get('body_battery').get()` |
| `hrv` | Heart rate variability data | `api_client.metrics.get('hrv').get()` |
| `respiration` | Respiration rate measurements | `api_client.metrics.get('respiration').get()` |
| `calories` | Daily calorie burn data | `api_client.metrics.get('calories').get()` |
| `activities` | Activity summaries and details | `api_client.metrics.get('activities').list(days=30)` |
| `daily_summary` | Comprehensive daily health summary | `api_client.metrics.get('daily_summary').get()` |

## 🤖 AI Health Agent Integration (MCP)

Garmy is specifically designed for building **AI health agents** and intelligent assistants through native **Model Context Protocol (MCP)** integration. Transform your Garmin health data into actionable insights using natural language interactions.

### What Makes Garmy AI-First?

Garmy isn't just an API wrapper – it's a complete AI health agent platform that enables:

- **🧠 Intelligent Health Analysis**: AI-powered insights into sleep patterns, training readiness, and recovery
- **🗣️ Natural Language Queries**: Ask questions like "How was my sleep quality this week?" or "Am I ready for training today?"
- **📊 Predictive Analytics**: Build AI models that predict optimal training times, recovery needs, and health trends
- **🔄 Real-time Monitoring**: Create AI agents that continuously monitor health metrics and provide recommendations
- **🎨 Custom Health Dashboards**: Generate AI-driven visualizations and reports tailored to individual health goals
- **📱 Multi-modal Integration**: Combine Garmin data with other health sources for comprehensive AI analysis

### MCP Installation

```bash
# Install Garmy with MCP support
pip install garmy[mcp]

# Verify installation
garmy-mcp --help
```

### MCP Server Setup

#### Option 1: Command Line Interface

```bash
# Start MCP server for Claude Desktop (STDIO transport)
garmy-mcp serve --transport stdio

# Start HTTP server for web clients
garmy-mcp serve --transport http --port 8080

# Show server information
garmy-mcp info

# List available metrics
garmy-mcp metrics

# Test server configuration
garmy-mcp test
```

#### Option 2: Programmatic Usage

```python
from garmy.mcp import GarmyMCPServer, MCPConfig

# Create and configure server
config = MCPConfig.for_production()
server = GarmyMCPServer(config)

# Run server
server.run(transport="stdio")  # For Claude Desktop
server.run(transport="http", port=8080)  # For HTTP clients
```

### Claude Desktop Configuration

#### Secure Setup (Recommended)

Add this to your Claude Desktop MCP configuration file:

```json
{
  "mcpServers": {
    "garmy": {
      "command": "/path/to/your/venv/bin/python",
      "args": ["-m", "garmy.mcp", "serve", "--transport", "stdio"],
      "env": {
        "GARMIN_EMAIL": "your_email@example.com",
        "GARMIN_PASSWORD": "your_password",
        "GARMY_MCP_DEBUG": "false",
        "GARMY_MCP_CACHE_ENABLED": "true"
      }
    }
  }
}
```

#### Configuration File Locations

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

### Authentication Options

Garmy MCP supports multiple authentication methods:

#### 1. Environment Variables (Most Secure)
```bash
export GARMIN_EMAIL="your_email@example.com"
export GARMIN_PASSWORD="your_password"
```
- ✅ Credentials never pass through AI servers
- ✅ Most secure method
- ✅ Use with: *"Auto-login to Garmin Connect"*

#### 2. Manual Input (Less Secure)
- ⚠️ Credentials may be visible to AI servers
- ⚠️ Use only when necessary
- ⚠️ Use with: *"Log into Garmin Connect with email [email] and password [password]"*

### AI Health Agent Commands

Once configured, your AI health agent can interact with Garmin data using natural language. Here are examples of what your AI assistant can do:

#### Intelligent Health Monitoring
- *"Analyze my recovery patterns and tell me if I should train today"*
- *"What's my sleep efficiency trend over the past month?"*
- *"Create a personalized training plan based on my readiness scores"*
- *"Identify correlations between my stress and sleep quality"*
- *"Generate a health report with actionable insights"*

#### Predictive Health Analytics
- *"Predict my optimal training windows for next week"*
- *"What factors are affecting my sleep quality most?"*
- *"Alert me when my recovery metrics indicate overtraining"*
- *"Build a model to predict my daily energy levels"*

#### Conversational Health Queries
- *"How am I progressing towards my fitness goals?"*
- *"What's unusual about my health data this week?"*
- *"Compare my current training load to last month"*
- *"Should I adjust my sleep schedule based on my data?"*

#### Smart Data Export & Visualization
- *"Create an interactive dashboard of my health metrics"*
- *"Export my data in a format suitable for machine learning"*
- *"Generate a health summary for my doctor"*
- *"Build charts showing my progress over time"*

### MCP Configuration Options

#### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GARMIN_EMAIL` | Garmin Connect email | None |
| `GARMIN_PASSWORD` | Garmin Connect password | None |
| `GARMY_MCP_DEBUG` | Enable debug logging | `false` |
| `GARMY_MCP_CACHE_ENABLED` | Enable data caching | `false` |
| `GARMY_MCP_CACHE_SIZE` | Cache size limit | `100` |
| `GARMY_MCP_MAX_HISTORY_DAYS` | Max historical data | `365` |
| `GARMY_MCP_DEFAULT_ANALYSIS_PERIOD` | Default analysis period | `30` |

#### Configuration Presets

```python
from garmy.mcp.config import MCPConfig

# Development setup
config = MCPConfig.for_development()

# Production setup  
config = MCPConfig.for_production()

# Minimal setup
config = MCPConfig.minimal()
```

### Troubleshooting MCP

#### Common Issues

1. **"Server not responding"**
   ```bash
   # Check if server is running
   garmy-mcp test
   
   # Restart with debug mode
   GARMY_MCP_DEBUG=true garmy-mcp serve --transport stdio
   ```

2. **"Authentication failed"**
   ```bash
   # Verify credentials
   echo $GARMIN_EMAIL
   echo $GARMIN_PASSWORD
   
   # Test authentication
   garmy-mcp test --auth
   ```

3. **"No data available"**
   ```bash
   # Check available metrics
   garmy-mcp metrics
   
   # Verify date range
   garmy-mcp test --date 2023-12-01
   ```

#### Debug Mode

Enable debug logging for troubleshooting:

```bash
# Enable debug mode
export GARMY_MCP_DEBUG=true

# Run server with debug output
garmy-mcp serve --transport stdio --debug
```

## 📊 AI Health Data Analysis

### Building AI Health Models

```python
from garmy import APIClient, AuthClient
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler

# Setup AI health analysis pipeline
auth_client = AuthClient()
api_client = APIClient(auth_client=auth_client)
auth_client.login("email", "password")

# Gather comprehensive health data for AI model
async def build_health_dataset(days=90):
    # Collect multiple health metrics concurrently
    tasks = [
        api_client.metrics.get('sleep').list_async(days=days),
        api_client.metrics.get('training_readiness').list_async(days=days),
        api_client.metrics.get('hrv').list_async(days=days),
        api_client.metrics.get('stress').list_async(days=days),
        api_client.metrics.get('body_battery').list_async(days=days)
    ]
    
    sleep_data, readiness_data, hrv_data, stress_data, battery_data = await asyncio.gather(*tasks)
    
    # Build comprehensive health dataset
    health_df = pd.DataFrame()
    # ... merge and process data for AI model training
    
    return health_df

# Train AI model to predict training readiness
def train_readiness_predictor(health_df):
    features = ['sleep_score', 'hrv_rmssd', 'stress_avg', 'body_battery_drained']
    X = health_df[features]
    y = health_df['training_readiness_score']
    
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X, y)
    
    return model

# AI-powered health insights
def generate_health_insights(model, current_metrics):
    predicted_readiness = model.predict([current_metrics])[0]
    
    insights = {
        'readiness_prediction': predicted_readiness,
        'recommendation': 'high_intensity' if predicted_readiness > 75 else 'recovery',
        'confidence': model.score(X_test, y_test)
    }
    
    return insights
```

### AI-Powered Health Monitoring

```python
# Create an AI health monitoring agent
class HealthMonitoringAgent:
    def __init__(self, api_client):
        self.api_client = api_client
        self.health_model = self.load_trained_model()
    
    async def daily_health_check(self):
        """Perform daily AI-powered health analysis"""
        # Get today's metrics
        today_data = await self.get_current_metrics()
        
        # AI analysis
        health_score = self.health_model.predict_health_score(today_data)
        recommendations = self.generate_recommendations(health_score, today_data)
        alerts = self.check_health_alerts(today_data)
        
        return {
            'health_score': health_score,
            'recommendations': recommendations,
            'alerts': alerts,
            'insights': self.generate_insights(today_data)
        }
    
    def generate_recommendations(self, health_score, data):
        """AI-generated personalized health recommendations"""
        if health_score > 80:
            return "Great day for high-intensity training!"
        elif health_score > 60:
            return "Moderate activity recommended. Focus on technique."
        else:
            return "Prioritize recovery today. Light movement only."
    
    async def weekly_health_report(self):
        """Generate comprehensive AI health report"""
        week_data = await self.api_client.metrics.get('daily_summary').list_async(days=7)
        
        # AI trend analysis
        trends = self.analyze_trends(week_data)
        predictions = self.predict_next_week(week_data)
        
        return self.format_health_report(trends, predictions)

# Usage
agent = HealthMonitoringAgent(api_client)
daily_insights = await agent.daily_health_check()
weekly_report = await agent.weekly_health_report()
```

## 🧑‍💻 Development

### Running Examples

Check out the `examples/` directory for comprehensive usage examples:

```bash
# Basic authentication example
python examples/basic_auth.py

# Sleep analysis demo
python examples/sleep_demo.py

# Training readiness analysis
python examples/training_readiness_demo.py

# Comprehensive metrics sync
python examples/metrics_sync_demo.py

# MCP server demo
python examples/mcp_integration_demo.py
```

### Adding Custom Metrics

Garmy's modular architecture makes it easy to add new metrics:

```python
from dataclasses import dataclass
from garmy.core.base import BaseMetric

@dataclass
class CustomMetric(BaseMetric):
    endpoint_path = "/usersummary-service/stats/custom/{date}"

    custom_field: int
    timestamp: str
    
    def validate(self) -> bool:
        """Custom validation logic"""
        return self.custom_field > 0
```

### Configuration

Customize Garmy behavior with configuration:

```python
from garmy.core.config import set_config, GarmyConfig

# Create custom configuration
config = GarmyConfig(
    request_timeout=30,
    retries=3,
    max_workers=10,
    default_user_agent="MyApp/1.0"
)

# Apply configuration
set_config(config)

# Or use environment variables
import os
os.environ['GARMY_REQUEST_TIMEOUT'] = '30'
os.environ['GARMY_MAX_WORKERS'] = '10'
```

### Testing

```bash
# Install development dependencies
make install-dev

# Run all tests
make test

# Run specific test modules
make test-core      # Core functionality
make test-auth      # Authentication
make test-metrics   # Metrics
make test-mcp       # MCP server

# Check code quality
make lint
make quick-check
```

## 🔧 Advanced Usage

### Async Operations

```python
import asyncio
from garmy import APIClient, AuthClient

async def analyze_weekly_data():
    auth_client = AuthClient()
    api_client = APIClient(auth_client=auth_client)
    
    # Async login
    await auth_client.login_async("email", "password")
    
    # Fetch multiple metrics concurrently
    tasks = [
        api_client.metrics.get('sleep').list_async(days=7),
        api_client.metrics.get('steps').list_async(days=7),
        api_client.metrics.get('stress').list_async(days=7)
    ]
    
    sleep_data, steps_data, stress_data = await asyncio.gather(*tasks)
    
    return {
        'sleep': sleep_data,
        'steps': steps_data,
        'stress': stress_data
    }

# Run async analysis
data = asyncio.run(analyze_weekly_data())
```

### Custom Error Handling

```python
from garmy.core.exceptions import APIError, AuthError, GarmyError

try:
    auth_client.login("wrong_email", "wrong_password")
except AuthError as e:
    print(f"Authentication failed: {e}")
except APIError as e:
    print(f"API error: {e}")
except GarmyError as e:
    print(f"General Garmy error: {e}")
```

### Rate Limiting & Retries

```python
from garmy.core.config import set_config, GarmyConfig

# Configure retry behavior
config = GarmyConfig(
    retries=5,
    backoff_factor=1.0,
    max_workers=5  # Limit concurrent requests
)
set_config(config)
```

## 🛡️ Security for AI Health Applications

### AI Agent Security Best Practices

1. **Environment Variables**: Essential for AI agents - store credentials securely outside code
2. **MCP Security**: Use environment variables in MCP configuration to prevent credential exposure to AI servers
3. **OAuth Token Management**: Garmy handles OAuth tokens securely with automatic refresh for long-running AI agents
4. **HTTPS Only**: All communications use HTTPS with certificate verification
5. **AI Data Privacy**: Health data never leaves your local environment unless explicitly exported
6. **Secure AI Pipelines**: Design AI workflows that protect sensitive health information

### Best Practices

```python
import os
from garmy import AuthClient

# ✅ Good: Use environment variables
email = os.getenv('GARMIN_EMAIL')
password = os.getenv('GARMIN_PASSWORD')

# ❌ Bad: Hardcode credentials
# email = "your_email@example.com"
# password = "your_password"

auth_client = AuthClient()
auth_client.login(email, password)
```

## 📝 API Reference

### Core Classes

- **`AuthClient`**: Handles authentication and session management
- **`APIClient`**: Main interface for accessing Garmin Connect data
- **`MetricAccessor`**: Provides access to specific metrics
- **`GarmyMCPServer`**: MCP server for AI assistant integration

### Configuration Classes

- **`GarmyConfig`**: Main configuration class
- **`MCPConfig`**: MCP server configuration
- **`ConfigManager`**: Configuration management utilities

### Metrics Classes

Each metric has its own dataclass with type-safe fields. Examples:
- **`SleepData`**: Sleep tracking information
- **`HeartRateData`**: Heart rate statistics
- **`StepsData`**: Step count and goals
- **`TrainingReadinessData`**: Training readiness scores

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](DEVELOPMENT.md) for details.

### Development Setup

```bash
# Clone repository
git clone https://github.com/bes-dev/garmy.git
cd garmy

# Install in development mode
make install-dev

# Run quality checks
make ci
```

### Submitting Changes

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-feature`
3. Make your changes
4. Run tests: `make ci`
5. Submit a pull request

## 🙏 Acknowledgments

Garmy was heavily inspired by the excellent [garth](https://github.com/matin/garth) library by [Matin Tamizi](https://github.com/matin). We're grateful for the foundational work that made this project possible. Garmy builds upon garth's concepts with:

- Enhanced modularity and extensibility
- Full type safety with mypy compliance
- Model Context Protocol (MCP) integration for AI assistants
- Comprehensive async/await support
- Auto-discovery system for metrics
- Modern Python architecture and testing practices

Special thanks to the garth project and its contributors for pioneering accessible Garmin Connect API access.

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## 👨‍💻 Author

**bes-dev** - [GitHub Profile](https://github.com/bes-dev)

## 🔗 Links

- **Documentation**: [DEVELOPMENT.md](DEVELOPMENT.md)
- **Examples**: [examples/](examples/)
- **Issues**: [GitHub Issues](https://github.com/bes-dev/garmy/issues)
- **PyPI**: [https://pypi.org/project/garmy/](https://pypi.org/project/garmy/)

---

*Garmy makes Garmin Connect data accessible with modern Python practices, type safety, and AI assistant integration via MCP.*