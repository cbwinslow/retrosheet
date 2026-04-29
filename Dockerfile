# Multi-stage build for baseball prediction warehouse
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install uv and dependencies
RUN pip install uv && \
    uv venv /app/.venv && \
    uv pip install --no-cache -e ".[live]"

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY baseball/ ./baseball/
COPY sql/ ./sql/
COPY scripts/ ./scripts/
COPY docs/ ./docs/

# Make venv the default Python
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from baseball.core.db import get_db_connection; get_db_connection()" || exit 1

# Default command
CMD ["python", "-m", "baseball.cli"]
