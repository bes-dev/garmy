#!/usr/bin/env python3
"""Command-line interface for Garmy LocalDB synchronization."""

import argparse
import getpass
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import List, Optional

from .sync import SyncManager
from .progress import ProgressReporter
from .models import MetricType
from .config import LocalDBConfig


def parse_date(date_str: str) -> date:
    """Parse date string in YYYY-MM-DD format."""
    try:
        return date.fromisoformat(date_str)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date format: {date_str}. Use YYYY-MM-DD")


def parse_metrics(metrics_str: str) -> List[MetricType]:
    """Parse comma-separated list of metrics."""
    if not metrics_str:
        return list(MetricType)
    
    metric_names = [name.strip().upper() for name in metrics_str.split(',')]
    metrics = []
    
    for name in metric_names:
        try:
            metric = MetricType[name]
            metrics.append(metric)
        except KeyError:
            available = ', '.join([m.name for m in MetricType])
            raise argparse.ArgumentTypeError(
                f"Invalid metric: {name}. Available: {available}"
            )
    
    return metrics


def get_credentials() -> tuple[str, str]:
    """Safely get Garmin credentials from user input."""
    print("Enter your Garmin Connect credentials:")
    email = input("Email: ").strip()
    
    if not email:
        print("Error: Email cannot be empty")
        sys.exit(1)
    
    password = getpass.getpass("Password: ")
    
    if not password:
        print("Error: Password cannot be empty")
        sys.exit(1)
    
    return email, password


def cmd_sync(args) -> int:
    """Execute sync command."""
    try:
        # Determine date range
        if args.last_days:
            end_date = date.today()
            start_date = end_date - timedelta(days=args.last_days - 1)
        elif args.date_range:
            start_date, end_date = args.date_range
        else:
            # Default: last 7 days
            end_date = date.today()
            start_date = end_date - timedelta(days=6)
        
        print(f"Syncing data from {start_date} to {end_date}")

        # Setup progress reporter
        progress_reporter = ProgressReporter(use_tqdm=args.progress == 'tqdm')

        # Initialize sync manager
        config = LocalDBConfig()
        manager = SyncManager(
            db_path=args.db_path,
            config=config,
            progress_reporter=progress_reporter
        )

        # Try to initialize with saved tokens first
        print("Connecting to Garmin Connect...")
        try:
            manager.initialize()
            print("Using saved authentication tokens")
        except RuntimeError:
            # No valid tokens, prompt for credentials
            email, password = get_credentials()
            manager.initialize(email, password)
        
        # Parse metrics
        metrics = parse_metrics(args.metrics) if args.metrics else list(MetricType)
        
        print(f"Syncing metrics: {', '.join([m.name for m in metrics])}")
        
        # Execute sync
        stats = manager.sync_range(
            user_id=args.user_id,
            start_date=start_date,
            end_date=end_date,
            metrics=metrics
        )
        
        # Print results
        print(f"\nSync completed!")
        print(f"  Completed: {stats['completed']}")
        print(f"  Skipped: {stats['skipped']}")
        print(f"  Failed: {stats['failed']}")
        print(f"  Total tasks: {stats['total_tasks']}")
        
        return 0 if stats['failed'] == 0 else 1
        
    except KeyboardInterrupt:
        print("\nSync interrupted by user")
        return 130
    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_status(args) -> int:
    """Show sync status."""
    try:
        from .db import HealthDB
        
        db = HealthDB(args.db_path)
        
        # Show overall statistics
        with db.get_session() as session:
            from .models import SyncStatus
            
            # Count by status
            status_counts = {}
            from sqlalchemy import func
            all_statuses = session.query(SyncStatus.status, 
                                       func.count(SyncStatus.status)).group_by(SyncStatus.status).all()
            
            for status, count in all_statuses:
                status_counts[status] = count
            
            print("=== SYNC STATUS OVERVIEW ===")
            for status in ['completed', 'pending', 'failed', 'skipped']:
                count = status_counts.get(status, 0)
                print(f"{status.capitalize()}: {count}")
            
            # Show failed records if any
            if status_counts.get('failed', 0) > 0:
                print(f"\n=== FAILED RECORDS ===")
                failed_records = session.query(SyncStatus).filter(
                    SyncStatus.status == 'failed'
                ).order_by(SyncStatus.sync_date.desc()).limit(10).all()
                
                for record in failed_records:
                    print(f"{record.sync_date} {record.metric_type}: {record.error_message}")
            
            # Show recent activity
            print(f"\n=== RECENT SYNC ACTIVITY ===")
            recent_records = session.query(SyncStatus).filter(
                SyncStatus.synced_at.isnot(None)
            ).order_by(SyncStatus.synced_at.desc()).limit(5).all()
            
            for record in recent_records:
                print(f"{record.synced_at} {record.sync_date} {record.metric_type}: {record.status}")
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_reset(args) -> int:
    """Reset failed sync statuses to pending."""
    try:
        from .db import HealthDB
        
        db = HealthDB(args.db_path)
        
        with db.get_session() as session:
            from .models import SyncStatus
            
            # Count failed records
            failed_count = session.query(SyncStatus).filter(SyncStatus.status == 'failed').count()
            
            if failed_count == 0:
                print("No failed records found")
                return 0
            
            # Confirm reset
            if not args.force:
                response = input(f"Reset {failed_count} failed records to pending? (y/N): ")
                if response.lower() != 'y':
                    print("Reset cancelled")
                    return 0
            
            # Reset failed to pending
            updated = session.query(SyncStatus).filter(SyncStatus.status == 'failed').update({
                'status': 'pending',
                'error_message': None,
                'synced_at': None
            })
            
            session.commit()
            print(f"Reset {updated} failed records to pending")
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        return 1


