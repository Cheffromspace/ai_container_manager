#!/bin/bash
# Docker wrapper script for the API proxy
# This script will be injected into the container and made executable

# We'll use the Docker socket on the host to run commands
# This requires the Docker socket to be mounted from the host

if [ ! -S /var/run/docker.sock ]; then
  echo "Error: Docker socket not found. Please mount the Docker socket from the host."
  exit 1
fi

# Define docker CLI command - use socat to communicate with the Docker socket
export DOCKER_HOST=unix:///var/run/docker.sock

# Check which docker command is available
if command -v docker &> /dev/null; then
  docker "$@"
elif [ -x /usr/bin/docker ]; then
  /usr/bin/docker "$@"
elif [ -x /usr/local/bin/docker ]; then
  /usr/local/bin/docker "$@"
else
  echo "Error: Docker command not found"
  exit 1
fi
