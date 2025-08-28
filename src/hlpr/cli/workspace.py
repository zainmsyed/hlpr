"""Workspace management and health commands."""
from __future__ import annotations

from typing import Annotated, Any

import typer

from hlpr.cli.base import app, console, create_table, print_error, print_success
from hlpr.core.settings import get_settings

# Create workspace subcommand
workspace_app = typer.Typer(help="Manage hlpr workspaces")
app.add_typer(workspace_app, name="workspace")


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
    from hlpr.cli.wizard import run_wizard as wizard_run
    wizard_run()


@app.command("setup")
def setup_environment(
    force: bool = typer.Option(False, "--force", "-f", help="Force re-setup even if already configured"),
    skip_docker: bool = typer.Option(False, "--skip-docker", help="Skip Docker setup"),
    skip_db: bool = typer.Option(False, "--skip-db", help="Skip database initialization"),
) -> None:
    """Interactive setup wizard for first-time configuration."""
    from hlpr.cli.wizard import run_setup_wizard
    run_setup_wizard(force=force, skip_docker=skip_docker, skip_db=skip_db)


@workspace_app.command("init")
def init_workspace(
    name: str = typer.Option(None, help="Name for the workspace"),
    template: str = typer.Option("default", help="Workspace template to use"),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing workspace"),
    skip_db: bool = typer.Option(False, "--skip-db", help="Skip database initialization"),
    skip_config: bool = typer.Option(False, "--skip-config", help="Skip configuration setup"),
):
    """Initialize a new hlpr workspace with default configuration."""
    from hlpr.cli.wizard import run_workspace_init
    run_workspace_init(
        name=name,
        template=template,
        force=force,
        skip_db=skip_db,
        skip_config=skip_config
    )


@workspace_app.command("status")
def workspace_status(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed information"),
    check_health: bool = typer.Option(True, "--check-health/--no-check-health", help="Include health checks"),
):
    """Show current workspace configuration and environment details."""
    from pathlib import Path

    console.print("\n[bold green]📊 Workspace Status[/bold green]")

    workspace_path = Path.cwd()
    config_file = workspace_path / "hlpr.toml"

    # Basic workspace info
    table = create_table("Workspace Information", ["Property", "Value"])

    if config_file.exists():
        try:
            import tomllib
            with open(config_file, "rb") as f:
                config = tomllib.load(f)

            workspace_config = config.get("workspace", {})
            table.add_row("Name", workspace_config.get("name", "Unknown"))
            table.add_row("Location", str(workspace_path))
            table.add_row("Template", workspace_config.get("template", "default"))
            table.add_row("Config File", str(config_file))

        except Exception as e:
            table.add_row("Config Status", f"[red]Error: {e}[/red]")
    else:
        table.add_row("Config Status", "[yellow]No hlpr.toml found[/yellow]")
        table.add_row("Location", str(workspace_path))

    console.print(table)

    # Environment information
    if verbose or check_health:
        console.print("\n[bold blue]Environment Details[/bold blue]")
        try:
            from hlpr.cli.executor import get_execution_info
            info = get_execution_info()

            env_table = create_table("Environment", ["Property", "Value"])
            env_table.add_row("Execution Context", info["context"])
            env_table.add_row("Docker Available", "✅" if info["docker_available"] else "❌")
            env_table.add_row("Is Docker", "✅" if info["is_docker"] else "❌")
            env_table.add_row("UV Available", "✅" if info["uv_available"] else "❌")
            env_table.add_row("Python Path", info["python_path"])
            console.print(env_table)

        except Exception as e:
            console.print(f"[red]Environment check failed: {e}[/red]")

    # Current configuration
    console.print("\n[bold blue]Current Configuration[/bold blue]")
    try:
        settings = get_settings()

        config_table = create_table("Settings", ["Setting", "Value"])
        config_table.add_row("Environment", settings.environment)
        config_table.add_row("Debug Mode", "✅" if settings.debug else "❌")
        config_table.add_row("API Prefix", settings.api_prefix)
        config_table.add_row("Database URL", settings.database_url or "Not set")

        console.print(config_table)

    except Exception as e:
        console.print(f"[red]Configuration check failed: {e}[/red]")

    # Active profiles and presets
    try:
        from hlpr.cli.presets import get_preset_manager
        from hlpr.cli.profiles import get_profile_manager

        profile_manager = get_profile_manager()
        preset_manager = get_preset_manager()

        profiles = profile_manager.list_profiles()
        presets = preset_manager.list_presets()

        if profiles or presets:
            console.print("\n[bold blue]Available Resources[/bold blue]")
            resource_table = create_table("Resources", ["Type", "Count", "Items"])
            if profiles:
                profile_names = ", ".join(list(profiles.keys())[:3])
                if len(profiles) > 3:
                    profile_names += f" (+{len(profiles) - 3} more)"
                resource_table.add_row("Profiles", str(len(profiles)), profile_names)
            if presets:
                preset_names = ", ".join(list(presets.keys())[:3])
                if len(presets) > 3:
                    preset_names += f" (+{len(presets) - 3} more)"
                resource_table.add_row("Presets", str(len(presets)), preset_names)
            console.print(resource_table)

    except Exception as e:
        if verbose:
            console.print(f"[red]Resource check failed: {e}[/red]")

    # Health checks
    if check_health:
        console.print("\n[bold blue]Health Checks[/bold blue]")
        health_table = create_table("Health", ["Component", "Status"])

        # Database health
        try:
            import asyncio
            asyncio.run(check_db_health())
            health_table.add_row("Database", "✅ Connected")
        except Exception:
            health_table.add_row("Database", "❌ Failed")

        # Docker health
        try:
            from hlpr.cli.executor import get_execution_info
            info = get_execution_info()
            if info["docker_available"]:
                health_table.add_row("Docker", "✅ Available")
            else:
                health_table.add_row("Docker", "⚠️ Not available")
        except Exception:
            health_table.add_row("Docker", "❌ Check failed")

        console.print(health_table)

    # Quick actions
    console.print("\n[bold blue]Quick Actions[/bold blue]")
    console.print("  • Switch profile: [green]hlpr workspace switch <profile>[/green]")
    console.print("  • Run wizard: [green]hlpr wizard[/green]")
    console.print("  • View health: [green]hlpr health[/green]")


