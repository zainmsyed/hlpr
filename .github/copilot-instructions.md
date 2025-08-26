<!--
  Copilot / Coding Agent Onboarding Guide
  Scope: High-level architecture, build & validation workflow, file map, and operational rules.
  Keep this doc < ~2 pages; update when build/test procedure changes.
-->

# hlpr Repository – Agent Onboarding Instructions

## 1. What This Project Is
`hlpr` is a Python 3.13 FastAPI + Typer + SQLAlchemy + DSPy application that:
* Provides REST + CLI for meeting ingestion & summarization
* Runs a heuristic + DSPy (LLM) hybrid pipeline (with optional optimization loop)
* Persists optimized DSPy program artifacts to `artifacts/` for reproducible inference

Primary tech: FastAPI, Typer (CLI), SQLAlchemy (async), DSPy (LLM orchestration), uv (dependency/runtime), Ruff (lint), pytest (tests), mypy (type checking).

CI (GitHub Actions) runs: uv sync, Ruff lint, mypy, pytest (see `.github/workflows/ci.yml`). All PR changes must keep these green.

## 2. Core Build & Validation Commands (ALWAYS USE THESE)
Environment uses `uv`; do **not** invoke `pip install` directly. Order matters.

Bootstrap (creates virtual env & installs deps):
```bash
uv sync
```
Run API (dev, hot reload):
```bash
uv run hlpr run-server
```
Alternate direct Uvicorn (avoid unless debugging path issues):
```bash
uv run uvicorn hlpr.main:app --reload
```
Run CLI health (quick sanity):
```bash
uv run hlpr health
```
Run tests (fast, < ~2s):
```bash
uv run pytest -q
```
Run full verbose tests:
```bash
uv run pytest tests -v
```
Lint (non‑fix):
```bash
uvx ruff check .
```
Lint + auto-fix:
```bash
uvx ruff check --fix
```
Type check:
```bash
uv run mypy src
```
Optimization (DSPy) example:
```bash
uv run hlpr optimize-meeting --iters 1 --model ollama/gemma3
```

If adding a new dependency edit `pyproject.toml` then run `uv sync`.

## 3. Runtime/Data Assumptions
* Python 3.13 (CI enforces) – do not assume lower version features.
* Default DB: SQLite file `hlpr.db` in project root (async driver aiosqlite). No migrations yet.
* Meeting optimization uses dataset at `documents/training-data/meetings.txt` (JSONL). Verified examples only unless `--include-unverified` passed.
* DSPy artifact expected at `artifacts/meeting/optimized_program.json`. Code gracefully falls back to heuristics if missing.
* Ollama local model optional; if using `ollama/<model>` ensure Ollama daemon is running on `http://localhost:11434`.

## 4. Project Layout (Key Paths)
```
pyproject.toml              # Dependencies, scripts, tool configs (ruff, mypy)
README.md                   # Developer quickstart
artifacts/meeting/          # DSPy optimized program JSON(s)
documents/training-data/    # Meeting dataset JSONL
src/hlpr/main.py            # FastAPI app factory (import path hlpr.main:app)
src/hlpr/cli.py             # Typer CLI (entrypoint 'hlpr')
src/hlpr/core/              # settings, logging, errors
src/hlpr/db/                # SQLAlchemy base, models, repositories
src/hlpr/dspy/              # Signatures, dataset loader, metrics, optimizer
src/hlpr/pipelines/         # meeting_summarization pipeline, interfaces
src/hlpr/routers/           # health, example, meetings
src/hlpr/services/          # service layer (pipelines wrapper)
tests/                      # mirrors structure (routers, services, dspy)
```

### Notable Source Files
* `src/hlpr/main.py` – creates FastAPI app, includes router registration.
* `src/hlpr/routers/meetings.py` – meeting endpoints (create & summarize).
* `src/hlpr/pipelines/meeting_summarization.py` – heuristic + DSPy ChainOfThought logic and artifact loading.
* `src/hlpr/dspy/optimizer.py` – produces artifact; uses simple F1 metrics.
* `src/hlpr/dspy/signatures.py` – DSPy `InputField`/`OutputField` declarations (must remain compliant with current DSPy API).
* `pyproject.toml` – authoritative lint/type settings (`ruff`, `mypy`), dependency versions.
* `.github/workflows/ci.yml` – defines required checks; replicate locally with commands above.

## 5. Adding or Modifying Code – Rules for Agents
1. ALWAYS run: `uv sync` (once per environment) before first build in a fresh clone.
2. After edits touching dependencies, run: `uv sync`.
3. Before opening PR (or concluding task) run in order:
  1. `uvx ruff check --fix`
  2. `uv run mypy src`
  3. `uv run pytest -q`
4. Keep new modules < ~200 lines; split if exceeding.
5. Put business logic in pipelines/services, not routers or CLI command bodies.
6. Use existing repository patterns (async SQLAlchemy sessions via dependencies, Pydantic for new schemas) – follow naming present.
7. If adding a new pipeline with DSPy optimization:
  * Add signature(s) in `src/hlpr/dspy/signatures.py`
  * Add metrics if needed under `dspy/metrics.py`
  * Store artifacts under `artifacts/<feature>/` (create directory) – loading pattern should mimic meeting pipeline.
8. Prefer graceful fallback (try/except) when integrating external model calls; tests run in an environment without remote API keys.
9. Do NOT introduce network calls in tests unless clearly isolated & optional.
10. If uncertain where to place code: search adjacent directory or replicate pattern in `meeting_summarization.py`.

## 6. Validation & Common Pitfalls
| Area | Pitfall | Mitigation |
|------|---------|-----------|
| CLI not found | Forget to install in editable mode | `uv sync` already installs; if missing entrypoint ensure `[project.scripts]` unchanged |
| DSPy failing | Signature fields missing Input/OutputField | Mirror pattern in `signatures.py` |
| Tests flaky | External model latency | Heuristic fallback ensures stability; keep model-dependent code wrapped in try/except |
| mypy failures | Strict mode rejects untyped defs | Add type hints; use Protocols for abstractions |
| ruff E/F errors | Style/import ordering | Run `uvx ruff check --fix` before commit |
| SQLite lock | Long-running server during test run | Stop dev server before running tests |

## 7. Extending Data Model
Add fields to existing models in `src/hlpr/db/models.py`, update repositories, and if persistent migrations are later added ensure Alembic script (not present yet). Keep tests updated.

## 8. Test Strategy Summary
* Fast unit/integration tests: run all with `uv run pytest -q`.
* New features: add tests mirroring directory (e.g., `tests/routers/<feature>_test.py`).
* Avoid network dependency; mock or use heuristic fallback.

## 9. Agent Behavior Guidelines
* TRUST this document first. Only search the repo if something here is missing or demonstrably outdated.
* Minimize exploratory grep if target file path is stated above.
* Use small, surgical patches; avoid mass reformatting unrelated code.
* Provide fallback logic for any new external integration.
* Keep artifact reads tolerant (existence + JSON parse guards).

## 10. Quick Reference (Copy/Paste)
```bash
# Bootstrap
uv sync

# Dev server
uv run hlpr run-server

# Health check
uv run hlpr health

# Optimize (example)
uv run hlpr optimize-meeting --iters 1 --model ollama/gemma3

# Lint / Type / Test
uvx ruff check --fix
uv run mypy src
uv run pytest -q
```

---
If you find an instruction invalid (command fails after retry), log the issue in PR description and minimally adapt while preserving style.
