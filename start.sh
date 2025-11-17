#!/bin/bash

# Start the application in the background
uvicorn src.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 1 \
    --timeout-keep-alive 60 &
    
# Wait for the application to start
sleep 5

# Check if the health endpoint is responding
while ! curl -s http://localhost:8000/health >/dev/null; do
    echo "Waiting for application to start..."
    sleep 1
done

echo "Application started successfully!"
wait
