"""Development-only CLI commands."""
from __future__ import annotations

import uvicorn

from hlpr.cli.base import app, console


@app.command("run-server")  # type: ignore[misc]
def run_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = True) -> None:  # pragma: no cover
    """Run the FastAPI development server."""
    uvicorn.run("hlpr.main:app", host=host, port=port, reload=reload)


@app.command("demo-process")  # type: ignore[misc]
def demo_process(text: str = "Sample project meeting transcript") -> None:
    """Placeholder for a future DSPy-powered processing pipeline."""
    console.print(f"[bold green]Processing text:[/bold green] {text}")
    # Placeholder logic
    console.print("[cyan]Result:[/cyan] (stub) summarization would appear here.")