# syntax=docker/dockerfile:1.4

# Use Playwright's Python image as the base
FROM --platform=linux/amd64 mcr.microsoft.com/playwright/python:v1.40.0-jammy as builder

# Set environment variables
ENV \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VERSION=1.6.1 \
    PATH="/home/pwuser/.local/bin:${PATH}"

# Install system dependencies
USER root
RUN --mount=type=cache,target=/var/cache/apt \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    libmagic1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --user --no-cache-dir poetry==${POETRY_VERSION}

# Set working directory and copy dependency files first for better caching
WORKDIR /app
COPY --chown=pwuser pyproject.toml poetry.lock* ./

# Install Python dependencies
RUN --mount=type=cache,target=/root/.cache/pypoetry \
    python -m poetry config virtualenvs.create false && \
    python -m poetry install --no-interaction --no-ansi --only main && \
    playwright install --with-deps

# Runtime stage
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# Copy installed dependencies from builder
COPY --from=builder /usr/local /usr/local
COPY --from=builder /home/pwuser/.local /home/pwuser/.local

# Set up non-root user and working directory
USER root
WORKDIR /app

# Create necessary directories with correct permissions
RUN mkdir -p /app/logs /app/downloads /app/temp && \
    chown -R pwuser:pwuser /app

# Copy application code and start script
COPY --chown=pwuser . .

# Ensure start script has correct line endings and permissions
RUN if [ -f start_fixed.sh ]; then \
        cp start_fixed.sh /app/start.sh && \
        sed -i 's/\r$//' /app/start.sh; \
    else \
        cp start.sh /app/start.sh && \
        sed -i 's/\r$//' /app/start.sh; \
    fi && \
    chmod +x /app/start.sh && \
    chown pwuser:pwuser /app/start.sh

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Switch to non-root user and set PATH
USER pwuser
ENV PATH="/home/pwuser/.local/bin:${PATH}"

# Command to run the application
CMD ["/app/start.sh"]