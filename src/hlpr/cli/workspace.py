"""Workspace management and health commands."""
from __future__ import annotations

from typing import Annotated

import typer

from hlpr.cli.base import app, console, create_table, print_error, print_success
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


@app.command("task")
def run_task(
    task_name: str | None = typer.Argument(None, help="Name of the task to run"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show commands without executing"),
    list_tasks: bool = typer.Option(False, "--list", "-l", help="List all available tasks"),
) -> None:
    """Run development tasks and workflows."""
    from hlpr.cli.tasks import get_task_runner

    runner = get_task_runner()

    if list_tasks:
        runner.list_tasks()
        return

    if not task_name:
        print_error("Task name required (or use --list to see available tasks)")
        return

    if not runner.run_task(task_name, dry_run):
        raise typer.Exit(1)


@app.command("profile")
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


@app.command("workflow")
def run_workflow(
    workflow_name: str = typer.Argument(..., help="Name of the workflow to run"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show steps without executing"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output"),
    list_workflows: bool = typer.Option(False, "--list", "-l", help="List all available workflows"),
) -> None:
    """Run predefined workflows and automation sequences."""
    from hlpr.cli.workflows import get_workflow_manager

    manager = get_workflow_manager()

    if list_workflows:
        manager.list_workflows()
        return

    if not manager.run_workflow(workflow_name, dry_run, verbose):
        raise typer.Exit(1)


@app.command("chain")
def run_command_chain(
    commands: Annotated[list[str], typer.Argument(help="Commands to run in sequence")],
    dry_run: bool = typer.Option(False, "--dry-run", help="Show commands without executing"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output"),
) -> None:
    """Run a chain of commands in sequence."""
    from hlpr.cli.workflows import run_command_chain as execute_chain

    if not execute_chain(commands, dry_run, verbose):
        raise typer.Exit(1)


@app.command("wizard")
def run_wizard() -> None:
    """Interactive command builder wizard."""
    from hlpr.cli.wizard import get_wizard

    wizard = get_wizard()
    wizard.run_wizard()