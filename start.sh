#!/bin/bash
# Ensure proper Docker socket permissions
if [ -S /var/run/docker.sock ]; then
  echo "Setting Docker socket permissions..."
  # We can now chmod the socket since we're running as root
  chmod 666 /var/run/docker.sock || true
  ls -la /var/run/docker.sock
fi

# Set Docker environment variables for Python Docker SDK
# This is the critical configuration - use triple slash format for Unix socket
export DOCKER_HOST="unix:///var/run/docker.sock"
echo "Setting DOCKER_HOST environment variable to: $DOCKER_HOST"

# Verify Docker CLI works
echo "Testing Docker CLI connection:"
docker info || echo "Docker CLI connection failed"

# Start the app
cd /app
echo "Starting AI Container Manager..."
# Debug mode disabled for cleaner logs
python run.py