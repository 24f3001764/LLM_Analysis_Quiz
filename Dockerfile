FROM --platform=linux/amd64 python:3.10-slim

# Set environment variables
ENV \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app \
    PORT=8000

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    ca-certificates \
    libmagic1 \
    wget \
    && update-ca-certificates --fresh \
    && rm -rf /var/lib/apt/lists/*

# Create app directory and set permissions
RUN useradd -m pwuser && \
    mkdir -p /app && \
    chown -R pwuser:pwuser /app

# Switch to non-root user
USER pwuser

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY --chown=pwuser:pwuser pyproject.toml ./

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install poetry==1.6.1 && \
    poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --only main

# Copy application code
COPY --chown=pwuser:pwuser . .

# Install Playwright and its dependencies
RUN pip install playwright==1.40.0 && \
    playwright install --with-deps chromium

# Create necessary directories
RUN mkdir -p /app/logs /app/downloads /app/temp && \
    chmod -R 755 /app/logs /app/downloads /app/temp

# Use start script if it exists, otherwise use default command
CMD ["/bin/sh", "-c", "if [ -f start_fixed.sh ]; then exec /bin/sh start_fixed.sh; elif [ -f start.sh ]; then exec /bin/sh start.sh; else echo 'No start script found'; exit 1; fi"]

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1