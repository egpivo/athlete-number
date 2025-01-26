#!/bin/bash

# Resolve the base path of the package
PACKAGE_BASE_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Load environment variables from .env file
if [ -f "${PACKAGE_BASE_PATH}/.env" ]; then
    set -o allexport
    source "${PACKAGE_BASE_PATH}/.env"
    set +o allexport
else
    echo "Error: .env file not found in ${PACKAGE_BASE_PATH}"
    exit 1
fi

# Set defaults if variables are not set
HOST=${HOST:-0.0.0.0}
PORT=${PORT:-5566}
WORKERS=${UVICORN_WORKERS:-1}
TIMEOUT=${TIMEOUT_KEEP_ALIVE:-60}

# Kill any process using the port
PID=$(lsof -ti :$PORT)
if [ -n "$PID" ]; then
    echo "Port $PORT is in use by process $PID. Terminating process..."
    kill -9 $PID
    echo "Process $PID terminated."
else
    echo "Port $PORT is free."
fi

# Run Gunicorn with Uvicorn worker class
echo "Starting Gunicorn on $HOST:$PORT with $WORKERS workers..."
poetry run gunicorn -k uvicorn.workers.UvicornWorker \
    --bind "$HOST:$PORT" \
    --workers "$WORKERS" \
    --timeout "$TIMEOUT" \
    --graceful-timeout 30 \
    athlete_number.main:app
