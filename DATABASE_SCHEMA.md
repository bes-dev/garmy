# Database Schema Architecture

This document describes the clean database schema architecture implemented in Garmy's health database system.

## 🏗️ Architecture Overview

The database schema is now **completely separated** from database implementation logic, providing:

- **📚 Self-documenting schema** with descriptions and metadata
- **🔍 Runtime validation** and introspection capabilities  
- **🚀 Evolution support** for future schema changes
- **🗺️ Clear mapping** from API data to database columns
- **🧹 Clean separation** of concerns

## 📁 Files

| File | Purpose |
|------|---------|
| `src/garmy/localdb/schema.py` | Centralized schema definition |
| `src/garmy/localdb/db.py` | Database implementation (uses schema) |
| `examples/schema_demo.py` | Schema architecture demonstration |

## 🗄️ Schema Definition

### Core Classes

```python
@dataclass
class TableDefinition:
    name: str                    # Table name
    sql: str                     # CREATE TABLE statement
    description: str             # Human-readable description  
    primary_key: List[str]       # Primary key columns
    indexes: List[str]           # Performance indexes

@dataclass  
class DatabaseSchema:
    version: SchemaVersion       # Schema version for migrations
    tables: List[TableDefinition] # All table definitions
    global_indexes: List[str]    # Cross-table indexes
```

### Current Schema (v1.0.0)

| Table | Purpose | Primary Key |
|-------|---------|-------------|
| `daily_metrics` | Legacy JSON storage | `(user_id, metric_date)` |
| `timeseries` | High-frequency data | `(user_id, metric_type, timestamp)` |
| `activities` | Activity records | `(user_id, activity_id)` |
| `daily_health_metrics` | Normalized daily data | `(user_id, metric_date)` |

## 🔄 Data Extraction

API data is extracted using direct attribute access in the sync process:

```python
# Example extraction in sync.py
def _extract_daily_summary_data(self, data: Any) -> Dict[str, Any]:
    return {
        'total_steps': getattr(data, 'total_steps', None),
        'resting_heart_rate': getattr(data, 'resting_heart_rate', None),
        'sleep_duration_hours': getattr(data, 'sleep_duration_hours', None),
        # ... direct attribute access
    }
```

## 🚀 Usage

### Schema Introspection

```python
from garmy.localdb.schema import get_schema_info, HEALTH_DB_SCHEMA

# Get schema information
info = get_schema_info()
print(f"Version: {info['version']}")
print(f"Tables: {info['total_tables']}")

# Access specific table
table = HEALTH_DB_SCHEMA.get_table("daily_health_metrics")
print(f"Description: {table.description}")
```

### Database Integration

```python
from garmy.localdb.db import HealthDB

db = HealthDB("health.db")

# Validate schema
is_valid = db.validate_schema()

# Get schema info from database
info = db.get_schema_info()
```

### Data Extraction

```python
# Direct attribute access in sync process
def extract_metrics(api_response):
    return {
        'total_steps': getattr(api_response, 'total_steps', None),
        'resting_heart_rate': getattr(api_response, 'resting_heart_rate', None)
    }
```

## 🎯 Benefits

### Before (Mixed Concerns)
```python
def _init_schema(self):
    # 120+ lines of hardcoded SQL strings
    conn.execute("""
        CREATE TABLE IF NOT EXISTS daily_health_metrics (
            user_id INTEGER NOT NULL,
            metric_date DATE NOT NULL,
            total_steps INTEGER,
            # ... 50+ more lines ...
        )
    """)
    # More hardcoded indexes...
```

### After (Clean Separation)
```python
def _init_schema(self):
    # Clean, maintainable implementation
    for statement in HEALTH_DB_SCHEMA.get_all_sql_statements():
        conn.execute(statement)
```

## 🔧 Schema Evolution

### Adding New Table

```python
NEW_TABLE = TableDefinition(
    name="wellness_metrics",
    description="Daily wellness and recovery metrics",
    primary_key=["user_id", "metric_date"],
    sql="""
        CREATE TABLE IF NOT EXISTS wellness_metrics (
            user_id INTEGER NOT NULL,
            metric_date DATE NOT NULL,
            stress_score INTEGER,
            recovery_score INTEGER,
            PRIMARY KEY (user_id, metric_date)
        )
    """,
    indexes=[
        "CREATE INDEX IF NOT EXISTS idx_wellness_stress ON wellness_metrics(stress_score)"
    ]
)

# Add to schema
HEALTH_DB_SCHEMA.tables.append(NEW_TABLE)
```

### Version Migration (Future)

```python
def migrate_v1_to_v2():
    """Example migration function."""
    statements = get_migration_statements(
        SchemaVersion.V1_0_0, 
        SchemaVersion.V2_0_0
    )
    for stmt in statements:
        conn.execute(stmt)
```

## 🧪 Testing

```python
def test_schema_completeness():
    """Test that all expected tables exist."""
    db = HealthDB(":memory:")
    
    expected_tables = set(get_table_names())
    actual_tables = set(/* get from db */)
    
    assert expected_tables == actual_tables
```

## 🎉 Result

The schema is now:

✅ **Self-documenting** - Each table has clear purpose and description  
✅ **Maintainable** - Single source of truth for all schema changes  
✅ **Testable** - Easy to validate and introspect  
✅ **Evolvable** - Built-in support for migrations and versioning  
✅ **Clean** - Complete separation from database implementation logic

Run `python examples/schema_demo.py` to see the new architecture in action!