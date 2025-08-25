# hlpr

Minimal scaffolding for the hlpr Project Management Assistant (FastAPI + DSPy) with a src layout.

## Features (current)
- FastAPI app factory (`hlpr.create_app`)
- Example router at `/example/`
- Health endpoint at `/health`
- Typer + Rich CLI (`hlpr` command) with health, run-server, summarize
- Settings management via `pydantic-settings`
- Basic error handling + custom `AppError`
- Async test setup using httpx ASGITransport
- Ruff linting configured
- Async SQLAlchemy setup (SQLite dev default, Postgres + pgvector ready)
- DSPy summarization pipeline skeleton (repository + service orchestration)

## Development

### Install dependencies
Use uv (preferred):

```bash
uv sync
```

### Run the API (dev)
```bash
uv run uvicorn hlpr.main:app --reload
```

Or via CLI:
```bash
uv run hlpr run-server
```

### CLI examples
```bash
uv run hlpr health
uv run hlpr demo-process --text "Sample meeting notes"
uv run hlpr summarize --document-id 1
```

### Run tests
```bash
uv run pytest -q
```

### Lint
```bash
uvx ruff check .
```

### Format (when added)
```bash
uvx ruff format .
```

### Type checking
```bash
uv run mypy src
```

### Pre-commit hooks
Install and run automatically on commit:
```bash
uv run pre-commit install
```
Run against all files:
```bash
uv run pre-commit run --all-files
```

### Continuous Integration
GitHub Actions workflow `ci.yml` runs on pushes and pull requests to `main`:
- uv sync (deps)
- Ruff lint
- mypy type check
- pytest unit tests

Status badges can be added later once the repo is public.

## Configuration
Environment variables (prefixed with `HLPR_`) override defaults, e.g.:
```bash
export HLPR_ENVIRONMENT=prod
export HLPR_DEBUG=false
export HLPR_DATABASE_URL="postgres+asyncpg://user:pass@localhost:5432/hlpr"
export HLPR_SQL_ECHO=true
```

By default an on-disk SQLite database (`sqlite+aiosqlite:///./hlpr.db`) is used for local development.

### Enabling pgvector in Postgres
Run inside your database (once):
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```
Future migrations will add embedding vector columns.

## Project layout
```
pyproject.toml
src/
  hlpr/
    main.py
    cli.py
    core/
      settings.py
      logging.py
      errors.py
    routers/
      example.py
      health.py
```

## Next steps (suggested)
- Add embedding & vector index table (pgvector) + retrieval interface
- Migrations tooling (Alembic) & seed scripts
- Celery task queue wiring for async pipeline runs
- Authentication & RBAC
- Expand DSPy pipelines (action items, classification) with evaluation
- Observability (OpenTelemetry + structured logs)

---
Happy building!
