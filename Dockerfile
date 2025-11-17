# syntax=docker/dockerfile:1.4

# Build stage
FROM --platform=linux/amd64 python:3.10-slim as builder

# Set environment variables
ENV \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VERSION=1.6.1 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=false \
    PIP_DEFAULT_TIMEOUT=100 \
    PYTHONPATH=/app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    ca-certificates \
    && update-ca-certificates --fresh \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - && \
    cd /usr/local/bin && \
    ln -s /opt/poetry/bin/poetry && \
    poetry config virtualenvs.create false

# Set working directory
WORKDIR /app

# Copy only the files needed for installing dependencies
COPY pyproject.toml poetry.lock* ./

# Install Python dependencies with retry logic
RUN --mount=type=cache,target=/root/.cache/pip \
    echo "Installing Python dependencies..." && \
    python -m pip install --upgrade pip && \
    pip install --no-cache-dir poetry==$POETRY_VERSION && \
    poetry install --no-interaction --no-ansi --only main --no-cache || \
    (echo "First attempt failed, retrying with --no-deps..." && \
     poetry install --no-interaction --no-ansi --only main --no-cache --no-deps && \
     echo "Installing with dependencies..." && \
     poetry install --no-interaction --no-ansi --only main --no-cache)

# Runtime stage
FROM --platform=linux/amd64 python:3.10-slim

# Install Playwright system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    libmagic1 \
    ca-certificates \
    wget \
    && update-ca-certificates --fresh \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app \
    PORT=8000 \
    PATH="/home/pwuser/.local/bin:${PATH}"

# Create app directory and set permissions
RUN useradd -m pwuser && \
    mkdir -p /app && \
    chown -R pwuser:pwuser /app

# Switch to non-root user
USER pwuser

# Set working directory
WORKDIR /app

# Copy installed dependencies from builder
COPY --from=builder --chown=pwuser:pwuser /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder --chown=pwuser:pwuser /usr/local/bin/poetry /usr/local/bin/poetry

# Copy application code
COPY --chown=pwuser:pwuser . .

# Create necessary directories
RUN mkdir -p /app/logs /app/downloads /app/temp && \
    chown -R pwuser:pwuser /app/logs /app/downloads /app/temp

# Install Playwright browsers
RUN python -m playwright install --with-deps

# Handle start script with proper line endings and permissions
RUN if [ -f start_fixed.sh ]; then \
        cp start_fixed.sh /app/start.sh; \
    else \
        cp start.sh /app/start.sh; \
    fi && \
    sed -i 's/\r$//' /app/start.sh && \
    chmod +x /app/start.sh

# Verify the start script
RUN file /app/start.sh

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Command to run the application
CMD ["/app/start.sh"]