"""Command-line interface for LocalDB."""

import asyncio
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

import click
from tqdm import tqdm

from .client import LocalDBClient


@click.group()
@click.option('--db-path', default=None, help='Database path (default: ~/.garmy/localdb.db)')
@click.pass_context
def cli(ctx, db_path):
    """Garmin LocalDB - Local database for Garmin data with analytics."""
    if db_path is None:
        db_path = Path.home() / '.garmy' / 'localdb.db'
    
    ctx.ensure_object(dict)
    ctx.obj['db_path'] = Path(db_path)


@cli.group()
@click.pass_context
def user(ctx):
    """User management commands."""
    pass


@user.command()
@click.argument('user_id')
@click.argument('email')
@click.option('--name', help='Display name')
@click.option('--token-path', help='Path to auth tokens')
@click.pass_context
def add(ctx, user_id, email, name, token_path):
    """Add a new user."""
    with LocalDBClient(ctx.obj['db_path']) as client:
        try:
            client.add_user(user_id, email, name, token_path)
            click.echo(f"✅ User {user_id} added successfully")
        except Exception as e:
            click.echo(f"❌ Error adding user: {e}", err=True)
            sys.exit(1)


@cli.command()
@click.argument('email')
@click.option('--name', help='Display name')
@click.option('--token-path', help='Path to auth tokens')
@click.pass_context
def setup_user(ctx, email, name, token_path):
    """Setup a new user and login to Garmin Connect."""
    # Generate user_id from email
    user_id = email.split('@')[0]
    
    # Securely prompt for password
    password = click.prompt(f'Garmin Connect password for {email}', hide_input=True, confirmation_prompt=False)
    
    with LocalDBClient(ctx.obj['db_path']) as client:
        try:
            # Check if user already exists
            existing_user = client.get_user(user_id)
            if existing_user:
                click.echo(f"👤 User {user_id} already exists")
                click.echo(f"📧 Email: {existing_user['email']}")
                
                # Try to login with existing user
                click.echo(f"🔐 Logging in {email} to Garmin Connect...")
                api_client = client._get_api_client(user_id)
                login_result = api_client.login(email, password)
                
                if api_client.is_authenticated:
                    click.echo(f"✅ Login successful for {email}")
                    click.echo(f"👤 Username: {api_client.username}")
                    if existing_user['last_sync']:
                        last_sync = existing_user['last_sync'].strftime('%Y-%m-%d %H:%M')
                        click.echo(f"🔄 Last sync: {last_sync}")
                    else:
                        click.echo(f"🔄 Last sync: Never")
                    click.echo(f"💡 Use 'garmy-localdb sync start {user_id}' to sync data")
                else:
                    click.echo(f"❌ Login failed for {email}", err=True)
                    sys.exit(1)
                return
            
            # Create new user
            client.add_user(user_id, email, name, token_path)
            click.echo(f"✅ User {user_id} ({email}) created successfully")
            
            # Login new user
            click.echo(f"🔐 Logging in {email} to Garmin Connect...")
            api_client = client._get_api_client(user_id)
            login_result = api_client.login(email, password)
            
            if api_client.is_authenticated:
                click.echo(f"✅ Login successful for {email}")
                click.echo(f"👤 Username: {api_client.username}")
                click.echo(f"💡 Use 'garmy-localdb sync start {user_id}' to sync data")
            else:
                click.echo(f"❌ Login failed for {email}", err=True)
                sys.exit(1)
                
        except Exception as e:
            if "UNIQUE constraint failed" in str(e):
                click.echo(f"❌ User with email {email} already exists", err=True)
            else:
                click.echo(f"❌ Error setting up user: {e}", err=True)
            sys.exit(1)


