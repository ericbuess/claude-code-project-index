#!/usr/bin/env bash
# Python runner that uses the saved Python command from installation

INSTALL_DIR="$HOME/.claude-code-project-index"
PYTHON_CMD_FILE="$INSTALL_DIR/.python_cmd"

# Read the saved Python command, or fallback to common defaults
if [[ -f "$PYTHON_CMD_FILE" ]]; then
    PYTHON_CMD=$(cat "$PYTHON_CMD_FILE")
else
    # Fallback: try to find Python
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        echo "Error: Python not found. Please reinstall PROJECT_INDEX." >&2
        exit 1
    fi
fi

# Execute the Python script with all arguments
exec "$PYTHON_CMD" "$@"