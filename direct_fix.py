#!/usr/bin/env python3
"""
Direct fix for the container command execution issue
This script uses the Docker API directly to execute commands
"""
import docker
import sys

def exec_command(container_id, command):
    """Execute a command directly using Docker API, always with bash -c"""
    try:
        # Connect to Docker API
        client = docker.from_env()
        
        # Get the container by ID or name
        container = client.containers.get(container_id)
        print(f"Container found: {container.name}")
        
        # Always use bash -c to execute commands
        print(f"\nExecuting command: {command}")
        exec_result = container.exec_run(
            ["/bin/bash", "-c", command],
            demux=True,
            tty=True
        )
        
        # Process the result
        exit_code = exec_result.exit_code
        print(f"Exit code: {exit_code}")
        
        # Handle output
        if isinstance(exec_result.output, tuple) and len(exec_result.output) == 2:
            stdout, stderr = exec_result.output
            output = ""
            
            if stdout:
                output += stdout.decode('utf-8', errors='replace')
            if stderr:
                stderr_text = stderr.decode('utf-8', errors='replace')
                if stderr_text.strip():
                    output += f"\nSTDERR: {stderr_text}"
                    
            print(f"Output:\n{output}")
            return exit_code, output
        else:
            output = exec_result.output.decode('utf-8', errors='replace') if exec_result.output else ""
            print(f"Output:\n{output}")
            return exit_code, output
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1, str(e)

if __name__ == "__main__":
    # Get container ID/name from command line or find from docker ps
    if len(sys.argv) > 1:
        container_id = sys.argv[1]
    else:
        # Try to find an AI container
        client = docker.from_env()
        containers = client.containers.list(filters={"name": "ai-container-"})
        if not containers or len(containers) == 0:
            print("No AI containers found. Please specify container ID/name as argument.")
            sys.exit(1)
        
        # Skip manager container
        container = None
        for c in containers:
            if c.name != "ai-container-manager":
                container = c
                break
        
        if not container:
            print("No suitable AI container found.")
            sys.exit(1)
            
        container_id = container.id
        print(f"Using container: {container.name} (ID: {container_id[:12]})")
    
    # Test various cd commands
    test_cases = [
        "cd",
        "cd /",
        "cd /tmp",
        "cd ~",
        "cd..",
        "cd/etc",
        "cd~",
        "cd && pwd",
        "cd ~ && pwd"
    ]
    
    for cmd in test_cases:
        print(f"\n===== Testing: {cmd} =====")
        exec_command(container_id, cmd)