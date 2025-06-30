# MCP Server Guide

Complete guide to Garmy's Model Context Protocol (MCP) server for AI assistant integration.

## 🎯 Overview

The Garmy MCP Server provides secure, read-only access to synchronized health data through the Model Context Protocol, enabling AI assistants like Claude to analyze health metrics safely.

## 🚀 Quick Start

### 1. Install MCP Dependencies
```bash
pip install garmy[mcp]
```

### 2. Prepare Health Data
```bash
# Sync recent health data first
garmy-sync sync --last-days 30
```

### 3. Start MCP Server
```bash
# Basic usage
garmy-mcp server --database health.db

# With custom configuration
garmy-mcp server --database health.db --max-rows 500 --enable-query-logging
```

### 4. Claude Desktop Integration
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

## 📋 Available Commands

### `garmy-mcp server`
Start the MCP server with specified configuration.

```bash
garmy-mcp server --database health.db [options]
```

**Configuration Options:**
- `--max-rows N`: Maximum rows per query (default: 1000, max: 5000)
- `--max-rows-absolute N`: Hard security limit (default: 5000, max: 10000)
- `--enable-query-logging`: Log SQL queries for debugging
- `--disable-strict-validation`: Relax SQL validation (not recommended)
- `--verbose`: Show detailed configuration and startup info

### `garmy-mcp info`
Display database information and available tools.

```bash
garmy-mcp info --database health.db
```

Shows:
- Database file size and accessibility
- Available tables with record counts
- MCP tools and their purposes
- Startup command suggestions

### `garmy-mcp config`
Show configuration examples for different use cases.

```bash
garmy-mcp config
```

## 🛠️ Available MCP Tools

### 🔍 Database Discovery

#### `explore_database_structure()`
**When to use:** Starting point for any health data analysis

Your first tool for understanding what health data is available. Always use this before running specific queries.

**Returns:**
- Available tables with descriptions and row counts
- Supported metric types
- Usage guidance

#### `get_table_details(table_name)`
**When to use:** When you need to understand the structure of a specific table

Use after `explore_database_structure` to see column details and sample data.

**Example:**
```python
get_table_details("daily_health_metrics")
```

### 📊 Data Analysis

#### `execute_sql_query(query, params)`
**When to use:** For specific data analysis using SQL queries

Main tool for querying any data from the database. Use it to analyze health metrics, activities, sync status, or find patterns across any tables.

**Security Features:**
- Only `SELECT` and `WITH` statements allowed
- Automatic row limiting (configurable)
- SQL injection prevention through parameterization
- Comprehensive validation

**Example Queries:**
```sql
-- Health metrics: Recent sleep trends
SELECT metric_date, sleep_duration_hours, deep_sleep_hours 
FROM daily_health_metrics 
WHERE user_id = 1 
ORDER BY metric_date DESC LIMIT 30

-- Activities: Workout analysis
SELECT activity_date, activity_name, duration_seconds/60 as minutes
FROM activities 
WHERE user_id = 1

-- Timeseries: Heart rate data
SELECT timestamp, value 
FROM timeseries 
WHERE metric_type = 'heart_rate' AND user_id = 1
```

#### `get_health_summary(user_id, days)`
**When to use:** For quick health overview without writing SQL

Ready-made summary of key health metrics over a specified period.

**Example:**
```python
get_health_summary(user_id=1, days=30)
```

### 📚 Documentation Resource

#### `health_data_guide()`
Complete guide to understanding and querying Garmin health data, including:
- Quick start workflow for new users
- Table descriptions with common query examples
- Available health metrics and their meanings
- Analysis tips and best practices

## ⚙️ Configuration Examples

### Production Configuration (Restrictive)
```bash
garmy-mcp server --database health.db \
  --max-rows 100 \
  --max-rows-absolute 500
```

### Development Configuration (Permissive with Logging)
```bash
garmy-mcp server --database health.db \
  --max-rows 2000 \
  --enable-query-logging \
  --verbose
```

### Debug Configuration (Relaxed Validation)
```bash
garmy-mcp server --database health.db \
  --disable-strict-validation \
  --enable-query-logging \
  --verbose
```

## 🔐 Security Features

### Query Validation
1. **Statement Type Validation**: Only `SELECT` and `WITH` allowed
2. **Keyword Filtering**: Blocks modification keywords (`INSERT`, `UPDATE`, etc.)
3. **Multi-Statement Prevention**: Prevents SQL injection via statement chaining
4. **Parameter Binding**: All user inputs are properly parameterized
5. **Row Limiting**: Automatic limits prevent excessive resource usage

