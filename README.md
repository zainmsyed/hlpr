# hlpr

Minimal scaffolding for the hlpr Project Management Assistant (FastAPI + DSPy) with a src layout.

## Features (current)

### Phase 1: Meeting Summarization Pipeline
- **Meeting Management**: Create, retrieve, and summarize meetings via REST API
  - `POST /meetings` - Create meeting with transcript and participants
  - `GET /meetings/{id}` - Retrieve meeting details
  - `POST /meetings/{id}/summarize` - Extract summary, action items, decisions
- **Dual Processing Modes**:
  - Heuristic extraction (regex-based patterns for action items/decisions)
  - Optional DSPy optimization with artifact fallback
- **DSPy Integration**: 
  - Signatures for meeting summary and action item extraction
  - Dataset loader for JSONL training data with verified/unverified filtering
  - Simple evaluation metrics (token overlap, exact match precision/recall)
  - CLI optimization command: `hlpr optimize-meeting`
- **Artifact Storage**: Optimized DSPy programs stored in `artifacts/meeting/`

### Core Infrastructure
- FastAPI app factory (`hlpr.create_app`)
- Example router at `/example/`
- Health endpoint at `/health`
- Typer + Rich CLI (`hlpr` command) with health, run-server, summarize, optimize-meeting
- Settings management via `pydantic-settings`
- Basic error handling + custom `AppError`
- Async test setup using httpx ASGITransport
- Ruff linting configured
- Async SQLAlchemy setup (SQLite dev default, Postgres + pgvector ready)
- Document summarization pipeline (legacy, pre-DSPy)

## Development

### Install dependencies
Use uv (preferred):

```bash
uv sync
```

### Docker
Build and start the application with Docker Compose:

```bash
docker compose build
docker compose up -d
```

Then open http://localhost:8000 or http://localhost:8000/docs in your browser.

### Development Scripts
The project includes several helper scripts to simplify development:

#### Initial Setup
```bash
# Run the initial setup (installs dependencies, starts Docker, initializes DB)
./scripts/setup.sh
```

#### Development Workflow
```bash
# Start development environment
./scripts/dev.sh start

# View logs
./scripts/dev.sh logs

# Access container shell
./scripts/dev.sh shell

# Stop development environment
./scripts/dev.sh stop

# Clean up everything (containers, volumes, images)
./scripts/dev.sh clean

# Get help on all available commands
./scripts/dev.sh help
```

#### Smart Command Execution
The `docker-exec.sh` script automatically detects whether you're running inside Docker or locally and routes commands appropriately:

```bash
# These commands work the same whether in Docker or local
./scripts/docker-exec.sh uv run hlpr health
./scripts/docker-exec.sh uv run hlpr optimize-meeting --iters 1
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

# DSPy optimization for meetings
uv run hlpr optimize-meeting --iters 5 --model ollama/llama3
uv run hlpr optimize-meeting --include-unverified --data-path path/to/custom.jsonl
```

### API examples
```bash
# Create a meeting
curl -X POST http://localhost:8000/meetings \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": 1,
    "title": "Sprint Planning",
    "transcript": "Alice will finalize the API spec by Friday. We decided to postpone the refactor. ACTION: Update the roadmap.",
    "participants": ["alice", "bob"]
  }'

# Summarize meeting (returns structured output with action items)
curl -X POST http://localhost:8000/meetings/1/summarize
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
export HLPR_MODEL="ollama/llama3"  # For DSPy optimization
```

By default an on-disk SQLite database (`sqlite+aiosqlite:///./hlpr.db`) is used for local development.

### DSPy Model Configuration
The system supports multiple LLM providers for optimization:
- **Ollama** (recommended for local development): `HLPR_MODEL=ollama/llama3`
- **OpenAI**: `HLPR_MODEL=gpt-4` (requires `OPENAI_API_KEY`)
- **Anthropic**: Configure via DSPy settings (requires `ANTHROPIC_API_KEY`)

For Ollama setup:
```bash
# Install and start Ollama
ollama pull llama3
ollama serve

# Verify model works
uv run hlpr optimize-meeting --iters 1 --model ollama/llama3
```

### Enabling pgvector in Postgres
Run inside your database (once):
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```
Future migrations will add embedding vector columns.

## Project layout
```
pyproject.toml
documents/training-data/meetings.txt    # JSONL training examples
artifacts/meeting/                      # DSPy optimization artifacts
src/
  hlpr/
    main.py
    cli.py
    dspy/                              # DSPy optimization modules
      signatures.py                    # Meeting summary & extraction signatures
      dataset.py                       # Training data loader
      metrics.py                       # Evaluation metrics
      optimizer.py                     # MIPRO-like optimization loop
    core/
      settings.py
      logging.py
      errors.py
    db/
      models.py                        # Meeting, Document, PipelineRun
      repositories.py                  # Data access layer
      base.py
    pipelines/
      meeting_summarization.py         # Heuristic + DSPy integration
      summarization.py                 # Legacy document summarizer
    routers/
      meetings.py                      # Meeting REST endpoints
      example.py
      health.py
    services/
      pipelines.py                     # Service orchestration
tests/
  routers/
  services/
  dspy/                               # DSPy component tests
```

## Next steps (suggested)

### Phase 2: Enhanced Processing
- Email/communication processing pipeline
- Document batch processing with RAG integration
- Real-time notifications and WebSocket support

### Phase 3: Advanced Features
- MIPRO optimization with full parameter tuning
- Multi-modal input support (audio transcription)
- Advanced evaluation metrics (ROUGE, semantic similarity)
- Cross-project knowledge transfer

### Infrastructure Improvements
- Add embedding & vector index table (pgvector) + retrieval interface
- Migrations tooling (Alembic) & seed scripts
- Celery task queue wiring for async pipeline runs
- Authentication & RBAC
- Observability (OpenTelemetry + structured logs)
- Production deployment (Docker, K8s)

---
Happy building!
