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
def serve(
    host: Optional[str],
    port: Optional[int],
    log_level: Optional[str],
    reload: bool
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

    click.echo("Starting AG-UI agent server...")
    from .server import main

    # Run the server
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        click.echo("\nServer stopped.")
    except Exception as e:
        click.echo(f"Error starting server: {e}", err=True)
        sys.exit(1)




if __name__ == "__main__":
    cli()