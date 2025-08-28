"""Error handling utilities and custom exceptions."""
from __future__ import annotations

from typing import Any

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel


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
