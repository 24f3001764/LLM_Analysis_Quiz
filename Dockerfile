# Use Playwright's Python image as the base
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# Install system dependencies
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Switch back to non-root user
USER pwuser
ENV PATH="/home/pwuser/.local/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY --chown=pwuser requirements.txt .

# Install Python dependencies
RUN pip install --user --no-cache-dir --upgrade pip && \
    pip install --user --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=pwuser . .

# Expose the port the app runs on
EXPOSE 8000

# Install curl for health checks
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Switch back to non-root user
USER pwuser

# Copy and set up the start script
COPY --chown=pwuser start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Command to run the application
CMD ["/app/start.sh"]