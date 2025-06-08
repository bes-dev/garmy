# Garmy Examples

This directory contains practical examples demonstrating how to use Garmy for accessing Garmin Connect data.

## 🚀 Getting Started

### Prerequisites

1. **Install Garmy**:
   ```bash
   pip install garmy
   ```

2. **Optional Dependencies** (for enhanced examples):
   ```bash
   pip install rich tqdm  # For beautiful terminal output and progress bars
   ```

### Quick Start

1. **Basic authentication**:
   ```bash
   python examples/basic_auth.py
   ```

2. **Explore activities data**:
   ```bash
   python examples/activities_demo.py
   ```

3. **Analyze sleep data**:
   ```bash
   python examples/sleep_demo.py
   ```

4. **Comprehensive metrics sync**:
   ```bash
   python examples/metrics_sync_demo.py
   ```

5. **Sleep phases analysis with CSV export**:
   ```bash
   python examples/sleep_phases_analysis.py
   ```

## 📁 Example Files

### 🔐 `basic_auth.py`
**Purpose**: Basic authentication with Garmin Connect

**Features**:
- Email/password authentication
- User profile retrieval
- Authentication status checking
- MFA support

### 🏃‍♂️ `activities_demo.py`
**Purpose**: Activity data analysis

**Features**:
- Recent activities retrieval
- Activity filtering and analysis
- Performance metrics extraction
- Activity type breakdown

### 🛌 `sleep_demo.py`
**Purpose**: Sleep data analysis

**Features**:
- Sleep quality metrics
- Sleep stage breakdown
- Weekly sleep trends
- Sleep efficiency analysis

### 🔄 `metrics_sync_demo.py`
**Purpose**: Comprehensive metrics synchronization

**Features**:
- Multi-metric data collection
- Cross-metric analysis
- Data correlation insights
- Comprehensive health overview

### 📈 `sleep_phases_analysis.py`
**Purpose**: Advanced sleep phases analysis with CSV export

**Features**:
- Interactive date range selection
- Detailed sleep phase breakdown
- Progress tracking with tqdm
- CSV export for further analysis
- Statistical summaries

## 🛠 Usage Patterns

### Basic Authentication
```python
from garmy import AuthClient, APIClient

# Create clients
auth_client = AuthClient()
api_client = APIClient(auth_client=auth_client)

# Authenticate
auth_client.login("your@email.com", "password")
```

### Accessing Metrics
```python
# Get specific metric
sleep_data = api_client.metrics.get('sleep').get()
print(f"Sleep score: {sleep_data.overall_sleep_score}")

# Get multiple days
week_data = api_client.metrics.get('steps').list(days=7)
for day in week_data:
    print(f"{day.calendar_date}: {day.total_steps} steps")

# See available metrics
print("Available metrics:", list(api_client.metrics.keys()))
```

### Async Operations
```python
import asyncio

async def get_multiple_metrics():
    # Fetch multiple metrics concurrently
    sleep_task = api_client.metrics.get('sleep').get_async()
    hrv_task = api_client.metrics.get('hrv').get_async()
    
    sleep_data, hrv_data = await asyncio.gather(sleep_task, hrv_task)
    return sleep_data, hrv_data
```

## 📋 Requirements

- **Python 3.8+**
- **Garmin Connect account**
- **Compatible Garmin device** (for metric data)

### Optional Dependencies
- **rich** - For enhanced terminal output in examples
- **tqdm** - For progress bars in analysis scripts

## 🐛 Troubleshooting

### Common Issues

1. **Authentication fails**:
   - Check credentials
   - Verify internet connection
   - Ensure Garmin Connect account is active

2. **No data available**:
   - Ensure device has synced with Garmin Connect
   - Check that you have the required data type
   - Some metrics require specific device types

3. **Metric not found**:
   ```python
   # Check available metrics
   print("Available metrics:", list(api_client.metrics.keys()))
   ```

## 🔧 Environment Variables

For secure authentication in scripts, you can use environment variables:

```bash
export GARMIN_EMAIL="your_email@example.com"
export GARMIN_PASSWORD="your_password"
```

Then in your scripts:
```python
import os
auth_client.login(os.getenv('GARMIN_EMAIL'), os.getenv('GARMIN_PASSWORD'))
```

## 📄 License

These examples are part of Garmy and are licensed under the Apache License 2.0.