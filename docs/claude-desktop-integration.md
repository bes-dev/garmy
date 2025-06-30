# Claude Desktop Integration

Complete guide to integrating Garmy's MCP server with Claude Desktop for AI-powered health data analysis.

## 🎯 Overview

Claude Desktop integration allows you to have natural conversations with Claude about your health data, enabling:
- **Natural language queries** about your health metrics
- **Trend analysis** and pattern recognition
- **Health insights** and recommendations
- **Data exploration** without writing SQL

## 🚀 Quick Setup

### 1. Prerequisites
```bash
# Install Garmy with MCP support
pip install garmy[mcp]

# Sync your health data
garmy-sync sync --last-days 30
```

### 2. Verify MCP Server Works
```bash
# Test the server
garmy-mcp info --database health.db

# Start server to verify it works
garmy-mcp server --database health.db --verbose
```

### 3. Configure Claude Desktop

#### Find Configuration File
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

#### Add Garmy Configuration
```json
{
  "mcpServers": {
    "garmy-localdb": {
      "command": "garmy-mcp",
      "args": ["server", "--database", "/full/path/to/health.db", "--max-rows", "500"]
    }
  }
}
```

### 4. Restart Claude Desktop
- Completely quit Claude Desktop
- Restart the application
- Look for the 🔌 (plug) icon indicating MCP connection

## ⚙️ Configuration Options

### Basic Configuration
```json
{
  "mcpServers": {
    "garmy-localdb": {
      "command": "garmy-mcp",
      "args": ["server", "--database", "/Users/yourname/health.db"]
    }
  }
}
```

### Production Configuration (Restrictive)
```json
{
  "mcpServers": {
    "garmy-localdb": {
      "command": "garmy-mcp",
      "args": [
        "server",
        "--database", "/path/to/health.db",
        "--max-rows", "100",
        "--max-rows-absolute", "500"
      ]
    }
  }
}
```

### Development Configuration (Verbose)
```json
{
  "mcpServers": {
    "garmy-localdb": {
      "command": "garmy-mcp",
      "args": [
        "server",
        "--database", "/path/to/health.db",
        "--max-rows", "1000",
        "--enable-query-logging",
        "--verbose"
      ]
    }
  }
}
```

### Using Environment Variables
```json
{
  "mcpServers": {
    "garmy-localdb": {
      "command": "garmy-mcp",
      "args": ["server", "--max-rows", "500"],
      "env": {
        "GARMY_DB_PATH": "/full/path/to/health.db"
      }
    }
  }
}
```

## 💬 Example Conversations

### Getting Started
**You:** "What health data do I have available?"

**Claude:** *Uses `explore_database_structure()` to show available tables and data*

### Sleep Analysis
**You:** "How has my sleep been over the last month?"

**Claude:** *Uses `execute_sql_query()` to analyze sleep patterns*

```sql
SELECT 
    metric_date,
    sleep_duration_hours,
    deep_sleep_percentage,
    rem_sleep_percentage
FROM daily_health_metrics 
WHERE user_id = 1 
    AND metric_date >= date('now', '-30 days')
    AND sleep_duration_hours IS NOT NULL
ORDER BY metric_date DESC
```

### Activity Analysis
**You:** "What are my most common workouts and their intensity?"

**Claude:** *Analyzes activities table*

```sql
SELECT 
    activity_name,
    COUNT(*) as workout_count,
    AVG(avg_heart_rate) as avg_heart_rate,
    AVG(training_load) as avg_training_load
FROM activities 
WHERE user_id = 1 
    AND activity_date >= date('now', '-90 days')
GROUP BY activity_name
ORDER BY workout_count DESC
```

### Health Correlations
**You:** "Is there a relationship between my stress levels and sleep quality?"

**Claude:** *Performs correlation analysis*

```sql
SELECT 
    metric_date,
    avg_stress_level,
    sleep_duration_hours,
    deep_sleep_percentage
FROM daily_health_metrics 
WHERE user_id = 1 
    AND avg_stress_level IS NOT NULL 
    AND sleep_duration_hours IS NOT NULL
    AND metric_date >= date('now', '-60 days')
ORDER BY metric_date
```

### Quick Health Summary
**You:** "Give me a quick health summary for the last week"

