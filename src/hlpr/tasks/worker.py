"""Background worker tasks for hlpr.

This module defines Celery tasks for background processing, including
batch meeting processing and pipeline optimization.
"""
from __future__ import annotations

import asyncio
from typing import Any

from celery.exceptions import SoftTimeLimitExceeded
from celery.utils.log import get_task_logger

from hlpr.tasks import TaskPriority, create_celery_app_for_worker

logger = get_task_logger(__name__)

# Create Celery app for worker
app = create_celery_app_for_worker()


@app.task(  # type: ignore[misc]
    bind=True,
    name="hlpr.tasks.worker.batch_process_meetings",
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 60},
    retry_backoff=True,
    retry_backoff_max=600,
)
def batch_process_meetings(
    self: Any,
    meeting_ids: list[int],
    pipeline_config: dict[str, Any] | None = None,
    priority: int = TaskPriority.NORMAL,
) -> dict[str, Any]:
    """Process multiple meetings in batch.

    Args:
        meeting_ids: List of meeting IDs to process
        pipeline_config: Optional pipeline configuration
        priority: Task priority level

    Returns:
        Dictionary with processing results
    """
    try:
        # Update task state to progress
        total_meetings = len(meeting_ids)
        self.update_state(
            state="PROGRESS",
            meta={"current": 0, "total": total_meetings, "message": "Starting batch processing"}
        )

        results = []
        successful = 0
        failed = 0

        for i, meeting_id in enumerate(meeting_ids):
            try:
                # Update progress
                self.update_state(
                    state="PROGRESS",
                    meta={
                        "current": i + 1,
                        "total": total_meetings,
                        "message": f"Processing meeting {meeting_id}"
                    }
                )

                # Process individual meeting with retry logic
                result = _process_single_meeting_with_retry(meeting_id, pipeline_config)
                results.append({
                    "meeting_id": meeting_id,
                    "status": "success",
                    "result": result
                })
                successful += 1

            except Exception as e:
                logger.error(f"Failed to process meeting {meeting_id}: {e}")
                results.append({
                    "meeting_id": meeting_id,
                    "status": "failed",
                    "error": str(e)
                })
                failed += 1

        return {
            "status": "completed",
            "total_processed": total_meetings,
            "successful": successful,
            "failed": failed,
            "results": results,
        }

    except SoftTimeLimitExceeded:
        logger.error("Batch processing timed out")
        return {
            "status": "timeout",
            "error": "Processing timed out",
            "total_processed": len(meeting_ids),
            "successful": successful,
            "failed": len(meeting_ids) - successful,
        }
    except Exception as e:
        logger.error(f"Batch processing failed: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "total_processed": 0,
            "successful": 0,
            "failed": len(meeting_ids),
        }


@app.task(  # type: ignore[misc]
    bind=True,
    name="hlpr.tasks.worker.optimize_meeting_pipeline",
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 2, "countdown": 300},
    retry_backoff=True,
    retry_backoff_max=1800,
)
def optimize_meeting_pipeline(
    self: Any,
    config: dict[str, Any],
    priority: int = TaskPriority.HIGH,
) -> dict[str, Any]:
    """Optimize meeting summarization pipeline using DSPy.

    Args:
        config: Optimization configuration
        priority: Task priority level

    Returns:
        Dictionary with optimization results
    """
    try:
        # Update task state
        self.update_state(
            state="PROGRESS",
            meta={"current": 0, "total": 100, "message": "Starting optimization"}
        )

        # Extract configuration
        iterations = config.get("iterations", 1)
        model = config.get("model", "ollama/gemma3")
        dataset_path = config.get("dataset_path", "documents/training-data/meetings.txt")

        # Run optimization
        result = _run_pipeline_optimization(
            iterations=iterations,
            model=model,
            dataset_path=dataset_path,
            task=self
        )

        return {
            "status": "completed",
            "result": result,
        }

    except SoftTimeLimitExceeded:
        logger.error("Pipeline optimization timed out")
        return {
            "status": "timeout",
            "error": "Optimization timed out",
        }
    except Exception as e:
        logger.error(f"Pipeline optimization failed: {e}")
        return {
            "status": "failed",
            "error": str(e),
        }