@user.command()
@click.pass_context
def list(ctx):
    """List all users."""
    with LocalDBClient(ctx.obj['db_path']) as client:
        users = client.list_users()
        
        if not users:
            click.echo("No users found")
            return
        
        click.echo("Users:")
        for user in users:
            last_sync = user.get('last_sync')
            last_sync_str = last_sync.strftime('%Y-%m-%d %H:%M') if last_sync else 'Never'
            click.echo(f"  {user['user_id']} ({user['email']}) - Last sync: {last_sync_str}")


@user.command()
@click.argument('user_id')
@click.pass_context
def remove(ctx, user_id):
    """Remove a user and all their data."""
    with LocalDBClient(ctx.obj['db_path']) as client:
        if not client.get_user(user_id):
            click.echo(f"❌ User {user_id} not found", err=True)
            sys.exit(1)
        
        if click.confirm(f"Are you sure you want to remove user {user_id} and ALL their data?"):
            client.remove_user(user_id)
            click.echo(f"✅ User {user_id} removed successfully")


@user.command()
@click.argument('user_id')
@click.pass_context
def login(ctx, user_id):
    """Login existing user to Garmin Connect."""
    with LocalDBClient(ctx.obj['db_path']) as client:
        user = client.get_user(user_id)
        if not user:
            click.echo(f"❌ User {user_id} not found", err=True)
            click.echo(f"💡 Use 'garmy-localdb setup-user <email>' to create a new user")
            sys.exit(1)
        
        email = user['email']
        
        # Securely prompt for password
        password = click.prompt(f'Garmin Connect password for {email}', hide_input=True, confirmation_prompt=False)
        
        try:
            # Get API client and try to login
            api_client = client._get_api_client(user_id)
            
            click.echo(f"🔐 Logging in {email} to Garmin Connect...")
            login_result = api_client.login(email, password)
            
            if api_client.is_authenticated:
                click.echo(f"✅ Login successful for {email}")
                click.echo(f"👤 Username: {api_client.username}")
                click.echo(f"💡 You can now sync data for user {user_id}")
            else:
                click.echo(f"❌ Login failed for {email}", err=True)
                sys.exit(1)
                
        except Exception as e:
            click.echo(f"❌ Login error: {e}", err=True)
            sys.exit(1)


@cli.group()
@click.pass_context
def sync(ctx):
    """Data synchronization commands."""
    pass


@sync.command()
@click.argument('user_id')
@click.option('--days', default=30, help='Number of days to check (default: 30)')
@click.option('--start-date', help='Start date (YYYY-MM-DD)')
@click.option('--end-date', help='End date (YYYY-MM-DD)')
@click.pass_context
def efficiency(ctx, user_id, days, start_date, end_date):
    """Check sync efficiency (how much data would be skipped)."""
    with LocalDBClient(ctx.obj['db_path']) as client:
        try:
            user = client.get_user(user_id)
            if not user:
                click.echo(f"❌ User {user_id} not found", err=True)
                sys.exit(1)
            
            # Calculate date range
            if start_date and end_date:
                start = datetime.strptime(start_date, '%Y-%m-%d').date()
                end = datetime.strptime(end_date, '%Y-%m-%d').date()
            else:
                end = date.today()
                start = end - timedelta(days=days-1)
            
            click.echo(f"🔍 Checking sync efficiency for {user_id}")
            click.echo(f"📅 Date range: {start} to {end} ({(end-start).days + 1} days)")
            
            # Get efficiency stats (auto-discovers all available metrics)
            stats = client.get_sync_efficiency_stats(user_id, start, end)
            
            if 'error' in stats:
                click.echo(f"❌ {stats['error']}", err=True)
                click.echo(f"💡 {stats['suggestion']}")
                sys.exit(1)
            
            available_metrics = stats.get('available_metrics', [])
            click.echo(f"📊 Checking {len(available_metrics)} metrics: {', '.join(available_metrics)}")
            
            # Display results
            click.echo("\n📈 Sync Efficiency Analysis:")
            click.echo(f"   Total operations: {stats['total_operations']}")
            click.echo(f"   Already synced: {stats['existing_operations']} ({stats['skip_efficiency']}%)")
            click.echo(f"   Need to sync: {stats['missing_operations']}")
            click.echo(f"   API calls saved: {stats['api_calls_saved']}")
            click.echo(f"   API calls needed: {stats['api_calls_needed']}")
            
            click.echo("\n📊 Per-metric data:")
            for metric, count in stats['metrics'].items():
                total_days = stats['date_range']['days']
                percentage = (count / total_days) * 100 if total_days > 0 else 0
                click.echo(f"   {metric}: {count}/{total_days} days ({percentage:.1f}%)")
            
            if stats['skip_efficiency'] > 80:
                click.echo(f"\n✅ High efficiency! {stats['skip_efficiency']}% of data already exists")
            elif stats['skip_efficiency'] > 50:
                click.echo(f"\n⚠️  Moderate efficiency. {stats['skip_efficiency']}% of data already exists")
            else:
                click.echo(f"\n🚀 Low efficiency. Most data needs to be synced ({stats['missing_operations']} operations)")
                
        except Exception as e:
            click.echo(f"❌ Error checking efficiency: {e}", err=True)
            sys.exit(1)


