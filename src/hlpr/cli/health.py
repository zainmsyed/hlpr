"""Health and environment information commands."""
from __future__ import annotations

from hlpr.cli.base import app, console, create_table
from hlpr.core.settings import get_settings


@app.command("health")  # type: ignore[misc]
def health() -> None:
    """Show basic health / config info."""
    settings = get_settings()
    table = create_table("hlpr Health", ["Key", "Value"])
    table.add_row("environment", settings.environment)
    table.add_row("debug", str(settings.debug))
    table.add_row("api_prefix", settings.api_prefix)
    console.print(table)


@app.command("env-info")  # type: ignore[misc]
def env_info() -> None:
    """Show detailed information about the current execution environment."""
    from hlpr.cli.executor import get_execution_info

    info = get_execution_info()

    table = create_table("Environment Information", ["Property", "Value"])
    table.add_row("Execution Context", info["context"])
    table.add_row("Docker Available", str(info["docker_available"]))
    table.add_row("Is Docker", str(info["is_docker"]))
    table.add_row("UV Available", str(info["uv_available"]))
    table.add_row("Python Path", info["python_path"])

    console.print(table)