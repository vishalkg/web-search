#!/bin/bash
# Stop WebSearch MCP daemon (idempotent)

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_DIR="$(dirname "$DIR")"
PID_FILE="$PROJECT_DIR/websearch.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "Daemon not running (no PID file)"
    exit 0  # Success - daemon is stopped
fi

PID=$(cat "$PID_FILE")

if ! kill -0 "$PID" 2>/dev/null; then
    echo "Daemon not running (process not found)"
    rm -f "$PID_FILE"
    exit 0  # Success - daemon is stopped
fi

echo "Stopping daemon (PID: $PID)..."
kill -TERM "$PID"

# Wait for graceful shutdown
for i in {1..10}; do
    if ! kill -0 "$PID" 2>/dev/null; then
        echo "Daemon stopped successfully"
        exit 0
    fi
    sleep 1
done

# Force kill if still running
echo "Daemon didn't stop gracefully, forcing shutdown..."
kill -KILL "$PID" 2>/dev/null
echo "Daemon force stopped"
