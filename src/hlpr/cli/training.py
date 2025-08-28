"""Training and optimization CLI commands."""
from __future__ import annotations

import typer

from hlpr.cli.base import app, console


@app.command("optimize-meeting")
def optimize_meeting(
    data_path: str = typer.Option(
        "documents/training-data/meetings.txt", help="Path to meeting dataset (JSONL)"
    ),
    iters: int = typer.Option(5, help="Number of optimization iterations"),
    include_unverified: bool = typer.Option(
        False, help="Include unverified / noisy examples"
    ),
    model: str | None = typer.Option(None, help="Model identifier (e.g., ollama/llama3)"),
    optimizer: str = typer.Option(
        "mipro", help="Optimization strategy: mipro, copro, bootstrap, bootstrap_random"
    ),
    max_bootstrapped_demos: int = typer.Option(4, help="Max bootstrapped demonstrations"),
    max_labeled_demos: int = typer.Option(16, help="Max labeled demonstrations"),
) -> None:  # pragma: no cover - IO heavy
    """Run advanced DSPy optimization (MIPROv2, COPRO, Bootstrap) over meeting dataset."""
    from rich.progress import Progress, SpinnerColumn, TextColumn

    from hlpr.dspy.optimizer import OptimizerConfig, optimize

    # Validate optimizer choice
    valid_optimizers = ["mipro", "copro", "bootstrap", "bootstrap_random"]
    if optimizer not in valid_optimizers:
        console.print(f"[red]Invalid optimizer: {optimizer}. Choose from: {valid_optimizers}[/red]")
        return

    cfg = OptimizerConfig(
        data_path=data_path,
        iters=iters,
        include_unverified=include_unverified,
        model=model,
        optimizer=optimizer,
        max_bootstrapped_demos=max_bootstrapped_demos,
        max_labeled_demos=max_labeled_demos,
    )

    console.print(f"[bold blue]🚀 Starting {optimizer.upper()} optimization[/bold blue]")
    console.print(f"📊 Dataset: {data_path}")
    console.print(f"🔧 Model: {model or 'gpt-3.5-turbo'}")
    console.print(f"🔁 Iterations: {iters}")
    console.print(f"📚 Include unverified: {include_unverified}")

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Optimizing...", total=None)
            result = optimize(cfg)
            progress.update(task, description="✅ Complete!")

        # Display results
        console.print("\n[bold green]🎉 Optimization Results[/bold green]")
        console.print(f"📈 Composite F1 Score: [bold cyan]{result['composite_score']:.3f}[/bold cyan]")
        console.print(f"📝 Summary F1: {result['summary_f1']:.3f}")
        console.print(f"📋 Action Items F1: {result['action_f1']:.3f}")
        console.print(f"⏱️  Optimization Time: {result['optimization_time']:.1f}s")
        console.print(f"💾 Artifact: [bold]{result['artifact_path']}[/bold]")

    except Exception as e:
        console.print(f"[red]❌ Optimization failed: {e}[/red]")
        raise typer.Exit(1) from None