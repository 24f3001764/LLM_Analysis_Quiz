# Build stage
FROM python:3.9-slim as builder

# Install system dependencies, Node.js and Playwright system dependencies as root
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    # Node.js installation
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    # Playwright system dependencies
    && apt-get install -y --no-install-recommends \
    libnss3 \
    libnspr4 \
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
    && rm -rf /var/lib/apt/lists/*

# Create non-root user and switch to it
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"
ENV PLAYWRIGHT_BROWSERS_PATH="/home/user/.cache/ms-playwright"

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY --chown=user requirements.txt .

# Create a script to install Playwright with retries
RUN echo '#!/bin/sh\n\
set -e\n\
max_attempts=3\n\
attempt=1\n\
until [ $attempt -gt $max_attempts ]\n\
do\n\
    echo "Attempt $attempt of $max_attempts to install Playwright browsers..."\n\
    if playwright install --with-deps chromium --with-deps firefox --with-deps webkit; then\n\
        echo "Playwright browsers installed successfully"\n\
        exit 0\n\
    else\n\
        echo "Attempt $attempt failed, retrying... ($((max_attempts - attempt)) attempts remaining)"\n\
        attempt=$((attempt + 1))\n\
        sleep 5\n\
    fi\ndone\n\
echo "Failed to install Playwright browsers after $max_attempts attempts"\n\
exit 1' > /home/user/install_playwright.sh && \
    chmod +x /home/user/install_playwright.sh

# Install Python dependencies and Playwright
RUN pip install --user --no-cache-dir --upgrade pip && \
    pip install --user --no-cache-dir -r requirements.txt && \
    python -m pip install --user --no-cache-dir playwright && \
    # Install browsers with retry script
    PLAYWRIGHT_BROWSERS_PATH=/home/user/.cache/ms-playwright \
    PLAYWRIGHT_DOWNLOAD_HOST=playwright.azureedge.net \
    /home/user/install_playwright.sh && \
    # Set correct permissions
    chmod -R 755 /home/user/.cache/ms-playwright

# Final stage
FROM python:3.9-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Playwright dependencies
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

# Create non-root user
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"
ENV PLAYWRIGHT_BROWSERS_PATH="/home/user/.cache/ms-playwright"

# Set working directory
WORKDIR /app

# Copy installed Python packages and Playwright browsers from builder
COPY --from=builder --chown=user /home/user/.local /home/user/.local
COPY --from=builder --chown=user /home/user/.cache/ms-playwright /home/user/.cache/ms-playwright

# Copy application code
COPY --chown=user . .

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]