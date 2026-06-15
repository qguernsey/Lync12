#!/usr/bin/env bash
set -euo pipefail

# Configurable defaults — override by setting the variable before running
SERIAL_PORT="${SERIAL_PORT:-/dev/ttyUSB0}"
LOG_LEVEL="${LOG_LEVEL:-WARNING}"
CACHE_TIMEOUT="${CACHE_TIMEOUT:-300}"
PORT="${PORT:-8080}"

echo "Starting Lync12 (hardware mode)"
echo "  SERIAL_PORT   = $SERIAL_PORT"
echo "  LOG_LEVEL     = $LOG_LEVEL"
echo "  CACHE_TIMEOUT = $CACHE_TIMEOUT"
echo "  PORT          = $PORT"

# Build the image if it doesn't exist or if source files are newer than the image
IMAGE="lync12-hardware"
if ! docker image inspect "$IMAGE" &>/dev/null; then
    echo "Building Docker image..."
    docker build -t "$IMAGE" /workspace/Lync12
elif find /workspace/Lync12 -name "*.py" -newer <(docker image inspect "$IMAGE" --format '{{.Metadata.LastTagTime}}' 2>/dev/null || echo "") 2>/dev/null | grep -q .; then
    echo "Source files changed — rebuilding Docker image..."
    docker build -t "$IMAGE" /workspace/Lync12
else
    echo "Docker image up to date."
fi

docker run --rm \
    --device "$SERIAL_PORT:$SERIAL_PORT" \
    -p "$PORT:$PORT" \
    -e SERIAL_PORT="$SERIAL_PORT" \
    -e LOG_LEVEL="$LOG_LEVEL" \
    -e CACHE_TIMEOUT="$CACHE_TIMEOUT" \
    -e PORT="$PORT" \
    "$IMAGE"
