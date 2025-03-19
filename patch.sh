#!/bin/bash
# This script patches the container manager to always use bash -c for command execution

set -e

echo "Copying app.py from the container..."
docker cp ai-container-manager:/app/app.py /tmp/app.py

echo "Modifying app.py to always use bash -c for commands..."
sed -i 's/needs_shell =.*$/needs_shell = True  # Always use shell/' /tmp/app.py

echo "Copying modified app.py back to the container..."
docker cp /tmp/app.py ai-container-manager:/app/app.py

echo "Restarting container manager..."
docker restart ai-container-manager

echo "Patch applied successfully!"
echo "The container manager now always uses bash -c for executing commands."
echo "This should fix the issue with cd and other shell builtin commands."