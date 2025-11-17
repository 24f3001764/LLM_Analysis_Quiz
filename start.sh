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
        if command -v ss &> /dev/null; then
            if ss -tuln | grep -q ":$port "; then
                return 1
            fi
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
export PYTHONPATH="/app:${PYTHONPATH:-}"

log "Starting Uvicorn server..."

# Start the application in the background
uvicorn src.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 1 \
    --no-access-log \
    --timeout-keep-alive 60 \
    --log-level info \
    --log-config /app/logging.ini &

# Get the PID of the background process
UVICORN_PID=$!

# Function to handle shutdown
shutdown() {
    log "Shutting down gracefully..."
    kill -TERM $UVICORN_PID 2>/dev/null
    wait $UVICORN_PID
    log "Uvicorn server stopped."
    exit 0
}

# Set up trap to catch signals
trap shutdown SIGTERM SIGINT

# Wait for the application to start
MAX_RETRIES=15
RETRY_COUNT=0
SLEEP_TIME=2

log "Waiting for application to start..."

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s --fail http://localhost:8000/health >/dev/null; then
        log "Application started successfully!"
        break
    fi
    
    log "Waiting for application to be ready... (Attempt $((RETRY_COUNT + 1))/$MAX_RETRIES)"
    sleep $SLEEP_TIME
    RETRY_COUNT=$((RETRY_COUNT + 1))
    
    # Check if the process is still running
    if ! kill -0 $UVICORN_PID 2>/dev/null; then
        log "Error: Uvicorn process is not running. Exiting..."
        exit 1
    fi
    
    # Increase sleep time for exponential backoff (max 10s)
    SLEEP_TIME=$((SLEEP_TIME < 10 ? SLEEP_TIME + 1 : 10))
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    log "Error: Application failed to start within the expected time"
    log "Last 20 lines of the log file:"
    tail -n 20 "$LOG_FILE"
    exit 1
fi

# Keep the container running
log "Application is running. Press Ctrl+C to stop."
wait $UVICORN_PID
