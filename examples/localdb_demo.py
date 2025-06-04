#!/usr/bin/env python3
"""
Local Database Demo

This example demonstrates how to use the local database functionality
to automatically sync and store Garmin Connect data locally.

Features demonstrated:
- Setting up users for local data storage
- Configuring and starting data synchronization
- Monitoring sync progress
- Querying locally stored data
- Multi-user support

Requirements:
- Install with localdb extras: pip install garmy[localdb]
- Valid Garmin Connect credentials
- SQLite (included with Python)
"""

import asyncio
import time
from datetime import date, datetime, timedelta
from pathlib import Path

from garmy.auth.client import AuthClient
from garmy.core.client import APIClient
from garmy.localdb import (
    LocalDBClient,
    LocalDBConfig,
    SyncConfig,
    UserConfig,
    SyncStatus,
)


async def main():
    """Main demo function."""
    print("🏃‍♂️ Garmin Local Database Demo")
    print("=" * 50)
    
    # Create local database configuration
    db_path = Path.home() / ".garmy" / "demo_localdb"
    config = LocalDBConfig.default(db_path)
    
    print(f"📁 Database path: {config.db_path}")
    print(f"🗜️  Compression: {config.compression}")
    print()
    
    # Initialize local database client
    with LocalDBClient(config) as local_client:
        # Demo 1: User Management
        await demo_user_management(local_client)
        
        # Demo 2: Data Synchronization
        await demo_data_synchronization(local_client)
        
        # Demo 3: Querying Local Data
        await demo_query_local_data(local_client)
        
        # Demo 4: Database Statistics
        await demo_database_stats(local_client)


async def demo_user_management(local_client: LocalDBClient):
    """Demonstrate user management functionality."""
    print("👤 User Management Demo")
    print("-" * 30)
    
    # Check existing users
    users = local_client.list_users()
    print(f"📋 Current users: {len(users)}")
    
    if users:
        for user in users:
            print(f"  - {user.email} ({user.user_id})")
            print(f"    Last sync: {user.last_sync or 'Never'}")
    else:
        print("  No users configured yet.")
    
    print("\n💡 To add a new user, use the CLI:")
    print("   garmy-localdb setup-user your-email@example.com")
    print()


async def demo_data_synchronization(local_client: LocalDBClient):
    """Demonstrate data synchronization."""
    print("🔄 Data Synchronization Demo")
    print("-" * 35)
    
    users = local_client.list_users()
    if not users:
        print("❌ No users configured. Please add a user first.")
        print("   Use: garmy-localdb setup-user your-email@example.com")
        return
    
    # Use the first available user
    user = users[0]
    print(f"👤 Using user: {user.email}")
    
    # Create sync configuration for last 7 days
    end_date = date.today()
    start_date = end_date - timedelta(days=7)
    
    sync_config = SyncConfig(
        user_id=user.user_id,
        start_date=start_date,
        end_date=end_date,
        metrics=["sleep", "heart_rate", "steps"],  # Sync only a few metrics for demo
        batch_size=3,
        retry_attempts=2,
        auto_resume=True,
        incremental=True,
    )
    
    print(f"📅 Sync period: {start_date} to {end_date}")
    print(f"📊 Metrics: {', '.join(sync_config.metrics)}")
    print()
    
    # Check if we have valid authentication
    try:
        # This is a simplified demo - in practice you'd handle auth properly
        print("🔐 Note: This demo requires valid authentication.")
        print("   In a real application, you would authenticate with Garmin Connect first.")
        print("   For now, we'll demonstrate the sync configuration only.")
        
        # Simulate starting sync (commented out to avoid auth issues)
        # sync_id = await local_client.start_sync(sync_config)
        # print(f"🚀 Started sync: {sync_id}")
        
        print("✅ Sync configuration created successfully!")
        print("💡 To actually start sync, use CLI with proper authentication:")
        print(f"   garmy-localdb sync {user.user_id} {start_date} {end_date}")
        
    except Exception as e:
        print(f"❌ Sync demo failed: {e}")
        print("💡 This is expected in demo mode without valid auth.")
    
    print()


