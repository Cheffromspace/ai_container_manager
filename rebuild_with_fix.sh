#!/bin/bash
# This script creates a fixed version of the container manager by:
# 1. Creating a new temporary Dockerfile
# 2. Building a new image based on the original but with our fix applied
# 3. Stopping and removing the old container
# 4. Starting a new container with the fixed image

set -e

echo "Creating temporary Dockerfile for the fixed image..."
cat > Dockerfile.fixed << 'EOL'
FROM n8n-ai-container-manager:latest

# Create a temporary file with our fixed version of exec_command
RUN echo '@app.route("/api/containers/<container_id>/exec", methods=["POST"])
@app.route("/api/containers/exec/<container_id>", methods=["POST"])  # Added alternative endpoint
def exec_command(container_id):
    """Execute a command in a container"""
    if container_id not in active_containers:
        # Log detailed information about the missing container
        logger.error(f"Container ID {container_id} not found in active_containers")
        logger.info(f"Available container IDs: {list(active_containers.keys())}")
        return jsonify({"error": "Container not found"}), 404
    
    data = request.json
    command = data.get("command")
    
    if not command:
        return jsonify({"error": "Command is required"}), 400
    
    try:
        # Get container
        container_info = active_containers[container_id]
        container = container_info["container_obj"]
        
        # ALWAYS use bash -c for ALL commands to ensure shell builtins work
        logger.info(f"Executing command with bash -c: {command}")
        exec_result = container.exec_run(
            ["/bin/bash", "-c", command],
            demux=True,  # Split stdout and stderr 
            tty=True     # Use a TTY for interactive commands
        )
        
        # Process the output
        exit_code = exec_result.exit_code
        output = ""
        
        # Handle output differently based on whether demux worked
        if isinstance(exec_result.output, tuple) and len(exec_result.output) == 2:
            # We have separate stdout and stderr
            stdout, stderr = exec_result.output
            
            if stdout:
                output += stdout.decode("utf-8", errors="replace")
            if stderr:
                stderr_text = stderr.decode("utf-8", errors="replace")
                if stderr_text.strip():  # Only add if not empty
                    output += f"\nSTDERR: {stderr_text}"
        else:
            # Combined output
            if exec_result.output:
                output = exec_result.output.decode("utf-8", errors="replace")
        
        # Log the result for debugging
        logger.info(f"Command execution result: exit_code={exit_code}, output_length={len(output)}")
        
        return jsonify({
            "exit_code": exit_code,
            "output": output
        })
    
    except Exception as e:
        logger.error(f"Failed to execute command in container {container_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500' > /tmp/fixed_function.py

# Find and replace the exec_command function with our fixed version
RUN sed -i -e '/^@app\.route.*\/exec.*, methods.*$/,/^@app\.route\|^def [^e]/!b;//!d;r /tmp/fixed_function.py' /app/app.py
EOL

echo "Building fixed container manager image..."
docker build -t n8n-ai-container-manager:fixed -f Dockerfile.fixed .

echo "Getting current container settings..."
CURRENT_PORT=$(docker port ai-container-manager | grep 5000 | awk -F':' '{print $2}')
CURRENT_NETWORKS=$(docker inspect ai-container-manager -f '{{range $net, $conf := .NetworkSettings.Networks}}{{$net}} {{end}}')

echo "Stopping and removing current container manager..."
docker stop ai-container-manager
docker rm ai-container-manager

echo "Starting new container manager with fixed image..."
docker run -d --name ai-container-manager \
  -p ${CURRENT_PORT:-5000}:5000 \
  --restart unless-stopped \
  n8n-ai-container-manager:fixed

# Reconnect to the same networks
for NETWORK in $CURRENT_NETWORKS; do
  echo "Connecting to network: $NETWORK"
  docker network connect $NETWORK ai-container-manager
done

echo "Waiting for container to start..."
sleep 5

echo "Fixed container manager is now running!"
echo "The fix ensures all commands are executed using /bin/bash -c,"
echo "which should resolve the issue with 'cd' and other shell builtins."
echo ""
echo "Test using: python3 test_specific_endpoint.py YOUR_CONTAINER_ID 'cd && pwd'"