**Claude:** *Uses `get_health_summary(user_id=1, days=7)`*

## 🔍 Available Tools for Claude

When properly configured, Claude has access to these tools:

### 🔍 Discovery Tools
- **`explore_database_structure()`** - See what health data is available
- **`get_table_details(table_name)`** - Understand table structure and sample data

### 📊 Analysis Tools
- **`execute_sql_query(query, params)`** - Run custom SQL queries for analysis
- **`get_health_summary(user_id, days)`** - Get quick health overview

### 📚 Reference
- **`health_data_guide()`** - Complete guide to the health data structure

## 🎨 Best Practices

### 1. Start with Exploration
```
"What health data do I have available? Show me the database structure."
```

### 2. Ask for Specific Analysis
```
"Analyze my sleep patterns over the last 30 days. Look for trends in sleep duration and quality."
```

### 3. Request Correlations
```
"Is there a correlation between my step count and sleep quality?"
```

### 4. Get Actionable Insights
```
"Based on my health data, what recommendations do you have for improving my recovery?"
```

### 5. Explore Different Time Periods
```
"Compare my fitness metrics from this month versus last month."
```

## 🛠️ Troubleshooting

### Claude Shows No MCP Connection

1. **Check Configuration File Location**
   ```bash
   # macOS
   ls -la ~/Library/Application\ Support/Claude/claude_desktop_config.json
   
   # Linux  
   ls -la ~/.config/Claude/claude_desktop_config.json
   ```

2. **Validate JSON Syntax**
   ```bash
   # Use jq to validate JSON
   cat claude_desktop_config.json | jq .
   ```

3. **Check Database Path**
   ```bash
   # Verify database exists and is readable
   garmy-mcp info --database /full/path/to/health.db
   ```

4. **Test MCP Server Manually**
   ```bash
   # Run the exact command from your config
   garmy-mcp server --database /path/to/health.db --max-rows 500
   ```

### Claude Can't Access Health Data

1. **Check MCP Server Logs**
   ```bash
   # Enable verbose logging
   garmy-mcp server --database health.db --verbose --enable-query-logging
   ```

2. **Verify Database Permissions**
   ```bash
   # Check file permissions
   ls -la health.db
   
   # Ensure read access
   chmod 644 health.db
   ```

3. **Test Database Content**
   ```bash
   # Verify data exists
   garmy-mcp info --database health.db
   ```

### Performance Issues

1. **Reduce Row Limits**
   ```json
   {
     "args": ["server", "--database", "/path/to/health.db", "--max-rows", "100"]
   }
   ```

2. **Enable Query Logging to Monitor Performance**
   ```json
   {
     "args": ["server", "--database", "/path/to/health.db", "--enable-query-logging"]
   }
   ```

## 🔧 Advanced Configuration

### Multiple Health Databases
```json
{
  "mcpServers": {
    "garmy-personal": {
      "command": "garmy-mcp",
      "args": ["server", "--database", "/path/to/personal_health.db"]
    },
    "garmy-family": {
      "command": "garmy-mcp", 
      "args": ["server", "--database", "/path/to/family_health.db"]
    }
  }
}
```

### Custom Security Settings
```json
{
  "mcpServers": {
    "garmy-localdb": {
      "command": "garmy-mcp",
      "args": [
        "server",
        "--database", "/path/to/health.db",
        "--max-rows", "50",
        "--max-rows-absolute", "200"
      ]
    }
  }
}
```

## 📊 Example Health Insights

With proper setup, you can ask Claude questions like:

- "What's my average sleep duration and how has it changed over time?"
- "Show me my most challenging workouts based on heart rate and training load"
- "Are there patterns in my stress levels throughout the week?"
- "How does my step count correlate with my sleep quality?"
- "What days do I have the best training readiness scores?"
- "Analyze my heart rate variability trends"
- "Compare my activity levels between weekdays and weekends"

## 🔗 Related Documentation

- **[MCP Server Guide](mcp-server-guide.md)** - Complete MCP server documentation
- **[MCP Tools Reference](mcp-tools-reference.md)** - Detailed tool documentation
- **[Database Schema](database-schema.md)** - Understanding your health data
- **[LocalDB Guide](localdb-guide.md)** - Setting up data synchronization