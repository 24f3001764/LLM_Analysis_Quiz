# Use Playwright's Python image as the base
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Switch to non-root user
USER pwuser
ENV PATH="/home/pwuser/.local/bin:${PATH}"

# Set working directory
WORKDIR /app

# Create necessary directories
RUN mkdir -p /app/logs /app/downloads /app/temp

# Copy requirements first to leverage Docker cache
COPY --chown=pwuser requirements.txt .

# Install Python dependencies
RUN pip install --user --no-cache-dir --upgrade pip && \
    pip install --user --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install --with-deps

# Copy application code
COPY --chown=pwuser . .

# Copy and set up the start script
COPY --chown=pwuser start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Command to run the application
CMD ["/app/start.sh"]