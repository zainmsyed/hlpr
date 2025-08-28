"""Workspace management and health commands."""
from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

import typer

from hlpr.cli.base import app, console, create_table, print_error, print_success
from hlpr.core.settings import get_settings

if TYPE_CHECKING:
    from hlpr.cli.wizard import CommandWizard


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


@app.command("setup")
def setup_environment(
    force: bool = typer.Option(False, "--force", "-f", help="Force re-setup even if already configured"),
    skip_docker: bool = typer.Option(False, "--skip-docker", help="Skip Docker setup"),
    skip_db: bool = typer.Option(False, "--skip-db", help="Skip database initialization"),
) -> None:
    """Interactive setup wizard for first-time configuration."""
    from hlpr.cli.wizard import get_wizard

    console.print("\n[bold green]🚀 hlpr Setup Wizard[/bold green]")
    console.print("Welcome! Let's set up your hlpr environment...\n")

    wizard = get_wizard()

    # Check if already set up
    if not force:
        try:
            # Basic health check
            from hlpr.cli.executor import get_execution_info
            info = get_execution_info()

            if info["docker_available"] or not info["is_docker"]:
                console.print("[yellow]Environment appears to already be configured.[/yellow]")
                if not wizard.prompt_yes_no("Run setup anyway?", False):
                    console.print("[green]Setup cancelled. Use --force to override.[/green]")
                    return
        except Exception:
            pass  # Continue with setup if checks fail

    # Environment type selection
    env_type = wizard.prompt_choice(
        "What type of environment are you setting up?",
        ["Development", "Production", "Testing"],
        "Development"
    )

    # Docker setup
    if not skip_docker:
        use_docker = wizard.prompt_yes_no(
            "Do you want to use Docker for the application?",
            True
        )

        if use_docker:
            console.print("\n[bold blue]Docker Setup:[/bold blue]")
            console.print("We'll run the development environment setup...")

            try:
                from hlpr.cli.workflows import run_workflow
                if not run_workflow("setup-dev", verbose=True):
                    print_error("Docker setup failed")
                    if not wizard.prompt_yes_no("Continue with setup anyway?", False):
                        raise typer.Exit(1)
            except Exception as e:
                print_error(f"Docker setup failed: {e}")
                if not wizard.prompt_yes_no("Continue with setup anyway?", False):
                    raise typer.Exit(1) from e
        else:
            console.print("[yellow]Skipping Docker setup. Make sure you have Python 3.13 and uv installed.[/yellow]")

    # Database setup
    if not skip_db:
        console.print("\n[bold blue]Database Setup:[/bold blue]")
        init_db = wizard.prompt_yes_no(
            "Initialize the database?",
            True
        )

        if init_db:
            try:
                from hlpr.cli.executor import smart_execute
                smart_execute("hlpr db-init")
                print_success("Database initialized successfully")
            except Exception as e:
                print_error(f"Database initialization failed: {e}")
                console.print("[yellow]You can initialize the database later with 'hlpr db-init'[/yellow]")

    # Configuration profiles
    console.print("\n[bold blue]Configuration:[/bold blue]")
    create_profile = wizard.prompt_yes_no(
        f"Create a {env_type.lower()} configuration profile?",
        True
    )

    if create_profile:
        profile_name = env_type.lower()
        try:
            from hlpr.cli.profiles import get_profile_manager
            manager = get_profile_manager()

            # Create default profile based on environment type
            if env_type == "Development":
                profile_config = {
                    "environment": "development",
                    "model": "ollama/gemma3",
                    "optimizer": "bootstrap",
                    "iters": 2,
                    "debug": True,
                    "auto_fallback": True
                }
            elif env_type == "Production":
                profile_config = {
                    "environment": "production",
                    "model": "gpt-4",
                    "optimizer": "mipro",
                    "iters": 20,
                    "debug": False,
                    "auto_fallback": False
                }
            else:  # Testing
                profile_config = {
                    "environment": "testing",
                    "model": "ollama/gemma3",
                    "optimizer": "bootstrap",
                    "iters": 1,
                    "debug": True,
                    "auto_fallback": True
                }

            manager.save_profile(profile_name, profile_config)
            print_success(f"Created '{profile_name}' profile")

            apply_now = wizard.prompt_yes_no(
                f"Apply the '{profile_name}' profile now?",
                True
            )

            if apply_now:
                manager.apply_profile(profile_name)
                print_success(f"Applied '{profile_name}' profile")

        except Exception as e:
            print_error(f"Profile creation failed: {e}")
            console.print("[yellow]You can create profiles later with 'hlpr profile create'[/yellow]")

    # Final health check
    console.print("\n[bold blue]Final Health Check:[/bold blue]")
    try:
        from hlpr.cli.executor import smart_execute
        smart_execute("hlpr health")
        print_success("Setup completed successfully!")
        console.print("\n[bold green]🎉 You're all set![/bold green]")
        console.print("Try running 'hlpr wizard' to build your first command interactively!")

    except Exception as e:
        print_error(f"Health check failed: {e}")
        console.print("[yellow]Setup completed with warnings. Check the output above.[/yellow]")


