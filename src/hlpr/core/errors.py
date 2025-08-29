"""Error handling utilities and custom exceptions."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base application error."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "app_error",
        http_status: int = status.HTTP_400_BAD_REQUEST,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.http_status = http_status

    def to_dict(self) -> dict[str, str]:  # minimal for now
        return {"error": self.code, "message": self.message}


class ErrorResponse(BaseModel):
    error: str
    message: str


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.http_status, content=exc.to_dict())


async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "validation_error",
            "message": "Invalid request payload",
            "details": exc.errors(),
        },
    )


# Optimization-specific errors

class OptimizationError(Exception):
    """Enhanced optimization errors with suggestions and context.

    Provides actionable guidance when optimization operations fail.
    """

    def __init__(
        self,
        message: str,
        suggestions: list[str] | None = None,
        context: dict[str, Any] | None = None
    ) -> None:
        super().__init__(message)
        self.message = message
        self.suggestions = suggestions or []
        self.context = context or {}

    def display(self) -> str:
        """Format error message with suggestions and context for display."""
        lines = [f"❌ Optimization Error: {self.message}"]

        if self.context:
            lines.append("📋 Context:")
            for key, value in self.context.items():
                lines.append(f"   {key}: {value}")

        if self.suggestions:
            lines.append("💡 Suggestions:")
            for suggestion in self.suggestions:
                lines.append(f"   • {suggestion}")

        return "\n".join(lines)

    def __str__(self) -> str:
        return self.display()


class ModelConfigurationError(OptimizationError):
    """Error when DSPy model configuration fails."""

    def __init__(
        self,
        model: str,
        original_error: Exception | None = None,
        context: dict[str, Any] | None = None
    ) -> None:
        message = f"Failed to configure DSPy model: {model}"
        suggestions = [
            "Check if the model name is correct",
            "Verify API keys are set for cloud models (OpenAI, etc.)",
            "Ensure Ollama is running for local models",
            "Check network connectivity for API-based models"
        ]

        if context is None:
            context = {"model": model}
        else:
            context["model"] = model

        if original_error:
            context["original_error"] = str(original_error)

        super().__init__(message, suggestions, context)


class ArtifactLoadError(OptimizationError):
    """Error when loading optimization artifacts fails."""

    def __init__(
        self,
        artifact_path: str,
        original_error: Exception | None = None,
        context: dict[str, Any] | None = None
    ) -> None:
        message = f"Failed to load optimization artifact: {artifact_path}"
        suggestions = [
            "Verify the artifact file exists and is readable",
            "Check if the artifact was created successfully during optimization",
            "Ensure the artifact format hasn't been corrupted",
            "Try re-running optimization to regenerate artifacts"
        ]

        if context is None:
            context = {"artifact_path": artifact_path}
        else:
            context["artifact_path"] = artifact_path

        if original_error:
            context["original_error"] = str(original_error)

        super().__init__(message, suggestions, context)


class DatasetLoadError(OptimizationError):
    """Error when loading training dataset fails."""

    def __init__(
        self,
        data_path: str,
        original_error: Exception | None = None,
        context: dict[str, Any] | None = None
    ) -> None:
        message = f"Failed to load training dataset: {data_path}"
        suggestions = [
            "Verify the dataset file exists at the specified path",
            "Check if the file has the correct JSONL format",
            "Ensure the file contains valid meeting examples",
            "Try using --include-unverified to include more examples"
        ]

        if context is None:
            context = {"data_path": data_path}
        else:
            context["data_path"] = data_path

        if original_error:
            context["original_error"] = str(original_error)

        super().__init__(message, suggestions, context)


# Task-specific error handling

class TaskErrorCode(Enum):
    """Standardized error codes for task operations."""

    # Database errors
    DATABASE_CONNECTION_ERROR = "DATABASE_CONNECTION_ERROR"
    DATABASE_QUERY_ERROR = "DATABASE_QUERY_ERROR"
    DATABASE_TRANSACTION_ERROR = "DATABASE_TRANSACTION_ERROR"

    # Meeting processing errors
    MEETING_NOT_FOUND = "MEETING_NOT_FOUND"
    MEETING_PROCESSING_ERROR = "MEETING_PROCESSING_ERROR"
    MEETING_VALIDATION_ERROR = "MEETING_VALIDATION_ERROR"

    # Model/LLM errors
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
    MODEL_TIMEOUT = "MODEL_TIMEOUT"
    MODEL_RATE_LIMITED = "MODEL_RATE_LIMITED"
    MODEL_INVALID_RESPONSE = "MODEL_INVALID_RESPONSE"

    # Configuration errors
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    CONFIGURATION_MISSING = "CONFIGURATION_MISSING"
    CONFIGURATION_INVALID = "CONFIGURATION_INVALID"

    # Resource errors
    RESOURCE_EXHAUSTED = "RESOURCE_EXHAUSTED"
    RESOURCE_TIMEOUT = "RESOURCE_TIMEOUT"
    RESOURCE_UNAVAILABLE = "RESOURCE_UNAVAILABLE"

    # Task system errors
    TASK_QUEUE_FULL = "TASK_QUEUE_FULL"
    TASK_TIMEOUT = "TASK_TIMEOUT"
    TASK_CANCELLED = "TASK_CANCELLED"

    # Generic errors
    UNKNOWN_ERROR = "UNKNOWN_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    PERMISSION_DENIED = "PERMISSION_DENIED"


@dataclass
class TaskError:
    """Structured error information for tasks."""

    code: TaskErrorCode
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 3
    retryable: bool = True
    context: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Set retryable flag based on error code."""
        # Define which errors are retryable
        non_retryable_codes = {
            TaskErrorCode.MEETING_NOT_FOUND,
            TaskErrorCode.CONFIGURATION_INVALID,
            TaskErrorCode.PERMISSION_DENIED,
            TaskErrorCode.VALIDATION_ERROR,
        }

        if self.code in non_retryable_codes:
            self.retryable = False

    def to_dict(self) -> dict[str, Any]:
        """Convert error to dictionary for serialization."""
        return {
            "code": self.code.value,
            "message": self.message,
            "details": self.details,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "retryable": self.retryable,
            "context": self.context,
        }

    def should_retry(self) -> bool:
        """Check if this error should be retried."""
        return self.retryable and self.retry_count < self.max_retries

    def increment_retry(self) -> None:
        """Increment retry count."""
        self.retry_count += 1

    def log_error(self, logger_instance: logging.Logger | None = None) -> None:
        """Log the error with appropriate level."""
        log = logger_instance or logger

        if self.code in {TaskErrorCode.MEETING_NOT_FOUND, TaskErrorCode.CONFIGURATION_INVALID}:
            log.warning(f"Task error: {self.code.value} - {self.message}", extra=self.context)
        else:
            log.error(f"Task error: {self.code.value} - {self.message}", extra=self.context)


