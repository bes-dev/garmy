"""Command-line interface for local database management."""

import asyncio
import json
import sys
import warnings
import logging
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import List, Optional
import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.layout import Layout
import time

# Suppress discovery warnings about shared endpoints
warnings.filterwarnings("ignore", message="Endpoint shared by multiple metrics")

# Configure logging to show warnings and errors
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

from ..auth.client import AuthClient
from ..core.client import APIClient
from .client import LocalDBClient
from .config import LocalDBConfig, SyncConfig, UserConfig
from .sync import SyncProgress, SyncStatus
from .exceptions import LocalDBError, UserNotFoundError


class LocalDBCLI:
    """CLI interface for local database operations."""
    
    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.console = Console()
        self.db_path = db_path or Path.home() / ".garmy" / "localdb"
        self.config = LocalDBConfig.default(self.db_path)
        self.local_client: Optional[LocalDBClient] = None
    
    def _get_client(self) -> LocalDBClient:
        """Get or create local client."""
        if self.local_client is None:
            self.local_client = LocalDBClient(self.config)
            self.local_client.open()
        return self.local_client
    
    def cleanup(self) -> None:
        """Clean up resources."""
        if self.local_client is not None:
            self.local_client.close()
            self.local_client = None
    
    def setup_user(self, email: str, display_name: Optional[str] = None) -> str:
        """Set up a new user or update existing one."""
        try:
            # Authenticate with Garmin
            auth_client = AuthClient()
            
            self.console.print("🔐 Authenticating with Garmin Connect...")
            password = click.prompt("Password", hide_input=True)
            
            auth_client.login(email, password)
            
            # Create user config
            user_id = email.replace("@", "_").replace(".", "_")
            user_config = UserConfig(
                user_id=user_id,
                email=email,
                display_name=display_name or email,
                created_at=datetime.now(),
                auth_token_path=str(Path.home() / ".garmy"),
            )
            
            # Add to local database using context manager
            with LocalDBClient(self.config) as client:
                client.add_user(user_config)
            
            self.console.print(f"✅ User {email} added successfully!", style="green")
            return user_id
            
        except Exception as e:
            self.console.print(f"❌ Failed to setup user: {e}", style="red")
            raise
    
    def list_users(self) -> None:
        """List all configured users."""
        try:
            with LocalDBClient(self.config) as client:
                users = client.list_users()
                
                if not users:
                    self.console.print("No users configured.", style="yellow")
                    return
                
                table = Table(title="Configured Users")
                table.add_column("User ID", style="cyan")
                table.add_column("Email", style="green")
                table.add_column("Display Name", style="blue")
                table.add_column("Last Sync", style="magenta")
                table.add_column("Created", style="dim")
                
                for user in users:
                    last_sync = user.last_sync.strftime("%Y-%m-%d %H:%M") if user.last_sync else "Never"
                    created = user.created_at.strftime("%Y-%m-%d") if user.created_at else "Unknown"
                    
                    table.add_row(
                        user.user_id,
                        user.email,
                        user.display_name or "",
                        last_sync,
                        created,
                    )
                
                self.console.print(table)
            
        except Exception as e:
            self.console.print(f"❌ Failed to list users: {e}", style="red")
    
    def remove_user(self, user_id: str, confirm: bool = False) -> None:
        """Remove a user and all their data."""
        try:
            if not confirm:
                self.console.print(f"⚠️  This will remove user {user_id} and ALL their data!", style="red")
                if not click.confirm("Are you sure?"):
                    return
            
            with LocalDBClient(self.config) as client:
                client.remove_user(user_id)
            
            self.console.print(f"✅ User {user_id} removed successfully!", style="green")
            
        except UserNotFoundError:
            self.console.print(f"❌ User {user_id} not found.", style="red")
        except Exception as e:
            self.console.print(f"❌ Failed to remove user: {e}", style="red")
    
    def start_sync(
        self,
        user_id: str,
        start_date: str,
        end_date: str,
        metrics: Optional[List[str]] = None,
        batch_size: int = 50,
        background: bool = False,
        chronological: bool = False,
    ) -> None:
        """Start data synchronization for a user."""
        try:
            client = self._get_client()
            
            # Parse dates
            start_dt = date.fromisoformat(start_date)
            end_dt = date.fromisoformat(end_date)
            
            # Create sync config
            sync_config = SyncConfig(
                user_id=user_id,
                start_date=start_dt,
                end_date=end_dt,
                metrics=metrics or [
                    "sleep", "heart_rate", "body_battery", "stress", "hrv",
                    "respiration", "training_readiness", "activities",
                    "steps", "calories", "daily_summary"
                ],
                batch_size=batch_size,
                auto_resume=True,
                incremental=True,
                reverse_chronological=not chronological,  # Default is reverse (newest first)
            )
            
            # Start sync
            sync_id = asyncio.run(client.start_sync(sync_config))
            
            order_info = "chronological (oldest first)" if chronological else "reverse chronological (newest first)"
            self.console.print(f"🚀 Started sync {sync_id} for user {user_id}", style="green")
            self.console.print(f"📅 Order: {order_info}", style="dim")
            
            if not background:
                # Monitor sync progress
                asyncio.run(self._monitor_sync(client, sync_id))
            else:
                self.console.print(f"💼 Sync running in background. Use 'garmy-localdb status {sync_id}' to monitor.")
            
        except Exception as e:
            self.console.print(f"❌ Failed to start sync: {e}", style="red")
    
    def sync_status(self, sync_id: Optional[str] = None) -> None:
        """Show sync status."""
        try:
            with LocalDBClient(self.config) as client:
                if sync_id:
                    # Show specific sync
                    progress = client.get_sync_progress(sync_id)
                    if progress:
                        self._display_sync_progress(progress)
                    else:
                        # Try to find in storage as well
                        self.console.print(f"❌ Sync {sync_id} not found in active syncs.", style="red")
                        self.console.print("💡 Checking database for completed/failed syncs...", style="dim")
                        
                        # Check if sync exists in storage
                        for user_config in client.storage.list_users():
                            status_data = client.storage.get_sync_status(user_config.user_id, sync_id)
                            if status_data:
                                from .sync import SyncProgress
                                progress = SyncProgress.from_dict(status_data)
                                self.console.print(f"📋 Found {sync_id} in storage:", style="blue")
                                self._display_sync_progress(progress)
                                return
                        
                        self.console.print(f"🔍 Sync {sync_id} not found anywhere.", style="yellow")
                else:
                    # Show all active syncs
                    active_syncs = client.list_active_syncs()
                    if not active_syncs:
                        self.console.print("No active syncs.", style="yellow")
                        return
                    
                    for progress in active_syncs:
                        self._display_sync_progress(progress)
                        self.console.print()
            
        except Exception as e:
            self.console.print(f"❌ Failed to get sync status: {e}", style="red")
    
    def pause_sync(self, sync_id: str) -> None:
        """Pause a running sync."""
        try:
            client = self._get_client()
            asyncio.run(client.pause_sync(sync_id))
            self.console.print(f"⏸️  Paused sync {sync_id}", style="yellow")
        except Exception as e:
            self.console.print(f"❌ Failed to pause sync: {e}", style="red")
    
    def resume_sync(self, sync_id: str) -> None:
        """Resume a paused sync."""
        try:
            client = self._get_client()
            asyncio.run(client.resume_sync(sync_id))
            self.console.print(f"▶️  Resumed sync {sync_id}", style="green")
        except Exception as e:
            self.console.print(f"❌ Failed to resume sync: {e}", style="red")
    
    def stop_sync(self, sync_id: str) -> None:
        """Stop a running sync."""
        try:
            client = self._get_client()
            asyncio.run(client.stop_sync(sync_id))
            self.console.print(f"⏹️  Stopped sync {sync_id}", style="red")
        except Exception as e:
            self.console.print(f"❌ Failed to stop sync: {e}", style="red")
    
    def query_data(
        self,
        user_id: str,
        metric: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        output_format: str = "table",
    ) -> None:
        """Query local data."""
        try:
            with LocalDBClient(self.config) as client:
                # Get available dates
                dates = client.list_metric_dates(
                    user_id, metric, start_date, end_date
                )
                
                if not dates:
                    self.console.print(f"No data found for {metric}", style="yellow")
                    return
                
                if output_format == "json":
                    # Output as JSON
                    data = {}
                    for date_str in dates:
                        metric_data = client.get_metric_data(user_id, metric, date_str)
                        if metric_data:
                            data[date_str] = metric_data
                    self.console.print(json.dumps(data, indent=2))
                else:
                    # Output as table
                    table = Table(title=f"{metric.title()} Data for {user_id}")
                    table.add_column("Date", style="cyan")
                    table.add_column("Data Available", style="green")
                    
                    for date_str in dates[-10:]:  # Show last 10 dates
                        metric_data = client.get_metric_data(user_id, metric, date_str)
                        available = "✅" if metric_data else "❌"
                        table.add_row(date_str, available)
                    
                    self.console.print(table)
                    
                    if len(dates) > 10:
                        self.console.print(f"... and {len(dates) - 10} more dates")
            
        except Exception as e:
            self.console.print(f"❌ Failed to query data: {e}", style="red")
    
    def database_stats(self) -> None:
        """Show database statistics."""
        try:
            with LocalDBClient(self.config) as client:
                stats = client.get_database_stats()
                
                # General stats
                self.console.print(Panel.fit(
                    f"Database Path: {stats['db_path']}\n"
                    f"Users: {stats['users_count']}\n"
                    f"Compression: {'Enabled' if stats['compression_enabled'] else 'Disabled'}",
                    title="Database Statistics",
                    style="blue"
                ))
                
                # User data counts
                if stats['user_data_counts']:
                    table = Table(title="User Data Counts")
                    table.add_column("User ID", style="cyan")
                    table.add_column("Data Records", style="green")
                    
                    for user_id, count in stats['user_data_counts'].items():
                        table.add_row(user_id, str(count))
                    
                    self.console.print(table)
            
        except Exception as e:
            self.console.print(f"❌ Failed to get database stats: {e}", style="red")
    
    def debug_sync(self, sync_id: str) -> None:
        """Debug a specific sync operation."""
        try:
            with LocalDBClient(self.config) as client:
                self.console.print(f"🔍 Debugging sync {sync_id}...", style="blue")
                
                # Check active syncs
                active_syncs = client.list_active_syncs()
                found_active = any(s.sync_id == sync_id for s in active_syncs)
                self.console.print(f"Active syncs: {found_active}")
                
                # Check storage for all users
                for user_config in client.storage.list_users():
                    status_data = client.storage.get_sync_status(user_config.user_id, sync_id)
                    if status_data:
                        self.console.print(f"📋 Found in storage for user {user_config.user_id}:")
                        self.console.print(json.dumps(status_data, indent=2))
                    
                    checkpoint_data = client.storage.get_sync_checkpoint(user_config.user_id, sync_id)
                    if checkpoint_data:
                        self.console.print(f"🔄 Checkpoint for user {user_config.user_id}:")
                        self.console.print(json.dumps(checkpoint_data, indent=2))
                
        except Exception as e:
            self.console.print(f"❌ Debug failed: {e}", style="red")
    
    def _display_sync_progress(self, progress: SyncProgress) -> None:
        """Display sync progress information."""
        # Status color
        status_colors = {
            SyncStatus.PENDING: "yellow",
            SyncStatus.RUNNING: "blue",
            SyncStatus.PAUSED: "orange",
            SyncStatus.COMPLETED: "green",
            SyncStatus.FAILED: "red",
            SyncStatus.INTERRUPTED: "magenta",
        }
        
        status_color = status_colors.get(progress.status, "white")
        
        # Create progress info
        lines = [
            f"Sync ID: {progress.sync_id}",
            f"User: {progress.user_id}",
            f"Status: {progress.status.value.title()}",
            f"Progress: {progress.completed_days}/{progress.total_days} days ({progress.progress_percentage:.1f}%)",
            f"Total Metrics: {progress.total_metrics}",
        ]
        
        if progress.current_metric:
            lines.append(f"Current Metric: {progress.current_metric}")
        
        if progress.current_date:
            lines.append(f"Current Date: {progress.current_date}")
        
        if progress.elapsed_time:
            lines.append(f"Elapsed: {progress.elapsed_time}")
        
        if progress.estimated_completion and progress.status == SyncStatus.RUNNING:
            eta = progress.estimated_completion.strftime("%H:%M:%S")
            lines.append(f"ETA: {eta}")
        
        if progress.error_message:
            lines.append(f"Error: {progress.error_message}")
        
        self.console.print(Panel(
            "\n".join(lines),
            title=f"Sync Progress",
            style=status_color,
        ))
    
    async def _monitor_sync(self, client: LocalDBClient, sync_id: str) -> None:
        """Monitor sync progress in real-time."""
        last_progress = None
        
        with Live(console=self.console, refresh_per_second=2) as live:
            while True:
                progress = client.get_sync_progress(sync_id)
                
                if progress is None:
                    live.update("Sync not found")
                    break
                
                # Create progress display
                layout = Layout()
                
                # Progress bars
                overall_progress = Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TaskProgressColumn(),
                )
                
                # Overall progress
                overall_task = overall_progress.add_task(
                    "Overall Progress", 
                    total=progress.total_days,
                    completed=progress.completed_days
                )
                
                # Metric progress
                metric_task = overall_progress.add_task(
                    f"Metrics ({progress.current_metric or 'N/A'})",
                    total=progress.total_metrics,
                    completed=progress.completed_metrics
                )
                
                # Status panel
                status_text = Text()
                status_text.append(f"Sync ID: {progress.sync_id}\n")
                status_text.append(f"User: {progress.user_id}\n")
                status_text.append(f"Status: {progress.status.value.title()}\n")
                
                if progress.current_date:
                    status_text.append(f"Current Date: {progress.current_date}\n")
                
                if progress.elapsed_time:
                    status_text.append(f"Elapsed: {progress.elapsed_time}\n")
                
                if progress.estimated_completion and progress.status == SyncStatus.RUNNING:
                    eta = progress.estimated_completion.strftime("%H:%M:%S")
                    status_text.append(f"ETA: {eta}\n")
                
                status_panel = Panel(status_text, title="Sync Status")
                
                # Combine layout
                layout.split_column(
                    Layout(status_panel, size=8),
                    Layout(overall_progress, size=4),
                )
                
                live.update(layout)
                
                # Check if sync is finished
                if progress.status in [SyncStatus.COMPLETED, SyncStatus.FAILED]:
                    break
                
                last_progress = progress
                await asyncio.sleep(1)
        
        # Final status
        if last_progress:
            if last_progress.status == SyncStatus.COMPLETED:
                self.console.print("✅ Sync completed successfully!", style="green")
            elif last_progress.status == SyncStatus.FAILED:
                self.console.print(f"❌ Sync failed: {last_progress.error_message}", style="red")


