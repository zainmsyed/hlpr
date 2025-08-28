"""CLI commands for hlpr."""
# Import all command modules to register them with the main app
from hlpr.cli import (  # noqa: F401
    development,
    meeting,
    plugins,
    presets,
    profiles,
    tasks,
    templates,
    training,
    wizard,
    workflows,
    workspace,
)
from hlpr.cli.base import app

__all__ = ["app", "development", "meeting", "plugins", "presets", "profiles", "tasks", "templates", "training", "wizard", "workspace", "workflows"]