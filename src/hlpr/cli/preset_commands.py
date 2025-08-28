"""Preset management commands."""
from __future__ import annotations

import typer

from hlpr.cli.base import app, console, create_table, print_error


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