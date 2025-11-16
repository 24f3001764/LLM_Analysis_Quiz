# Build stage
FROM python:3.9-slim as builder

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user and switch to it
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY --chown=user requirements.txt .
RUN pip install --user --no-cache-dir --upgrade pip && \
    pip install --user --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN python -m playwright install --with-deps chromium

# Runtime stage
FROM python:3.9-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # For Playwright
    libglib2.0-0 \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libatspi2.0-0 \
    libx11-xcb1 \
    # For python-magic
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user and switch to it
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder --chown=user /home/user/.local /home/user/.local

# Copy Playwright browsers from builder
COPY --from=builder --chown=user /home/user/.cache/ms-playwright /home/user/.cache/ms-playwright

# Copy application code
COPY --chown=user . .

# Environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PLAYWRIGHT_BROWSERS_PATH=/home/user/.cache/ms-playwright

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
