#!/bin/sh

# Health check for llama-server container
PORT=${PORT:-"8080"}

# Try to reach the health endpoint
if curl -f -s "http://localhost:${PORT}/health" > /dev/null 2>&1; then
    exit 0
elif curl -f -s "http://localhost:${PORT}/v1/models" > /dev/null 2>&1; then
    # Fallback to models endpoint if health endpoint doesn't exist
    exit 0
else
    echo "Health check failed: llama-server not responding on port ${PORT}"
    exit 1
fi