#!/bin/bash
# Script to prepare SSH keys for container build
# This script should be run before building the container image

# Create temporary directory for SSH keys (gitignored)
mkdir -p docker/ssh_keys_tmp
chmod 700 docker/ssh_keys_tmp

# Copy GitHub SSH key and known_hosts
cp /home/jonflatt/.ssh/github-personal docker/ssh_keys_tmp/
cp /home/jonflatt/.ssh/known_hosts docker/ssh_keys_tmp/ 2>/dev/null || true

# Set correct permissions
chmod 600 docker/ssh_keys_tmp/github-personal
chmod 644 docker/ssh_keys_tmp/known_hosts 2>/dev/null || true

echo "SSH keys prepared for container build in docker/ssh_keys_tmp/"
echo "Run this before building container images"
echo "WARNING: These keys are temporary and will not be committed to the repository"