# Breaking Changes: Legacy Support Removal

## ⚠️ BREAKING CHANGES

This release removes **ALL backward compatibility** with legacy JSON storage. This is an intentional breaking change to simplify the codebase and eliminate maintenance overhead.

## 🗑️ Removed Components

### 1. Legacy JSON Storage System
**Removed:**
- `daily_metrics` table (JSON storage)
- `DAILY_METRICS` schema definition
- `HealthMetric` class wrapper
- `get_daily_metrics()` method
- `store_daily_metric()` method

### 2. Schema Changes
**Before (4 tables):**
```
- daily_metrics (JSON storage) ❌ REMOVED
- timeseries (High-frequency data) ✅ KEPT
- activities (Activity records) ✅ KEPT  
- daily_health_metrics (Normalized data) ✅ KEPT
```

**After (3 tables):**
```
- timeseries (High-frequency data) ✅
- activities (Activity records) ✅
- daily_health_metrics (Normalized data) ✅
```

## 💥 What Breaks

### 1. Existing Databases
- **Old databases will NOT work** with the new schema
- Tables created before this change will be incompatible
- `daily_metrics` table will not be created or accessed

### 2. Data Migration Required
If you have existing data in `daily_metrics` table:

```sql
-- Manual migration required (if needed)
-- Extract data from old daily_metrics.data JSON column
-- Transform and insert into daily_health_metrics normalized columns
```

### 3. Code Dependencies
Any code that used:
```python
# These methods NO LONGER EXIST
db.get_daily_metrics(...)     # ❌ REMOVED
db.store_daily_metric(...)    # ❌ REMOVED

# This class NO LONGER EXISTS  
HealthMetric(...)             # ❌ REMOVED
```

## ✅ Migration Path

### For New Installations
- No migration needed
- Fresh installations use only normalized schema
- Better performance and cleaner architecture

### For Existing Installations  
**Option 1: Fresh Start**
```bash
# Delete old database and start fresh
rm your_health.db
# New schema will be created automatically
```

**Option 2: Manual Migration (if data preservation needed)**
```python
# Backup your data first!
# Manual extraction and transformation required
# Contact for migration assistance if needed
```

## 🎯 Benefits

### 1. Simplified Architecture
- Single storage pattern (normalized only)
- No dual storage maintenance
- Cleaner, more predictable code

### 2. Better Performance  
- No JSON parsing overhead
- Optimized indexes for queries
- Efficient SQL operations

### 3. Easier Maintenance
- One schema to maintain
- No legacy code paths
- Simpler testing and debugging

### 4. Reduced Code Size
- 203 fewer lines of code (-10%)
- Eliminated complexity
- Focused functionality

## 🗂️ New Schema (Final)

### Current Tables (3 total)
1. **`timeseries`** - High-frequency metrics (HR, stress, etc.)
2. **`activities`** - Individual workouts and activities  
3. **`daily_health_metrics`** - Daily aggregated health data

### Key Features
- All data stored in normalized columns
- Efficient indexes for common queries
- Direct SQL access for analytics
- Type-safe column access

## 🚀 Advantages of Breaking Changes

### For Developers
- Cleaner, more focused API
- No legacy compatibility overhead
- Easier to understand and maintain
- Better performance characteristics

### For Users  
- Faster sync operations
- More reliable data storage
- Better query performance
- Future-proof architecture

## 📋 Action Required

1. **Backup existing data** if needed
2. **Update application code** to remove legacy method calls
3. **Test with new schema** before production deployment
4. **Create fresh database** or migrate data manually

## 🆘 Support

If you need help with migration:
- Check the documentation for new API usage
- Use direct SQL queries for analytics
- Consider the examples in `health_db_demo.py`

## 📈 Schema Comparison

### Before (Legacy Support)
```
📊 Total Tables: 4
📋 JSON Storage: daily_metrics (legacy)
🔍 Dual Storage: JSON + Normalized
⚡ Performance: Mixed (JSON parsing overhead)
🧹 Maintenance: Complex (dual paths)
```

### After (Clean Architecture)  
```
📊 Total Tables: 3  
📋 Storage: Normalized only
🔍 Single Pattern: Efficient columns
⚡ Performance: Optimized (no JSON overhead)
🧹 Maintenance: Simple (single path)
```

## 🎉 Result

The health database is now:
- **20% fewer tables** (4 → 3)
- **10% less code** (2052 → 1849 lines)
- **100% normalized storage** (no JSON)
- **Zero legacy overhead** (clean architecture)

This breaking change prioritizes long-term maintainability and performance over short-term compatibility.