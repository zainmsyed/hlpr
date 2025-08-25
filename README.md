# hlpr

Minimal scaffolding for the hlpr Project Management Assistant (FastAPI + DSPy) with a src layout.

## Features (current)
- FastAPI app factory (`hlpr.create_app`)
- Example router at `/example/`
- Health endpoint at `/health`
- Typer + Rich CLI (`hlpr` command) with health info and run-server
- Settings management via `pydantic-settings`
- Basic error handling + custom `AppError`
- Async test setup using httpx ASGITransport
- Ruff linting configured

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
```

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
- Database integration (SQLAlchemy + async engine)
- Vector store for RAG
- Celery task queue wiring
- Authentication & RBAC
- Extended DSPy pipelines
- Observability (OpenTelemetry)

---
Happy building!
