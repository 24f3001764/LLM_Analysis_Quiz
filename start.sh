#!/bin/bash
set -e

echo "Starting Uvicorn server..."

# Start the application in the background
uvicorn src.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 1 \
    --no-access-log \
    --timeout-keep-alive 60 &

# Wait for the application to start
echo "Waiting for application to start..."
sleep 5

# Check if the health endpoint is responding
MAX_RETRIES=10
RETRY_COUNT=0
SLEEP_TIME=5

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s --fail http://localhost:8000/health >/dev/null; then
        echo "Application started successfully!"
        break
    fi
    
    echo "Waiting for application to be ready... (Attempt $((RETRY_COUNT + 1))/$MAX_RETRIES)"
    sleep $SLEEP_TIME
    RETRY_COUNT=$((RETRY_COUNT + 1))
    
    # Increase sleep time for exponential backoff
    SLEEP_TIME=$((SLEEP_TIME + 2))
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "Error: Application failed to start within the expected time"
    exit 1
fi

# Keep the container running
wait
