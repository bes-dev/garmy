#!/usr/bin/env python3
"""
Demo of the new database schema architecture.

This script demonstrates:
- Clean separation of schema definition from database logic
- Schema validation and introspection
- Centralized schema management
- Easy schema evolution and migration planning
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.garmy.localdb.db import HealthDB
from src.garmy.localdb.schema import (
    HEALTH_DB_SCHEMA,
    SchemaVersion,
    get_schema_info,
    get_table_names,
)


def demo_schema_info():
    """Demo schema introspection capabilities."""
    print("🗄️  Database Schema Information")
    print("=" * 50)

    schema_info = get_schema_info()

    print(f"📊 Schema Version: {schema_info['version']}")
    print(f"📋 Total Tables: {schema_info['total_tables']}")
    print(f"🔍 Total Indexes: {schema_info['total_indexes']}")
    print()

    print("📁 Tables:")
    for table_name, info in schema_info["tables"].items():
        print(f"   • {table_name}")
        print(f"     Description: {info['description']}")
        print(f"     Primary Key: {', '.join(info['primary_key'])}")
        print(f"     Indexes: {info['indexes_count']}")
        print()


def demo_schema_definition():
    """Demo clean schema definition structure."""
    print("\n🏗️  Schema Definition Structure")
    print("=" * 40)

    print(f"Schema contains {len(HEALTH_DB_SCHEMA.tables)} tables:")

    for table in HEALTH_DB_SCHEMA.tables:
        print(f"\n📋 {table.name.upper()}")
        print(f"   Purpose: {table.description}")
        print(f"   Primary Key: [{', '.join(table.primary_key)}]")
        print(f"   Indexes: {len(table.indexes)} performance indexes")

        # Show table SQL (first few lines)
        sql_lines = table.sql.strip().split("\n")
        print(f"   Schema Preview:")
        for i, line in enumerate(sql_lines[:4]):
            if line.strip():
                print(f"     {line.strip()}")
        if len(sql_lines) > 4:
            print("     ...")


def demo_data_extraction():
    """Demo how sync process extracts data to database columns."""
    print("\n🔄 Data Extraction Process")
    print("=" * 30)

    print("The sync process uses direct attribute access:")
    print()
    print("📊 Example extraction logic:")
    print("   API Response → Database Column")
    print("   data.total_steps → total_steps")
    print("   data.resting_heart_rate → resting_heart_rate")
    print("   data.sleep_duration_hours → sleep_duration_hours")
    print("   data.training_readiness.score → training_readiness_score")
    print()
    print("🔧 Implementation uses getattr() for safe extraction:")
    print("   getattr(data, 'total_steps', None)")
    print("   getattr(training_readiness, 'score', None)")
    print()
    print("✅ No mapping table needed - direct attribute access!")


def demo_database_integration():
    """Demo how the schema integrates with the database."""
    print("\n💾 Database Integration Demo")
    print("=" * 35)

    # Create temporary database for demo
    db_path = Path("schema_demo.db")
    db = HealthDB(db_path)

    print("✅ Database initialized with new schema architecture")

    # Validate schema
    is_valid = db.validate_schema()
    print(f"🔍 Schema validation: {'✅ PASSED' if is_valid else '❌ FAILED'}")

    # Show schema info from database
    db_schema_info = db.get_schema_info()
    print(f"📊 Schema version: {db_schema_info['version']}")
    print(f"📋 Tables created: {db_schema_info['total_tables']}")

    print("\n📁 Expected vs Created Tables:")
    expected_tables = set(get_table_names())
    print(f"   Expected: {', '.join(sorted(expected_tables))}")

    # Check actual tables in database
    with db.connection() as conn:
        actual_tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    print(f"   Created:  {', '.join(sorted(actual_tables))}")

    missing = expected_tables - actual_tables
    extra = actual_tables - expected_tables

    if missing:
        print(f"   ❌ Missing: {', '.join(missing)}")
    if extra:
        print(f"   ➕ Extra: {', '.join(extra)}")
    if not missing and not extra:
        print("   ✅ Perfect match!")

    # Clean up demo database
    if db_path.exists():
        db_path.unlink()
        print(f"\n🧹 Cleaned up demo database: {db_path}")


def demo_benefits():
    """Demo the benefits of this architecture."""
    print("\n🌟 Benefits of Centralized Schema Management")
    print("=" * 55)

    benefits = [
        "🧹 Clean separation: Schema definition is separate from database logic",
        "📚 Documentation: Each table has clear description and purpose",
        "🔍 Introspection: Easy to query schema info programmatically",
        "🚀 Evolution: Schema changes are centralized and trackable",
        "🔧 Validation: Can validate database matches expected schema",
        "📊 Mapping: Clear mapping from API data to database columns",
        "🧪 Testing: Easy to create test schemas and validate migrations",
        "🏗️ Maintenance: Single source of truth for all schema changes",
    ]

    for benefit in benefits:
        print(f"   {benefit}")


def main():
    """Run all schema demos."""
    print("🗄️  Health Database Schema Architecture Demo")
    print("=" * 60)
    print("This demo shows the clean separation of schema definition")
    print("from database implementation logic.\n")

    demo_schema_info()
    demo_schema_definition()
    demo_data_extraction()
    demo_database_integration()
    demo_benefits()

    print(f"\n🎉 Schema Demo Complete!")
    print(f"💡 The schema is now:")
    print(f"   • Documented and well-structured")
    print(f"   • Separated from database implementation")
    print(f"   • Easy to evolve and maintain")
    print(f"   • Self-validating and introspectable")


if __name__ == "__main__":
    main()