# Click CLI commands
@click.group()
@click.option("--db-path", type=click.Path(), help="Database path")
@click.pass_context
def cli(ctx: click.Context, db_path: Optional[str]) -> None:
    """Garmin Local Database CLI."""
    ctx.ensure_object(dict)
    ctx.obj["cli"] = LocalDBCLI(Path(db_path) if db_path else None)


@cli.command()
@click.argument("email")
@click.option("--name", help="Display name")
@click.pass_context
def setup_user(ctx: click.Context, email: str, name: Optional[str]) -> None:
    """Set up a new user."""
    cli_obj = ctx.obj["cli"]
    cli_obj.setup_user(email, name)


@cli.command()
@click.pass_context
def list_users(ctx: click.Context) -> None:
    """List all users."""
    cli_obj = ctx.obj["cli"]
    cli_obj.list_users()


@cli.command()
@click.argument("user_id")
@click.option("--yes", is_flag=True, help="Skip confirmation")
@click.pass_context
def remove_user(ctx: click.Context, user_id: str, yes: bool) -> None:
    """Remove a user and all their data."""
    cli_obj = ctx.obj["cli"]
    cli_obj.remove_user(user_id, yes)


@cli.command()
@click.argument("user_id")
@click.argument("start_date")
@click.argument("end_date")
@click.option("--metrics", multiple=True, help="Metrics to sync")
@click.option("--batch-size", default=50, help="Batch size")
@click.option("--background", is_flag=True, help="Run in background")
@click.option("--chronological", is_flag=True, help="Sync in chronological order (oldest first). Default is reverse chronological (newest first).")
@click.pass_context
def sync(
    ctx: click.Context,
    user_id: str,
    start_date: str,
    end_date: str,
    metrics: tuple,
    batch_size: int,
    background: bool,
    chronological: bool,
) -> None:
    """Start data synchronization."""
    cli_obj = ctx.obj["cli"]
    cli_obj.start_sync(
        user_id, 
        start_date, 
        end_date, 
        list(metrics) if metrics else None,
        batch_size,
        background,
        chronological,
    )


