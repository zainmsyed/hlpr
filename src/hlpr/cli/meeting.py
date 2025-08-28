"""Meeting-related CLI commands."""
from __future__ import annotations

import typer

from hlpr.cli.base import app, console


@app.command("summarize")
def summarize(document_id: int) -> None:  # pragma: no cover - IO heavy
    """Summarize a document by its ID using the summarization pipeline."""
    import asyncio

    from hlpr.db.base import get_session_factory, init_models
    from hlpr.db.repositories import DocumentRepository, PipelineRunRepository
    from hlpr.services.pipelines import PipelineService

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


@app.command("summarize-meeting")
def summarize_meeting(
    meeting_id: int,
    model: str = typer.Option("ollama/gemma3", help="DSPy model identifier (e.g., ollama/gemma3)"),
    output: str | None = typer.Option(None, "-o", "--output", help="Output Markdown file path"),
) -> None:
    """Invoke DSPy MeetingProgram with Ollama/Gemma3 and write Markdown minutes."""
    import asyncio

    from hlpr.db.base import get_session_factory, init_models

    async def _run() -> None:
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
                from pathlib import Path

                import dspy
                name = model.split("/")[-1]
                # Use Docker detection like in optimizer.py
                api_base = "http://host.docker.internal:11434" if Path("/.dockerenv").exists() else "http://localhost:11434"
                dspy.configure(lm=dspy.LM(model=f"ollama/{name}", api_base=api_base))
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
            action_items = res.get("action_items", [])
            console.print("[bold green]Summary:[/bold green]\n" + summary)
            if action_items:
                console.print("\n[bold cyan]Action Items:[/bold cyan]")
                for it in action_items:
                    console.print(f" - {it}")
            # Write Markdown file
            from pathlib import Path
            md = [f"# Meeting {meeting_id} Minutes", "", "## Summary", summary, "", "## Action Items"]
            md += [f"- {it}" for it in action_items] if action_items else ["- None"]
            path = Path(output) if output else Path(f"meeting_{meeting_id}_minutes.md")
            try:
                path.write_text("\n".join(md), encoding="utf-8")
                console.print(f"[bold green]Wrote minutes to {path}[/bold green]")
            except Exception as e:
                console.print(f"[red]Error writing file: {e}[/]")

    asyncio.run(_run())