@sync.command()
@click.argument('user_id')
@click.option('--days', default=7, help='Number of days to sync (from today backwards)')
@click.option('--start-date', help='Start date (YYYY-MM-DD)')
@click.option('--end-date', help='End date (YYYY-MM-DD)')
@click.pass_context
def start(ctx, user_id, days, start_date, end_date):
    """Start data synchronization for ALL available metrics."""
    
    # Parse dates
    if start_date and end_date:
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()
    else:
        end = date.today()
        start = end - timedelta(days=days-1)
    
    async def sync_data():
        with LocalDBClient(ctx.obj['db_path']) as client:
            if not client.get_user(user_id):
                click.echo(f"❌ User {user_id} not found", err=True)
                return
            
            # Initialize tqdm progress bar
            pbar = None
            
            def progress_callback(progress):
                nonlocal pbar
                
                # Initialize progress bar on first call
                if pbar is None:
                    total_ops = progress.total_dates * progress.total_metrics
                    pbar = tqdm(
                        total=total_ops,
                        desc="Синхронизация",
                        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]"
                    )
                
                # Update progress bar
                if progress.current_metric and progress.current_date:
                    desc = f"{progress.current_metric} за {progress.current_date}"
                    pbar.set_description(desc[:50])  # Limit description length
                
                # Update position
                current_ops = progress.completed_metrics
                if current_ops > pbar.n:
                    pbar.update(current_ops - pbar.n)
            
            try:
                # Always sync ALL available metrics
                click.echo(f"🔄 Auto-syncing ALL available metrics for {user_id}")
                click.echo(f"📅 Date range: {start} to {end}")
                result = await client.sync_user_data(user_id, start, end, progress_callback)
                
                # Close progress bar
                if pbar:
                    pbar.close()
                
                click.echo("✅ Sync completed!")
                click.echo(f"📊 Total records: {result['total_records']}")
                
                if 'available_metrics' in result:
                    available_metrics = result['available_metrics']
                    click.echo(f"📈 Synced metrics: {', '.join(available_metrics)}")
                
                for metric, metric_result in result['metrics_synced'].items():
                    click.echo(f"  {metric}: {metric_result['records_synced']} new, {metric_result['records_updated']} updated")
                
                if result['errors']:
                    click.echo(f"\n⚠️  {len(result['errors'])} errors occurred:")
                    for error in result['errors'][:5]:  # Show first 5 errors
                        click.echo(f"  {error}")
            
            except Exception as e:
                if pbar:
                    pbar.close()
                click.echo(f"❌ Sync failed: {e}", err=True)
    
    asyncio.run(sync_data())


