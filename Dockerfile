# syntax=docker/dockerfile:1

FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies and uv
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev curl \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && mv /root/.local/bin/uv /usr/local/bin/ \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency definitions
# Copy project metadata and README
COPY pyproject.toml uv.lock README.md ./
# Copy package source for installation
COPY src ./src

# Copy application source
COPY . .

# Install dependencies and the package using uv
RUN uv sync --frozen

# Install the package in editable mode
RUN uv pip install -e .

# Expose FastAPI port
EXPOSE 8000

# Start the FastAPI server via the `hlpr` CLI using uv run
CMD ["uv", "run", "hlpr", "run-server", "--host", "0.0.0.0", "--port", "8000"]
