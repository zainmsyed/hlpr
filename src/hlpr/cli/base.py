"""Base CLI utilities and common functionality."""
from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

# Global console instance
console = Console()

# Common CLI app instance
app = typer.Typer(help="hlpr command line interface")


def create_table(title: str, columns: list[str]) -> Table:
    """Create a rich table with standard formatting."""
    from rich.table import Table

    table = Table(title=title)
    for column in columns:
        table.add_column(column)
    return table


def print_success(message: str) -> None:
    """Print a success message."""
    console.print(f"[bold green]✅ {message}[/bold green]")


def print_error(message: str) -> None:
    """Print an error message."""
    console.print(f"[bold red]❌ {message}[/bold red]")


def print_warning(message: str) -> None:
    """Print a warning message."""
    console.print(f"[bold yellow]⚠️ {message}[/bold yellow]")


def print_info(message: str) -> None:
    """Print an info message."""
    console.print(f"[bold blue]ℹ️ {message}[/bold blue]")