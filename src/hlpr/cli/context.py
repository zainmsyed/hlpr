"""Environment detection and smart execution utilities."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Literal

ExecutionContext = Literal["docker_inside", "docker_available", "local_only"]


def detect_execution_context() -> ExecutionContext:
    """Automatically detect if we're in Docker, have Docker available, or are local-only.

    Returns:
        ExecutionContext: The detected execution context
    """
    # Check if we're inside a Docker container
    if Path("/.dockerenv").exists():
        return "docker_inside"

    # Check if Docker Compose is available and has running services
    try:
        result = subprocess.run(
            ["docker", "compose", "ps"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and "app" in result.stdout:
            return "docker_available"
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        pass

    # Check if Docker is available at all
    try:
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return "docker_available"
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        pass

    return "local_only"


def is_docker_context(context: ExecutionContext) -> bool:
    """Check if the context involves Docker."""
    return context in ["docker_inside", "docker_available"]


def get_docker_compose_command() -> list[str]:
    """Get the appropriate Docker Compose command for the current system."""
    # Try newer 'docker compose' first, fall back to 'docker-compose'
    commands = [
        ["docker", "compose"],
        ["docker-compose"]
    ]

    for cmd in commands:
        try:
            result = subprocess.run(
                cmd + ["--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return cmd
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            continue

    raise RuntimeError("Docker Compose not found. Please install Docker Compose.")


def get_uv_command() -> list[str]:
    """Get the uv command, checking if it's available."""
    try:
        result = subprocess.run(
            ["uv", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return ["uv", "run"]
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        pass

    # Fall back to python -m if uv not available
    return ["python", "-m"]