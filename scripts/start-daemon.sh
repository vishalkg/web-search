#!/bin/bash
# Start WebSearch MCP daemon (idempotent)

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_DIR="$(dirname "$DIR")"
PID_FILE="$PROJECT_DIR/websearch.pid"

# Check if already running
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "Daemon already running (PID: $PID)"
        echo "Server URL: http://127.0.0.1:8090/mcp"
        exit 0  # Success - daemon is running
    else
        echo "Removing stale PID file"
        rm -f "$PID_FILE"
    fi
fi

# Start daemon
echo "Starting WebSearch MCP daemon..."
cd "$PROJECT_DIR"
source ../venv/bin/activate
nohup python -m websearch.server --daemon > websearch-daemon.log 2>&1 &

# Wait a moment and check if it started
sleep 2
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    echo "Daemon started successfully (PID: $PID)"
    echo "Server URL: http://127.0.0.1:8090/mcp"
    echo "Log file: $PROJECT_DIR/websearch-daemon.log"
else
    echo "Failed to start daemon. Check websearch-daemon.log for errors."
    exit 1
fi
