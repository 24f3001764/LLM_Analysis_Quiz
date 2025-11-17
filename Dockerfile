# Use Playwright's Python image as the base
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Use the existing 'pwuser' that comes with the Playwright image
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

# Command to run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]