async def demo_query_local_data(local_client: LocalDBClient):
    """Demonstrate querying locally stored data."""
    print("🔍 Local Data Query Demo")
    print("-" * 30)
    
    users = local_client.list_users()
    if not users:
        print("❌ No users configured.")
        return
    
    user = users[0]
    print(f"👤 Querying data for: {user.email}")
    
    # List available metrics
    try:
        metrics = local_client.list_user_metrics(user.user_id)
        print(f"📊 Available metrics: {len(metrics)}")
        
        if metrics:
            for metric in metrics[:5]:  # Show first 5 metrics
                print(f"  - {metric}")
                
                # Get available dates for this metric
                dates = local_client.list_metric_dates(user.user_id, metric)
                print(f"    Available dates: {len(dates)}")
                
                if dates:
                    # Show sample data from the most recent date
                    recent_date = dates[-1]
                    data = local_client.get_metric_data(user.user_id, metric, recent_date)
                    
                    if data:
                        print(f"    Sample from {recent_date}:")
                        # Show first few keys of the data
                        sample_keys = list(data.keys())[:3]
                        for key in sample_keys:
                            print(f"      {key}: {data[key]}")
                        if len(data) > 3:
                            print(f"      ... and {len(data) - 3} more fields")
                    else:
                        print(f"    No data available for {recent_date}")
                print()
        else:
            print("  No metrics data found.")
            print("💡 Run a sync first to populate local data:")
            print(f"   garmy-localdb sync {user.user_id} 2023-12-01 2023-12-07")
    
    except Exception as e:
        print(f"❌ Query failed: {e}")
    
    print()


async def demo_database_stats(local_client: LocalDBClient):
    """Demonstrate database statistics."""
    print("📈 Database Statistics Demo")
    print("-" * 35)
    
    try:
        stats = local_client.get_database_stats()
        
        print(f"👥 Total users: {stats['users_count']}")
        print(f"📁 Database path: {stats['db_path']}")
        print(f"🗜️  Compression: {'Enabled' if stats['compression_enabled'] else 'Disabled'}")
        print()
        
        if stats['user_data_counts']:
            print("📊 Data records per user:")
            for user_id, count in stats['user_data_counts'].items():
                print(f"  {user_id}: {count:,} records")
        else:
            print("📊 No data records found.")
        
    except Exception as e:
        print(f"❌ Stats query failed: {e}")
    
    print()


def demo_cli_commands():
    """Show example CLI commands."""
    print("🖥️  CLI Commands Demo")
    print("-" * 25)
    
    print("Here are some useful CLI commands you can try:")
    print()
    
    print("📋 List users:")
    print("   garmy-localdb list-users")
    print()
    
    print("👤 Add new user:")
    print("   garmy-localdb setup-user your-email@example.com --name 'Your Name'")
    print()
    
    print("🔄 Start sync (last 30 days):")
    print("   garmy-localdb sync user_id 2023-11-01 2023-11-30")
    print()
    
    print("📊 Check sync status:")
    print("   garmy-localdb status")
    print("   garmy-localdb status <sync_id>")
    print()
    
    print("🔍 Query local data:")
    print("   garmy-localdb query user_id sleep --format json")
    print("   garmy-localdb query user_id heart_rate --start-date 2023-11-01")
    print()
    
    print("📈 Database statistics:")
    print("   garmy-localdb stats")
    print()
    
    print("⏸️  Control sync operations:")
    print("   garmy-localdb pause <sync_id>")
    print("   garmy-localdb resume <sync_id>")
    print("   garmy-localdb stop <sync_id>")
    print()


if __name__ == "__main__":
    print("Starting Garmin Local Database Demo...")
    print()
    
    # Run main demo
    asyncio.run(main())
    
    # Show CLI commands
    demo_cli_commands()
    
    print("✅ Demo completed!")
    print()
    print("🚀 Next steps:")
    print("1. Install with localdb extras: pip install garmy[localdb]")
    print("2. Set up a user: garmy-localdb setup-user your-email@example.com")
    print("3. Start syncing: garmy-localdb sync user_id start_date end_date")
    print("4. Monitor progress: garmy-localdb status")
    print("5. Query your data: garmy-localdb query user_id metric_name")
    print()
    print("📚 For more information, see the documentation and examples.")