#!/bin/bash

# Directory containing VS Code server installations
VSCODE_DIR="$HOME/.vscode-server-insiders"

# Keep the most recent version and delete older ones
find "$VSCODE_DIR/bin" -mindepth 1 -maxdepth 1 -type d | sort | head -n -1 | xargs rm -rf

# Optionally, clean up old extensions
find "$VSCODE_DIR/extensions" -mindepth 1 -maxdepth 1 -type d | sort | head -n -1 | xargs rm -rf
