#!/bin/bash
# This script completely replaces the exec_command function in the container manager
# to ensure all commands are always executed using bash -c

set -e

# Create a temporary file for the patched content
TEMP_FILE=$(mktemp)

echo "Copying app.py from the container..."
docker cp ai-container-manager:/app/app.py $TEMP_FILE

echo "Backing up original app.py..."
cp $TEMP_FILE ${TEMP_FILE}.bak

echo "Creating the fixed version of the exec_command function..."
cat > ${TEMP_FILE}.new << 'EOL'
@app.route('/api/containers/<container_id>/exec', methods=['POST'])
@app.route('/api/containers/exec/<container_id>', methods=['POST'])  # Added alternative endpoint
def exec_command(container_id):
    """Execute a command in a container"""
    if container_id not in active_containers:
        # Log detailed information about the missing container
        logger.error(f"Container ID {container_id} not found in active_containers")
        logger.info(f"Available container IDs: {list(active_containers.keys())}")
        return jsonify({'error': 'Container not found'}), 404
    
    data = request.json
    command = data.get('command')
    
    if not command:
        return jsonify({'error': 'Command is required'}), 400
    
    try:
        # Get container
        container_info = active_containers[container_id]
        container = container_info['container_obj']
        
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
                output += stdout.decode('utf-8', errors='replace')
            if stderr:
                stderr_text = stderr.decode('utf-8', errors='replace')
                if stderr_text.strip():  # Only add if not empty
                    output += f"\nSTDERR: {stderr_text}"
        else:
            # Combined output
            if exec_result.output:
                output = exec_result.output.decode('utf-8', errors='replace')
        
        # Log the result for debugging
        logger.info(f"Command execution result: exit_code={exit_code}, output_length={len(output)}")
        
        return jsonify({
            'exit_code': exit_code,
            'output': output
        })
    
    except Exception as e:
        logger.error(f"Failed to execute command in container {container_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500
EOL

echo "Replacing the exec_command function in app.py..."
# Use awk to find and replace the function
awk 'BEGIN {
    replacing = 0
    replaced = 0
}

/^@app\.route\(\'\/api\/containers\/<container_id>\/exec\'/ {
    if (!replaced) {
        # Start of the function found, begin replacing
        replacing = 1
        # Include the content from our new file
        system("cat " ENVIRON["TEMP_FILE"] ".new")
        replaced = 1
    }
}

# If currently replacing, skip lines until we find the end of the function
# (defined as a line with just a blank line followed by @app.route or def)
{
    if (!replacing) {
        print
    } else if (NF == 0) {
        # Empty line, check if next non-empty line starts a new route or function
        replacing = 0
        print
    }
}' ${TEMP_FILE} > ${TEMP_FILE}.patched

echo "Copying patched app.py back to the container..."
docker cp ${TEMP_FILE}.patched ai-container-manager:/app/app.py

echo "Restarting container manager..."
docker restart ai-container-manager

echo "Cleaning up temporary files..."
rm -f ${TEMP_FILE} ${TEMP_FILE}.new ${TEMP_FILE}.patched ${TEMP_FILE}.bak

echo "Patch applied successfully!"
echo "All commands will now be executed using /bin/bash -c, ensuring shell builtins like 'cd' work properly."
echo "Please wait a few seconds for the container manager to restart, then test your commands again."