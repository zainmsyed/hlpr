"""CLI commands for hlpr."""
# Import all command modules to register them with the main app
from hlpr.cli import development, meeting, training, workspace  # noqa: F401
from hlpr.cli.base import app

__all__ = ["app", "development", "meeting", "training", "workspace"]