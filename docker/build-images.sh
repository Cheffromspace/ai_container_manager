#!/bin/bash

# Move to project root
cd $(dirname "$0")/..

# Build the container manager service
echo "Building AI Container Manager service..."
docker build -t ai-container-manager -f docker/Dockerfile .

# Build the AI container image
echo "Building AI Container image..."
docker build -t ai-container-image -f docker/Dockerfile.container .

# Build the API proxy image
echo "Building API Proxy image..."
docker build -t n8n-api-proxy -f docker/Dockerfile.proxy .

echo "All images built successfully!"
echo "You can start the AI Container Manager with: docker-compose up -d ai-container-manager"
echo "You can start the API Proxy with: docker-compose up -d api-proxy"