"""CLI commands for hlpr."""
# Import all command modules to register them with the main app
from hlpr.cli import (  # noqa: F401
    development,
    health,
    meeting,
    plugins,
    preset_commands,
    presets,
    profile_commands,
    profiles,
    setup,
    task_commands,
    tasks,
    templates,
    training,
    wizard,
    workflow_commands,
    workflows,
    workspace,
)
from hlpr.cli.base import app

__all__ = ["app", "development", "health", "meeting", "plugins", "preset_commands", "presets", "profile_commands", "profiles", "setup", "task_commands", "tasks", "templates", "training", "wizard", "workflow_commands", "workflows", "workspace"]