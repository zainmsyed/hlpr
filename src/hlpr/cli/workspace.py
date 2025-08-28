"""Workspace management and health commands."""
from __future__ import annotations

import typer

from hlpr.cli.base import app, console, create_table
from hlpr.core.settings import get_settings


@app.command("health")
def health() -> None:
    """Show basic health / config info."""
    settings = get_settings()
    table = create_table("hlpr Health", ["Key", "Value"])
    table.add_row("environment", settings.environment)
    table.add_row("debug", str(settings.debug))
    table.add_row("api_prefix", settings.api_prefix)
    console.print(table)


@app.command("db-init")
def db_init(
    drop: bool = typer.Option(False, "--drop", help="Drop existing tables before initializing"),
) -> None:
    """Initialize database tables."""
    import asyncio

    from hlpr.db.base import init_models

    async def _run() -> None:
        # Ensure tables exist (optionally drop)
        await init_models(drop=drop)
        console.print("[green]Database initialized[/green]")

    asyncio.run(_run())