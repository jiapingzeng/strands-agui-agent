"""
Command-line interface for Strands AG-UI Agent.
"""

import asyncio
import sys
from typing import Optional

import click

from .config import config


@click.group()
@click.version_option(version="0.2.0")
def cli():
    """Strands AG-UI Agent CLI."""
    pass


@cli.command()
@click.option("--host", default=None, help="Host to bind to")
@click.option("--port", type=int, default=None, help="Port to bind to")
@click.option("--log-level", default=None, help="Log level")
@click.option("--reload", is_flag=True, help="Enable auto-reload")
@click.option("--frontend-tools", is_flag=True, default=True, help="Use frontend tool execution (default)")
@click.option("--legacy", is_flag=True, help="Use legacy backend tool execution")
def serve(
    host: Optional[str],
    port: Optional[int],
    log_level: Optional[str],
    reload: bool,
    frontend_tools: bool,
    legacy: bool
):
    """Start the AG-UI agent server."""

    # Override config with CLI options
    if host:
        config.server.host = host
    if port:
        config.server.port = port
    if log_level:
        config.server.log_level = log_level
    if reload:
        config.server.reload = reload

    # Choose implementation
    if legacy:
        click.echo("Starting legacy server (backend tool execution)...")
        from .server import main
    else:
        click.echo("Starting frontend tool server (recommended)...")
        from .frontend_tool_server import main

    # Run the server
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        click.echo("\nServer stopped.")
    except Exception as e:
        click.echo(f"Error starting server: {e}", err=True)
        sys.exit(1)


@cli.command()
def demo():
    """Run the frontend tool execution demonstration."""
    click.echo("Running frontend tool execution demo...")

    try:
        from ..examples.frontend_tool_example import demonstrate_frontend_tool_execution
        asyncio.run(demonstrate_frontend_tool_execution())
    except ImportError:
        click.echo("Demo not available. Make sure examples are installed.", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Demo error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--url", default="http://localhost:8000", help="Server URL to test")
def test(url: str):
    """Test the server with sample requests."""
    click.echo(f"Testing server at {url}...")

    try:
        from ..examples.frontend_tool_client import FrontendToolClient
        client = FrontendToolClient(url)

        async def run_test():
            await client.run_complete_flow("Calculate 25 * 4 and get weather for San Francisco")

        asyncio.run(run_test())
        click.echo("Test completed successfully!")

    except ImportError:
        click.echo("Test client not available.", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Test error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()