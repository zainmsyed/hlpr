"""Task runner for common development workflows."""
from __future__ import annotations

import subprocess
from typing import Any

from hlpr.cli.base import SmartCLIError, console, print_error, print_info, print_success


class TaskRunner:
    """Simple task runner for common development workflows."""

    def __init__(self) -> None:
        self.tasks: dict[str, dict[str, Any]] = {}
        self._register_tasks()

    def _register_tasks(self) -> None:
        """Register all available tasks."""
        self.tasks = {
            "dev": {
                "description": "Start development environment",
                "commands": [
                    "docker compose up -d",
                    "hlpr health"
                ],
                "background": False
            },
            "dev-stop": {
                "description": "Stop development environment",
                "commands": ["docker compose down"],
                "background": False
            },
            "dev-logs": {
                "description": "Show development logs",
                "commands": ["docker compose logs -f app"],
                "background": True
            },
            "dev-shell": {
                "description": "Open shell in development container",
                "commands": ["docker compose exec app bash"],
                "background": False
            },
            "train-quick": {
                "description": "Quick training with default preset",
                "commands": ["hlpr train --preset quick"],
                "background": False
            },
            "train-dev": {
                "description": "Training for development",
                "commands": ["hlpr train --preset development"],
                "background": False
            },
            "train-prod": {
                "description": "Production training",
                "commands": ["hlpr train --preset production"],
                "background": False
            },
            "test": {
                "description": "Run test suite",
                "commands": ["uv run pytest -q"],
                "background": False
            },
            "test-verbose": {
                "description": "Run test suite with verbose output",
                "commands": ["uv run pytest tests -v"],
                "background": False
            },
            "lint": {
                "description": "Run linting (non-fix)",
                "commands": ["uvx ruff check ."],
                "background": False
            },
            "lint-fix": {
                "description": "Run linting with auto-fix",
                "commands": ["uvx ruff check --fix"],
                "background": False
            },
            "type-check": {
                "description": "Run type checking",
                "commands": ["uv run mypy src"],
                "background": False
            },
            "quality": {
                "description": "Run full quality checks (lint + type + test)",
                "commands": [
                    "uvx ruff check --fix",
                    "uv run mypy src",
                    "uv run pytest -q"
                ],
                "background": False
            },
            "clean": {
                "description": "Clean up development environment",
                "commands": [
                    "docker compose down -v",
                    "docker system prune -f",
                    "find . -type d -name '__pycache__' -exec rm -rf {} +",
                    "find . -name '*.pyc' -delete"
                ],
                "background": False
            },
            "setup": {
                "description": "Initial project setup",
                "commands": [
                    "uv sync",
                    "docker compose build",
                    "hlpr db-init"
                ],
                "background": False
            }
        }

    def list_tasks(self) -> None:
        """List all available tasks."""
        from rich.table import Table

        table = Table(title="Available Tasks")
        table.add_column("Task", style="cyan", no_wrap=True)
        table.add_column("Description", style="white")
        table.add_column("Commands", style="dim")

        for name, task in sorted(self.tasks.items()):
            commands = task["commands"]
            if isinstance(commands, list):
                cmd_preview = " && ".join(commands[:2])
                if len(commands) > 2:
                    cmd_preview += f" && ... ({len(commands)} commands)"
            else:
                cmd_preview = str(commands)

            table.add_row(name, task["description"], cmd_preview)

        console.print(table)

    def run_task(self, name: str, dry_run: bool = False) -> bool:
        """Run a specific task.

        Args:
            name: Name of the task to run
            dry_run: If True, show commands without executing

        Returns:
            True if successful, False otherwise
        """
        if name not in self.tasks:
            available = sorted(self.tasks.keys())
            suggestions = [
                f"Try 'hlpr task {available[0]}' for common tasks" if available else "No tasks available",
                "Run 'hlpr task --list' to see all available tasks",
                "Use 'hlpr wizard' to build commands interactively",
                "Create custom tasks with 'hlpr task create'"
            ]
            SmartCLIError(
                f"Task '{name}' not found",
                suggestions=suggestions,
                error_code="TASK_NOT_FOUND",
                help_url="https://docs.hlpr.dev/tasks"
            ).display()
            return False

        task = self.tasks[name]
        commands = task["commands"]
        description = task["description"]

        print_info(f"Running task: {name} - {description}")

        if dry_run:
            print_info("Dry run mode - showing commands:")
            if isinstance(commands, list):
                for i, cmd in enumerate(commands, 1):
                    console.print(f"  {i}. {cmd}")
            else:
                console.print(f"  1. {commands}")
            return True

        try:
            if isinstance(commands, list):
                for i, cmd in enumerate(commands, 1):
                    print_info(f"Step {i}/{len(commands)}: {cmd}")
                    result = subprocess.run(cmd, shell=True, check=True, text=True)
            else:
                result = subprocess.run(commands, shell=True, check=True, text=True)

            print_success(f"Task '{name}' completed successfully")
            return True

        except subprocess.CalledProcessError as e:
            print_error(f"Task '{name}' failed at step {i if 'i' in locals() else 1}")
            print_error(f"Command: {e.cmd}")
            print_error(f"Exit code: {e.returncode}")
            if e.stderr:
                console.print(f"[dim]Error output: {e.stderr}[/dim]")
            return False
        except Exception as e:
            print_error(f"Task '{name}' failed: {e}")
            return False

    def create_custom_task(self, name: str, description: str, commands: list[str]) -> bool:
        """Create a custom task.

        Args:
            name: Task name
            description: Task description
            commands: List of commands to run

        Returns:
            True if successful, False otherwise
        """
        if name in self.tasks:
            print_error(f"Task '{name}' already exists")
            return False

        self.tasks[name] = {
            "description": description,
            "commands": commands,
            "background": False
        }

        print_success(f"Created custom task '{name}'")
        return True


# Global task runner instance
_task_runner: TaskRunner | None = None


def get_task_runner() -> TaskRunner:
    """Get the global task runner instance."""
    global _task_runner
    if _task_runner is None:
        _task_runner = TaskRunner()
    return _task_runner


def run_task(name: str, dry_run: bool = False) -> bool:
    """Run a task by name."""
    return get_task_runner().run_task(name, dry_run)


def list_tasks() -> None:
    """List all available tasks."""
    get_task_runner().list_tasks()