@app.command("configure")
def configure_environment(
    target: str = typer.Argument("all", help="What to configure: all, presets, profiles, environment"),
    interactive: bool = typer.Option(True, "--interactive/--non-interactive", help="Use interactive mode"),
) -> None:
    """Interactive configuration editor for hlpr settings."""
    from hlpr.cli.wizard import get_wizard

    console.print("\n[bold green]⚙️ hlpr Configuration Editor[/bold green]")

    wizard = get_wizard()

    if target in ["all", "presets"]:
        console.print("\n[bold blue]Preset Configuration:[/bold blue]")
        if interactive:
            configure_presets_interactive(wizard)
        else:
            console.print("Use 'hlpr presets create' for non-interactive preset creation")

    if target in ["all", "profiles"]:
        console.print("\n[bold blue]Profile Configuration:[/bold blue]")
        if interactive:
            configure_profiles_interactive(wizard)
        else:
            console.print("Use 'hlpr profile create' for non-interactive profile creation")

    if target in ["all", "environment"]:
        console.print("\n[bold blue]Environment Configuration:[/bold blue]")
        if interactive:
            configure_environment_interactive(wizard)
        else:
            console.print("Environment configuration requires interactive mode")

    print_success("Configuration completed!")


def configure_presets_interactive(wizard: CommandWizard) -> None:
    """Interactive preset configuration."""
    from hlpr.cli.presets import get_preset_manager

    manager = get_preset_manager()

    action = wizard.prompt_choice(
        "What would you like to do with presets?",
        ["Create new preset", "Edit existing preset", "Delete preset", "List presets"],
        "Create new preset"
    )

    if action == "Create new preset":
        name = wizard.prompt_input("Preset name", validator=lambda x: x.strip() or (_ for _ in ()).throw(ValueError("Name cannot be empty")))

        if manager.get_preset(name):
            if not wizard.prompt_yes_no(f"Preset '{name}' already exists. Overwrite?", False):
                return

        # Gather preset configuration
        model = wizard.prompt_choice(
            "Choose model:",
            ["ollama/gemma3", "gpt-3.5-turbo", "gpt-4", "claude-3-haiku"],
            "ollama/gemma3"
        )

        optimizer = wizard.prompt_choice(
            "Choose optimizer:",
            ["bootstrap", "mipro", "copro", "bootstrap_random"],
            "bootstrap"
        )

        iters = int(wizard.prompt_input("Number of iterations", "5"))

        config = {
            "model": model,
            "optimizer": optimizer,
            "iters": iters
        }

        manager.save_preset(name, config)
        print_success(f"Created preset '{name}'")

    elif action == "Edit existing preset":
        presets = manager.list_presets()
        if not presets:
            console.print("[yellow]No presets found. Create one first.[/yellow]")
            return

        preset_names = list(presets.keys())
        name = wizard.prompt_choice("Choose preset to edit:", preset_names)

        preset = manager.get_preset(name)
        if not preset:
            print_error(f"Preset '{name}' not found")
            return

        console.print(f"[bold blue]Current configuration for '{name}':[/bold blue]")
        for key, value in preset.model_dump().items():
            if value is not None:
                console.print(f"  {key}: {value}")

        # Edit logic would go here - simplified for now
        console.print("[yellow]Edit functionality not yet implemented. Use 'hlpr presets create' to overwrite.[/yellow]")

    elif action == "Delete preset":
        presets = manager.list_presets()
        if not presets:
            console.print("[yellow]No presets found.[/yellow]")
            return

        preset_names = list(presets.keys())
        name = wizard.prompt_choice("Choose preset to delete:", preset_names)

        if wizard.prompt_yes_no(f"Are you sure you want to delete preset '{name}'?", False):
            # Delete functionality would go here
            console.print("[yellow]Delete functionality not yet implemented.[/yellow]")

    else:  # List presets
        manager.list_presets()


