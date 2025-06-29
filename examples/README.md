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
   pip install rich  # For beautiful terminal output
   ```

### Quick Start

1. **Basic authentication**:
   ```bash
   python examples/basic_auth.py
   ```

2. **View your training readiness data**:
   ```bash
   python examples/training_readiness_demo.py
   ```

3. **Explore activities data**:
   ```bash
   python examples/activities_demo.py
   ```

4. **Analyze sleep data**:
   ```bash
   python examples/sleep_demo.py
   ```

5. **Heart rate analysis**:
   ```bash
   python examples/heart_rate_demo.py
   ```

6. **Comprehensive metrics sync**:
   ```bash
   python examples/metrics_sync_demo.py
   ```

7. **Sleep phases analysis with CSV export**:
   ```bash
   python examples/sleep_phases_analysis.py
   ```

8. **🏥 Health Database System (NEW!)**:
   ```bash
   python examples/health_db_demo.py
   ```

9. **🗄️ Database Schema Architecture (NEW!)**:
   ```bash
   python examples/schema_demo.py
   ```

## 📁 Example Files

### 🔐 `basic_auth.py`
**Purpose**: Basic authentication with Garmin Connect

**Features**:
- Email/password authentication
- User profile retrieval
- Authentication status checking

**Usage**:
```bash
python examples/basic_auth.py
```

### 📊 `training_readiness_demo.py`
**Purpose**: Training Readiness data access and analysis

**Features**:
- Current training readiness score
- Weekly trend analysis
- Readiness level interpretation
- Factor breakdown analysis

**Usage**:
```bash
python examples/training_readiness_demo.py
```

### 🏃‍♂️ `activities_demo.py`
**Purpose**: Activity data analysis

**Features**:
- Recent activities retrieval
- Activity filtering and analysis
- Performance metrics extraction
- Activity type breakdown

**Usage**:
```bash
python examples/activities_demo.py
```

### 🛌 `sleep_demo.py`
**Purpose**: Sleep data analysis

**Features**:
- Sleep quality metrics
- Sleep stage breakdown
- Weekly sleep trends
- Sleep efficiency analysis

**Usage**:
```bash
python examples/sleep_demo.py
```

### ❤️ `heart_rate_demo.py`
**Purpose**: Heart rate data analysis

**Features**:
- Daily heart rate statistics
- Heart rate zones analysis
- Resting heart rate trends

**Usage**:
```bash
python examples/heart_rate_demo.py
```

### 🔄 `metrics_sync_demo.py`
**Purpose**: Comprehensive metrics synchronization

**Features**:
- Multi-metric data collection
- Cross-metric analysis
- Data correlation insights
- Comprehensive health overview

**Usage**:
```bash
python examples/metrics_sync_demo.py
```

### 📈 `sleep_phases_analysis.py`
**Purpose**: Advanced sleep phases analysis with CSV export

**Features**:
- Interactive date range selection
- Detailed sleep phase breakdown
- Progress tracking with tqdm
- CSV export for further analysis
- Statistical summaries

**Usage**:
```bash
python examples/sleep_phases_analysis.py
```

### 💪 `body_battery_demo.py`
**Purpose**: Body Battery energy analysis

**Features**:
- Current Body Battery level
- Daily energy patterns
- Charging and draining analysis

### 🫁 `respiration_demo.py`
**Purpose**: Respiration rate monitoring

**Features**:
- Daily respiration rate data
- Breathing pattern analysis
- Sleep vs. active respiration comparison

### 😰 `stress_demo.py`
**Purpose**: Stress level monitoring

**Features**:
- Daily stress level tracking
- Stress pattern analysis
- Recovery time insights

### 🔥 `calories_demo.py`
**Purpose**: Calorie burn analysis

**Features**:
- Daily calorie expenditure
- Active vs. resting calories
- Calorie goal tracking

### 👣 `steps_demo.py`
**Purpose**: Step count and activity tracking

**Features**:
- Daily step counts
- Goal achievement tracking
- Movement pattern analysis

### ❤️‍🔥 `hrv_demo.py`
**Purpose**: Heart Rate Variability analysis

**Features**:
- HRV measurements
- Recovery indicators
- Training adaptation insights

### 📊 `daily_summary_demo.py`
**Purpose**: Comprehensive daily health summary

**Features**:
- All-in-one health overview
- Daily metrics compilation
- Health trend analysis

### 🏥 `health_db_demo.py` ⭐ **NEW!**
**Purpose**: Complete health database system demonstration

**Features**:
- **Database synchronization** with normalized schema
- **Progress tracking** with multiple display options (Rich, TQDM, logging)
- **Health analytics** with sleep, activity, and wellness insights
- **Data export** capabilities (JSON, CSV)
- **Advanced SQL queries** for health correlations
- **Real-time progress** updates during sync

**Usage**:
```bash
# Set your credentials
export GARMIN_EMAIL="your_email@example.com"
export GARMIN_PASSWORD="your_password"

# Run the comprehensive demo
python examples/health_db_demo.py
```

**What it demonstrates**:
- 📊 Different progress reporting styles
- 💾 Normalized database storage for efficient queries
- 📈 Health trends and correlations analysis
- 🏃‍♂️ Activity patterns and performance metrics
- 😴 Sleep quality analysis with phase breakdowns
- 📤 Data export for external analysis
- 🔍 Advanced SQL queries for health insights

### 🗄️ `schema_demo.py` ⭐ **NEW!**
**Purpose**: Database schema architecture demonstration

**Features**:
- **Clean schema separation** from database implementation logic
- **Centralized schema management** with version tracking
- **Schema validation** and introspection capabilities
- **Direct data extraction** using attribute access
- **Evolution support** for future schema changes
- **Self-documenting** schema with descriptions and metadata

**Usage**:
```bash
python examples/schema_demo.py
```

**What it demonstrates**:
- 🏗️ Structured schema definition with TableDefinition classes
- 📚 Comprehensive documentation for each table and column
- 🔍 Runtime schema validation and introspection
- 🔧 Direct attribute extraction from API responses to database
- 🚀 Foundation for schema migrations and evolution
- 🧹 Clean separation of concerns in database architecture

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

### Getting Help

- Check the main documentation
- Review error messages for specific guidance
- Ensure your device supports the requested metric type

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

## 🤝 Contributing

When contributing examples:

1. Include comprehensive docstrings
2. Add error handling
3. Test thoroughly with different data scenarios
4. Follow established patterns
5. Include usage instructions

## 📄 License

These examples are part of Garmy and are licensed under the Apache License 2.0.