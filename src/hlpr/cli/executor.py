"""Smart execution wrapper for routing commands to appropriate execution context."""
from __future__ import annotations

import subprocess
import sys
from typing import Any

from hlpr.cli.base import console, print_error, print_info, print_success
from hlpr.cli.context import (
    detect_execution_context,
    get_docker_compose_command,
    get_uv_command,
    is_docker_context,
)


def smart_execute(
    command: str,
    args: list[str] | None = None,
    *,
    background: bool = False,
    capture_output: bool = False,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Execute a command with smart routing based on execution context.

    Args:
        command: The command to execute (e.g., 'hlpr', 'python')
        args: List of arguments for the command
        background: Whether to run in background (not supported with smart execution)
        capture_output: Whether to capture stdout/stderr
        check: Whether to raise exception on non-zero exit code

    Returns:
        CompletedProcess with execution results

    Raises:
        RuntimeError: If execution context cannot be determined or command fails
    """
    if args is None:
        args = []

    context = detect_execution_context()
    print_info(f"Detected execution context: {context}")

    if background:
        print_error("Background execution not supported with smart routing")
        raise ValueError("Background execution not supported")

    # Build the full command based on context
    if context == "docker_inside":
        # Already in container, run directly
        full_command = [command] + args
        print_info("Executing directly in Docker container")

    elif context == "docker_available":
        # Route through docker compose
        docker_cmd = get_docker_compose_command()
        full_command = docker_cmd + ["exec", "app", command] + args
        print_info("Executing via Docker Compose")

    else:
        # Local execution with uv
        uv_cmd = get_uv_command()
        full_command = uv_cmd + [command] + args
        print_info("Executing locally with uv")

    print_info(f"Running: {' '.join(full_command)}")

    try:
        result = subprocess.run(
            full_command,
            capture_output=capture_output,
            text=True,
            check=check,
        )
        print_success("Command executed successfully")
        return result

    except subprocess.CalledProcessError as e:
        print_error(f"Command failed with exit code {e.returncode}")
        if e.stdout:
            console.print(f"[dim]stdout: {e.stdout}[/dim]")
        if e.stderr:
            console.print(f"[dim]stderr: {e.stderr}[/dim]")
        raise
    except FileNotFoundError as e:
        print_error(f"Command not found: {e}")
        raise RuntimeError(f"Required command not found: {command}") from e


def smart_execute_python(
    script_path: str,
    args: list[str] | None = None,
    **kwargs: Any,
) -> subprocess.CompletedProcess[str]:
    """Execute a Python script with smart routing."""
    return smart_execute("python", [script_path] + (args or []), **kwargs)


def smart_execute_hlpr(
    subcommand: str,
    args: list[str] | None = None,
    **kwargs: Any,
) -> subprocess.CompletedProcess[str]:
    """Execute an hlpr CLI command with smart routing."""
    return smart_execute("hlpr", [subcommand] + (args or []), **kwargs)


def get_execution_info() -> dict[str, Any]:
    """Get information about the current execution environment."""
    context = detect_execution_context()

    info = {
        "context": context,
        "is_docker": is_docker_context(context),
        "docker_available": context in ["docker_inside", "docker_available"],
        "uv_available": False,
        "python_path": sys.executable,
    }

    # Check uv availability
    try:
        result = subprocess.run(
            ["uv", "--version"],
            capture_output=True,
            timeout=5
        )
        info["uv_available"] = result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        pass

    return info