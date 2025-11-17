# syntax=docker/dockerfile:1.4

# Use Playwright's Python image as the base
FROM --platform=linux/amd64 mcr.microsoft.com/playwright/python:v1.40.0-jammy

# Set environment variables
ENV \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/home/pwuser/.local/bin:${PATH}" \
    PYTHONPATH="/app:${PYTHONPATH:-}" \
    PORT=8000

# Install system dependencies
USER root
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libmagic1 \
    curl \
    ca-certificates \
    build-essential \
    python3-dev \
    python3-venv \
    && update-ca-certificates --fresh \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Create necessary directories with correct permissions
RUN mkdir -p /app/logs /app/downloads /app/temp && \
    chown -R pwuser:pwuser /app

# Copy only the files needed for installing dependencies first
COPY --chown=pwuser pyproject.toml poetry.lock* ./

# Create a minimal README.md
RUN echo "# LLM Analysis Quiz" > README.md && \
    chown pwuser:pwuser README.md

# Install Python dependencies
RUN echo "Installing Python dependencies..." && \
    python -m pip install --upgrade pip && \
    pip install --user --no-cache-dir poetry==1.6.1 && \
    python -m poetry config virtualenvs.create false && \
    python -m poetry install --no-interaction --no-ansi --only main --no-cache

# Install Playwright browsers
RUN playwright install --with-deps

# Copy the rest of the application
COPY --chown=pwuser . .

# Handle start script with proper line endings and permissions
RUN if [ -f start_fixed.sh ]; then \
        cp start_fixed.sh /app/start.sh; \
    else \
        cp start.sh /app/start.sh; \
    fi && \
    sed -i 's/\r$//' /app/start.sh && \
    chmod +x /app/start.sh && \
    chown pwuser:pwuser /app/start.sh

# Verify the start script
RUN ls -la /app/start.sh && \
    file /app/start.sh

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Switch to non-root user
USER pwuser

# Command to run the application
CMD ["/app/start.sh"]