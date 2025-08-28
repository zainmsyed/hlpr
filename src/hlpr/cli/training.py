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
        "mipro", help="Optimization strategy: mipro, bootstrap"
    ),
    max_bootstrapped_demos: int = typer.Option(4, help="Max bootstrapped demonstrations"),
    max_labeled_demos: int = typer.Option(16, help="Max labeled demonstrations"),
) -> None:  # pragma: no cover - IO heavy
    """Run advanced DSPy optimization (MIPROv2, COPRO, Bootstrap) over meeting dataset."""
    from rich.progress import Progress, SpinnerColumn, TextColumn

    from hlpr.dspy.optimizer import OptimizerConfig, optimize

    # Validate optimizer choice
    valid_optimizers = ["mipro", "bootstrap"]
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


@app.command("train")
def train(
    preset: str = typer.Option("quick", help="Preset configuration to use (quick, development, production, experimental)"),
    iters: int | None = typer.Option(None, help="Override number of optimization iterations"),
    model: str | None = typer.Option(None, help="Override model identifier"),
    optimizer: str | None = typer.Option(None, help="Override optimization strategy"),
    include_unverified: bool | None = typer.Option(None, help="Override whether to include unverified examples"),
    max_bootstrapped_demos: int | None = typer.Option(None, help="Override max bootstrapped demonstrations"),
    max_labeled_demos: int | None = typer.Option(None, help="Override max labeled demonstrations"),
    advanced: bool = typer.Option(False, "--advanced", help="Show all available options"),
) -> None:  # pragma: no cover - IO heavy
    """Quick training with presets - simplified interface for common optimization tasks.

    This command provides a simplified way to run DSPy optimization using predefined
    presets or custom overrides. Use 'hlpr train --advanced' to see all options.
    """
    from hlpr.cli.presets import apply_preset_to_args, get_preset_manager

    # Get preset manager and create defaults if needed
    manager = get_preset_manager()
    if not manager.list_presets():
        console.print("[yellow]No presets found. Creating default presets...[/yellow]")
        manager.create_default_presets()

    # Build arguments dictionary
    args = {
        "data_path": "documents/training-data/meetings.txt",  # Fixed for now
        "iters": iters,
        "include_unverified": include_unverified,
        "model": model,
        "optimizer": optimizer,
        "max_bootstrapped_demos": max_bootstrapped_demos,
        "max_labeled_demos": max_labeled_demos,
    }

    # Apply preset
    try:
        updated_args = apply_preset_to_args(preset, args)
    except Exception as e:
        console.print(f"[red]Failed to apply preset '{preset}': {e}[/red]")
        console.print("[yellow]Available presets:[/yellow]")
        for name in manager.list_presets().keys():
            console.print(f"  • {name}")
        return

    if advanced:
        # Show advanced options and exit
        console.print("[bold blue]Advanced Training Options:[/bold blue]")
        console.print("\n[bold]Available Presets:[/bold]")
        for name, preset_config in manager.list_presets().items():
            console.print(f"  [cyan]{name}[/cyan]: {preset_config.model_dump(exclude_unset=True)}")

        console.print("\n[bold]Override Options:[/bold]")
        console.print("  --iters INT                    Number of optimization iterations")
        console.print("  --model TEXT                   Model identifier (e.g., ollama/gemma3)")
        console.print("  --optimizer TEXT               Optimization strategy (mipro, bootstrap, etc.)")
        console.print("  --include-unverified           Include unverified/noisy examples")
        console.print("  --max-bootstrapped-demos INT   Max bootstrapped demonstrations")
        console.print("  --max-labeled-demos INT        Max labeled demonstrations")

        console.print("\n[bold]Examples:[/bold]")
        console.print("  hlpr train --preset production --iters 20")
        console.print("  hlpr train --model gpt-4 --optimizer mipro")
        return

    # Call the full optimize-meeting command with preset-applied args
    optimize_meeting(
        data_path=updated_args["data_path"],
        iters=updated_args["iters"],
        include_unverified=updated_args["include_unverified"],
        model=updated_args["model"],
        optimizer=updated_args["optimizer"],
        max_bootstrapped_demos=updated_args["max_bootstrapped_demos"],
        max_labeled_demos=updated_args["max_labeled_demos"],
    )