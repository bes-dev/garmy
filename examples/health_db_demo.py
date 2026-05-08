#!/usr/bin/env python3
"""
Comprehensive demo of the Garmin Health Database system.

This script demonstrates:
- Database synchronization with progress tracking
- Normalized health metrics storage
- Activity tracking and analytics
- Different progress reporting styles
- Data export capabilities
- Advanced SQL queries for health analysis

Usage:
    export GARMIN_EMAIL="your_email@example.com"
    export GARMIN_PASSWORD="your_password"
    python examples/health_db_demo.py
"""

import asyncio
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.garmy.localdb.config import LocalDBConfig
from src.garmy.localdb.progress import MultiReporter, create_reporter
from src.garmy.localdb.sync import SyncManager


class HealthDBDemo:
    """Comprehensive demo of the health database system."""

    def __init__(self):
        self.db_path = Path("health_demo.db")
        self.user_id = 1
        self.sync_manager = None

    async def run_complete_demo(self):
        """Run the complete demonstration."""
        print("🏥 Garmin Health Database System Demo")
        print("=" * 50)

        # Get credentials
        email = os.getenv("GARMIN_EMAIL")
        password = os.getenv("GARMIN_PASSWORD")

        if not email or not password:
            print(
                "❌ Please set GARMIN_EMAIL and GARMIN_PASSWORD environment variables"
            )
            return

        try:
            await self._demo_progress_types()
            await self._demo_sync_and_analytics()
            await self._demo_data_export()
            await self._demo_advanced_queries()
            self._cleanup()

        except Exception as e:
            print(f"❌ Demo failed: {e}")
            import traceback

            traceback.print_exc()

    async def _demo_progress_types(self):
        """Demo different progress reporting styles."""
        print("\n📊 Progress Reporting Demo")
        print("-" * 30)

        email = os.getenv("GARMIN_EMAIL")
        password = os.getenv("GARMIN_PASSWORD")

        # Demo period (small for quick demo)
        end_date = date.today()
        start_date = end_date - timedelta(days=2)

        # 1. Rich progress (if available)
        try:
            print("🎨 Rich Progress (beautiful terminal UI):")
            rich_reporter = create_reporter(
                "rich", name="Health Sync", show_stats_table=True
            )

            config = LocalDBConfig()
            sync_manager = SyncManager(
                db_path=Path("demo_rich.db"),
                config=config,
                progress_reporter=rich_reporter,
            )

            await sync_manager.initialize(email, password)
            await sync_manager.sync_range(self.user_id, start_date, end_date)
            print("✅ Rich demo completed\n")

        except ImportError:
            print("⚠️ Rich not available (install: pip install rich)\n")

        # 2. TQDM progress bar
        try:
            print("📊 TQDM Progress Bar:")
            tqdm_reporter = create_reporter(
                "tqdm", name="Health Sync", show_details=True
            )

            config = LocalDBConfig()
            sync_manager = SyncManager(
                db_path=Path("demo_tqdm.db"),
                config=config,
                progress_reporter=tqdm_reporter,
            )

            await sync_manager.initialize(email, password)
            await sync_manager.sync_range(self.user_id, start_date, end_date)
            print("✅ TQDM demo completed\n")

        except ImportError:
            print("⚠️ TQDM not available (install: pip install tqdm)\n")

        # 3. Combined reporting
        print("🔄 Combined Progress (Logging + JSON):")
        multi_reporter = MultiReporter("Combined Sync")
        multi_reporter.add_reporter(create_reporter("logging", name="Health Sync"))
        multi_reporter.add_reporter(
            create_reporter("json", output_file="sync_report.json", real_time=False)
        )

        config = LocalDBConfig()
        sync_manager = SyncManager(
            db_path=Path("demo_combined.db"),
            config=config,
            progress_reporter=multi_reporter,
        )

        await sync_manager.initialize(email, password)
        await sync_manager.sync_range(self.user_id, start_date, end_date)
        print("✅ Combined demo completed (see sync_report.json)\n")

    async def _demo_sync_and_analytics(self):
        """Demo main synchronization and analytics."""
        print("\n💚 Health Data Synchronization & Analytics")
        print("-" * 45)

        # Clean start
        if self.db_path.exists():
            self.db_path.unlink()

        # Setup with automatic progress selection
        config = LocalDBConfig()

        try:
            progress_reporter = create_reporter("rich", name="Health Analytics")
            print("🎨 Using Rich progress display")
        except ImportError:
            try:
                progress_reporter = create_reporter("tqdm", name="Health Analytics")
                print("📊 Using TQDM progress display")
            except ImportError:
                progress_reporter = create_reporter("logging", name="Health Analytics")
                print("📝 Using logging progress display")

        self.sync_manager = SyncManager(
            db_path=self.db_path, config=config, progress_reporter=progress_reporter
        )

        # Initialize
        email = os.getenv("GARMIN_EMAIL")
        password = os.getenv("GARMIN_PASSWORD")
        await self.sync_manager.initialize(email, password)

        # Sync recent data
        end_date = date.today()
        start_date = end_date - timedelta(days=7)

        print(f"\n📅 Syncing health data: {start_date} to {end_date}")
        stats = await self.sync_manager.sync_range(self.user_id, start_date, end_date)

        print(f"\n📊 Sync Results:")
        print(f"   ✅ Success: {stats['completed']}")
        print(f"   ⏭️  Skipped: {stats['skipped']}")
        print(f"   ❌ Failed: {stats['failed']}")
        print(f"   📈 Total: {stats['total_tasks']}")

        # Simple database statistics using direct SQL
        with self.sync_manager.db.connection() as conn:
            health_count = conn.execute(
                "SELECT COUNT(*) FROM daily_health_metrics"
            ).fetchone()[0]
            activities_count = conn.execute(
                "SELECT COUNT(*) FROM activities"
            ).fetchone()[0]
            timeseries_count = conn.execute(
                "SELECT COUNT(*) FROM timeseries"
            ).fetchone()[0]

            print(f"\n🏗️  Database Statistics:")
            print(f"   📋 Health metrics: {health_count}")
            print(f"   🏃‍♂️ Activities: {activities_count}")
            print(f"   📊 Timeseries points: {timeseries_count}")

        # Show simple analytics using direct SQL
        await self._show_simple_analytics(start_date, end_date)

    async def _show_simple_analytics(self, start_date: date, end_date: date):
        """Show simple analytics using direct SQL queries."""
        print(f"\n📊 Simple Analytics (Direct SQL)")

        with self.sync_manager.db.connection() as conn:
            # Health trends
            trends = conn.execute(
                """
                SELECT 
                    AVG(total_steps) as avg_daily_steps,
                    AVG(resting_heart_rate) as avg_resting_hr,
                    AVG(sleep_duration_hours) as avg_sleep_hours,
                    COUNT(CASE WHEN total_steps > 10000 THEN 1 END) as days_over_10k_steps
                FROM daily_health_metrics 
                WHERE user_id = ? AND metric_date BETWEEN ? AND ?
            """,
                (self.user_id, start_date.isoformat(), end_date.isoformat()),
            ).fetchone()

            if trends and trends[0]:
                print(f"   👟 Average daily steps: {trends[0]:,.0f}")
                print(
                    f"   ❤️ Average resting HR: {trends[1]:.0f} bpm"
                    if trends[1]
                    else "   ❤️ No HR data"
                )
                print(
                    f"   😴 Average sleep: {trends[2]:.1f} hours"
                    if trends[2]
                    else "   😴 No sleep data"
                )
                print(f"   🎯 Days >10k steps: {trends[3]}")

            # Activities summary
            activities = conn.execute(
                """
                SELECT COUNT(*) as total_activities, COUNT(DISTINCT activity_name) as activity_types
                FROM activities 
                WHERE user_id = ? AND activity_date BETWEEN ? AND ?
            """,
                (self.user_id, start_date.isoformat(), end_date.isoformat()),
            ).fetchone()

            if activities and activities[0] > 0:
                print(f"\n🏃‍♂️ Activities:")
                print(f"   📈 Total activities: {activities[0]}")
                print(f"   🎯 Activity types: {activities[1]}")
            else:
                print(f"\n🏃‍♂️ No activities found in this period")

    async def _demo_data_export(self):
        """Demo data export capabilities."""
        print(f"\n📤 Data Export Demo")
        print("-" * 20)

        if not self.sync_manager:
            print("⚠️ No sync manager available for export demo")
            return

        end_date = date.today()
        start_date = end_date - timedelta(days=7)

        # Export health metrics
        health_data = self.sync_manager.query_health_metrics(
            self.user_id, start_date, end_date
        )
        if health_data:
            # Save to JSON
            export_file = "health_export.json"
            with open(export_file, "w") as f:
                json.dump(health_data, f, indent=2, default=str)
            print(
                f"✅ Health metrics exported to {export_file} ({len(health_data)} records)"
            )

        # Export activities
        activities = self.sync_manager.query_activities(
            self.user_id, start_date, end_date
        )
        if activities:
            activities_file = "activities_export.json"
            with open(activities_file, "w") as f:
                json.dump(activities, f, indent=2, default=str)
            print(
                f"✅ Activities exported to {activities_file} ({len(activities)} records)"
            )

        # Export timeseries (last day only)
        if health_data:
            from datetime import datetime

            from src.garmy.localdb.models import MetricType

            last_date = datetime.strptime(
                health_data[-1]["metric_date"], "%Y-%m-%d"
            ).date()
            start_time = datetime.combine(last_date, datetime.min.time())
            end_time = start_time + timedelta(days=1)

            hr_data = self.sync_manager.query_timeseries(
                self.user_id, MetricType.HEART_RATE, start_time, end_time
            )
            if hr_data:
                hr_file = "heart_rate_timeseries.json"
                with open(hr_file, "w") as f:
                    json.dump(hr_data, f, indent=2, default=str)
                print(
                    f"✅ Heart rate timeseries exported to {hr_file} ({len(hr_data)} points)"
                )

    async def _demo_advanced_queries(self):
        """Demo advanced SQL queries."""
        print(f"\n🔍 Advanced Health Analytics")
        print("-" * 35)

        if not self.sync_manager:
            print("⚠️ No sync manager available for queries demo")
            return

        # Direct SQL queries for advanced analytics
        with self.sync_manager.db.connection() as conn:

            # 1. Sleep quality vs training readiness correlation
            print("📊 Sleep Quality vs Training Readiness:")
            correlation = conn.execute(
                """
                SELECT 
                    CASE 
                        WHEN sleep_duration_hours >= 8 THEN 'Good Sleep (8+ hrs)'
                        WHEN sleep_duration_hours >= 6 THEN 'Fair Sleep (6-8 hrs)'
                        ELSE 'Poor Sleep (<6 hrs)'
                    END as sleep_quality,
                    AVG(training_readiness_score) as avg_readiness,
                    COUNT(*) as days
                FROM daily_health_metrics 
                WHERE user_id = ? AND sleep_duration_hours IS NOT NULL 
                AND training_readiness_score IS NOT NULL
                GROUP BY 1
                ORDER BY avg_readiness DESC
            """,
                (self.user_id,),
            ).fetchall()

            for row in correlation:
                print(f"   {row[0]}: Readiness {row[1]:.0f}, {row[2]} days")

            # 2. Activity patterns by day of week
            print(f"\n📅 Activity Patterns by Day of Week:")
            weekly_pattern = conn.execute(
                """
                SELECT 
                    CASE strftime('%w', activity_date)
                        WHEN '0' THEN 'Sunday'
                        WHEN '1' THEN 'Monday'
                        WHEN '2' THEN 'Tuesday'
                        WHEN '3' THEN 'Wednesday'
                        WHEN '4' THEN 'Thursday'
                        WHEN '5' THEN 'Friday'
                        WHEN '6' THEN 'Saturday'
                    END as day_of_week,
                    COUNT(*) as activities,
                    AVG(duration_seconds/60) as avg_duration_min
                FROM activities 
                WHERE user_id = ?
                GROUP BY strftime('%w', activity_date)
                ORDER BY strftime('%w', activity_date)
            """,
                (self.user_id,),
            ).fetchall()

            for row in weekly_pattern:
                print(f"   {row[0]}: {row[1]} activities, {row[2]:.0f} min avg")

            # 3. Most active days
            print(f"\n🏆 Most Active Days:")
            active_days = conn.execute(
                """
                SELECT 
                    metric_date,
                    total_steps,
                    (SELECT COUNT(*) FROM activities a 
                     WHERE a.user_id = dhm.user_id AND a.activity_date = dhm.metric_date) as activities_count
                FROM daily_health_metrics dhm
                WHERE user_id = ? AND total_steps IS NOT NULL
                ORDER BY total_steps DESC
                LIMIT 5
            """,
                (self.user_id,),
            ).fetchall()

            for row in active_days:
                print(f"   📅 {row[0]}: {row[1]:,} steps, {row[2]} activities")

            # 4. Recovery analysis
            print(f"\n🔋 Recovery Analysis (Body Battery vs Stress):")
            recovery = conn.execute(
                """
                SELECT 
                    metric_date,
                    body_battery_high,
                    body_battery_low,
                    (body_battery_high - body_battery_low) as battery_recovery,
                    avg_stress_level
                FROM daily_health_metrics 
                WHERE user_id = ? 
                AND body_battery_high IS NOT NULL 
                AND avg_stress_level IS NOT NULL
                ORDER BY battery_recovery DESC
                LIMIT 5
            """,
                (self.user_id,),
            ).fetchall()

            for row in recovery:
                print(f"   📅 {row[0]}: 🔋 Recovery {row[3]}, 😰 Stress {row[4]}")

    def _cleanup(self):
        """Clean up demo files."""
        print(f"\n🧹 Cleanup")
        print("-" * 10)

        # Show file sizes
        demo_files = [
            "health_demo.db",
            "demo_rich.db",
            "demo_tqdm.db",
            "demo_combined.db",
            "health_export.json",
            "activities_export.json",
            "heart_rate_timeseries.json",
            "sync_report.json",
        ]

        print("📁 Generated files:")
        total_size = 0
        for file_path in demo_files:
            path = Path(file_path)
            if path.exists():
                size_kb = path.stat().st_size / 1024
                total_size += size_kb
                print(f"   📄 {file_path}: {size_kb:.1f} KB")

        print(f"   📊 Total size: {total_size:.1f} KB")

        # Option to clean up
        response = input("\n🗑️  Delete demo files? (y/N): ").lower().strip()
        if response == "y":
            for file_path in demo_files:
                path = Path(file_path)
                if path.exists():
                    path.unlink()
                    print(f"   ✅ Deleted {file_path}")
        else:
            print("   📂 Demo files kept for inspection")


async def main():
    """Main demo function."""
    demo = HealthDBDemo()
    await demo.run_complete_demo()

    print(f"\n🎉 Demo completed!")
    print(f"\n💡 Next steps:")
    print(f"   • Explore the generated files")
    print(f"   • Check out other examples in the examples/ directory")
    print(f"   • Read PROGRESS_SYSTEM.md for progress customization")
    print(f"   • Integrate the health DB into your own projects")


if __name__ == "__main__":
    print("🏥 Garmin Health Database Demo")
    print("🔐 Make sure GARMIN_EMAIL and GARMIN_PASSWORD are set")
    print("📦 Optional dependencies for better progress display:")
    print("   pip install rich tqdm")
    print()

    asyncio.run(main())