@sync.command()
@click.argument('user_id')
@click.option('--days', default=30, help='Number of recent days to sync')
@click.pass_context
def recent(ctx, user_id, days):
    """Sync recent data (all available metrics for last N days)."""
    
    async def sync_recent():
        with LocalDBClient(ctx.obj['db_path']) as client:
            if not client.get_user(user_id):
                click.echo(f"❌ User {user_id} not found", err=True)
                return
            
            click.echo(f"🔄 Auto-syncing ALL metrics for last {days} days")
            
            # Initialize tqdm progress bar
            pbar = None
            
            def progress_callback(progress):
                nonlocal pbar
                
                # Initialize progress bar on first call
                if pbar is None:
                    total_ops = progress.total_dates * progress.total_metrics
                    pbar = tqdm(
                        total=total_ops,
                        desc="Синхронизация",
                        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]"
                    )
                
                # Update progress bar
                if progress.current_metric and progress.current_date:
                    desc = f"{progress.current_metric} за {progress.current_date}"
                    pbar.set_description(desc[:50])  # Limit description length
                
                # Update position
                current_ops = progress.completed_metrics
                if current_ops > pbar.n:
                    pbar.update(current_ops - pbar.n)
            
            try:
                result = await client.sync_recent_user_data(user_id, days, progress_callback)
                
                # Close progress bar
                if pbar:
                    pbar.close()
                
                click.echo("✅ Recent sync completed!")
                click.echo(f"📊 Total records: {result['total_records']}")
                
                for metric, metric_result in result['metrics_synced'].items():
                    click.echo(f"  {metric}: {metric_result['records_synced']} new, {metric_result['records_updated']} updated")
                
                if result['errors']:
                    click.echo(f"\n⚠️  {len(result['errors'])} errors occurred:")
                    for error in result['errors'][:5]:
                        click.echo(f"  {error}")
            
            except Exception as e:
                if pbar:
                    pbar.close()
                click.echo(f"❌ Recent sync failed: {e}", err=True)
    
    asyncio.run(sync_recent())


@cli.group()
@click.pass_context  
def analytics(ctx):
    """Analytics and reporting commands."""
    pass


@analytics.command()
@click.argument('user_id')
@click.option('--days', default=30, help='Number of days to analyze')
@click.pass_context
def steps(ctx, user_id, days):
    """Show steps analytics for a user."""
    with LocalDBClient(ctx.obj['db_path']) as client:
        if not client.get_user(user_id):
            click.echo(f"❌ User {user_id} not found", err=True)
            return
        
        analytics = client.get_steps_analytics(user_id, days)
        
        if 'error' in analytics:
            click.echo(f"❌ {analytics['error']}", err=True)
            return
        
        period = analytics['period']
        totals = analytics['totals']
        averages = analytics['averages']
        goals = analytics['goals']
        activity = analytics['activity_distribution']
        
        click.echo(f"👟 Steps Analytics for {user_id}")
        click.echo(f"📅 Period: {period['start']} to {period['end']} ({period['days']} days)")
        click.echo()
        click.echo(f"📊 Totals:")
        click.echo(f"  Steps: {totals['steps']:,}")
        click.echo(f"  Distance: {totals['distance_km']:.1f} km")
        click.echo()
        click.echo(f"📈 Daily Averages:")
        click.echo(f"  Steps: {averages['daily_steps']:,}")
        click.echo(f"  Distance: {averages['daily_distance_km']:.1f} km")
        click.echo()
        click.echo(f"🎯 Goal Achievement:")
        click.echo(f"  Days achieved: {goals['days_achieved']}")
        click.echo(f"  Achievement rate: {goals['achievement_rate']:.1f}%")
        click.echo()
        click.echo(f"🚶 Activity Distribution:")
        click.echo(f"  High activity (≥10k): {activity['high_activity_days']} days")
        click.echo(f"  Moderate (5k-10k): {activity['moderate_activity_days']} days")
        click.echo(f"  Low activity (<5k): {activity['low_activity_days']} days")