def create_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Garmy LocalDB - Synchronize Garmin health data to local database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s sync --last-days 7                    # Sync last 7 days
  %(prog)s sync --date-range 2024-01-01 2024-01-31  # Sync date range
  %(prog)s sync --metrics DAILY_SUMMARY,SLEEP    # Sync specific metrics
  %(prog)s status                                 # Show sync status
  %(prog)s reset --force                         # Reset failed records
        """
    )
    
    # Global options
    parser.add_argument('--db-path', type=Path, default=Path('health.db'),
                       help='Path to SQLite database file (default: health.db)')
    parser.add_argument('--user-id', type=int, default=1,
                       help='User ID for database records (default: 1)')
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Sync command
    sync_parser = subparsers.add_parser('sync', help='Synchronize data from Garmin Connect')
    
    # Date range options (mutually exclusive)
    date_group = sync_parser.add_mutually_exclusive_group()
    date_group.add_argument('--last-days', type=int, metavar='N',
                           help='Sync data for last N days')
    date_group.add_argument('--date-range', nargs=2, type=parse_date, 
                           metavar=('START', 'END'),
                           help='Sync data between START and END dates (YYYY-MM-DD)')
    
    # Sync options
    sync_parser.add_argument('--metrics', type=str,
                            help='Comma-separated list of metrics to sync (default: all)')
    sync_parser.add_argument('--progress', choices=['tqdm', 'simple', 'silent'], 
                            default='tqdm',
                            help='Progress display mode (default: tqdm)')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show synchronization status')
    
    # Reset command
    reset_parser = subparsers.add_parser('reset', help='Reset failed sync records to pending')
    reset_parser.add_argument('--force', action='store_true',
                             help='Reset without confirmation prompt')
    
    return parser


def main() -> int:
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Execute command
    if args.command == 'sync':
        return cmd_sync(args)
    elif args.command == 'status':
        return cmd_status(args)
    elif args.command == 'reset':
        return cmd_reset(args)
    else:
        print(f"Unknown command: {args.command}")
        return 1


if __name__ == '__main__':
    sys.exit(main())