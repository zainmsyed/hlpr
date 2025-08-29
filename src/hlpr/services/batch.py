"""Batch processing service for hlpr.

This module provides high-level batch processing capabilities,
including job submission, monitoring, and result aggregation.
"""
from __future__ import annotations

import logging
from typing import Any

from hlpr.tasks import TaskPriority, get_celery_app, get_task_result
from hlpr.tasks.worker import batch_process_meetings

logger = logging.getLogger(__name__)


class BatchProcessingService:
    """Service for managing batch processing jobs."""

    def __init__(self) -> None:
        self.celery_app = get_celery_app()

    def submit_meeting_batch(
        self,
        meeting_ids: list[int],
        pipeline_config: dict[str, Any] | None = None,
        priority: int = TaskPriority.NORMAL,
        queue: str = "batch",
    ) -> str:
        """Submit a batch of meetings for processing.

        Args:
            meeting_ids: List of meeting IDs to process
            pipeline_config: Optional pipeline configuration
            priority: Task priority level
            queue: Queue to submit to

        Returns:
            Task ID for tracking the batch job
        """
        try:
            # Submit the batch processing task
            task = batch_process_meetings.apply_async(
                args=[meeting_ids, pipeline_config],
                kwargs={"priority": priority},
                queue=queue,
                priority=priority,
            )

            logger.info(f"Submitted batch processing task {task.id} for {len(meeting_ids)} meetings")
            return str(task.id)

        except Exception as e:
            logger.error(f"Failed to submit batch processing task: {e}")
            raise

    def submit_optimization_job(
        self,
        config: dict[str, Any],
        priority: int = TaskPriority.HIGH,
        queue: str = "optimization",
    ) -> str:
        """Submit a pipeline optimization job.

        Args:
            config: Optimization configuration
            priority: Task priority level
            queue: Queue to submit to

        Returns:
            Task ID for tracking the optimization job
        """
        try:
            from hlpr.tasks.worker import optimize_meeting_pipeline

            # Submit the optimization task
            task = optimize_meeting_pipeline.apply_async(
                args=[config],
                kwargs={"priority": priority},
                queue=queue,
                priority=priority,
            )

            logger.info(f"Submitted optimization task {task.id}")
            return str(task.id)

        except Exception as e:
            logger.error(f"Failed to submit optimization task: {e}")
            raise

    def get_batch_status(self, task_id: str) -> dict[str, Any] | None:
        """Get the status of a batch processing task.

        Args:
            task_id: The task ID to check

        Returns:
            Dictionary with task status information
        """
        try:
            result = get_task_result(task_id)

            if result and isinstance(result, dict):
                # Add batch-specific information
                if result.get("status") == "PROGRESS":
                    result["progress_percentage"] = (
                        result.get("current", 0) / result.get("total", 1) * 100
                    )

                return result  # type: ignore[no-any-return]

            return None

        except Exception as e:
            logger.error(f"Error getting batch status for {task_id}: {e}")
            return None

    def cancel_batch(self, task_id: str) -> bool:
        """Cancel a batch processing task.

        Args:
            task_id: The task ID to cancel

        Returns:
            True if successfully cancelled, False otherwise
        """
        try:
            from hlpr.tasks import revoke_task
            success = bool(revoke_task(task_id, terminate=True))

            if success:
                logger.info(f"Cancelled batch task {task_id}")
            else:
                logger.warning(f"Failed to cancel batch task {task_id}")

            return success

        except Exception as e:
            logger.error(f"Error cancelling batch task {task_id}: {e}")
            return False

    def get_batch_results(self, task_id: str) -> dict[str, Any] | None:
        """Get the results of a completed batch processing task.

        Args:
            task_id: The task ID to get results for

        Returns:
            Dictionary with batch results or None if not completed
        """
        try:
            result = get_task_result(task_id)

            if result and isinstance(result, dict) and result.get("status") == "SUCCESS":
                batch_result = result.get("result")
                return batch_result if isinstance(batch_result, dict) else None

            return None

        except Exception as e:
            logger.error(f"Error getting batch results for {task_id}: {e}")
            return None

    def list_active_batches(self) -> list[dict[str, Any]]:
        """List all active batch processing tasks.

        Returns:
            List of active batch task information
        """
        try:
            from hlpr.tasks.queue import get_queue_manager
            queue_manager = get_queue_manager()

            # Get active tasks from batch queue
            active_tasks = queue_manager.list_active_tasks("batch")

            # Filter for batch processing tasks
            batch_tasks = [
                task for task in active_tasks
                if task.get("name") == "hlpr.tasks.worker.batch_process_meetings"
            ]

            return batch_tasks

        except Exception as e:
            logger.error(f"Error listing active batches: {e}")
            return []

    def create_meeting_batch_from_query(
        self,
        query: str | None = None,
        limit: int | None = None,
        priority: int = TaskPriority.NORMAL,
    ) -> str:
        """Create and submit a batch from a database query.

        Args:
            query: Optional query to filter meetings
            limit: Optional limit on number of meetings
            priority: Task priority level

        Returns:
            Task ID for the created batch
        """
        try:
            # This would query the database to get meeting IDs
            # For now, we'll create a simple batch with some example IDs
            meeting_ids = [1, 2, 3, 4, 5]  # Example IDs

            if limit:
                meeting_ids = meeting_ids[:limit]

            # Submit the batch
            task_id = self.submit_meeting_batch(
                meeting_ids=meeting_ids,
                priority=priority,
            )

            logger.info(f"Created batch from query with {len(meeting_ids)} meetings")
            return task_id

        except Exception as e:
            logger.error(f"Error creating batch from query: {e}")
            raise


class BatchJob:
    """Represents a batch processing job."""

    def __init__(
        self,
        task_id: str,
        job_type: str,
        description: str,
        created_by: str | None = None,
    ):
        self.task_id = task_id
        self.job_type = job_type
        self.description = description
        self.created_by = created_by
        self.created_at = "2025-08-28T00:00:00Z"  # Would be datetime.now()

    def to_dict(self) -> dict[str, Any]:
        """Convert batch job to dictionary."""
        return {
            "task_id": self.task_id,
            "job_type": self.job_type,
            "description": self.description,
            "created_by": self.created_by,
            "created_at": self.created_at,
        }


# Global batch service instance
_batch_service: BatchProcessingService | None = None


def get_batch_service() -> BatchProcessingService:
    """Get the global batch processing service instance."""
    global _batch_service
    if _batch_service is None:
        _batch_service = BatchProcessingService()
    return _batch_service