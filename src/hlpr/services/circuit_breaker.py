"""Circuit breaker service for protecting LLM calls.

This module provides circuit breaker protection for external LLM services
to prevent cascade failures and improve system resilience.
"""
from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from circuitbreaker import CircuitBreaker

from hlpr.core.errors import TaskError, TaskErrorCode

logger = logging.getLogger(__name__)


class CircuitBreakerState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, requests rejected
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""

    failure_threshold: int = 5  # Number of failures before opening
    recovery_timeout: float = 60.0  # Seconds to wait before trying half-open
    expected_exception: tuple[type[Exception], ...] = (Exception,)  # Exceptions that count as failures
    success_threshold: int = 3  # Successes needed to close from half-open
    timeout: float = 30.0  # Request timeout in seconds
    name: str = "llm_circuit_breaker"


@dataclass
class CircuitBreakerStats:
    """Statistics for circuit breaker monitoring."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_failure_time: float | None = None
    last_success_time: float | None = None
    state_changes: list[dict[str, Any]] = field(default_factory=list)

    def record_success(self) -> None:
        """Record a successful request."""
        self.total_requests += 1
        self.successful_requests += 1
        self.consecutive_successes += 1
        self.consecutive_failures = 0
        self.last_success_time = time.time()

    def record_failure(self) -> None:
        """Record a failed request."""
        self.total_requests += 1
        self.failed_requests += 1
        self.consecutive_failures += 1
        self.consecutive_successes = 0
        self.last_failure_time = time.time()

    def get_success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests

    def to_dict(self) -> dict[str, Any]:
        """Convert stats to dictionary."""
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": self.get_success_rate(),
            "consecutive_failures": self.consecutive_failures,
            "consecutive_successes": self.consecutive_successes,
            "last_failure_time": self.last_failure_time,
            "last_success_time": self.last_success_time,
            "state_changes": self.state_changes[-10:],  # Last 10 state changes
        }


class LLMServiceCircuitBreaker:
    """Circuit breaker for LLM service calls."""

    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.stats = CircuitBreakerStats()
        self._state = CircuitBreakerState.CLOSED
        self._last_state_change = time.time()
        self._circuit_breaker = self._create_circuit_breaker()

    def _create_circuit_breaker(self) -> CircuitBreaker:
        """Create the underlying circuit breaker."""
        return CircuitBreaker(
            failure_threshold=self.config.failure_threshold,
            recovery_timeout=self.config.recovery_timeout,
            expected_exception=self.config.expected_exception,
            success_threshold=self.config.success_threshold,
            name=self.config.name,
        )

    @property
    def state(self) -> CircuitBreakerState:
        """Get current circuit breaker state."""
        return self._state

    def _update_state(self, new_state: CircuitBreakerState) -> None:
        """Update circuit breaker state and record change."""
        if self._state != new_state:
            old_state = self._state
            self._state = new_state
            self._last_state_change = time.time()

            state_change = {
                "timestamp": self._last_state_change,
                "from_state": old_state.value,
                "to_state": new_state.value,
                "consecutive_failures": self.stats.consecutive_failures,
                "consecutive_successes": self.stats.consecutive_successes,
            }
            self.stats.state_changes.append(state_change)

            logger.info(
                f"Circuit breaker state changed: {old_state.value} -> {new_state.value} "
                f"(failures: {self.stats.consecutive_failures}, successes: {self.stats.consecutive_successes})"
            )

    def should_attempt_request(self) -> bool:
        """Check if a request should be attempted based on circuit breaker state."""
        current_time = time.time()

        if self._state == CircuitBreakerState.CLOSED:
            return True
        elif self._state == CircuitBreakerState.OPEN:
            # Check if recovery timeout has passed
            if current_time - self._last_state_change >= self.config.recovery_timeout:
                self._update_state(CircuitBreakerState.HALF_OPEN)
                logger.info("Circuit breaker entering half-open state for recovery test")
                return True
            return False
        elif self._state == CircuitBreakerState.HALF_OPEN:
            return True

        return False

    def record_success(self) -> None:
        """Record a successful request."""
        self.stats.record_success()

        if self._state == CircuitBreakerState.HALF_OPEN:
            if self.stats.consecutive_successes >= self.config.success_threshold:
                self._update_state(CircuitBreakerState.CLOSED)
                logger.info("Circuit breaker closed after successful recovery")

    def record_failure(self) -> None:
        """Record a failed request."""
        self.stats.record_failure()

        if self._state == CircuitBreakerState.HALF_OPEN:
            self._update_state(CircuitBreakerState.OPEN)
            logger.warning("Circuit breaker opened due to failure during recovery")
        elif self._state == CircuitBreakerState.CLOSED:
            if self.stats.consecutive_failures >= self.config.failure_threshold:
                self._update_state(CircuitBreakerState.OPEN)
                logger.warning("Circuit breaker opened due to consecutive failures")

    async def call_with_circuit_breaker(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any
    ) -> Any:
        """Execute a function with circuit breaker protection."""
        if not self.should_attempt_request():
            raise TaskError(
                code=TaskErrorCode.MODEL_UNAVAILABLE,
                message="Circuit breaker is open - LLM service temporarily unavailable",
                context={
                    "circuit_breaker_state": self._state.value,
                    "consecutive_failures": self.stats.consecutive_failures,
                    "last_failure_time": self.stats.last_failure_time,
                }
            )

        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.config.timeout
            )
            self.record_success()
            return result

        except self.config.expected_exception as e:
            self.record_failure()
            raise TaskError(
                code=TaskErrorCode.MODEL_UNAVAILABLE,
                message=f"LLM service error: {e}",
                details={"original_error": str(e), "error_type": type(e).__name__},
                context={
                    "circuit_breaker_state": self._state.value,
                    "consecutive_failures": self.stats.consecutive_failures,
                }
            ) from e
        except TimeoutError as e:
            self.record_failure()
            raise TaskError(
                code=TaskErrorCode.MODEL_TIMEOUT,
                message=f"LLM service timeout after {self.config.timeout}s",
                details={"timeout_seconds": self.config.timeout},
                context={
                    "circuit_breaker_state": self._state.value,
                    "consecutive_failures": self.stats.consecutive_failures,
                }
            ) from e

    def get_stats(self) -> dict[str, Any]:
        """Get circuit breaker statistics."""
        return {
            "state": self._state.value,
            "last_state_change": self._last_state_change,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "recovery_timeout": self.config.recovery_timeout,
                "success_threshold": self.config.success_threshold,
                "timeout": self.config.timeout,
            },
            "stats": self.stats.to_dict(),
        }


# Global circuit breaker instances
_ollama_circuit_breaker: LLMServiceCircuitBreaker | None = None
_openai_circuit_breaker: LLMServiceCircuitBreaker | None = None


def get_ollama_circuit_breaker() -> LLMServiceCircuitBreaker:
    """Get or create Ollama circuit breaker."""
    global _ollama_circuit_breaker
    if _ollama_circuit_breaker is None:
        config = CircuitBreakerConfig(
            name="ollama_circuit_breaker",
            failure_threshold=3,  # Ollama is local, so lower threshold
            recovery_timeout=30.0,  # Faster recovery for local service
            timeout=60.0,  # Longer timeout for local model inference
        )
        _ollama_circuit_breaker = LLMServiceCircuitBreaker(config)
    return _ollama_circuit_breaker


def get_openai_circuit_breaker() -> LLMServiceCircuitBreaker:
    """Get or create OpenAI circuit breaker."""
    global _openai_circuit_breaker
    if _openai_circuit_breaker is None:
        config = CircuitBreakerConfig(
            name="openai_circuit_breaker",
            failure_threshold=5,  # Higher threshold for cloud service
            recovery_timeout=60.0,  # Longer recovery time for cloud service
            timeout=30.0,  # Standard timeout for API calls
        )
        _openai_circuit_breaker = LLMServiceCircuitBreaker(config)
    return _openai_circuit_breaker


def get_circuit_breaker_for_model(model: str) -> LLMServiceCircuitBreaker:
    """Get appropriate circuit breaker for a model."""
    if model.startswith("ollama/"):
        return get_ollama_circuit_breaker()
    else:
        return get_openai_circuit_breaker()


@asynccontextmanager
async def circuit_breaker_context(model: str) -> AsyncGenerator[LLMServiceCircuitBreaker]:
    """Context manager for circuit breaker protection."""
    circuit_breaker = get_circuit_breaker_for_model(model)

    # Check if we should attempt the request
    if not circuit_breaker.should_attempt_request():
        raise TaskError(
            code=TaskErrorCode.MODEL_UNAVAILABLE,
            message=f"Circuit breaker is open for {model}",
            context={"model": model, "state": circuit_breaker.state.value}
        )

    try:
        yield circuit_breaker
    except Exception:
        circuit_breaker.record_failure()
        raise
    else:
        circuit_breaker.record_success()


class CircuitBreakerProtectedLM:
    """DSPy LM wrapper with circuit breaker protection."""

    def __init__(
        self,
        model: str,
        api_base: str | None = None,
        circuit_breaker: LLMServiceCircuitBreaker | None = None,
        **kwargs: Any
    ):
        """Initialize circuit breaker-protected language model."""
        self.model = model
        self.api_base = api_base
        self.circuit_breaker = circuit_breaker or get_circuit_breaker_for_model(model)
        self.kwargs = kwargs

        # Create the underlying DSPy LM
        try:
            import dspy
            if api_base:
                self._lm = dspy.LM(model=model, api_base=api_base, **kwargs)
            else:
                self._lm = dspy.LM(model=model, **kwargs)
        except Exception as e:
            logger.error(f"Failed to create DSPy LM: {e}")
            raise

    async def __call__(
        self,
        prompt: str,
        **kwargs: Any
    ) -> Any:
        """Execute LLM call with circuit breaker protection."""
        async def _call_lm() -> Any:
            # Use asyncio.to_thread for synchronous DSPy calls
            import asyncio
            return await asyncio.to_thread(self._lm, prompt, **kwargs)

        return await self.circuit_breaker.call_with_circuit_breaker(_call_lm)

    def __getattr__(self, name: str) -> Any:
        """Delegate other attributes to the underlying LM."""
        return getattr(self._lm, name)