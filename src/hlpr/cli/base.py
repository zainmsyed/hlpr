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


class SmartCLIError(Exception):
    """Enhanced CLI error with suggestions and better formatting."""

    def __init__(
        self,
        message: str,
        *,
        suggestions: list[str] | None = None,
        error_code: str | None = None,
        help_url: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.suggestions = suggestions or []
        self.error_code = error_code
        self.help_url = help_url

    def display(self) -> None:
        """Display the error with formatting and suggestions."""
        # Print main error message
        console.print(f"[bold red]❌ Error:[/bold red] {self.message}")

        # Print error code if provided
        if self.error_code:
            console.print(f"[dim red]Error Code: {self.error_code}[/dim red]")

        # Print suggestions if provided
        if self.suggestions:
            console.print("[bold yellow]💡 Suggestions:[/bold yellow]")
            for i, suggestion in enumerate(self.suggestions, 1):
                console.print(f"  {i}. {suggestion}")

        # Print help URL if provided
        if self.help_url:
            console.print(f"[bold blue]🔗 Help:[/bold blue] {self.help_url}")

    def __str__(self) -> str:
        """String representation of the error."""
        return self.message


def raise_smart_error(
    message: str,
    *,
    suggestions: list[str] | None = None,
    error_code: str | None = None,
    help_url: str | None = None,
) -> None:
    """Raise a SmartCLIError with the given parameters."""
    error = SmartCLIError(
        message=message,
        suggestions=suggestions,
        error_code=error_code,
        help_url=help_url,
    )
    error.display()
    raise error