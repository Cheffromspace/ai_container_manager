#!/usr/bin/env python3
"""
Test directly using Docker API without going through the container manager API
"""
import subprocess
import sys
import json

def run_docker_exec(container_id, command):
    """Execute a command in a Docker container using docker exec"""
    try:
        # Always use bash -c to ensure shell builtins work
        full_command = ["docker", "exec", container_id, "/bin/bash", "-c", command]
        print(f"Running: {' '.join(full_command)}")
        
        result = subprocess.run(
            full_command,
            capture_output=True,
            text=True
        )
        
        print(f"Exit code: {result.returncode}")
        if result.stdout:
            print(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            print(f"STDERR:\n{result.stderr}")
            
        return result.returncode == 0
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

def test_cd_commands(container_id):
    """Test various cd commands"""
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
        run_docker_exec(container_id, cmd)

if __name__ == "__main__":
    # Get container ID from command line or find first AI container
    if len(sys.argv) > 1:
        container_id = sys.argv[1]
    else:
        # Get list of running containers
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Look for ai-container- (not the manager)
        container_id = None
        for line in result.stdout.splitlines():
            if line.startswith('ai-container-') and line != 'ai-container-manager':
                container_id = line
                break
        
        if not container_id:
            print("No AI container found. Specify container ID/name as argument.")
            sys.exit(1)
    
    print(f"Using container: {container_id}")
    test_cd_commands(container_id)