#!/usr/bin/env python3
"""Command-line interface for Garmy LocalDB synchronization."""

import argparse
import getpass
import os
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import List, Optional, Tuple

from .config import LocalDBConfig
from .models import MetricType
from .progress import ProgressReporter
from .sync import SyncManager


def resolve_paths(args: argparse.Namespace) -> Tuple[Path, Optional[str]]:
    """Resolve database path and token directory from arguments.

    Priority for profile path:
    1. --profile-path CLI argument
    2. GARMY_PROFILE_PATH environment variable

    When profile path is set:
    - db_path = <profile>/health.db
    - token_dir = <profile>/

    When profile path is not set:
    - db_path = --db-path argument or default (health.db)
    - token_dir = None (uses default ~/.garmy/)

    Args:
        args: Parsed command-line arguments

    Returns:
        Tuple of (db_path, token_dir)
    """
    # Check for profile path (CLI takes precedence over env var)
    profile_path = args.profile_path
    if profile_path is None:
        env_profile = os.getenv("GARMY_PROFILE_PATH")
        if env_profile:
            profile_path = Path(env_profile).expanduser()

    if profile_path:
        # Use profile path for both database and tokens
        profile_path = Path(profile_path).expanduser()
        db_path = profile_path / "health.db"
        token_dir = str(profile_path)
        return db_path, token_dir
    else:
        # Use individual paths
        db_path = args.db_path if args.db_path else Path("health.db")
        token_dir = None  # Will use default ~/.garmy/
        return db_path, token_dir


def parse_date(date_str: str) -> date:
    """Parse date string in YYYY-MM-DD format."""
    try:
        return date.fromisoformat(date_str)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Invalid date format: {date_str}. Use YYYY-MM-DD"
        )


