#!/usr/bin/env bash
set -euo pipefail

# Configurable defaults — override by setting the variable before running
SERIAL_PORT="${SERIAL_PORT:-/dev/ttyUSB0}"
LOG_LEVEL="${LOG_LEVEL:-WARNING}"
CACHE_TIMEOUT="${CACHE_TIMEOUT:-300}"
PORT="${PORT:-8080}"

# MQTT bridge (disabled by default — set MQTT_ENABLED=true to activate)
MQTT_ENABLED="${MQTT_ENABLED:-false}"
MQTT_BROKER="${MQTT_BROKER:-localhost}"
MQTT_PORT="${MQTT_PORT:-1883}"
MQTT_USERNAME="${MQTT_USERNAME:-}"
MQTT_PASSWORD="${MQTT_PASSWORD:-}"
MQTT_TOPIC_PREFIX="${MQTT_TOPIC_PREFIX:-lync12}"
MQTT_STATE_INTERVAL="${MQTT_STATE_INTERVAL:-60}"

echo "Starting Lync12 (hardware mode)"
echo "  SERIAL_PORT        = $SERIAL_PORT"
echo "  LOG_LEVEL          = $LOG_LEVEL"
echo "  CACHE_TIMEOUT      = $CACHE_TIMEOUT"
echo "  PORT               = $PORT"
echo "  MQTT_ENABLED       = $MQTT_ENABLED"
if [ "$MQTT_ENABLED" = "true" ]; then
    echo "  MQTT_BROKER        = $MQTT_BROKER"
    echo "  MQTT_PORT          = $MQTT_PORT"
    echo "  MQTT_TOPIC_PREFIX  = $MQTT_TOPIC_PREFIX"
fi

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
    -e MQTT_ENABLED="$MQTT_ENABLED" \
    -e MQTT_BROKER="$MQTT_BROKER" \
    -e MQTT_PORT="$MQTT_PORT" \
    -e MQTT_USERNAME="$MQTT_USERNAME" \
    -e MQTT_PASSWORD="$MQTT_PASSWORD" \
    -e MQTT_TOPIC_PREFIX="$MQTT_TOPIC_PREFIX" \
    -e MQTT_STATE_INTERVAL="$MQTT_STATE_INTERVAL" \
    "$IMAGE"
