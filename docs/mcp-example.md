# MCP Usage Example

Complete walkthrough from data synchronization to AI analysis with Claude Desktop.

## 🎯 Overview

This example shows the complete workflow:
1. **Sync health data** from Garmin Connect to local database
2. **Setup MCP server** for AI access
3. **Configure Claude Desktop** for health data analysis
4. **Analyze data** with natural language queries

## 📋 Prerequisites

```bash
# Install Garmy with all features
pip install garmy[all]

# Verify installation
garmy-sync --help
garmy-mcp --help
```

## Step 1: Sync Your Health Data 📊

### Initial Setup
```bash
# Sync last 30 days of health data
garmy-sync --db-path health.db sync --last-days 30
```

**What happens:**
- Downloads sleep, activity, heart rate, stress, and other metrics
- Stores data in local SQLite database (`health.db`)
- Creates normalized tables for efficient querying

**Example output:**
```
Syncing data from 2024-12-01 to 2024-12-30
Enter your Garmin Connect credentials:
Email: your_email@garmin.com
Password: [hidden]
Connecting to Garmin Connect...
Syncing metrics: DAILY_SUMMARY, SLEEP, ACTIVITIES, BODY_BATTERY, STRESS, HEART_RATE, TRAINING_READINESS, HRV, RESPIRATION, STEPS, CALORIES

Sync completed!
  Completed: 287
  Skipped: 43
  Failed: 0
  Total tasks: 330
```

### Verify Your Data
```bash
# Check sync status
garmy-sync --db-path health.db status

# Show database information
garmy-mcp info --database health.db
```

## Step 2: Setup MCP Server 🤖

### Test MCP Server
```bash
# Start MCP server (test it works)
garmy-mcp server --database health.db --verbose
```

**Expected output:**
```
[06/30/25 14:29:43] INFO Starting MCP server 'Garmin Health Data Explorer' with transport 'stdio'
```

Press `Ctrl+C` to stop the test server.

### Configure for Claude Desktop

**macOS:** Edit `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** Edit `%APPDATA%\Claude\claude_desktop_config.json`
**Linux:** Edit `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "garmy-health": {
      "command": "garmy-mcp",
      "args": [
        "server",
        "--database", "/full/path/to/health.db",
        "--max-rows", "500"
      ]
    }
  }
}
```

**Important:** Use the **full absolute path** to your `health.db` file!

## Step 3: Configure Claude Desktop 🖥️

### Restart Claude Desktop
1. **Completely quit** Claude Desktop
2. **Restart** the application
3. Look for the **🔌 plug icon** indicating MCP connection

### Verify Connection
You should see the MCP connection indicator in Claude Desktop. If not, check:
- JSON syntax is correct
- Database path is absolute and correct
- File permissions allow reading `health.db`

## Step 4: Analyze Your Health Data 💬

Now you can have natural conversations with Claude about your health data!

### Getting Started Queries

**Explore what data you have:**
> "What health data do I have available? Show me the database structure."

**Claude will use** `explore_database_structure()` **and respond with:**
```
I can see you have comprehensive health data with 4 main tables:

📊 daily_health_metrics (30 records): Daily summaries including steps, sleep, heart rate, stress
🏃 activities (12 records): Individual workouts with performance metrics  
📈 timeseries (8,640 records): High-frequency heart rate, stress, body battery data
📋 sync_status (330 records): Data synchronization tracking

You have data spanning from 2024-12-01 to 2024-12-30.
```

### Sleep Analysis Examples

**Basic sleep overview:**
> "How has my sleep been over the last month?"

**Detailed sleep analysis:**
> "Analyze my sleep patterns. Show me average sleep duration, deep sleep percentage, and any trends over time."

**Sleep quality insights:**
> "What factors might be affecting my sleep quality? Look at correlations between sleep duration, stress levels, and activity."

### Activity and Fitness Analysis

**Workout summary:**
> "What are my most common workouts and how intense are they typically?"

**Performance trends:**
> "Show me my fitness progression over the last month. Look at heart rate trends, training load, and recovery patterns."

**Activity vs recovery:**
> "Is there a relationship between my workout intensity and my next-day recovery metrics like HRV and training readiness?"

### Health Correlations

**Stress and sleep:**
> "Is there a correlation between my daily stress levels and sleep quality?"

**Steps and energy:**
> "How does my daily step count relate to my body battery levels and energy throughout the day?"

**Weekly patterns:**
> "Do I have different health patterns on weekdays vs weekends? Compare my sleep, activity, and stress."

### Advanced Analysis

**Custom time periods:**
> "Compare my health metrics from the first week of December vs the last week. What changed?"

**Specific insights:**
> "What days did I have the best training readiness scores? What factors contributed to those high scores?"

**Data-driven recommendations:**
> "Based on my health data patterns, what recommendations do you have for improving my recovery and performance?"

## 📊 Example Claude Conversation

**You:** "What health data do I have available?"

**Claude:** Uses `explore_database_structure()` and shows available tables and data ranges.

**You:** "Analyze my sleep over the last 2 weeks"

**Claude:** Uses `execute_sql_query()` with:
```sql
SELECT 
    metric_date,
    sleep_duration_hours,
    deep_sleep_percentage,
    rem_sleep_percentage,
    light_sleep_percentage
FROM daily_health_metrics 
WHERE metric_date >= date('now', '-14 days')
    AND sleep_duration_hours IS NOT NULL
ORDER BY metric_date
```

**Claude:** Provides analysis like:
- Average sleep duration: 7.3 hours
- Deep sleep average: 22%
- Trend: Sleep duration improving over time
- Best sleep: December 15th (8.2 hours, 28% deep)

**You:** "What correlates with my best sleep days?"

**Claude:** Analyzes multiple factors and finds patterns like:
- Lower stress days (< 25) correlate with better sleep
- Days with 8,000+ steps show 15% more deep sleep
- Workout days followed by better sleep quality

## 🔧 Troubleshooting

### MCP Server Issues

**Claude shows no MCP connection:**
```bash
# Test server manually
garmy-mcp server --database health.db --verbose

# Check database exists and is readable
ls -la health.db
garmy-mcp info --database health.db
```

**JSON configuration errors:**
```bash
# Validate JSON syntax
cat ~/.config/Claude/claude_desktop_config.json | python -m json.tool
```

### Data Issues

**No data available:**
```bash
# Check if sync worked
garmy-sync --db-path health.db status

# Re-sync if needed
garmy-sync --db-path health.db sync --last-days 7
```

**Missing specific metrics:**
```bash
# Check specific tables
sqlite3 health.db "SELECT COUNT(*) FROM daily_health_metrics WHERE sleep_duration_hours IS NOT NULL;"
```

## 🎯 Next Steps

- **[Database Schema](database-schema.md)** - Understand your data structure
- **[MCP Server Guide](mcp-server-guide.md)** - Advanced MCP configuration
- **[LocalDB Guide](localdb-guide.md)** - Advanced sync operations
- **[Claude Desktop Integration](claude-desktop-integration.md)** - Detailed Claude setup

## 💡 Pro Tips

1. **Regular syncing:** Set up daily sync with `garmy-sync sync --last-days 1`
2. **Data exploration:** Start with `explore_database_structure()` to understand your data
3. **Specific queries:** Be specific about time ranges and metrics for better analysis
4. **Multiple perspectives:** Ask Claude to analyze from different angles (weekly patterns, correlations, trends)
5. **Actionable insights:** Ask for recommendations based on your data patterns