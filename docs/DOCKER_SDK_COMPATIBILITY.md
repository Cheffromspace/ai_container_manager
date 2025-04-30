# Docker SDK Compatibility Guide

This document explains how to address common Docker SDK compatibility issues in the AI Container Manager.

## Understanding the "Not supported URL scheme http+docker" Error

### The Problem

If you encounter the error "Not supported URL scheme http+docker" when the AI Container Manager attempts to connect to Docker, this indicates a compatibility issue between:

- The Docker SDK for Python (docker-py)
- The Requests library

This issue specifically occurs with:
- docker-py versions < 7.1.0
- requests versions ≥ 2.32.0

### Root Cause

In requests 2.32.0 and newer, the adapter for handling the "http+docker" URL scheme was removed, which docker-py versions below 7.1.0 rely on. This causes the Docker SDK to fail when attempting to connect to the Docker socket.

## The Solution

The solution involves:

1. **Using compatible library versions**:
   - Ensure docker-py is at version 7.1.0 or higher
   - This version is compatible with requests 2.32.2

2. **Using the correct Docker socket URL format**:
   - Always use triple slashes for Unix socket paths
   - Correct: `unix:///var/run/docker.sock`
   - Incorrect: `unix://var/run/docker.sock`

3. **Setting the correct DOCKER_HOST environment variable**:
   ```bash
   export DOCKER_HOST="unix:///var/run/docker.sock"
   ```

## Implementation in the AI Container Manager

The AI Container Manager addresses this issue through:

1. **Updated requirements.txt**:
   ```
   flask==2.3.3
   docker==7.1.0
   gunicorn==23.0.0
   pyjwt==2.10.1
   requests==2.32.2
   ```

2. **Correct Docker client initialization in app.py**:
   ```python
   def initialize_docker_client():
       """Initialize Docker client"""
       global client
       
       try:
           # Use the correct triple-slash format for Unix socket path
           docker_host = os.environ.get('DOCKER_HOST', 'unix:///var/run/docker.sock')
           logger.info(f"Connecting to Docker with: {docker_host}")
           
           # Initialize with explicit API version negotiation
           client = docker.DockerClient(base_url=docker_host, version='auto')
           
           # Verify connection works by calling an API endpoint
           version = client.version()
           logger.info(f"Docker connection successful! API Version: {version.get('ApiVersion', 'unknown')}")
           return True
       except Exception as e:
           logger.error(f"Error initializing Docker client: {str(e)}")
           logger.error("Docker functionality will be limited.")
           return False
   ```

3. **Environment variable settings in start.sh**:
   ```bash
   # Set Docker environment variables for Python Docker SDK
   # This is the critical configuration - use triple slash format for Unix socket
   export DOCKER_HOST="unix:///var/run/docker.sock"
   echo "Setting DOCKER_HOST environment variable to: $DOCKER_HOST"
   ```

## Testing the Docker Connection

You can verify if the Docker connection is working by:

1. Checking the container logs for successful connection:
   ```bash
   docker logs ai-container-manager | grep "Docker connection successful"
   ```

2. Making a test API call that requires Docker:
   ```bash
   curl -X POST -H "X-API-Key: YOUR_API_KEY" http://localhost:5000/api/containers
   ```

## Updating Container Images

It's important to note that **both** Docker images need to be updated for full compatibility:

1. **ai-container-manager** (built from Dockerfile): The main API service that handles container creation and management.

2. **ai-container-image** (built from Dockerfile.container): The base image for spawned containers.

If only the manager image is updated but not the container image, you may still see "Not supported URL scheme http+docker" errors in the logs of the spawned containers.

## Container Shell Access for Debugging

If you need to debug Docker connectivity inside the container:

```bash
# Get a shell in the running container
docker exec -it ai-container-manager /bin/bash

# Check Docker socket availability
ls -l /var/run/docker.sock

# Verify environment variables
echo $DOCKER_HOST

# Test Docker connection with Python
python -c "import docker; client = docker.DockerClient(base_url='unix:///var/run/docker.sock'); print(client.version())"
```

## For Custom Implementations

If you're building a custom implementation, ensure your code:

1. Uses Docker SDK 7.1.0 or higher
2. Always initializes the Docker client with the triple-slash format
3. Sets the DOCKER_HOST environment variable correctly
4. Includes proper exception handling for Docker connection issues

For more information, see the [full documentation](DOCUMENTATION.md).