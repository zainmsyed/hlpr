"""Task queue system initialization for hlpr.

This module provides the foundation for background task processing using Celery
with Redis as the message broker and result backend.
"""
from __future__ import annotations

import logging
from typing import Any

from celery import Celery

from hlpr.core.settings import get_settings

logger = logging.getLogger(__name__)

# Global Celery app instance
_celery_app: Celery | None = None


def get_celery_app() -> Celery:
    """Get or create the Celery application instance."""
    global _celery_app

    if _celery_app is None:
        settings = get_settings()

        _celery_app = Celery(
            "hlpr",
            broker=settings.redis_url,
            backend=settings.redis_url,
            include=["hlpr.tasks.worker"],
        )

        # Configure Celery
        _celery_app.conf.update(
            # Task settings
            task_serializer="json",
            accept_content=["json"],
            result_serializer="json",
            timezone="UTC",
            enable_utc=True,

            # Worker settings
            worker_prefetch_multiplier=1,
            task_acks_late=True,
            worker_disable_rate_limits=False,

            # Result backend settings
            result_expires=3600,  # 1 hour
            result_backend_transport_options={
                "retry_policy": {"timeout": 5.0}
            },

            # Routing
            task_routes={
                "hlpr.tasks.worker.batch_process_meetings": {"queue": "batch"},
                "hlpr.tasks.worker.optimize_meeting_pipeline": {"queue": "optimization"},
            },

            # Task time limits
            task_time_limit=3600,  # 1 hour
            task_soft_time_limit=3300,  # 55 minutes
        )

        logger.info("Celery application initialized with Redis broker")

    return _celery_app


def create_celery_app_for_worker() -> Celery:
    """Create a Celery app instance specifically for worker processes."""
    settings = get_settings()

    app = Celery(
        "hlpr_worker",
        broker=settings.redis_url,
        backend=settings.redis_url,
        include=["hlpr.tasks.worker"],
    )

    # Worker-specific configuration
    app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        worker_prefetch_multiplier=1,
        task_acks_late=True,
        result_expires=3600,
    )

    return app


# Task result status constants
class TaskStatus:
    """Task execution status constants."""

    PENDING = "PENDING"
    PROGRESS = "PROGRESS"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    RETRY = "RETRY"
    REVOKED = "REVOKED"


# Task priority constants
class TaskPriority:
    """Task priority levels."""

    LOW = 0
    NORMAL = 5
    HIGH = 9
    CRITICAL = 10


def get_task_result(task_id: str) -> dict[str, Any] | None:
    """Get the result of a task by its ID.

    Args:
        task_id: The task ID to retrieve

    Returns:
        Task result dictionary or None if not found
    """
    try:
        app = get_celery_app()
        result = app.AsyncResult(task_id)

        if result.state == TaskStatus.SUCCESS:
            return {
                "status": result.state,
                "result": result.result,
                "task_id": task_id,
            }
        elif result.state == TaskStatus.FAILURE:
            return {
                "status": result.state,
                "error": str(result.info),
                "traceback": result.traceback,
                "task_id": task_id,
            }
        elif result.state == TaskStatus.PROGRESS:
            return {
                "status": result.state,
                "current": result.info.get("current", 0),
                "total": result.info.get("total", 100),
                "message": result.info.get("message", ""),
                "task_id": task_id,
            }
        else:
            return {
                "status": result.state,
                "task_id": task_id,
            }
    except Exception as e:
        logger.error(f"Error retrieving task result for {task_id}: {e}")
        return None


def revoke_task(task_id: str, terminate: bool = False) -> bool:
    """Revoke a task by its ID.

    Args:
        task_id: The task ID to revoke
        terminate: Whether to terminate the task if it's currently running

    Returns:
        True if successfully revoked, False otherwise
    """
    try:
        app = get_celery_app()
        app.control.revoke(task_id, terminate=terminate)
        logger.info(f"Task {task_id} revoked (terminate={terminate})")
        return True
    except Exception as e:
        logger.error(f"Error revoking task {task_id}: {e}")
        return False