"""CLI for Garmy MCP server.

Provides command-line interface for running and managing the MCP server.
"""

import logging
from typing import Optional

import click

from .config import ConfigManager, MCPConfig
from .server import GarmyMCPServer


@click.group()
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.option("--config-file", type=click.Path(exists=True), help="Path to config file")
@click.pass_context
def cli(ctx: click.Context, debug: bool, config_file: Optional[str]):
    """Garmy MCP Server CLI.

    Manage and run MCP servers for Garmin Connect health data.
    """
    # Setup logging
    if debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    # Load configuration
    config = MCPConfig() if config_file else ConfigManager.load_from_env()

    # Store in context
    ctx.ensure_object(dict)
    ctx.obj["config"] = config


@cli.command()
@click.option(
    "--transport",
    type=click.Choice(["stdio", "http"]),
    default="stdio",
    help="Transport protocol",
)
@click.option("--host", default="127.0.0.1", help="Host for HTTP transport")
@click.option("--port", default=8000, help="Port for HTTP transport")
@click.option("--path", default="/mcp", help="Path for HTTP transport")
@click.pass_context
def run(ctx: click.Context, transport: str, host: str, port: int, path: str):
    """Run the MCP server."""
    config = ctx.obj["config"]

    # Suppress output for MCP stdio to avoid JSON parsing issues
    if transport != "stdio":
        click.echo("Starting Garmy MCP Server")
        click.echo(f"Transport: {transport}")

    server = GarmyMCPServer(config)

    try:
        if transport == "stdio":
            server.run(transport="stdio")
        elif transport == "http":
            click.echo(f"HTTP Server: http://{host}:{port}{path}")
            server.run(transport="streamable-http", host=host, port=port, path=path)
    except KeyboardInterrupt:
        if transport != "stdio":
            click.echo("\nServer stopped")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort() from e


@cli.command()
@click.pass_context
def info(ctx: click.Context):
    """Show server information."""
    config = ctx.obj["config"]

    click.echo("Garmy MCP Server Information")
    click.echo("=" * 40)
    click.echo(f"Server Name: {config.server_name}")
    click.echo(f"Version: {config.server_version}")
    click.echo()

    click.echo("Features:")
    click.echo(f"  Auth Tools: {config.enable_auth_tools}")
    click.echo(f"  Metric Tools: {config.enable_metric_tools}")
    click.echo(f"  Analysis Tools: {config.enable_analysis_tools}")
    click.echo(f"  Resources: {config.enable_resources}")
    click.echo(f"  Prompts: {config.enable_prompts}")
    click.echo()

    click.echo("Limits:")
    click.echo(f"  Max History Days: {config.max_history_days}")
    click.echo(f"  Analysis Period: {config.default_analysis_period}")
    click.echo(f"  Cache: {'Enabled' if config.cache_enabled else 'Disabled'}")
    if config.cache_enabled:
        click.echo(f"  Cache Size: {config.cache_size}")


@cli.command()
@click.pass_context
def metrics(ctx: click.Context):
    """List available metrics."""
    from ..core.discovery import MetricDiscovery

    try:
        discovered_metrics = MetricDiscovery.discover_metrics()
        MetricDiscovery.validate_metrics(discovered_metrics)

        click.echo(f"Available Metrics ({len(discovered_metrics)})")
        click.echo("=" * 40)

        for name, config in discovered_metrics.items():
            status = " (DEPRECATED)" if config.deprecated else ""
            click.echo(f"{name}{status}")
            click.echo(f"   Class: {config.metric_class.__name__}")
            click.echo(f"   Endpoint: {config.endpoint or 'Dynamic'}")
            if config.description:
                click.echo(f"   Description: {config.description}")
            click.echo()

    except Exception as e:
        click.echo(f"Error discovering metrics: {e}", err=True)
        raise click.Abort() from e


@cli.command()
@click.option(
    "--profile",
    type=click.Choice(["development", "production", "minimal"]),
    help="Configuration profile",
)
def config(profile: Optional[str]):
    """Show or generate configuration."""
    if profile:
        if profile == "development":
            config = MCPConfig.for_development()
        elif profile == "production":
            config = MCPConfig.for_production()
        elif profile == "minimal":
            config = MCPConfig.minimal()

        click.echo(f"{profile.title()} Configuration:")
        click.echo("=" * 40)
        click.echo(f"Server Name: {config.server_name}")
        click.echo(f"Debug Mode: {config.debug_mode}")
        click.echo(f"Cache Enabled: {config.cache_enabled}")
        click.echo(f"Cache Size: {config.cache_size}")
        click.echo(f"Max History Days: {config.max_history_days}")
    else:
        click.echo("Available profiles: development, production, minimal")
        click.echo("Use --profile <name> to see configuration details")


def main():
    """Entry point for CLI."""
    cli()
