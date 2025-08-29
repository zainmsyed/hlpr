"""Task management commands."""
from __future__ import annotations

import typer

from hlpr.cli.base import app, print_error


@app.command("task-status")  # type: ignore[misc]
def task_status(
    task_id: str = typer.Argument(..., help="Task ID to check status for"),
) -> None:
    """Check the status of a background task."""
    from rich.table import Table

    from hlpr.cli.base import console
    from hlpr.tasks import get_task_result

    try:
        result = get_task_result(task_id)

        if not result:
            print_error(f"Task {task_id} not found or has expired")
            return

        # Create status table
        table = Table(title=f"Task Status: {task_id}")
        table.add_column("Property", style="cyan", no_wrap=True)
        table.add_column("Value", style="white")

        table.add_row("Task ID", task_id)
        table.add_row("Status", result.get("status", "Unknown"))

        if result.get("status") == "PROGRESS":
            current = result.get("current", 0)
            total = result.get("total", 100)
            percentage = (current / total * 100) if total > 0 else 0
            table.add_row("Progress", f"{current}/{total} ({percentage:.1f}%)")
            table.add_row("Message", result.get("message", ""))

        elif result.get("status") == "SUCCESS":
            table.add_row("Completed", "Yes")

        elif result.get("status") == "FAILURE":
            table.add_row("Error", result.get("error", "Unknown error"))
            if result.get("traceback"):
                table.add_row("Traceback", result.get("traceback", "")[:200] + "...")

        console.print(table)

    except Exception as e:
        print_error(f"Error checking task status: {e}")


@app.command("task-result")  # type: ignore[misc]
def task_result(
    task_id: str = typer.Argument(..., help="Task ID to get results for"),
) -> None:
    """Get the results of a completed background task."""

    from rich import print_json

    from hlpr.cli.base import console
    from hlpr.tasks import get_task_result

    try:
        result = get_task_result(task_id)

        if not result:
            print_error(f"Task {task_id} not found or has expired")
            return

        if result.get("status") != "SUCCESS":
            print_error(f"Task {task_id} is not completed yet. Status: {result.get('status')}")
            return

        # Pretty print the result
        console.print(f"[bold green]Results for task {task_id}:[/bold green]")
        print_json(data=result.get("result", {}))

    except Exception as e:
        print_error(f"Error getting task results: {e}")


@app.command("task-cancel")  # type: ignore[misc]
def task_cancel(
    task_id: str = typer.Argument(..., help="Task ID to cancel"),
) -> None:
    """Cancel a running background task."""
    from hlpr.cli.base import print_success
    from hlpr.tasks import revoke_task

    try:
        success = revoke_task(task_id, terminate=True)

        if success:
            print_success(f"Task {task_id} cancelled successfully")
        else:
            print_error(f"Failed to cancel task {task_id}")

    except Exception as e:
        print_error(f"Error cancelling task: {e}")


@app.command("task-list")  # type: ignore[misc]
def task_list(
    queue: str = typer.Option("all", help="Queue to list tasks from (celery, batch, optimization, all)"),
) -> None:
    """List active background tasks."""
    import asyncio

    from rich.table import Table

    from hlpr.cli.base import console
    from hlpr.tasks.queue import get_queue_manager

    async def _list_tasks() -> None:
        try:
            queue_manager = get_queue_manager()

            if queue == "all":
                # Get stats for all queues
                stats = await queue_manager.get_all_queue_stats()

                table = Table(title="Queue Statistics")
                table.add_column("Queue", style="cyan", no_wrap=True)
                table.add_column("Length", style="white")
                table.add_column("Active", style="white")
                table.add_column("Scheduled", style="white")
                table.add_column("Total Pending", style="white")

                for queue_name, queue_stats in stats.items():
                    table.add_row(
                        queue_name,
                        str(queue_stats.get("length", 0)),
                        str(queue_stats.get("active_tasks", 0)),
                        str(queue_stats.get("scheduled_tasks", 0)),
                        str(queue_stats.get("total_pending", 0)),
                    )

                console.print(table)

            else:
                # Get active tasks for specific queue
                active_tasks = await queue_manager.list_active_tasks(queue)

                if not active_tasks:
                    console.print(f"[yellow]No active tasks in queue '{queue}'[/yellow]")
                    return

                table = Table(title=f"Active Tasks in Queue: {queue}")
                table.add_column("Task ID", style="cyan", no_wrap=True)
                table.add_column("Name", style="white")
                table.add_column("Worker", style="white")
                table.add_column("Started", style="white")

                for task in active_tasks:
                    table.add_row(
                        task.get("task_id", ""),
                        task.get("name", ""),
                        task.get("worker", ""),
                        task.get("started", ""),
                    )

                console.print(table)

        except Exception as e:
            print_error(f"Error listing tasks: {e}")

    asyncio.run(_list_tasks())


@app.command("batch-submit")  # type: ignore[misc]
def batch_submit(
    meeting_ids: str = typer.Argument(..., help="Comma-separated list of meeting IDs"),
    priority: int = typer.Option(5, help="Task priority (1-10, higher = more important)"),
) -> None:
    """Submit a batch of meetings for processing."""
    from hlpr.cli.base import console, print_success
    from hlpr.services.batch import get_batch_service

    try:
        # Parse meeting IDs
        ids = [int(id.strip()) for id in meeting_ids.split(",") if id.strip()]

        if not ids:
            print_error("No valid meeting IDs provided")
            return

        # Submit batch
        batch_service = get_batch_service()
        task_id = batch_service.submit_meeting_batch(
            meeting_ids=ids,
            priority=priority,
        )

        print_success("Batch submitted successfully!")
        console.print(f"📊 Task ID: {task_id}")
        console.print(f"📚 Meetings: {len(ids)}")
        console.print(f"⭐ Priority: {priority}")
        console.print()
        console.print("[yellow]Monitor progress with:[/yellow]")
        console.print(f"  hlpr task-status {task_id}")

    except Exception as e:
        print_error(f"Error submitting batch: {e}")


@app.command("batch-status")  # type: ignore[misc]
def batch_status(
    task_id: str = typer.Argument(..., help="Batch task ID to check"),
) -> None:
    """Check the status of a batch processing task."""
    from rich.table import Table

    from hlpr.cli.base import console
    from hlpr.services.batch import get_batch_service

    try:
        batch_service = get_batch_service()
        result = batch_service.get_batch_status(task_id)

        if not result:
            print_error(f"Batch task {task_id} not found")
            return

        # Create status table
        table = Table(title=f"Batch Status: {task_id}")
        table.add_column("Property", style="cyan", no_wrap=True)
        table.add_column("Value", style="white")

        table.add_row("Task ID", task_id)
        table.add_row("Status", result.get("status", "Unknown"))

        if result.get("status") == "PROGRESS":
            current = result.get("current", 0)
            total = result.get("total", 100)
            percentage = (current / total * 100) if total > 0 else 0
            table.add_row("Progress", f"{current}/{total} ({percentage:.1f}%)")
            table.add_row("Message", result.get("message", ""))

        elif result.get("status") == "SUCCESS":
            batch_result = result.get("result", {})
            table.add_row("Total Processed", str(batch_result.get("total_processed", 0)))
            table.add_row("Successful", str(batch_result.get("successful", 0)))
            table.add_row("Failed", str(batch_result.get("failed", 0)))

        console.print(table)

    except Exception as e:
        print_error(f"Error checking batch status: {e}")