def _process_single_meeting(
    meeting_id: int,
    pipeline_config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Process a single meeting.

    Args:
        meeting_id: The meeting ID to process
        pipeline_config: Optional pipeline configuration

    Returns:
        Processing result
    """
    # Use asyncio.run for proper event loop management
    return asyncio.run(_process_single_meeting_async(meeting_id, pipeline_config))


async def _process_single_meeting_async(
    meeting_id: int,
    pipeline_config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Async implementation of single meeting processing.

    Args:
        meeting_id: The meeting ID to process
        pipeline_config: Optional pipeline configuration

    Returns:
        Processing result
    """
    # Import here to avoid circular imports
    from hlpr.db.base import get_session_factory, init_models
    from hlpr.db.repositories import MeetingRepository
    from hlpr.services.pipelines import PipelineService

    # Initialize database
    await init_models(drop=False)
    session_factory = get_session_factory()

    async with session_factory() as session:
        # Create repositories
        from hlpr.db.repositories import DocumentRepository, PipelineRunRepository
        docs_repo = DocumentRepository(session)
        runs_repo = PipelineRunRepository(session)
        meeting_repo = MeetingRepository(session)

        # Create pipeline service
        pipeline_service = PipelineService(docs_repo, runs_repo)

        # Get meeting
        meeting = await meeting_repo.get(meeting_id)
        if not meeting:
            raise ValueError(f"Meeting {meeting_id} not found")

        # Run summarization pipeline
        result = await pipeline_service._run_meeting_summarization(meeting_repo, meeting_id)

        # Add processing metadata
        result.update({
            "processed_at": "2025-08-28T00:00:00Z",  # Would be datetime.now()
            "pipeline_config": pipeline_config or {},
            "processing_method": "batch",
        })

        return result  # type: ignore[no-any-return]


def _process_single_meeting_with_retry(
    meeting_id: int,
    pipeline_config: dict[str, Any] | None = None,
    max_retries: int = 3,
    retry_delay: float = 1.0,
) -> dict[str, Any]:
    """Process a single meeting with retry logic.

    Args:
        meeting_id: The meeting ID to process
        pipeline_config: Optional pipeline configuration
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds

    Returns:
        Processing result

    Raises:
        Exception: If all retry attempts fail
    """
    import time

    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return _process_single_meeting(meeting_id, pipeline_config)
        except Exception as e:
            last_exception = e
            logger.warning(f"Attempt {attempt + 1}/{max_retries + 1} failed for meeting {meeting_id}: {e}")

            if attempt < max_retries:
                # Exponential backoff
                delay = retry_delay * (2 ** attempt)
                logger.info(f"Retrying meeting {meeting_id} in {delay} seconds...")
                time.sleep(delay)
            else:
                logger.error(f"All retry attempts failed for meeting {meeting_id}")
                raise last_exception from None

    # This should never be reached, but just in case
    raise last_exception or Exception(f"Failed to process meeting {meeting_id}") from None


def _run_pipeline_optimization(
    iterations: int,
    model: str,
    dataset_path: str,
    task: Any,
) -> dict[str, Any]:
    """Run DSPy pipeline optimization.

    Args:
        iterations: Number of optimization iterations
        model: Model identifier
        dataset_path: Path to training dataset
        task: Celery task instance for progress updates

    Returns:
        Optimization results
    """
    # Use asyncio.run for proper event loop management
    return asyncio.run(_run_pipeline_optimization_async(iterations, model, dataset_path, task))


async def _run_pipeline_optimization_async(
    iterations: int,
    model: str,
    dataset_path: str,
    task: Any,
) -> dict[str, Any]:
    """Async implementation of pipeline optimization.

    Args:
        iterations: Number of optimization iterations
        model: Model identifier
        dataset_path: Path to training dataset
        task: Celery task instance for progress updates

    Returns:
        Optimization results
    """
    try:
        # Update progress
        task.update_state(
            state="PROGRESS",
            meta={"current": 10, "total": 100, "message": "Loading dataset"}
        )

        # Import here to avoid circular imports and potential async issues
        import asyncio

        from hlpr.core.optimization import OptimizationConfig
        from hlpr.dspy.optimizer import optimize

        # Create optimization config
        opt_config = OptimizationConfig(
            data_path=dataset_path,
            model=model,
            optimizer="mipro",  # Default to MIPRO
            iters=iterations,
            artifact_dir="artifacts/meeting/optimized_program_dspy"
        )

        # Run optimization in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        optimization_result = await loop.run_in_executor(
            None,  # Use default thread pool
            optimize,
            opt_config
        )

        return {
            "iterations_completed": iterations,
            "model_used": model,
            "dataset_used": dataset_path,
            "artifact_saved": optimization_result.get("artifact_path", "artifacts/meeting/optimized_program_dspy/metadata.json"),
            "optimization_score": float(optimization_result.get("composite_score", 0.0)),
            "completed_at": "2025-08-28T00:00:00Z",
        }

    except Exception as e:
        logger.error(f"Error in pipeline optimization: {e}")
        raise


@app.task(name="hlpr.tasks.worker.health_check")  # type: ignore[misc]
def health_check() -> dict[str, Any]:
    """Simple health check task.

    Returns:
        Health check result
    """
    return {
        "status": "healthy",
        "timestamp": "2025-08-28T00:00:00Z",
        "worker": "active",
    }


@app.task(name="hlpr.tasks.worker.cleanup_expired_tasks")  # type: ignore[misc]
def cleanup_expired_tasks() -> dict[str, Any]:
    """Clean up expired task results from Redis.

    Returns:
        Cleanup result
    """
    try:
        # This would implement cleanup logic for expired task results
        # For now, return a simple success
        return {
            "status": "completed",
            "cleaned_count": 0,
            "timestamp": "2025-08-28T00:00:00Z",
        }
    except Exception as e:
        logger.error(f"Error in cleanup task: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "timestamp": "2025-08-28T00:00:00Z",
        }