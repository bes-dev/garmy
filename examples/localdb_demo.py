#!/usr/bin/env python3
"""LocalDB 1.0 Demo - Modern SQLAlchemy-based analytics and storage.

=====================================

This example demonstrates the LocalDB 1.0 architecture built from scratch
with SQLAlchemy, focused on analytics capabilities and type-safe operations.

Key features:
- Automatic extraction from dataclasses to specialized tables
- Fast analytics queries with optimized indexing
- Type-safe operations with SQLAlchemy models
- Comprehensive data quality reporting
- Future-proof schema ready for ML and data science
- High-performance queries for statistics and trends

Example output:
    Sleep Analytics (30 days):
    - Average sleep: 7.2 hours
    - Sleep efficiency: 87.3%
    - Deep sleep: 18.5%
    
    Steps Analytics (30 days):
    - Total steps: 312,450
    - Daily average: 10,415 steps
    - Goal achievement: 83.3%
"""

from datetime import date, timedelta
from pathlib import Path

from garmy.localdb.storage import LocalDataStore
from garmy.localdb.config import LocalDBConfig


def main():
    """Demonstrate LocalDB 1.0 capabilities."""
    print("🚀 Garmin LocalDB 1.0 Demo (Modern SQLAlchemy Architecture)")
    print("=" * 60)

    # Setup database
    db_path = Path.home() / ".garmy" / "localdb"
    config = LocalDBConfig.default(db_path / "garmin_data.db")
    
    print(f"🗄️  Database: {config.db_path}")
    print(f"📊 Using SQLAlchemy models with specialized analytics tables")
    print()

    try:
        with LocalDataStore(config) as store:
            # Demonstrate analytics capabilities
            demo_analytics(store)
            
            # Demonstrate data quality reporting
            demo_data_quality(store)
            
            # Demonstrate storage optimization
            demo_storage_info(store)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        print("💡 Make sure you have data synced first")


def demo_analytics(store: LocalDataStore):
    """Demonstrate analytics capabilities."""
    print("📈 Analytics Demo")
    print("-" * 20)
    
    # Check if we have users
    users = store.list_users()
    if not users:
        print("ℹ️  No users found. Please sync some data first.")
        return
    
    user_id = users[0].user_id
    print(f"👤 Analyzing data for user: {user_id}")
    
    # Date range for analysis
    end_date = date.today()
    start_date = end_date - timedelta(days=30)
    
    print(f"📅 Date range: {start_date} to {end_date}")
    print()
    
    # Sleep analytics
    try:
        sleep_analytics = store.get_sleep_analytics(user_id, start_date, end_date)
        if sleep_analytics:
            print("😴 Sleep Analytics (Last 30 days):")
            print(f"   📊 Total nights: {sleep_analytics.get('total_days', 0)}")
            print(f"   🛌 Average sleep: {sleep_analytics.get('average_sleep_hours', 0):.1f} hours")
            print(f"   ⚡ Sleep efficiency: {sleep_analytics.get('average_efficiency', 0):.1f}%")
            print(f"   🌙 Deep sleep: {sleep_analytics.get('average_deep_sleep_percentage', 0):.1f}%")
            print(f"   🏆 Best night: {sleep_analytics.get('best_sleep_day', 'N/A')}")
            print(f"   📉 Worst night: {sleep_analytics.get('worst_sleep_day', 'N/A')}")
        else:
            print("😴 No sleep data available for analytics")
        print()
    except Exception as e:
        print(f"😴 Sleep analytics error: {e}")
        print()
    
    # Steps analytics
    try:
        steps_analytics = store.get_steps_analytics(user_id, start_date, end_date)
        if steps_analytics:
            print("🚶 Steps Analytics (Last 30 days):")
            print(f"   📊 Total days: {steps_analytics.get('total_days', 0)}")
            print(f"   👟 Total steps: {steps_analytics.get('total_steps', 0):,}")
            print(f"   📈 Daily average: {steps_analytics.get('average_daily_steps', 0):,} steps")
            print(f"   🎯 Goals achieved: {steps_analytics.get('goals_achieved', 0)}")
            print(f"   ✅ Goal rate: {steps_analytics.get('goal_achievement_rate', 0):.1f}%")
            print(f"   🏃 Best day: {steps_analytics.get('best_day_steps', 0):,} steps")
            print(f"   🚶 Total distance: {steps_analytics.get('total_distance_km', 0):.1f} km")
        else:
            print("🚶 No steps data available for analytics")
        print()
    except Exception as e:
        print(f"🚶 Steps analytics error: {e}")
        print()


