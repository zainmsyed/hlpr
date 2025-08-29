"""Task queue management for hlpr.

This module provides high-level abstractions for managing task queues,
including queue inspection, task monitoring, and queue operations.
"""
from __future__ import annotations

import logging
from typing import Any

from hlpr.core.redis_client import redis_delete
from hlpr.tasks import get_celery_app

logger = logging.getLogger(__name__)


class TaskQueueManager:
    """Manager for task queue operations and monitoring."""

    def __init__(self) -> None:
        self.celery_app = get_celery_app()

    async def get_queue_stats(self, queue_name: str = "celery") -> dict[str, Any]:
        """Get statistics for a specific queue.

        Args:
            queue_name: Name of the queue to inspect

        Returns:
            Dictionary with queue statistics
        """
        try:
            # Get active queues
            inspect = self.celery_app.control.inspect()

            # Get queue length using Redis
            from hlpr.core.redis_client import get_redis_client
            redis_client = await get_redis_client()
            queue_length = await redis_client.llen(f"celery:{queue_name}")

            # Get active tasks
            active_tasks = inspect.active()
            if active_tasks:
                active_count = sum(len(tasks) for tasks in active_tasks.values())
            else:
                active_count = 0

            # Get scheduled tasks
            scheduled_tasks = inspect.scheduled()
            if scheduled_tasks:
                scheduled_count = sum(len(tasks) for tasks in scheduled_tasks.values())
            else:
                scheduled_count = 0

            return {
                "queue_name": queue_name,
                "length": queue_length,
                "active_tasks": active_count,
                "scheduled_tasks": scheduled_count,
                "total_pending": queue_length + scheduled_count,
            }
        except Exception as e:
            logger.error(f"Error getting queue stats for {queue_name}: {e}")
            return {
                "queue_name": queue_name,
                "error": str(e),
                "length": 0,
                "active_tasks": 0,
                "scheduled_tasks": 0,
                "total_pending": 0,
            }

    async def get_all_queue_stats(self) -> dict[str, dict[str, Any]]:
        """Get statistics for all queues.

        Returns:
            Dictionary mapping queue names to their statistics
        """
        queues = ["celery", "batch", "optimization"]
        stats = {}

        for queue in queues:
            stats[queue] = await self.get_queue_stats(queue)

        return stats

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a running or pending task.

        Args:
            task_id: The task ID to cancel

        Returns:
            True if successfully cancelled, False otherwise
        """
        try:
            # First try to revoke the task
            from hlpr.tasks import revoke_task
            success = bool(revoke_task(task_id, terminate=True))

            if success:
                # Clean up any cached results
                await redis_delete(f"celery-task-meta-{task_id}")
                logger.info(f"Task {task_id} cancelled successfully")
            else:
                logger.warning(f"Failed to cancel task {task_id}")

            return success
        except Exception as e:
            logger.error(f"Error cancelling task {task_id}: {e}")
            return False

    async def get_task_info(self, task_id: str) -> dict[str, Any] | None:
        """Get detailed information about a task.

        Args:
            task_id: The task ID to inspect

        Returns:
            Dictionary with task information or None if not found
        """
        try:
            from hlpr.tasks import get_task_result
            result = get_task_result(task_id)

            if result is not None and isinstance(result, dict):
                # Add additional metadata
                result["queue"] = await self._get_task_queue(task_id)
                result["worker"] = await self._get_task_worker(task_id)
                result["started_at"] = await self._get_task_start_time(task_id)
                return result  # type: ignore[no-any-return]
            else:
                return None
        except Exception as e:
            logger.error(f"Error getting task info for {task_id}: {e}")
            return None

    async def list_active_tasks(self, queue_name: str = "celery") -> list[dict[str, Any]]:
        """List all active tasks in a queue.

        Args:
            queue_name: Name of the queue to inspect

        Returns:
            List of active task dictionaries
        """
        try:
            inspect = self.celery_app.control.inspect()
            active_tasks = inspect.active()

            if not active_tasks:
                return []

            tasks = []
            for worker, worker_tasks in active_tasks.items():
                for task in worker_tasks:
                    if task.get("delivery_info", {}).get("routing_key") == queue_name:
                        tasks.append({
                            "task_id": task["id"],
                            "name": task["name"],
                            "args": task["args"],
                            "kwargs": task["kwargs"],
                            "worker": worker,
                            "started": task.get("time_start"),
                            "queue": queue_name,
                        })

            return tasks
        except Exception as e:
            logger.error(f"Error listing active tasks for queue {queue_name}: {e}")
            return []

    async def purge_queue(self, queue_name: str) -> int:
        """Purge all pending tasks from a queue.

        Args:
            queue_name: Name of the queue to purge

        Returns:
            Number of tasks purged
        """
        try:
            from hlpr.core.redis_client import get_redis_client
            redis_client = await get_redis_client()

            queue_key = f"celery:{queue_name}"
            purged_count = int(await redis_client.delete(queue_key))

            logger.info(f"Purged {purged_count} tasks from queue {queue_name}")
            return purged_count
        except Exception as e:
            logger.error(f"Error purging queue {queue_name}: {e}")
            return 0

    async def _get_task_queue(self, task_id: str) -> str | None:
        """Get the queue name for a task."""
        try:
            # This is a simplified check - in practice, you'd need to scan the queue
            # For now, we'll return None as this requires more complex Redis operations
            return None
        except Exception:
            return None

    async def _get_task_worker(self, task_id: str) -> str | None:
        """Get the worker processing a task."""
        try:
            inspect = self.celery_app.control.inspect()
            active_tasks = inspect.active()

            if active_tasks:
                for _worker, tasks in active_tasks.items():
                    if any(task["id"] == task_id for task in tasks):
                        return str(_worker)

            return None
        except Exception:
            return None

    async def _get_task_start_time(self, task_id: str) -> float | None:
        """Get the start time of a task."""
        try:
            inspect = self.celery_app.control.inspect()
            active_tasks = inspect.active()

            if active_tasks:
                for _worker, tasks in active_tasks.items():
                    for task in tasks:
                        if task["id"] == task_id:
                            time_start = task.get("time_start")
                            return float(time_start) if time_start is not None else None

            return None
        except Exception:
            return None


# Global queue manager instance
_queue_manager: TaskQueueManager | None = None


def get_queue_manager() -> TaskQueueManager:
    """Get the global queue manager instance."""
    global _queue_manager
    if _queue_manager is None:
        _queue_manager = TaskQueueManager()
    return _queue_manager