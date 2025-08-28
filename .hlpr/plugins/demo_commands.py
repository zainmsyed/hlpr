# Example plugin: demo_commands.py
"""
Demo plugin showing how to create custom hlpr commands.

This plugin demonstrates:
- Basic command registration with @hlpr_command
- Parameter handling with typer options
- Integration with hlpr's console and utilities
- Error handling and success messages
"""

import typer

from hlpr.cli.base import console, print_error, print_success
from hlpr.cli.plugins import hlpr_command


@hlpr_command("quick-demo", help="Run a quick demo workflow")
def quick_demo_workflow(
    meeting_id: int = typer.Option(..., "--meeting-id", "-m", help="Meeting ID to process"),
    model: str = typer.Option("ollama/gemma3", "--model", help="Model to use"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be done")
):
    """Demo workflow: create, train, and summarize a meeting."""
    console.print(f"🚀 Starting demo workflow for meeting {meeting_id}")

    if dry_run:
        console.print("[yellow]DRY RUN MODE - No actual processing[/yellow]")
        console.print(f"  Would process meeting: {meeting_id}")
        console.print(f"  Would use model: {model}")
        return

    try:
        # Simulate processing steps
        console.print("  📝 Step 1: Loading meeting data...")
        console.print("  🧠 Step 2: Initializing model...")
        console.print("  ⚙️ Step 3: Running optimization...")
        console.print("  📊 Step 4: Generating summary...")

        # Your custom logic would go here
        # For example:
        # from hlpr.services import MeetingService
        # service = MeetingService()
        # result = service.process_meeting(meeting_id, model)

        print_success(f"Demo completed for meeting {meeting_id} using {model}")

    except Exception as e:
        print_error(f"Demo failed: {e}")


@hlpr_command("hello", help="Say hello with custom greeting")
def hello_command(
    name: str = typer.Option("World", "--name", "-n", help="Name to greet"),
    style: str = typer.Option("normal", "--style", help="Greeting style: normal, excited, formal"),
    repeat: int = typer.Option(1, "--repeat", "-r", help="Number of times to repeat")
):
    """A simple hello command with different styles."""
    greetings = {
        "excited": f"HELLO {name.upper()}!!! 🎉",
        "formal": f"Good day, {name}. How do you do?",
        "normal": f"Hello, {name}!",
        "pirate": f"Ahoy, {name}! Ye be greeted!",
        "robot": f"GREETING: {name}. HUMAN DETECTED."
    }

    greeting = greetings.get(style, f"Hello, {name}!")

    for i in range(repeat):
        if repeat > 1:
            console.print(f"[green]{i+1}. {greeting}[/green]")
        else:
            console.print(f"[green]{greeting}[/green]")


@hlpr_command("workspace-info", help="Show extended workspace information")
def workspace_info_command(
    include_files: bool = typer.Option(False, "--files", help="Include file listing"),
    include_stats: bool = typer.Option(False, "--stats", help="Include workspace statistics")
):
    """Extended workspace information beyond the basic status command."""
    import os
    from pathlib import Path

    console.print("[bold green]📊 Extended Workspace Information[/bold green]")

    cwd = Path.cwd()

    # Basic info
    console.print(f"Current directory: [bold]{cwd}[/bold]")
    console.print(f"Absolute path: [bold]{cwd.absolute()}[/bold]")

    # File information
    if include_files:
        console.print("\n[bold blue]Files in workspace:[/bold blue]")
        try:
            files = list(cwd.iterdir())
            files.sort()

            for file_path in files:
                if file_path.is_file():
                    size = file_path.stat().st_size
                    console.print(f"  📄 {file_path.name} ({size} bytes)")
                elif file_path.is_dir():
                    item_count = len(list(file_path.iterdir()))
                    console.print(f"  📁 {file_path.name}/ ({item_count} items)")
        except Exception as e:
            console.print(f"[red]Error reading files: {e}[/red]")

    # Statistics
    if include_stats:
        console.print("\n[bold blue]Workspace Statistics:[/bold blue]")
        try:
            total_files = 0
            total_dirs = 0
            total_size = 0

            for root, dirs, files in os.walk(cwd):
                total_dirs += len(dirs)
                total_files += len(files)
                for file in files:
                    try:
                        total_size += os.path.getsize(os.path.join(root, file))
                    except OSError:
                        pass

            console.print(f"  Total files: {total_files}")
            console.print(f"  Total directories: {total_dirs}")
            console.print(f"  Total size: {total_size:,} bytes ({total_size/1024/1024:.2f} MB)")

        except Exception as e:
            console.print(f"[red]Error calculating stats: {e}[/red]")

    print_success("Workspace information displayed!")


@hlpr_command("meeting-workflow", help="Complete meeting processing workflow")
def meeting_workflow_command(
    meeting_id: int = typer.Option(..., "--meeting-id", "-m", help="Meeting ID to process"),
    steps: str = typer.Option("all", "--steps", help="Steps to run: all, create, train, summarize"),
    output_format: str = typer.Option("markdown", "--format", help="Output format")
):
    """Run a complete meeting processing workflow with custom steps."""
    console.print(f"🔄 Starting meeting workflow for ID: {meeting_id}")
    console.print(f"Steps to run: {steps}")
    console.print(f"Output format: {output_format}")

    workflow_steps = {
        "create": "📝 Creating meeting record",
        "train": "🧠 Training optimization model",
        "summarize": "📊 Generating meeting summary"
    }

    if steps == "all":
        steps_to_run = workflow_steps.keys()
    else:
        steps_to_run = [s.strip() for s in steps.split(",")]

    for step in steps_to_run:
        if step in workflow_steps:
            console.print(f"  {workflow_steps[step]}...")
            # Simulate processing time
            import time
            time.sleep(0.5)
        else:
            print_error(f"Unknown step: {step}")
            return

    print_success(f"Meeting workflow completed for ID {meeting_id}!")
    console.print(f"Output saved in {output_format} format")