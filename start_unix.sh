#!/bin/bash
set -euo pipefail

# Set up logging
LOG_FILE="/app/logs/app-$(date +'%Y%m%d').log"
mkdir -p /app/logs
exec > >(tee -a "${LOG_FILE}") 2>&1

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Function to check if port is available
port_available() {
    local port=$1
    if command -v nc &> /dev/null; then
        if nc -z localhost "$port"; then
            return 1
        fi
    else
        if command -v netstat &> /dev/null; then
            if netstat -tuln | grep -q ":$port "; then
                return 1
            fi
        else
            log "Warning: Neither nc nor netstat is available. Cannot check port availability."
        fi
    fi
    return 0
}

# Check if port is already in use
if ! port_available 8000; then
    log "Port 8000 is already in use. Another instance might be running."
    exit 1
fi

# Set environment variables
export PYTHONUNBUFFERED=1
export PYTHONPATH="/app:${PYTHONPATH:-}"

# Install dependencies if needed
if [ -f "poetry.lock" ]; then
    log "Installing Python dependencies..."
    python -m pip install --user --no-cache-dir poetry==1.6.1
    python -m poetry config virtualenvs.create false
    python -m poetry install --no-interaction --no-ansi --only main
fi

# Run database migrations if needed
if [ -f "alembic.ini" ] && [ -d "alembic" ]; then
    log "Running database migrations..."
    alembic upgrade head
fi

# Start the application
log "Starting application..."

# Function to handle shutdown
shutdown() {
    log "Shutting down..."
    pkill -f "uvicorn" || true
    exit 0
}

# Set up trap to catch signals
trap shutdown SIGTERM SIGINT

# Start the application in the background
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload & 

# Wait for the application to start
MAX_RETRIES=30
COUNTER=0
while ! nc -z localhost 8000; do
    sleep 1
    COUNTER=$((COUNTER + 1))
    if [ $COUNTER -ge $MAX_RETRIES ]; then
        log "Failed to start application: Timeout waiting for server to start"
        exit 1
    fi
done

log "Application started successfully"

# Keep the container running
while true; do
    sleep 60
    # Check if the application is still running
    if ! nc -z localhost 8000; then
        log "Application is no longer running. Exiting..."
        exit 1
    fi
done
