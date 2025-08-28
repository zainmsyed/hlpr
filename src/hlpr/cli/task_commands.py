"""Task management commands."""
from __future__ import annotations

import typer

from hlpr.cli.base import app, print_error


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