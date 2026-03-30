# Garmy Fork — Full Data Capture

**Date**: 2026-03-30
**Status**: Approved

## Problem

Garmy 2.0.0 syncs all 11 Garmin Connect metric types but discards most of the data:

- **Activities**: Only stores name, duration, avg HR, training load, start time. The raw API returns 80+ fields including distance, pace, splits, cadence, power, HR zones, elevation, VO2max.
- **Respiration timeseries**: Extractor checks for `data.respiration_readings` which doesn't exist. Actual attribute is `data.respiration_values_array` (575 intraday readings, silently dropped).
- **HRV timeseries**: 101 overnight readings available but excluded from the timeseries extraction allow-list.
- **Sync frequency**: Nightly at 02:00 means activity data isn't available until the next day.

## Approach

Fork garmy, extend the existing sync pipeline to persist full API data. All changes are backwards-compatible and configurable so the fork can be contributed upstream.

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Fork vs workaround | Fork garmy | Fix at the source; upstream-friendly |
| Install method | `pip install` from GitHub URL | Simple; Ansible role changes one line |
| Activity detail storage | Extend `Activity` model + new `activity_splits` table | Flat fields for querying + structured splits |
| Large nested data (HR zones, power zones, split summaries) | JSON columns | Variable structure, queried via `json_extract()` in SQLite |
| Configuration | `SyncConfig` flags | Backwards compatible; defaults to full detail |
| MCP tools | No changes | `execute_sql_query` is sufficient |
| Schema migration | SQLAlchemy `create_all()` | Auto-adds new columns/tables; existing data preserved |
| TDD | Tests first for every change | User requirement |

## Changes

### 1. Activity Model — New Fields on `ActivitySummary`

Add to the dataclass in `garmy/metrics/activities.py`:

```python
# Distance and pace
distance: Optional[float] = None              # meters
average_speed: Optional[float] = None          # m/s
max_speed: Optional[float] = None              # m/s
avg_grade_adjusted_speed: Optional[float] = None  # m/s

# Best efforts
fastest_split_1000: Optional[float] = None     # seconds
fastest_split_1609: Optional[float] = None     # seconds (1 mile)
fastest_split_5000: Optional[float] = None     # seconds

# Elevation
elevation_gain: Optional[float] = None         # meters
elevation_loss: Optional[float] = None         # meters
min_elevation: Optional[float] = None          # meters
max_elevation: Optional[float] = None          # meters

# Calories and steps
calories: Optional[float] = None
steps: Optional[int] = None

# Running dynamics
avg_running_cadence: Optional[float] = None    # steps/min
max_running_cadence: Optional[float] = None    # steps/min
avg_stride_length: Optional[float] = None      # cm
avg_ground_contact_time: Optional[float] = None  # ms
avg_vertical_oscillation: Optional[float] = None  # mm
avg_vertical_ratio: Optional[float] = None     # percent
avg_ground_contact_balance: Optional[float] = None  # percent

# Power
avg_power: Optional[float] = None              # watts
max_power: Optional[float] = None              # watts
norm_power: Optional[float] = None             # watts

# Physiological
vo2_max_value: Optional[float] = None

# Respiration during activity
min_respiration_rate: Optional[float] = None   # already exists
max_respiration_rate: Optional[float] = None   # already exists
avg_respiration_rate: Optional[float] = None   # already exists

# Zone data (JSON)
hr_time_in_zones: Optional[Dict[str, float]] = None
power_time_in_zones: Optional[Dict[str, float]] = None

# Splits (JSON, summary level — detailed splits in activity_splits table)
split_summaries: Optional[List[Dict[str, Any]]] = None

# Intensity
moderate_intensity_minutes: Optional[int] = None
vigorous_intensity_minutes: Optional[int] = None
```

The `create_list_parser` auto-maps camelCase API keys to snake_case dataclass fields. Fields not present in the API response default to `None`.

### 2. Activity SQLAlchemy Model — New Columns

Add to `Activity` in `garmy/localdb/models.py`:

```python
# Distance and pace
distance = Column(Float)
average_speed = Column(Float)
max_speed = Column(Float)
avg_grade_adjusted_speed = Column(Float)

# Best efforts
fastest_split_1000 = Column(Float)
fastest_split_1609 = Column(Float)
fastest_split_5000 = Column(Float)

# Elevation
elevation_gain = Column(Float)
elevation_loss = Column(Float)
min_elevation = Column(Float)
max_elevation = Column(Float)

# Calories and steps
calories = Column(Float)
steps = Column(Integer)

# Running dynamics
avg_running_cadence = Column(Float)
max_running_cadence = Column(Float)
avg_stride_length = Column(Float)
avg_ground_contact_time = Column(Float)
avg_vertical_oscillation = Column(Float)
avg_vertical_ratio = Column(Float)
avg_ground_contact_balance = Column(Float)

# Power
avg_power = Column(Float)
max_power = Column(Float)
norm_power = Column(Float)

# Physiological
vo2_max_value = Column(Float)

# Zone data (JSON)
hr_time_in_zones = Column(JSON)
power_time_in_zones = Column(JSON)

# Splits summary (JSON)
split_summaries = Column(JSON)

# Intensity
moderate_intensity_minutes = Column(Integer)
vigorous_intensity_minutes = Column(Integer)
```

### 3. New `ActivitySplit` Model + Table

New SQLAlchemy model in `garmy/localdb/models.py`:

```python
class ActivitySplit(Base):
    """Per-lap split data from activities."""
    __tablename__ = "activity_splits"

    user_id = Column(Integer, primary_key=True, nullable=False)
    activity_id = Column(String, primary_key=True, nullable=False)
    split_index = Column(Integer, primary_key=True, nullable=False)
    split_type = Column(String, nullable=False)
    no_of_splits = Column(Integer)
    distance = Column(Float)
    duration = Column(Float)
    average_speed = Column(Float)
    max_speed = Column(Float)
    total_ascent = Column(Float)
    elevation_loss = Column(Float)
    max_elevation_gain = Column(Float)
    average_elevation_gain = Column(Float)
    max_distance = Column(Float)
```

### 4. DataExtractor Changes

**`_extract_activity_data()`** — extract all new fields from the raw API response. The raw response uses camelCase keys (`averageSpeed`, `elevationGain`, etc.). Map to snake_case for the dataclass.

Key mappings for fields where API key differs from field name:
- `averageHR` → `avg_heart_rate`
- `averageRunningCadenceInStepsPerMinute` → `avg_running_cadence`
- `maxRunningCadenceInStepsPerMinute` → `max_running_cadence`
- `avgGroundContactTime` → `avg_ground_contact_time`
- `avgVerticalOscillation` → `avg_vertical_oscillation`
- `vO2MaxValue` → `vo2_max_value`
- `activityTrainingLoad` → `training_load`

HR/power zone data extracted as dicts:
```python
hr_time_in_zones = {
    "zone_1": raw.get("hrTimeInZone_1"),
    "zone_2": raw.get("hrTimeInZone_2"),
    ...
}
```

Split summaries stored as-is (list of dicts from the API).

**New `_extract_activity_splits()`** — extract `splitSummaries` list into `ActivitySplit` records with sequential `split_index`.

**`extract_timeseries_data()` — fix respiration**:

```python
elif metric_type == MetricType.RESPIRATION:
    if hasattr(data, 'respiration_values_array') and data.respiration_values_array:
        for reading in data.respiration_values_array:
            if isinstance(reading, (list, tuple)) and len(reading) >= 2:
                timeseries_data.append((reading[0], reading[1], {}))
```

**`extract_timeseries_data()` — add HRV**:

Need to verify the parsed attribute name. Raw API has `hrvReadings` with `hrvValue` and `readingTimeGMT`. The parsed object likely has `hrv_readings`. Each reading stored as timeseries with timestamp + HRV value.

### 5. SyncManager Changes

**Timeseries allow-list** — change hardcoded list to configurable:

```python
# In SyncConfig:
timeseries_metrics: List[str] = field(default_factory=lambda: [
    "body_battery", "stress", "heart_rate", "respiration", "hrv"
])
```

**`_sync_metric_for_date()`** — use config instead of hardcoded list:

```python
if metric_type.value in self.config.sync.timeseries_metrics:
    timeseries_data = self.extractor.extract_timeseries_data(data, metric_type)
    ...
```

**`_sync_activities_for_date()`** — when `full_activity_detail` is enabled:
1. Use `activities_iterator.get_activities_for_date()` as before
2. But extract all fields via updated `_extract_activity_data()`
3. Also extract and store splits via `_extract_activity_splits()`

**Activity re-sync** — when `full_activity_detail` is enabled, activities that already exist but lack the new fields (e.g., `distance IS NULL`) should be re-synced. Add a check: if `activity_exists` and `full_activity_detail` is True, check if key fields are populated. If not, update rather than skip.

### 6. HealthDB Changes

**`store_activity()`** — write all new fields (currently hardcodes 7 fields, needs to write ~30).

