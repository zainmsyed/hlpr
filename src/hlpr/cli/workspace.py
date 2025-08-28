"""Workspace management and health commands."""
from __future__ import annotations

import typer

from hlpr.cli.base import app, console, create_table, print_error
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


@app.command("env-info")
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


@app.command("presets")
def manage_presets(
    action: str = typer.Argument("list", help="Action: list, create, show"),
    name: str | None = typer.Option(None, help="Preset name for create/show actions"),
) -> None:
    """Manage command presets for simplified CLI usage."""
    from hlpr.cli.presets import get_preset_manager

    manager = get_preset_manager()

    if action == "list":
        presets = manager.list_presets()
        if not presets:
            console.print("[yellow]No presets found. Creating default presets...[/yellow]")
            manager.create_default_presets()
            presets = manager.list_presets()

        table = create_table("Available Presets", ["Name", "Model", "Optimizer", "Iterations"])
        for name, config in presets.items():
            table.add_row(
                name,
                config.model or "default",
                config.optimizer or "default",
                str(config.iters or "default")
            )
        console.print(table)

    elif action == "show":
        if not name:
            print_error("Preset name required for show action")
            return

        preset = manager.get_preset(name)
        if not preset:
            print_error(f"Preset '{name}' not found")
            return

        console.print(f"[bold blue]Preset: {name}[/bold blue]")
        preset_dict = preset.model_dump(exclude_unset=True)
        for key, value in preset_dict.items():
            console.print(f"  {key}: {value}")

    elif action == "create":
        print_error("Interactive preset creation not yet implemented")
        console.print("[yellow]To create presets manually, edit ~/.hlpr/presets.yml[/yellow]")

    else:
        print_error(f"Unknown action: {action}")
        console.print("[yellow]Available actions: list, show, create[/yellow]")