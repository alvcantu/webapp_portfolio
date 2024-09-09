#!/bin/bash

# Directory containing VS Code server installations
VSCODE_DIR="$HOME/.vscode-server-insiders"

# Function to log actions
log_action() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$VSCODE_DIR/cleanup.log"
}

# Keep the most recent version and delete older ones
find "$VSCODE_DIR/bin" -mindepth 1 -maxdepth 1 -type d | sort | head -n -1 | xargs rm -rf
log_action "Deleted old VS Code versions"

# Clean up old extensions
find "$VSCODE_DIR/extensions" -mindepth 1 -maxdepth 1 -type d | sort | head -n -1 | xargs rm -rf
log_action "Deleted old extension versions"

# Remove unused extensions (assuming there's a way to track usage)
find "$VSCODE_DIR/extensions" -mindepth 1 -maxdepth 1 -type d -mtime +30 -exec rm -rf {} \;
log_action "Deleted extensions not used in the last 30 days"

# Clean up logs (adjust path if logs are stored elsewhere)
find "$VSCODE_DIR/logs" -type f -mtime +1 -exec rm {} \;
log_action "Deleted logs older than 1 days"

# Remove temporary files
find "$VSCODE_DIR" -type f -name "*.tmp" -delete
log_action "Deleted temporary files"

# Remove cache files (adjust according to VS Code's actual cache directory)
find "$VSCODE_DIR/data" -type f -mtime +5 -delete
log_action "Deleted cache files older than 5 days"

# Remove backup files
find "$VSCODE_DIR" -type f -name "*~" -delete
log_action "Deleted backup files"

# Remove old configuration files (if any)
find "$VSCODE_DIR" -type f -name "*.old" -delete
log_action "Deleted old configuration files"

# Optional: If VS Code uses a specific naming convention for unused files or directories
find "$VSCODE_DIR" -type f -name "unused_*" -delete
find "$VSCODE_DIR" -type d -name "unused_*" -exec rm -rf {} \;

log_action "Cleanup script completed"