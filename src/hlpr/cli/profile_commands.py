"""Profile management commands."""
from __future__ import annotations

import typer

from hlpr.cli.base import app, console, create_table, print_error, print_success


@app.command("profile")  # type: ignore[misc]
def manage_profiles(
    action: str = typer.Argument("list", help="Action: list, show, apply, create"),
    name: str | None = typer.Option(None, help="Profile name for show/apply actions"),
) -> None:
    """Manage configuration profiles for different environments."""
    from hlpr.cli.profiles import get_profile_manager

    manager = get_profile_manager()

    if action == "list":
        profiles = manager.list_profiles()
        if not profiles:
            console.print("[yellow]No profiles found. Creating default profiles...[/yellow]")
            manager.create_default_profiles()
            profiles = manager.list_profiles()

        table = create_table("Available Profiles", ["Name", "Environment", "Model", "Optimizer"])
        for name, config in profiles.items():
            table.add_row(
                name,
                config.environment or "default",
                config.model or "default",
                config.optimizer or "default"
            )
        console.print(table)

    elif action == "show":
        if not name:
            print_error("Profile name required for show action")
            return

        profile = manager.get_profile(name)
        if not profile:
            print_error(f"Profile '{name}' not found")
            return

        console.print(f"[bold blue]Profile: {name}[/bold blue]")
        profile_dict = profile.model_dump(exclude_unset=True)
        for key, value in profile_dict.items():
            console.print(f"  {key}: {value}")

    elif action == "apply":
        if not name:
            print_error("Profile name required for apply action")
            return

        config = manager.apply_profile(name)
        if config:
            print_success(f"Profile '{name}' applied successfully")
        else:
            print_error(f"Failed to apply profile '{name}'")

    elif action == "create":
        print_error("Interactive profile creation not yet implemented")
        console.print("[yellow]To create profiles manually, edit ~/.hlpr/profiles.toml[/yellow]")

    else:
        print_error(f"Unknown action: {action}")
        console.print("[yellow]Available actions: list, show, apply, create[/yellow]")