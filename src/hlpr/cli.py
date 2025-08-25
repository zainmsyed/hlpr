"""Typer CLI entrypoint for hlpr."""

import typer
import uvicorn
from rich.console import Console
from rich.table import Table

from hlpr.core.settings import get_settings

app_cli = typer.Typer(help="hlpr command line interface")
console = Console()


@app_cli.command("health")
def health() -> None:
    """Show basic health / config info."""
    settings = get_settings()
    table = Table(title="hlpr Health")
    table.add_column("Key")
    table.add_column("Value")
    table.add_row("environment", settings.environment)
    table.add_row("debug", str(settings.debug))
    table.add_row("api_prefix", settings.api_prefix)
    console.print(table)


@app_cli.command("run-server")
def run_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = True) -> None:  # pragma: no cover
    """Run the FastAPI development server."""
    uvicorn.run("hlpr.main:app", host=host, port=port, reload=reload)


@app_cli.command("demo-process")
def demo_process(text: str = "Sample project meeting transcript") -> None:
    """Placeholder for a future DSPy-powered processing pipeline."""
    console.print(f"[bold green]Processing text:[/bold green] {text}")
    # Placeholder logic
    console.print("[cyan]Result:[/cyan] (stub) summarization would appear here.")


if __name__ == "__main__":  # pragma: no cover
    app_cli()
