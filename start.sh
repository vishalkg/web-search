#!/bin/bash

# Get the directory where this script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Activate virtual environment and run the server
source "$DIR/../venv/bin/activate"
exec python "$DIR/server.py" "$@"