**New `store_activity_splits()`** — batch insert `ActivitySplit` records for an activity.

**`_activity_to_dict()`** — include all new fields in query results.

### 7. Configuration

New fields on `SyncConfig`:

```python
# Full activity detail (distance, pace, splits, dynamics, power, zones)
full_activity_detail: bool = True

# Which metrics get timeseries extraction
timeseries_metrics: List[str] = field(default_factory=lambda: [
    "body_battery", "stress", "heart_rate", "respiration", "hrv"
])
```

Default `True` / full list for new installs. Existing users get the enhanced data automatically on upgrade. Setting `full_activity_detail = False` preserves the old minimal behaviour.

### 8. Homelab Deployment Changes (separate PR)

In the homelab repo, not the garmy fork:

- **`ansible/vars/versions.yml`**: Change `garmy_version` from `2.0.0` to the fork's git ref
- **`ansible/roles/garmin_mcp/tasks/main.yml`**: Change `pip install garmy[all]=={{ garmy_version }}` to `pip install "garmy[all] @ git+https://github.com/<user>/garmy.git@<ref>"`
- **`garmy-sync.timer`**: Change `OnCalendar=*-*-* 02:00:00` to `OnCalendar=*-*-* *:00:00`
- **`garmy-sync.service`**: Change sync window from `2` to `1` day (hourly means today only)
- **Initial backfill**: One-time run of `garmy-sync.py 365` to re-sync historical activities with full detail (existing activities will be updated with new fields)

## Test Plan (TDD)

Tests written before implementation, using fixture data captured from today's API investigation.

### Test fixtures (saved as JSON files)
- `tests/fixtures/activity_raw.json` — full raw API response for one activity (the South Gloucestershire run)
- `tests/fixtures/respiration_raw.json` — raw respiration response with 575 readings
- `tests/fixtures/hrv_raw.json` — raw HRV response with 101 readings
- `tests/fixtures/activity_list_raw.json` — raw activity list response

### Test cases

1. **`test_activity_summary_parses_all_fields`** — parse raw fixture → `ActivitySummary`, assert distance, speed, elevation, cadence, power, splits, zones all populated
2. **`test_activity_summary_backwards_compatible`** — parse fixture with `full_activity_detail=False` config context → only original fields populated
3. **`test_extract_activity_data_full`** — `DataExtractor._extract_activity_data()` with raw dict → all fields extracted
4. **`test_extract_activity_splits`** — `DataExtractor._extract_activity_splits()` → correct number of splits with correct types
5. **`test_store_activity_full`** — write full activity to SQLite → read back → all fields match
6. **`test_store_activity_splits`** — write splits → read back → correct data
7. **`test_activity_resync_when_missing_fields`** — existing minimal activity + full_detail=True → activity updated with new fields
8. **`test_respiration_timeseries_extraction`** — parse respiration fixture → 575 timeseries data points
9. **`test_hrv_timeseries_extraction`** — parse HRV fixture → 101 timeseries data points
10. **`test_timeseries_config_respected`** — set `timeseries_metrics=["heart_rate"]` → only HR extracted, others skipped
11. **`test_sync_config_defaults`** — new `SyncConfig()` has `full_activity_detail=True` and full `timeseries_metrics` list

## Files to Modify (in garmy fork)

```
garmy/metrics/activities.py          # Add ~25 fields to ActivitySummary
garmy/localdb/models.py              # Add columns to Activity, new ActivitySplit model
garmy/localdb/extractors.py          # Fix respiration, add HRV, extend activity extraction
garmy/localdb/sync.py                # Configurable timeseries list, activity re-sync logic
garmy/localdb/db.py                  # store_activity() full fields, new store_activity_splits()
garmy/localdb/config.py              # New SyncConfig fields
tests/fixtures/                      # New fixture files
tests/test_full_activity_detail.py   # New test file
tests/test_timeseries_extraction.py  # New test file
```

## Files to Modify (in homelab repo, separate PR)

```
ansible/vars/versions.yml                        # garmy version → fork git ref
ansible/roles/garmin_mcp/tasks/main.yml          # pip install source
ansible/roles/garmin_mcp/tasks/main.yml          # timer + sync window
```

## Out of Scope

- Per-second GPS track data (`get_activity_details()`) — 50-500KB per activity, deliberate exclusion
- Steps/calories timeseries — API returns daily aggregates, not intraday readings
- Training readiness timeseries — no intraday data exists in the API
- MCP tool changes — SQL is sufficient
