"""Meeting-related CLI commands."""
from __future__ import annotations

import typer

from hlpr.cli.base import app, console


@app.command("summarize")  # type: ignore[misc]
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


@app.command("quick-meeting")  # type: ignore[misc]
def quick_meeting(
    meeting_id: int,
    preset: str = typer.Option("default", help="Output preset (default, detailed, minimal)"),
    model: str | None = typer.Option(None, help="Override model identifier"),
) -> None:  # pragma: no cover - IO heavy
    """Quick meeting summarization with smart defaults.

    This command provides a simplified way to summarize meetings using
    predefined output presets and automatic model detection.
    """
    import asyncio

    from hlpr.db.base import get_session_factory, init_models

    # Define output presets
    presets: dict[str, dict[str, str | bool]] = {
        "default": {
            "output": f"meeting_{meeting_id}_summary.md",
            "include_action_items": True,
            "include_transcript": False,
        },
        "detailed": {
            "output": f"meeting_{meeting_id}_detailed.md",
            "include_action_items": True,
            "include_transcript": True,
        },
        "minimal": {
            "output": f"meeting_{meeting_id}_minimal.md",
            "include_action_items": False,
            "include_transcript": False,
        },
    }

    if preset not in presets:
        console.print(f"[red]Unknown preset: {preset}[/red]")
        console.print(f"[yellow]Available presets: {', '.join(presets.keys())}[/yellow]")
        return

    preset_config = presets[preset]
    output_file = str(preset_config["output"])

    # Use provided model or default
    selected_model = model or "ollama/gemma3"

    console.print("[bold blue]🚀 Quick Meeting Summarization[/bold blue]")
    console.print(f"📊 Meeting ID: {meeting_id}")
    console.print(f"🔧 Model: {selected_model}")
    console.print(f"📝 Preset: {preset}")
    console.print(f"💾 Output: {output_file}")

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

            # Configure DSPy for the selected model
            try:
                from pathlib import Path

                import dspy

                name = selected_model.split("/")[-1]
                # Use Docker detection like in optimizer.py
                api_base = "http://host.docker.internal:11434" if Path("/.dockerenv").exists() else "http://localhost:11434"
                dspy.configure(lm=dspy.LM(model=f"ollama/{name}", api_base=api_base))
            except Exception as e:
                console.print(f"[yellow]Warning: failed to configure DSPy model {selected_model}: {e}[/]")

            # Run MeetingProgram
            try:
                from hlpr.dspy.programs import MeetingProgram

                prog = MeetingProgram()
                res = prog(transcript=transcript)
            except Exception as e:
                console.print(f"[red]Error invoking MeetingProgram: {e}[/]")
                return

            summary = res.get("summary", "")
            action_items = res.get("action_items", [])

            console.print("[bold green]Summary:[/bold green]\n" + summary)

            if action_items and preset_config["include_action_items"]:
                console.print("\n[bold cyan]Action Items:[/bold cyan]")
                for it in action_items:
                    console.print(f" - {it}")

            # Generate output based on preset
            from pathlib import Path

            md = [f"# Meeting {meeting_id} Summary", "", "## Summary", summary, ""]

            if action_items and preset_config["include_action_items"]:
                md += ["## Action Items"] + [f"- {it}" for it in action_items] + [""]

            if preset_config["include_transcript"]:
                md += ["## Transcript", "", "```", transcript, "```"]

            path = Path(output_file)
            try:
                path.write_text("\n".join(md), encoding="utf-8")
                console.print(f"[bold green]✅ Wrote summary to {path}[/bold green]")
            except Exception as e:
                console.print(f"[red]Error writing file: {e}[/]")

    asyncio.run(_run())