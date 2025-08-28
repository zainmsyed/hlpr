"""Workflow management commands."""
from __future__ import annotations

from typing import Annotated

import typer

from hlpr.cli.base import app


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