@cli.command()
@click.argument("sync_id", required=False)
@click.pass_context
def status(ctx: click.Context, sync_id: Optional[str]) -> None:
    """Show sync status."""
    cli_obj = ctx.obj["cli"]
    cli_obj.sync_status(sync_id)


@cli.command()
@click.argument("sync_id")
@click.pass_context
def pause(ctx: click.Context, sync_id: str) -> None:
    """Pause a sync."""
    cli_obj = ctx.obj["cli"]
    cli_obj.pause_sync(sync_id)


@cli.command()
@click.argument("sync_id")
@click.pass_context
def resume(ctx: click.Context, sync_id: str) -> None:
    """Resume a sync."""
    cli_obj = ctx.obj["cli"]
    cli_obj.resume_sync(sync_id)


@cli.command()
@click.argument("sync_id")
@click.pass_context
def stop(ctx: click.Context, sync_id: str) -> None:
    """Stop a sync."""
    cli_obj = ctx.obj["cli"]
    cli_obj.stop_sync(sync_id)


@cli.command()
@click.argument("user_id")
@click.argument("metric")
@click.option("--start-date", help="Start date (YYYY-MM-DD)")
@click.option("--end-date", help="End date (YYYY-MM-DD)")
@click.option("--format", "output_format", default="table", type=click.Choice(["table", "json"]))
@click.pass_context
def query(
    ctx: click.Context,
    user_id: str,
    metric: str,
    start_date: Optional[str],
    end_date: Optional[str],
    output_format: str,
) -> None:
    """Query local data."""
    cli_obj = ctx.obj["cli"]
    cli_obj.query_data(user_id, metric, start_date, end_date, output_format)


@cli.command()
@click.pass_context
def stats(ctx: click.Context) -> None:
    """Show database statistics."""
    cli_obj = ctx.obj["cli"]
    cli_obj.database_stats()


@cli.command()
@click.argument("sync_id")
@click.pass_context
def debug(ctx: click.Context, sync_id: str) -> None:
    """Debug a specific sync operation."""
    cli_obj = ctx.obj["cli"]
    cli_obj.debug_sync(sync_id)


def main() -> None:
    """Main CLI entry point."""
    cli()


if __name__ == "__main__":
    main()