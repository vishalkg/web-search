#!/bin/bash
# Check WebSearch MCP daemon status

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_DIR="$(dirname "$DIR")"
PID_FILE="$PROJECT_DIR/websearch.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "Status: STOPPED (no PID file)"
    exit 1
fi

PID=$(cat "$PID_FILE")

if ! kill -0 "$PID" 2>/dev/null; then
    echo "Status: STOPPED (process not found)"
    rm -f "$PID_FILE"
    exit 1
fi

echo "Status: RUNNING"
echo "PID: $PID"
echo "Server URL: http://127.0.0.1:8090/mcp"

# Test server response
if command -v curl >/dev/null 2>&1; then
    echo -n "Server response: "
    if curl -s --max-time 3 "http://127.0.0.1:8090/mcp" >/dev/null 2>&1; then
        echo "OK"
    else
        echo "NOT RESPONDING"
    fi
fi

# Show resource usage
echo "Memory usage: $(ps -o rss= -p "$PID" 2>/dev/null | awk '{print int($1/1024)"MB"}' || echo "N/A")"
echo "CPU usage: $(ps -o %cpu= -p "$PID" 2>/dev/null | awk '{print $1"%"}' || echo "N/A")"