async def check_db_health() -> None:
    """Check database connectivity."""
    from sqlalchemy import text

    from hlpr.db.dependencies import get_db

    async for session in get_db():
        await session.execute(text("SELECT 1"))
        break
        break


@workspace_app.command("switch")
def switch_workspace(
    target: str = typer.Argument(..., help="Profile or environment to switch to"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show changes without applying"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output"),
):
    """Switch to a different workspace profile or environment."""
    console.print(f"\n[bold green]🔄 Switching workspace to:[/bold green] [bold]{target}[/bold]")

    if dry_run:
        console.print("[yellow]DRY RUN MODE - No changes will be applied[/yellow]")

    try:
        # Try to apply as profile first
        from hlpr.cli.profiles import get_profile_manager
        manager = get_profile_manager()

        profile = manager.get_profile(target)
        if profile:
            console.print(f"Found profile: [blue]{target}[/blue]")

            if verbose:
                console.print("\n[bold]Profile configuration:[/bold]")
                profile_dict = profile.model_dump(exclude_unset=True)
                for key, value in profile_dict.items():
                    console.print(f"  {key}: {value}")

            if not dry_run:
                if manager.apply_profile(target):
                    print_success(f"Successfully switched to profile '{target}'")

                    # Show current status
                    console.print("\n[bold]Current workspace status:[/bold]")
                    workspace_status(verbose=False, check_health=False)
                else:
                    print_error(f"Failed to apply profile '{target}'")
            else:
                console.print("[yellow]Would apply profile configuration[/yellow]")

        else:
            # Try as environment type
            valid_environments = ["development", "staging", "production", "testing"]

            if target in valid_environments:
                console.print(f"Switching to environment: [blue]{target}[/blue]")

                # Create or apply environment-specific configuration
                env_config = get_environment_config(target)

                if verbose:
                    console.print("\n[bold]Environment configuration:[/bold]")
                    for key, value in env_config.items():
                        console.print(f"  {key}: {value}")

                if not dry_run:
                    # Apply environment configuration
                    manager.save_profile(f"env-{target}", env_config)
                    if manager.apply_profile(f"env-{target}"):
                        print_success(f"Successfully switched to {target} environment")
                    else:
                        print_error(f"Failed to apply {target} environment configuration")
                else:
                    console.print("[yellow]Would apply environment configuration[/yellow]")

            else:
                print_error(f"Profile or environment '{target}' not found")
                console.print("\n[bold]Available options:[/bold]")

                # Show available profiles
                profiles = manager.list_profiles()
                if profiles:
                    console.print("  [bold]Profiles:[/bold]")
                    for name in profiles.keys():
                        console.print(f"    • {name}")

                # Show available environments
                console.print("  [bold]Environments:[/bold]")
                for env in valid_environments:
                    console.print(f"    • {env}")

                console.print("\n[yellow]Create a new profile with: hlpr profile create[/yellow]")
                return

    except Exception as e:
        print_error(f"Workspace switch failed: {e}")
        if verbose:
            console.print(f"[red]Error details: {e}[/red]")
        raise typer.Exit(1) from e


def get_environment_config(environment: str) -> dict[str, Any]:
    """Get default configuration for an environment type."""
    configs = {
        "development": {
            "environment": "development",
            "model": "ollama/gemma3",
            "optimizer": "bootstrap",
            "iters": 2,
            "debug": True,
            "auto_fallback": True,
            "database_url": "sqlite+aiosqlite:///./hlpr.db"
        },
        "staging": {
            "environment": "staging",
            "model": "gpt-3.5-turbo",
            "optimizer": "mipro",
            "iters": 5,
            "debug": False,
            "auto_fallback": True,
            "database_url": "sqlite+aiosqlite:///./hlpr.db"
        },
        "production": {
            "environment": "production",
            "model": "gpt-4",
            "optimizer": "mipro",
            "iters": 20,
            "debug": False,
            "auto_fallback": False,
            "database_url": "sqlite+aiosqlite:///./hlpr.db"
        },
        "testing": {
            "environment": "testing",
            "model": "ollama/gemma3",
            "optimizer": "bootstrap",
            "iters": 1,
            "debug": True,
            "auto_fallback": True,
            "database_url": "sqlite+aiosqlite:///./test_hlpr.db"
        }
    }

    return configs.get(environment, configs["development"])




