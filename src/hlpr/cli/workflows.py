"""Workflow automation commands for chaining operations."""
from __future__ import annotations

import subprocess
import time
from typing import Any

from hlpr.cli.base import SmartCLIError, console, print_error, print_info, print_success
from hlpr.cli.executor import smart_execute


class WorkflowManager:
    """Manages command workflows and pipelines."""

    def __init__(self) -> None:
        self.workflows: dict[str, dict[str, Any]] = {}
        self._register_workflows()

    def _register_workflows(self) -> None:
        """Register predefined workflows."""
        self.workflows = {
            "setup-dev": {
                "description": "Complete development environment setup",
                "steps": [
                    {
                        "name": "Install dependencies",
                        "command": "uv sync",
                        "continue_on_error": False
                    },
                    {
                        "name": "Start Docker services",
                        "command": "docker compose up -d",
                        "continue_on_error": False
                    },
                    {
                        "name": "Wait for services",
                        "command": "sleep 5",
                        "continue_on_error": True
                    },
                    {
                        "name": "Initialize database",
                        "command": "hlpr db-init",
                        "continue_on_error": False
                    },
                    {
                        "name": "Health check",
                        "command": "hlpr health",
                        "continue_on_error": False
                    }
                ]
            },
            "quick-train": {
                "description": "Quick training workflow",
                "steps": [
                    {
                        "name": "Health check",
                        "command": "hlpr health",
                        "continue_on_error": False
                    },
                    {
                        "name": "Quick training",
                        "command": "hlpr train --preset quick",
                        "continue_on_error": False
                    }
                ]
            },
            "full-train": {
                "description": "Full training pipeline with validation",
                "steps": [
                    {
                        "name": "Environment check",
                        "command": "hlpr env-info",
                        "continue_on_error": False
                    },
                    {
                        "name": "Code quality check",
                        "command": "uvx ruff check .",
                        "continue_on_error": False
                    },
                    {
                        "name": "Type check",
                        "command": "uv run mypy src",
                        "continue_on_error": False
                    },
                    {
                        "name": "Run tests",
                        "command": "uv run pytest -q",
                        "continue_on_error": False
                    },
                    {
                        "name": "Full training",
                        "command": "hlpr train --preset production",
                        "continue_on_error": False
                    }
                ]
            },
            "cleanup": {
                "description": "Clean up development environment",
                "steps": [
                    {
                        "name": "Stop services",
                        "command": "docker compose down",
                        "continue_on_error": True
                    },
                    {
                        "name": "Clean containers",
                        "command": "docker system prune -f",
                        "continue_on_error": True
                    },
                    {
                        "name": "Clean cache",
                        "command": "find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true",
                        "continue_on_error": True
                    }
                ]
            }
        }

    def list_workflows(self) -> None:
        """List all available workflows."""
        from rich.table import Table

        table = Table(title="Available Workflows")
        table.add_column("Workflow", style="cyan", no_wrap=True)
        table.add_column("Description", style="white")
        table.add_column("Steps", style="dim")

        for name, workflow in sorted(self.workflows.items()):
            steps = len(workflow["steps"])
            table.add_row(name, workflow["description"], str(steps))

        console.print(table)

    def run_workflow(self, name: str, dry_run: bool = False, verbose: bool = False) -> bool:
        """Run a workflow by name.

        Args:
            name: Name of the workflow to run
            dry_run: If True, show steps without executing
            verbose: If True, show detailed output

        Returns:
            True if successful, False otherwise
        """
        if name not in self.workflows:
            available = sorted(self.workflows.keys())
            suggestions = [
                f"Use 'hlpr workflow {available[0]}' for a quick start" if available else "Create a custom workflow",
                "Run 'hlpr workflow --list' to see all available workflows",
                "Use 'hlpr wizard' to build commands interactively"
            ]
            SmartCLIError(
                f"Workflow '{name}' not found",
                suggestions=suggestions,
                error_code="WORKFLOW_NOT_FOUND",
                help_url="https://docs.hlpr.dev/workflows"
            ).display()
            return False

        workflow = self.workflows[name]
        steps = workflow["steps"]
        description = workflow["description"]

        print_info(f"Running workflow: {name} - {description}")
        print_info(f"Total steps: {len(steps)}")

        if dry_run:
            print_info("Dry run mode - showing steps:")
            for i, step in enumerate(steps, 1):
                console.print(f"  {i}. {step['name']}: {step['command']}")
            return True

        success_count = 0
        start_time = time.time()

        for i, step in enumerate(steps, 1):
            step_name = step["name"]
            command = step["command"]
            continue_on_error = step.get("continue_on_error", False)

            print_info(f"Step {i}/{len(steps)}: {step_name}")

            if verbose:
                console.print(f"[dim]Command: {command}[/dim]")

            try:
                # Use smart_execute for hlpr commands, subprocess for others
                if command.startswith("hlpr"):
                    smart_execute(command, capture_output=not verbose)
                else:
                    subprocess.run(
                        command,
                        shell=True,
                        check=True,
                        text=True,
                        capture_output=not verbose
                    )

                print_success(f"✓ {step_name} completed")
                success_count += 1

            except subprocess.CalledProcessError as e:
                if continue_on_error:
                    print_error(f"⚠ {step_name} failed (continuing): {e}")
                else:
                    print_error(f"✗ {step_name} failed: {e}")
                    return False
            except Exception as e:
                if continue_on_error:
                    print_error(f"⚠ {step_name} failed (continuing): {e}")
                else:
                    print_error(f"✗ {step_name} failed: {e}")
                    return False

        elapsed_time = time.time() - start_time
        print_success(f"Workflow '{name}' completed: {success_count}/{len(steps)} steps successful")
        print_info(f"Completed in {elapsed_time:.1f}s")
        return True

    def run_command_chain(self, commands: list[str], dry_run: bool = False, verbose: bool = False) -> bool:
        """Run a chain of commands.

        Args:
            commands: List of commands to run in sequence
            dry_run: If True, show commands without executing
            verbose: If True, show detailed output

        Returns:
            True if all commands successful, False otherwise
        """
        print_info(f"Running command chain with {len(commands)} commands")

        if dry_run:
            print_info("Dry run mode - showing commands:")
            for i, cmd in enumerate(commands, 1):
                console.print(f"  {i}. {cmd}")
            return True

        success_count = 0
        start_time = time.time()

        for i, command in enumerate(commands, 1):
            print_info(f"Command {i}/{len(commands)}: {command[:50]}{'...' if len(command) > 50 else ''}")

            if verbose:
                console.print(f"[dim]Full command: {command}[/dim]")

            try:
                if command.startswith("hlpr"):
                    smart_execute(command, capture_output=not verbose)
                else:
                    subprocess.run(
                        command,
                        shell=True,
                        check=True,
                        text=True,
                        capture_output=not verbose
                    )

                print_success(f"✓ Command {i} completed")
                success_count += 1

            except subprocess.CalledProcessError as e:
                print_error(f"✗ Command {i} failed: {e}")
                return False
            except Exception as e:
                print_error(f"✗ Command {i} failed: {e}")
                return False

        elapsed_time = time.time() - start_time
        print_success(f"Command chain completed: {success_count}/{len(commands)} commands successful")
        print_info(f"Completed in {elapsed_time:.1f}s")
        return True


# Global workflow manager instance
_workflow_manager: WorkflowManager | None = None


def get_workflow_manager() -> WorkflowManager:
    """Get the global workflow manager instance."""
    global _workflow_manager
    if _workflow_manager is None:
        _workflow_manager = WorkflowManager()
    return _workflow_manager


def run_workflow(name: str, dry_run: bool = False, verbose: bool = False) -> bool:
    """Run a workflow by name."""
    return get_workflow_manager().run_workflow(name, dry_run, verbose)


def run_command_chain(commands: list[str], dry_run: bool = False, verbose: bool = False) -> bool:
    """Run a chain of commands."""
    return get_workflow_manager().run_command_chain(commands, dry_run, verbose)


def list_workflows() -> None:
    """List all available workflows."""
    get_workflow_manager().list_workflows()