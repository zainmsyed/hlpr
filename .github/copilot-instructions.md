# Copilot instructions for dspy project with FastAPI integration

- Goal: Keep code small, focused, and modular for maintainability and testability.

- Recommended project structure:
  - `app/main.py`: Initialize FastAPI instance and include routers.
  - `app/routers/`: One router per resource or feature (e.g., `users.py`, `items.py`).
  - `app/schemas/`: Pydantic models for requests and responses.
  - `app/services/`: Business logic and data processing using dspy modules.
  - `app/core/`: Shared configuration, dependencies, and utilities.
  - `dspy/`: Encapsulate data pipelines, transformations, and processing logic independent of API.
  - `app/tasks/`: Celery task definitions for background processing (batch jobs, heavy pipelines).
  - `app/ws/`: WebSocket endpoints for live updates and real-time features.
  - `app/db/`: Database session management, repository patterns, and vector DB integration.
  - `app/cli/` or `app/cli.py`: Typer-based CLI entrypoint(s) using Rich for styled output.

- Best practices:
  - Single Responsibility: each file holds one concern (router, schema, service, or pipeline).
  - Dependency Injection: use FastAPI's `Depends` for database sessions, settings, and other dependencies.
  - Thin routers: delegate processing and validation to `services` and `schemas` layers.
  - Pydantic models: use for request validation and response serialization to ensure type safety.
  - Isolate heavy data processing in `dspy` modules; the API layer should only orchestrate calls.
  - Async tasks: offload heavy workloads to Celery tasks in `app/tasks`, keeping the API layer thin.
  - Realtime: define WebSocket handlers separately in `app/ws` to manage live updates.
  - File size: aim for under ~200 lines per file; split larger modules by functionality.
  - Environment management: use `uv` to manage dependencies and virtual environments.
  - Minimal dependencies: keep external packages to the bare minimum needed to reduce complexity and potential vulnerabilities.
  - Linting: enforce code style and quality using `ruff`; run `uvx ruff check` as the primary linter command.
  - Command execution: use `uv run <command>` to execute scripts and services within the `uv` environment.
  - CLI design: keep Typer command functions thin—delegate to services; use Rich for progress bars, tables, and status; prefer subcommands grouped by domain (e.g., `hlpr embeddings build`).
  - CLI extensibility: new feature modules expose a `register_cli(app)` hook to append commands.
  - Avoid business logic in CLI layer—put logic in services or pipelines for reuse in API & tasks.

- Testing:
  - Place tests in `tests/` mirroring application structure (e.g., `tests/routers`, `tests/services`, `tests/tasks`).
  - Unit test `services`, `dspy`, and Celery logic separately from integration tests on API endpoints.
  - Integration test WebSocket endpoints (e.g., with `pytest-asyncio`).
