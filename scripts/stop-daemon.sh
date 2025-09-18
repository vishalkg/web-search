#!/bin/bash
# Stop WebSearch MCP daemon

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_DIR="$(dirname "$DIR")"
PID_FILE="$PROJECT_DIR/websearch.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "No PID file found. Daemon may not be running."
    exit 1
fi

PID=$(cat "$PID_FILE")

if ! kill -0 "$PID" 2>/dev/null; then
    echo "Process $PID not found. Removing stale PID file."
    rm -f "$PID_FILE"
    exit 1
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
