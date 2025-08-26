# syntax=docker/dockerfile:1

FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency definitions
# Copy project metadata and README
COPY pyproject.toml uv.lock README.md ./
# Copy package source for installation
COPY src ./src

# Copy application source
COPY . .

# Re-install the package so new CLI commands (e.g., db-init) are included
RUN pip install .

# Expose FastAPI port
EXPOSE 8000

# Start the FastAPI server via the `hlpr` CLI
CMD ["hlpr", "run-server", "--host", "0.0.0.0", "--port", "8000"]
