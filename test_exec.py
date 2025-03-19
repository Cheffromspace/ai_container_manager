#!/usr/bin/env python3
import requests
import json
import sys

def test_exec_command(container_id, command):
    """Test executing a command in a container using the API endpoint"""
    # Make sure we're using the full container ID, not just the short version
    url = f"http://localhost:5000/api/containers"
    
    try:
        # First get the list of containers to find the full ID
        response = requests.get(url)
        if response.status_code == 200:
            containers = response.json()
            full_id = None
            
            # Check if any container has a matching ID or name containing the ID
            for container in containers:
                if container['id'] == container_id or container_id in container.get('name', ''):
                    full_id = container['id']
                    break
                    
            if not full_id:
                print(f"\nContainer with ID {container_id} not found")
                return
                
            # Now execute the command
            exec_url = f"http://localhost:5000/api/containers/{full_id}/exec"
            headers = {"Content-Type": "application/json"}
            data = {"command": command}
            
            response = requests.post(exec_url, headers=headers, json=data)
            print(f"\n===== Command: {command} =====")
            print(f"Status code: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"Exit code: {result.get('exit_code')}")
                print(f"Output:\n{result.get('output')}")
            else:
                print(f"Error: {response.text}")
        else:
            print(f"Failed to get container list: {response.text}")
    except Exception as e:
        print(f"Request failed: {str(e)}")

if __name__ == "__main__":
    # First, try to get all running containers
    print("Checking for running ai-containers...")
    try:
        container_name = None
        # Use the docker command-line to get container info
        import subprocess
        process = subprocess.run(['docker', 'ps', '--format', '{{.Names}}'], 
                                capture_output=True, text=True)
        
        for line in process.stdout.splitlines():
            if line.startswith('ai-container-') and line != 'ai-container-manager':
                container_name = line
                container_id = container_name.split('-')[-1]
                print(f"Found container: {container_name} with ID: {container_id}")
                break
        
        if not container_name:
            print("No ai-container found.")
            container_id = "996031f5"  # Fallback
    except Exception as e:
        print(f"Error getting container list: {e}")
        container_id = "996031f5"  # Fallback
    
    if len(sys.argv) > 1:
        container_id = sys.argv[1]
    
    # Test different commands
    test_exec_command(container_id, "pwd")
    # Now 'cd' should work with our updated API
    test_exec_command(container_id, "cd ~ && pwd")
    test_exec_command(container_id, "cd /etc && ls -la")
    test_exec_command(container_id, "ls -la")
    test_exec_command(container_id, "echo 'Hello from container!'")