### Database Access
- **Read-Only Connection**: Database opened in read-only mode
- **Input Sanitization**: Table names validated with regex patterns
- **Error Handling**: Comprehensive error catching and sanitization
- **Resource Management**: Automatic connection cleanup

## 📊 Health Data Analysis Examples

### Sleep Analysis
```sql
-- Get sleep trends over the last month
SELECT 
    metric_date,
    sleep_duration_hours,
    deep_sleep_percentage,
    rem_sleep_percentage
FROM daily_health_metrics 
WHERE user_id = 1 
    AND metric_date >= date('now', '-30 days')
    AND sleep_duration_hours IS NOT NULL
ORDER BY metric_date;
```

### Activity Performance
```sql
-- Analyze workout intensity and heart rate
SELECT 
    activity_date,
    activity_name,
    duration_seconds / 60.0 as duration_minutes,
    avg_heart_rate,
    training_load
FROM activities 
WHERE user_id = 1 
    AND activity_date >= date('now', '-7 days')
ORDER BY activity_date DESC;
```

### Stress and Recovery Correlation
```sql
-- Correlate stress levels with sleep quality
SELECT 
    metric_date,
    avg_stress_level,
    sleep_duration_hours,
    body_battery_high - body_battery_low as battery_drain,
    training_readiness_score
FROM daily_health_metrics 
WHERE user_id = 1 
    AND metric_date >= date('now', '-14 days')
    AND avg_stress_level IS NOT NULL
ORDER BY metric_date;
```

### Heart Rate Variability Trends
```sql
-- Track HRV patterns over time
SELECT 
    metric_date,
    hrv_weekly_avg,
    hrv_last_night_avg,
    hrv_status,
    resting_heart_rate
FROM daily_health_metrics 
WHERE user_id = 1 
    AND hrv_weekly_avg IS NOT NULL
    AND metric_date >= date('now', '-60 days')
ORDER BY metric_date;
```

## 🔧 Advanced Configuration

### Custom Configuration Class
```python
from garmy.mcp import MCPConfig, create_mcp_server
from pathlib import Path

# Create custom configuration
config = MCPConfig(
    db_path=Path("health.db"),
    max_rows=500,
    max_rows_absolute=2000,
    enable_query_logging=True,
    strict_validation=True
)

# Create server with custom config
mcp_server = create_mcp_server(config)
```

### Environment Variables
```bash
# Alternative to --database argument
export GARMY_DB_PATH="/path/to/health.db"
garmy-mcp server --max-rows 500
```

### Query Logging
When `--enable-query-logging` is enabled, you'll see detailed logs:

```
2024-06-30 12:00:00 - garmy.mcp.database - INFO - Executing query: SELECT * FROM daily_health_metrics LIMIT 1000
2024-06-30 12:00:00 - garmy.mcp.database - INFO - Parameters: [1]
2024-06-30 12:00:00 - garmy.mcp.database - INFO - Query returned 245 rows
```

## 🛠️ Troubleshooting

### Common Issues

1. **FastMCP Not Installed**
   ```bash
   pip install garmy[mcp]
   # or
   pip install fastmcp
   ```

2. **Database Not Found**
   ```bash
   # Ensure database path is correct
   garmy-mcp info --database health.db
   
   # Or set environment variable
   export GARMY_DB_PATH="/full/path/to/health.db"
   ```

3. **Permission Denied**
   ```bash
   # Check database file permissions
   ls -la health.db
   chmod 644 health.db  # If needed
   ```

4. **Query Validation Errors**
   ```bash
   # Use debug mode to see detailed errors
   garmy-mcp server --database health.db --verbose --enable-query-logging
   ```

### Debug Mode
```bash
# Enable maximum verbosity for troubleshooting
garmy-mcp server --database health.db \
  --verbose \
  --enable-query-logging \
  --disable-strict-validation
```

## 🔗 Related Documentation

- **[Claude Desktop Integration](claude-desktop-integration.md)** - Detailed Claude setup
- **[MCP Tools Reference](mcp-tools-reference.md)** - Complete tool documentation
- **[Database Schema](database-schema.md)** - Understanding the data structure
- **[LocalDB Guide](localdb-guide.md)** - Setting up local data storage