"""Setup and initialization commands."""
from __future__ import annotations

import typer

from hlpr.cli.base import app, print_info, print_success


@app.command("setup")
def setup_wizard() -> None:
    """Interactive setup wizard for first-time configuration."""
    from pathlib import Path

    print_info("Welcome to hlpr setup wizard!")
    print_info("This will help you configure hlpr for your environment.")

    # Check if already configured
    config_dir = Path.home() / ".hlpr"
    presets_file = config_dir / "presets.yml"

    if presets_file.exists():
        if not typer.confirm("Configuration already exists. Reconfigure?"):
            print_info("Setup cancelled.")
            return

    # Detect environment
    env_type = typer.prompt(
        "What type of environment are you setting up?",
        type=typer.Choice(["development", "production", "testing"]),  # type: ignore[attr-defined]
        default="development"
    )

    print_info(f"Setting up {env_type} environment.")

    # Docker setup
    use_docker = typer.confirm("Will you be using Docker for this setup?", default=False)

    if use_docker:
        print_info("Docker setup selected.")
        # Could add Docker-specific configuration here
    else:
        print_info("Local setup selected.")

    # Create basic configuration
    config_dir.mkdir(parents=True, exist_ok=True)

    # Create default presets if they don't exist
    from hlpr.cli.presets import get_preset_manager
    manager = get_preset_manager()
    if not manager.list_presets():
        print_info("Creating default presets...")
        manager.create_default_presets()

    print_success("Setup complete!")
    print_info("You can now use 'hlpr train' to start training models.")
    print_info("Use 'hlpr presets list' to see available presets.")