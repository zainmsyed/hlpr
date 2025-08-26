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
# Copy source code for installation
COPY src ./src

# Install the package (and its dependencies) so `hlpr` CLI & `uvicorn` are available
RUN pip install .

# Copy application source
COPY . .

# Expose FastAPI port
EXPOSE 8000

# Start the FastAPI server via the `hlpr` CLI
CMD ["hlpr", "run-server", "--host", "0.0.0.0", "--port", "8000"]