def parse_metrics(metrics_str: str) -> List[MetricType]:
    """Parse comma-separated list of metrics."""
    if not metrics_str:
        return list(MetricType)

    metric_names = [name.strip().upper() for name in metrics_str.split(",")]
    metrics = []

    for name in metric_names:
        try:
            metric = MetricType[name]
            metrics.append(metric)
        except KeyError:
            available = ", ".join([m.name for m in MetricType])
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
        # Resolve paths from profile or individual arguments
        db_path, token_dir = resolve_paths(args)

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
        print(f"Database: {db_path}")

        # Setup progress reporter
        progress_reporter = ProgressReporter(use_tqdm=args.progress == "tqdm")

        # Initialize sync manager
        config = LocalDBConfig()
        manager = SyncManager(
            db_path=db_path,
            config=config,
            progress_reporter=progress_reporter,
            token_dir=token_dir,
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
            metrics=metrics,
            resync_days=args.resync_days,
        )

        # Print results
        print(f"\nSync completed!")
        print(f"  Completed: {stats['completed']}")
        print(f"  Skipped: {stats['skipped']}")
        print(f"  Failed: {stats['failed']}")
        print(f"  Total tasks: {stats['total_tasks']}")

        return 0 if stats["failed"] == 0 else 1

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

        # Resolve paths from profile or individual arguments
        db_path, _ = resolve_paths(args)
        db = HealthDB(db_path)

        # Show overall statistics
        with db.get_session() as session:
            from .models import SyncStatus

            # Count by status
            status_counts = {}
            from sqlalchemy import func

            all_statuses = (
                session.query(SyncStatus.status, func.count(SyncStatus.status))
                .group_by(SyncStatus.status)
                .all()
            )

            for status, count in all_statuses:
                status_counts[status] = count

            print("=== SYNC STATUS OVERVIEW ===")
            for status in ["completed", "pending", "failed", "skipped"]:
                count = status_counts.get(status, 0)
                print(f"{status.capitalize()}: {count}")

            # Show failed records if any
            if status_counts.get("failed", 0) > 0:
                print(f"\n=== FAILED RECORDS ===")
                failed_records = (
                    session.query(SyncStatus)
                    .filter(SyncStatus.status == "failed")
                    .order_by(SyncStatus.sync_date.desc())
                    .limit(10)
                    .all()
                )

                for record in failed_records:
                    print(
                        f"{record.sync_date} {record.metric_type}: {record.error_message}"
                    )

            # Show recent activity
            print(f"\n=== RECENT SYNC ACTIVITY ===")
            recent_records = (
                session.query(SyncStatus)
                .filter(SyncStatus.synced_at.isnot(None))
                .order_by(SyncStatus.synced_at.desc())
                .limit(5)
                .all()
            )

            for record in recent_records:
                print(
                    f"{record.synced_at} {record.sync_date} {record.metric_type}: {record.status}"
                )

            # Show activity details backfill status
            from sqlalchemy import and_

            from .models import Activity

            total_activities = (
                session.query(Activity).filter(Activity.user_id == args.user_id).count()
            )

            backfilled = (
                session.query(Activity)
                .filter(
                    and_(
                        Activity.user_id == args.user_id,
                        Activity.details_synced == True,  # noqa: E712
                    )
                )
                .count()
            )

            pending = total_activities - backfilled

            print(f"\n=== ACTIVITY DETAILS BACKFILL ===")
            print(f"Total activities: {total_activities}")
            print(f"Details synced: {backfilled}")
            print(f"Pending backfill: {pending}")
            if total_activities > 0:
                print(f"Progress: {backfilled / total_activities * 100:.1f}%")

        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_reset(args) -> int:
    """Reset failed sync statuses to pending."""
    try:
        from .db import HealthDB

        # Resolve paths from profile or individual arguments
        db_path, _ = resolve_paths(args)
        db = HealthDB(db_path)

        with db.get_session() as session:
            from .models import SyncStatus

            # Count failed records
            failed_count = (
                session.query(SyncStatus).filter(SyncStatus.status == "failed").count()
            )

            if failed_count == 0:
                print("No failed records found")
                return 0

            # Confirm reset
            if not args.force:
                response = input(
                    f"Reset {failed_count} failed records to pending? (y/N): "
                )
                if response.lower() != "y":
                    print("Reset cancelled")
                    return 0

            # Reset failed to pending
            updated = (
                session.query(SyncStatus)
                .filter(SyncStatus.status == "failed")
                .update({"status": "pending", "error_message": None, "synced_at": None})
            )

            session.commit()
            print(f"Reset {updated} failed records to pending")

        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_backfill(args) -> int:
    """Backfill activity details for existing activities."""
    try:
        # Resolve paths from profile or individual arguments
        db_path, token_dir = resolve_paths(args)

        # Setup progress reporter
        progress_reporter = ProgressReporter(use_tqdm=args.progress == "tqdm")

        # Initialize sync manager
        config = LocalDBConfig()
        manager = SyncManager(
            db_path=db_path,
            config=config,
            progress_reporter=progress_reporter,
            token_dir=token_dir,
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

        print(f"\nBackfilling activity details (limit: {args.limit} activities)")

        # Execute backfill
        stats = manager.backfill_activity_details(
            user_id=args.user_id, limit=args.limit
        )

        # Print results
        print(f"\nBackfill completed!")
        print(f"  Total activities: {stats['total']}")
        print(f"  Completed: {stats['completed']}")
        print(f"  Failed: {stats['failed']}")

        return 0 if stats["failed"] == 0 else 1

    except KeyboardInterrupt:
        print("\nBackfill interrupted by user")
        return 130
    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_backfill_splits(args) -> int:
    """Backfill splits for cardio activities."""
    try:
        # Resolve paths from profile or individual arguments
        db_path, token_dir = resolve_paths(args)

        # Setup progress reporter
        progress_reporter = ProgressReporter(use_tqdm=args.progress == "tqdm")

        # Initialize sync manager
        config = LocalDBConfig()
        manager = SyncManager(
            db_path=db_path,
            config=config,
            progress_reporter=progress_reporter,
            token_dir=token_dir,
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

        print(f"\nBackfilling splits for cardio activities (limit: {args.limit})")

        # Execute backfill
        stats = manager.backfill_activity_splits(user_id=args.user_id, limit=args.limit)

        # Print results
        print(f"\nSplits backfill completed!")
        print(f"  Total activities: {stats['total']}")
        print(f"  Completed: {stats['completed']}")
        print(f"  Skipped: {stats['skipped']}")
        print(f"  Failed: {stats['failed']}")

        return 0 if stats["failed"] == 0 else 1

    except KeyboardInterrupt:
        print("\nBackfill interrupted by user")
        return 130
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
  %(prog)s sync --profile-path ~/profiles/user1  # Sync using profile directory
  %(prog)s status                                 # Show sync status
  %(prog)s reset --force                         # Reset failed records
  %(prog)s backfill --limit 50                   # Backfill activity details
  %(prog)s backfill-splits --limit 50            # Backfill splits for cardio

Environment Variables:
  GARMY_PROFILE_PATH    Profile directory path (contains tokens and database)
        """,
    )

    # Global options
    parser.add_argument(
        "--profile-path",
        type=Path,
        default=None,
        help="Path to profile directory containing tokens and database. "
        "When set, uses <profile>/health.db for database and <profile>/ for tokens. "
        "Can also be set via GARMY_PROFILE_PATH environment variable.",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=None,
        help="Path to SQLite database file. If --profile-path is set, this is ignored. "
        "(default: health.db in current directory or profile directory)",
    )
    parser.add_argument(
        "--user-id",
        type=int,
        default=1,
        help="User ID for database records (default: 1)",
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Sync command
    sync_parser = subparsers.add_parser(
        "sync", help="Synchronize data from Garmin Connect"
    )

    # Date range options (mutually exclusive)
    date_group = sync_parser.add_mutually_exclusive_group()
    date_group.add_argument(
        "--last-days", type=int, metavar="N", help="Sync data for last N days"
    )
    date_group.add_argument(
        "--date-range",
        nargs=2,
        type=parse_date,
        metavar=("START", "END"),
        help="Sync data between START and END dates (YYYY-MM-DD)",
    )

    # Sync options
    sync_parser.add_argument(
        "--metrics",
        type=str,
        help="Comma-separated list of metrics to sync (default: all)",
    )
    sync_parser.add_argument(
        "--resync-days",
        type=int,
        default=0,
        metavar="N",
        help="Force re-sync of the last N days even if already completed. "
        "Useful for updating partial data from earlier syncs (default: 0)",
    )
    sync_parser.add_argument(
        "--progress",
        choices=["tqdm", "simple", "silent"],
        default="tqdm",
        help="Progress display mode (default: tqdm)",
    )

    # Status command
    status_parser = subparsers.add_parser("status", help="Show synchronization status")

    # Reset command
    reset_parser = subparsers.add_parser(
        "reset", help="Reset failed sync records to pending"
    )
    reset_parser.add_argument(
        "--force", action="store_true", help="Reset without confirmation prompt"
    )

    # Backfill command
    backfill_parser = subparsers.add_parser(
        "backfill", help="Backfill activity details for existing activities"
    )
    backfill_parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum number of activities to process (default: 100)",
    )
    backfill_parser.add_argument(
        "--progress",
        choices=["tqdm", "simple", "silent"],
        default="tqdm",
        help="Progress display mode (default: tqdm)",
    )

    # Backfill splits command
    backfill_splits_parser = subparsers.add_parser(
        "backfill-splits", help="Backfill splits/laps for cardio activities"
    )
    backfill_splits_parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum number of activities to process (default: 100)",
    )
    backfill_splits_parser.add_argument(
        "--progress",
        choices=["tqdm", "simple", "silent"],
        default="tqdm",
        help="Progress display mode (default: tqdm)",
    )

    return parser


def main() -> int:
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Execute command
    if args.command == "sync":
        return cmd_sync(args)
    elif args.command == "status":
        return cmd_status(args)
    elif args.command == "reset":
        return cmd_reset(args)
    elif args.command == "backfill":
        return cmd_backfill(args)
    elif args.command == "backfill-splits":
        return cmd_backfill_splits(args)
    else:
        print(f"Unknown command: {args.command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
