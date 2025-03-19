#!/bin/bash

# Build the container manager service
echo "Building AI Container Manager service..."
docker build -t ai-container-manager .

# Build the AI container image
echo "Building AI Container image..."
docker build -t ai-container-image -f Dockerfile.container .

echo "Both images built successfully!"
echo "You can start the AI Container Manager with: docker-compose up -d ai-container-manager"