def demo_data_quality(store: LocalDataStore):
    """Demonstrate data quality reporting."""
    print("🔍 Data Quality Report")
    print("-" * 25)
    
    users = store.list_users()
    if not users:
        print("ℹ️  No users to analyze")
        return
    
    user_id = users[0].user_id
    
    try:
        quality_report = store.get_data_quality_report(user_id)
        
        print(f"👤 User: {quality_report['user_id']}")
        print(f"📊 Total records: {quality_report['total_records']:,}")
        print(f"📅 Date coverage: {quality_report['date_range']['days_covered']} days")
        print(f"   From: {quality_report['date_range']['start'] or 'N/A'}")
        print(f"   To: {quality_report['date_range']['end'] or 'N/A'}")
        print(f"💾 Storage usage: {quality_report['storage_usage_mb']:.1f} MB")
        print()
        
        print("📋 Metrics coverage:")
        metrics_coverage = quality_report['metrics_coverage']
        if metrics_coverage:
            for metric, count in sorted(metrics_coverage.items()):
                print(f"   {metric}: {count:,} records")
        else:
            print("   No metrics data found")
        print()
        
    except Exception as e:
        print(f"❌ Data quality report error: {e}")
        print()


def demo_storage_info(store: LocalDataStore):
    """Demonstrate storage and database information."""
    print("🗄️  Storage Information")
    print("-" * 25)
    
    try:
        db_stats = store.get_database_stats()
        
        print(f"📍 Database path: {db_stats['db_path']}")
        print(f"👥 Users: {db_stats['users_count']}")
        print(f"📊 Total records: {db_stats['total_metric_records']:,}")
        print()
        
        print("📈 Records by metric type:")
        metric_counts = db_stats.get('metric_type_counts', {})
        for metric, count in sorted(metric_counts.items()):
            print(f"   {metric}: {count:,}")
        print()
        
        print("👤 Records by user:")
        user_counts = db_stats.get('user_data_counts', {})
        for user, count in sorted(user_counts.items()):
            print(f"   {user}: {count:,}")
        print()
        
    except Exception as e:
        print(f"❌ Storage info error: {e}")
        print()


def demo_advanced_features():
    """Demonstrate LocalDB 1.0 architecture highlights."""
    print("🚀 LocalDB 1.0 Architecture")
    print("-" * 30)
    
    print("✨ Core Features:")
    print("   🔄 Automatic dataclass extraction to specialized tables")
    print("   📊 Fast analytics with optimized database indexes")
    print("   🛡️  Type-safe operations with SQLAlchemy models")
    print("   📈 Hybrid properties for computed metrics")
    print("   🔍 Comprehensive data quality reporting")
    print("   📤 Enhanced export capabilities")
    print("   🗃️  Optimized storage with metadata tracking")
    print("   🔮 Future-proof schema with Alembic migrations")
    print("   🤖 Ready for ML and data science workflows")
    print()
    
    print("🏗️  Architecture Design:")
    print("   • Dual storage: Generic JSON + specialized analytics tables")
    print("   • Automatic metric extraction from API dataclasses")
    print("   • Optimized indexes for common query patterns")
    print("   • Comprehensive relationship mapping with foreign keys")
    print("   • Efficient upsert operations for data updates")
    print("   • Built-in data integrity and validation")
    print()


if __name__ == "__main__":
    demo_advanced_features()
    main()
    
    print("💡 LocalDB 1.0 Notes:")
    print("   • Modern SQLAlchemy architecture built from scratch")
    print("   • Enhanced analytics capabilities with specialized tables")
    print("   • Type-safe metric extraction from dataclasses")
    print("   • Optimized for advanced reporting and ML applications")
    print("   • Future schema changes handled by Alembic migrations")
    print("   • Production-ready for data science and analytics workflows")