def configure_profiles_interactive(wizard: CommandWizard) -> None:
    """Interactive profile configuration."""
    from hlpr.cli.profiles import get_profile_manager

    manager = get_profile_manager()

    action = wizard.prompt_choice(
        "What would you like to do with profiles?",
        ["Create new profile", "Edit existing profile", "Apply profile", "List profiles"],
        "Create new profile"
    )

    if action == "Create new profile":
        name = wizard.prompt_input("Profile name", validator=lambda x: x.strip() or (_ for _ in ()).throw(ValueError("Name cannot be empty")))

        if manager.get_profile(name):
            if not wizard.prompt_yes_no(f"Profile '{name}' already exists. Overwrite?", False):
                return

        # Gather profile configuration
        environment = wizard.prompt_choice(
            "Environment:",
            ["development", "staging", "production"],
            "development"
        )

        model = wizard.prompt_choice(
            "Model:",
            ["ollama/gemma3", "gpt-3.5-turbo", "gpt-4", "claude-3-haiku"],
            "ollama/gemma3"
        )

        optimizer = wizard.prompt_choice(
            "Optimizer:",
            ["bootstrap", "mipro", "copro"],
            "bootstrap"
        )

        iters = int(wizard.prompt_input("Iterations", "5"))
        debug = wizard.prompt_yes_no("Enable debug mode?", False)

        config = {
            "environment": environment,
            "model": model,
            "optimizer": optimizer,
            "iters": iters,
            "debug": debug
        }

        manager.save_profile(name, config)
        print_success(f"Created profile '{name}'")

    elif action == "Apply profile":
        profiles = manager.list_profiles()
        if not profiles:
            console.print("[yellow]No profiles found. Create one first.[/yellow]")
            return

        profile_names = list(profiles.keys())
        name = wizard.prompt_choice("Choose profile to apply:", profile_names)

        if manager.apply_profile(name):
            print_success(f"Applied profile '{name}'")
        else:
            print_error(f"Failed to apply profile '{name}'")

    else:  # List profiles or Edit
        manager.list_profiles()
        if action == "Edit existing profile":
            console.print("[yellow]Edit functionality not yet implemented. Use 'hlpr profile create' to overwrite.[/yellow]")


def configure_environment_interactive(wizard: CommandWizard) -> None:
    """Interactive environment configuration."""
    console.print("[yellow]Environment configuration wizard not yet implemented.[/yellow]")
    console.print("For now, you can:")
    console.print("  • Use 'hlpr env-info' to see current environment")
    console.print("  • Use 'hlpr profile apply <name>' to switch configurations")
    console.print("  • Edit configuration files manually")