@analytics.command()
@click.argument('user_id')
@click.option('--days', default=30, help='Number of days to analyze')
@click.pass_context
def sleep(ctx, user_id, days):
    """Show sleep analytics for a user."""
    with LocalDBClient(ctx.obj['db_path']) as client:
        if not client.get_user(user_id):
            click.echo(f"❌ User {user_id} not found", err=True)
            return
        
        analytics = client.get_sleep_analytics(user_id, days)
        
        if 'error' in analytics:
            click.echo(f"❌ {analytics['error']}", err=True)
            return
        
        period = analytics['period']
        averages = analytics['averages']
        quality = analytics['sleep_quality']
        physio = analytics['physiological']
        
        click.echo(f"😴 Sleep Analytics for {user_id}")
        click.echo(f"📅 Period: {period['start']} to {period['end']} ({period['days']} days)")
        click.echo()
        click.echo(f"⏰ Average Sleep:")
        click.echo(f"  Duration: {averages['duration_hours']:.1f} hours")
        click.echo(f"  Deep sleep: {averages['deep_sleep_hours']:.1f} hours")
        click.echo(f"  REM sleep: {averages['rem_sleep_hours']:.1f} hours")
        click.echo(f"  Efficiency: {averages['efficiency_percentage']:.1f}%")
        click.echo()
        click.echo(f"🌟 Sleep Quality:")
        click.echo(f"  Excellent nights: {quality['excellent_nights']}")
        click.echo(f"  Good nights: {quality['good_nights']}")
        click.echo(f"  Poor nights: {quality['poor_nights']}")
        
        if physio['avg_spo2'] or physio['avg_respiration']:
            click.echo()
            click.echo(f"🫁 Physiological:")
            if physio['avg_spo2']:
                click.echo(f"  Average SpO2: {physio['avg_spo2']:.1f}%")
            if physio['avg_respiration']:
                click.echo(f"  Average respiration: {physio['avg_respiration']:.1f} bpm")


@analytics.command()
@click.argument('user_id')
@click.option('--days', default=30, help='Number of days to analyze')
@click.pass_context
def heart_rate(ctx, user_id, days):
    """Show heart rate analytics for a user."""
    with LocalDBClient(ctx.obj['db_path']) as client:
        if not client.get_user(user_id):
            click.echo(f"❌ User {user_id} not found", err=True)
            return
        
        analytics = client.get_heart_rate_analytics(user_id, days)
        
        if 'error' in analytics:
            click.echo(f"❌ {analytics['error']}", err=True)
            return
        
        period = analytics['period']
        averages = analytics['averages']
        trends = analytics['trends']
        
        click.echo(f"❤️ Heart Rate Analytics for {user_id}")
        click.echo(f"📅 Period: {period['start']} to {period['end']} ({period['days']} days)")
        click.echo()
        click.echo(f"📈 Averages:")
        click.echo(f"  Resting HR: {averages['resting_hr']:.1f} bpm")
        click.echo(f"  Max HR: {averages['max_hr']:.1f} bpm")
        click.echo()
        click.echo(f"📊 Trends:")
        
        trend_icon = {"improving": "📈", "declining": "📉", "stable": "➡️"}.get(trends['resting_hr_trend'], "➡️")
        click.echo(f"  Resting HR trend: {trend_icon} {trends['resting_hr_trend'].title()}")


@cli.command()
@click.pass_context
def stats(ctx):
    """Show database statistics."""
    with LocalDBClient(ctx.obj['db_path']) as client:
        stats = client.get_database_stats()
        
        click.echo("📊 Database Statistics")
        click.echo(f"👥 Users: {stats['users']}")
        click.echo(f"📊 Total records: {stats['total_records']}")
        click.echo()
        click.echo("📈 Metrics breakdown:")
        for metric, count in stats['metrics'].items():
            click.echo(f"  {metric}: {count:,} records")


def main():
    """Entry point for garmy-localdb command."""
    cli()


if __name__ == '__main__':
    main()