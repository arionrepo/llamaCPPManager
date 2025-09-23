#!/bin/sh
set -e

# Default values
MODEL_PATH=${MODEL_PATH:-"/models/model.gguf"}
PORT=${PORT:-"8080"}
HOST=${HOST:-"0.0.0.0"}

# Log startup information
echo "llamaCPPManager Container Starting"
echo "Model Path: ${MODEL_PATH}"
echo "Port: ${PORT}"
echo "Host: ${HOST}"

# Validate model file exists
if [ ! -f "${MODEL_PATH}" ]; then
    echo "ERROR: Model file not found at ${MODEL_PATH}"
    echo "Available files in /models:"
    ls -la /models/ || echo "No /models directory"
    exit 1
fi

# Prepare llama-server arguments
ARGS="--model ${MODEL_PATH} --host ${HOST} --port ${PORT}"

# Add additional arguments from environment
if [ -n "${EXTRA_ARGS}" ]; then
    ARGS="${ARGS} ${EXTRA_ARGS}"
fi

echo "Starting llama-server with: ${ARGS}"

# Execute llama-server
exec /usr/local/bin/llama-server ${ARGS}