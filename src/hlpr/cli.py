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


@app_cli.command("summarize-meeting")
def summarize_meeting(
    meeting_id: int,
    model: str = typer.Option("ollama/gemma3", help="DSPy model identifier (e.g., ollama/gemma3)"),
    output: str | None = typer.Option(None, "-o", "--output", help="Output Markdown file path"),
) -> None:
    """Invoke DSPy MeetingProgram with Ollama/Gemma3 and write Markdown minutes."""
    import asyncio

    async def _run():
        await init_models(drop=False)
        session_factory = get_session_factory()
        async with session_factory() as session:
            from hlpr.db.repositories import MeetingRepository
            # Load meeting
            meeting = await MeetingRepository(session).get(meeting_id)
            if meeting is None:
                console.print(f"[red]Meeting {meeting_id} not found[/red]")
                return
            transcript = meeting.transcript
            # Configure DSPy for Ollama/Gemma3
            try:
                import dspy
                name = model.split("/")[-1]
                dspy.configure(lm=dspy.LM(model=f"ollama/{name}", api_base="http://localhost:11434"))
            except Exception as e:
                console.print(f"[yellow]Warning: failed to configure DSPy model {model}: {e}[/]")
            # Run MeetingProgram
            try:
                from hlpr.dspy.optimizer import MeetingProgram
                prog = MeetingProgram()
                res = prog(transcript=transcript)
            except Exception as e:
                console.print(f"[red]Error invoking MeetingProgram: {e}[/]")
                return
            summary = res.get("summary", "")
            items = res.get("action_items", [])
            console.print("[bold green]Summary:[/bold green]\n" + summary)
            if items:
                console.print("\n[bold cyan]Action Items:[/bold cyan]")
                for it in items:
                    console.print(f" - {it}")
            # Write Markdown file
            from pathlib import Path
            md = [f"# Meeting {meeting_id} Minutes", "", "## Summary", summary, "", "## Action Items"]
            md += [f"- {it}" for it in items] if items else ["- None"]
            path = Path(output) if output else Path(f"meeting_{meeting_id}_minutes.md")
            try:
                path.write_text("\n".join(md), encoding="utf-8")
                console.print(f"[bold green]Wrote minutes to {path}[/bold green]")
            except Exception as e:
                console.print(f"[red]Error writing file: {e}[/]")
    asyncio.run(_run())


@app_cli.command("optimize-meeting")
def optimize_meeting(
    data_path: str = typer.Option(
        "documents/training-data/meetings.txt", help="Path to meeting dataset (JSONL)"
    ),
    iters: int = typer.Option(2, help="Number of optimization iterations"),
    include_unverified: bool = typer.Option(
        False, help="Include unverified / noisy examples"
    ),
    model: str | None = typer.Option(None, help="Model identifier (e.g., ollama/llama3)"),
) -> None:  # pragma: no cover - IO heavy
    """Run lightweight DSPy optimization over meeting dataset and store artifact."""
    cfg = OptimizerConfig(
        data_path=data_path,
        iters=iters,
        include_unverified=include_unverified,
        model=model,
    )
    result = optimize(cfg)
    console.print(f"[green]Optimization complete[/green]: {result}")


@app_cli.command("db-init")
def db_init(
    drop: bool = typer.Option(False, "--drop", help="Drop existing tables before initializing"),
) -> None:
    """Initialize database tables."""
    import asyncio
    from hlpr.db.base import init_models

    async def _run():
        # Ensure tables exist (optionally drop)
        await init_models(drop=drop)
        console.print("[green]Database initialized[/green]")

    asyncio.run(_run())


if __name__ == "__main__":  # pragma: no cover
    app_cli()
