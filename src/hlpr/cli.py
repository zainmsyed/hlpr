"""Typer CLI entrypoint for hlpr."""

import typer
import uvicorn
from rich.console import Console
from rich.table import Table

from hlpr.core.settings import get_settings
from hlpr.db.base import get_session_factory, init_models
from hlpr.db.repositories import DocumentRepository, PipelineRunRepository
from hlpr.dspy.optimizer import OptimizerConfig, optimize
from hlpr.services.pipelines import PipelineService

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


@app_cli.command("summarize")
def summarize(document_id: int) -> None:  # pragma: no cover - IO heavy
    """Summarize a document by its ID using the summarization pipeline."""
    import asyncio

    async def _run() -> None:
        # Ensure tables exist (safe to call multiple times)
        await init_models(drop=False)
        session_factory = get_session_factory()
        async with session_factory() as session:
            docs = DocumentRepository(session)
            runs = PipelineRunRepository(session)
            service = PipelineService(docs, runs)
            result = await service.summarize_document(document_id)
            console.print(result)

    asyncio.run(_run())

if __name__ == "__main__":  # pragma: no cover
    app_cli()


@app_cli.command("optimize-meeting")
def optimize_meeting(
    data_path: str = "documents/training-data/meetings.txt",
    iters: int = 2,
    include_unverified: bool = typer.Option(False, help="Include unverified / noisy examples"),
    model: str | None = typer.Option(None, help="Model identifier (e.g., ollama/llama3)"),
):  # pragma: no cover - IO heavy
    """Run lightweight DSPy optimization over meeting dataset and store artifact."""
    cfg = OptimizerConfig(
        data_path=data_path,
        iters=iters,
        include_unverified=include_unverified,
        model=model,
    )
    result = optimize(cfg)
    console.print(f"[green]Optimization complete[/green]: {result}")