class TaskErrorHandler:
    """Centralized error handling for tasks."""

    @staticmethod
    def handle_database_error(error: Exception, context: dict[str, Any]) -> TaskError:
        """Handle database-related errors."""
        if "not found" in str(error).lower():
            return TaskError(
                code=TaskErrorCode.MEETING_NOT_FOUND,
                message=f"Database entity not found: {error}",
                details={"original_error": str(error)},
                context=context,
            )
        elif "connection" in str(error).lower():
            return TaskError(
                code=TaskErrorCode.DATABASE_CONNECTION_ERROR,
                message=f"Database connection error: {error}",
                details={"original_error": str(error)},
                context=context,
            )
        else:
            return TaskError(
                code=TaskErrorCode.DATABASE_QUERY_ERROR,
                message=f"Database query error: {error}",
                details={"original_error": str(error)},
                context=context,
            )

    @staticmethod
    def handle_model_error(error: Exception, context: dict[str, Any]) -> TaskError:
        """Handle model/LLM-related errors."""
        error_str = str(error).lower()

        if "timeout" in error_str:
            return TaskError(
                code=TaskErrorCode.MODEL_TIMEOUT,
                message=f"Model timeout: {error}",
                details={"original_error": str(error)},
                context=context,
            )
        elif "rate limit" in error_str or "429" in error_str:
            return TaskError(
                code=TaskErrorCode.MODEL_RATE_LIMITED,
                message=f"Model rate limited: {error}",
                details={"original_error": str(error)},
                context=context,
            )
        elif "unavailable" in error_str or "503" in error_str:
            return TaskError(
                code=TaskErrorCode.MODEL_UNAVAILABLE,
                message=f"Model unavailable: {error}",
                details={"original_error": str(error)},
                context=context,
            )
        else:
            return TaskError(
                code=TaskErrorCode.MODEL_INVALID_RESPONSE,
                message=f"Model error: {error}",
                details={"original_error": str(error)},
                context=context,
            )

    @staticmethod
    def handle_resource_error(error: Exception, context: dict[str, Any]) -> TaskError:
        """Handle resource-related errors."""
        error_str = str(error).lower()

        if "timeout" in error_str:
            return TaskError(
                code=TaskErrorCode.RESOURCE_TIMEOUT,
                message=f"Resource timeout: {error}",
                details={"original_error": str(error)},
                context=context,
            )
        elif "exhausted" in error_str or "out of memory" in error_str:
            return TaskError(
                code=TaskErrorCode.RESOURCE_EXHAUSTED,
                message=f"Resource exhausted: {error}",
                details={"original_error": str(error)},
                context=context,
            )
        else:
            return TaskError(
                code=TaskErrorCode.RESOURCE_UNAVAILABLE,
                message=f"Resource unavailable: {error}",
                details={"original_error": str(error)},
                context=context,
            )

    @staticmethod
    def handle_generic_error(error: Exception, context: dict[str, Any]) -> TaskError:
        """Handle generic/unexpected errors."""
        return TaskError(
            code=TaskErrorCode.UNKNOWN_ERROR,
            message=f"Unexpected error: {error}",
            details={"original_error": str(error), "error_type": type(error).__name__},
            context=context,
        )

    @classmethod
    def create_error_from_exception(
        cls,
        error: Exception,
        context: dict[str, Any],
        retry_count: int = 0
    ) -> TaskError:
        """Create a TaskError from an exception with automatic classification."""
        error_str = str(error).lower()

        # Classify error based on content
        if any(keyword in error_str for keyword in ["database", "sql", "sqlite", "postgres"]):
            task_error = cls.handle_database_error(error, context)
        elif any(keyword in error_str for keyword in ["model", "llm", "dspy", "ollama"]):
            task_error = cls.handle_model_error(error, context)
        elif any(keyword in error_str for keyword in ["timeout", "resource", "memory", "connection"]):
            task_error = cls.handle_resource_error(error, context)
        else:
            task_error = cls.handle_generic_error(error, context)

        # Set retry count
        task_error.retry_count = retry_count

        return task_error


def with_error_handling(max_retries: int = 3) -> Any:
    """Decorator for functions that need structured error handling."""
    def decorator(func: Any) -> Any:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            retry_count = 0
            context = {
                "function": func.__name__,
                "args": str(args) if args else None,
                "kwargs": str(kwargs) if kwargs else None,
            }

            while retry_count <= max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    task_error = TaskErrorHandler.create_error_from_exception(
                        e, context, retry_count
                    )

                    if not task_error.should_retry():
                        task_error.log_error()
                        raise e

                    task_error.log_error()
                    retry_count += 1
                    task_error.increment_retry()

                    # Exponential backoff
                    import time
                    delay = min(2 ** retry_count, 30)  # Max 30 seconds
                    time.sleep(delay)

            # If we get here, all retries failed
            raise Exception(f"Function {func.__name__} failed after {max_retries} retries")

        return wrapper
    return decorator
