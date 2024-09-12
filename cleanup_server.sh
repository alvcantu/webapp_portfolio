#!/bin/bash

# Directory containing VS Code server installations
VSCODE_DIR="$HOME/.vscode-server-insiders"
CACHE_DIR="$HOME/.cache"

# Function to log actions
log_action() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$VSCODE_DIR/cleanup.log"
}

# Function to safely delete files older than a specified number of days
clean_files() {
    local dir=$1
    local days=$2
    echo "Cleaning $dir of files older than $days days..."
    find "$dir" -type f -mtime +$days -delete
    log_action "Deleted files in $dir older than $days days"
}

# Clean up VS Code Server
# Keep the most recent version and delete older ones
find "$VSCODE_DIR/bin" -mindepth 1 -maxdepth 1 -type d | sort | head -n -1 | xargs rm -rf
log_action "Deleted old VS Code versions"

# Clean up old extensions
find "$VSCODE_DIR/extensions" -mindepth 1 -maxdepth 1 -type d | sort | head -n -1 | xargs rm -rf
log_action "Deleted old extension versions"

# Remove unused extensions (assuming there's a way to track usage)
find "$VSCODE_DIR/extensions" -mindepth 1 -maxdepth 1 -type d -mtime +30 -exec rm -rf {} \;
log_action "Deleted extensions not used in the last 30 days"

# Clean up logs
find "$VSCODE_DIR" -type f -mtime +1 -exec rm {} \;
log_action "Deleted logs older than 1 days"

# Remove temporary files
find "$VSCODE_DIR" -type f -name "*.tmp" -delete
log_action "Deleted temporary files"

# Remove cache files
find "$VSCODE_DIR/data" -type f -mtime +5 -delete
log_action "Deleted cache files older than 5 days"

# Remove backup files
find "$VSCODE_DIR" -type f -name "*~" -delete
log_action "Deleted backup files"

# Remove old configuration files
find "$VSCODE_DIR" -type f -name "*.old" -delete
log_action "Deleted old configuration files"

# Optional: If VS Code uses a specific naming convention for unused files or directories
find "$VSCODE_DIR" -type f -name "unused_*" -delete
find "$VSCODE_DIR" -type d -name "unused_*" -exec rm -rf {} \;

# Clean up .cache directory
clean_files "$CACHE_DIR" 5

# Clear out trash if your system uses .cache or similar for trash
if [ -d "$HOME/.local/share/Trash" ]; then
    rm -rf "$HOME/.local/share/Trash/files/*"
    log_action "Emptied Trash"
fi

log_action "Cleanup script completed"