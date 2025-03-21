#!/bin/bash
# Script to copy SSH keys from host to a specific container
# This script should be run on the host system

# Usage: ./host_ssh_copy.sh container_name

CONTAINER_NAME=$1

if [ -z "$CONTAINER_NAME" ]; then
    echo "Usage: $0 container_name"
    exit 1
fi

# Create temporary directory
TMP_DIR=$(mktemp -d)
chmod 700 $TMP_DIR

# Copy SSH keys to temp directory
cp /home/jonflatt/.ssh/github-personal $TMP_DIR/
cp /home/jonflatt/.ssh/known_hosts $TMP_DIR/ 2>/dev/null || true

# Set temporary readable permissions
chmod 644 $TMP_DIR/github-personal

# Copy to container
echo "Copying SSH keys to container $CONTAINER_NAME..."
docker cp $TMP_DIR/github-personal $CONTAINER_NAME:/root/.ssh/
docker cp $TMP_DIR/known_hosts $CONTAINER_NAME:/root/.ssh/ 2>/dev/null || true

# Fix permissions inside container
docker exec $CONTAINER_NAME chmod 700 /root/.ssh
docker exec $CONTAINER_NAME chmod 600 /root/.ssh/github-personal
docker exec $CONTAINER_NAME chmod 644 /root/.ssh/known_hosts 2>/dev/null || true

# Clean up
rm -rf $TMP_DIR

echo "SSH keys successfully copied to container $CONTAINER_NAME"