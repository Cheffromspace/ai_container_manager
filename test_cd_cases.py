#!/usr/bin/env python3
"""
Debug utility to test API container exec functionality
Specifically designed to troubleshoot the 'cd' command issue
"""
import requests
import json
import sys

def list_containers():
    """Get list of active containers from the API"""
    url = "http://localhost:5000/api/containers"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error listing containers: {response.text}")
            return []
    except Exception as e:
        print(f"Request failed: {str(e)}")
        return []

def test_cd_commands(container_id):
    """Test different variations of the cd command"""
    test_cases = [
        # Basic cd command
        "cd",
        # cd with common paths
        "cd /",
        "cd /tmp",
        "cd ~",
        # cd with relative paths
        "cd ..",
        "cd ../",
        # cd with complex commands
        "cd && pwd",
        "cd ~ && pwd",
        "/bin/bash -c 'cd && pwd'",
        "/bin/bash -c 'cd /tmp && pwd'",
        # cd with absolute path (no space)
        "cd/etc",
        "cd/tmp",
        # cd with home path (no space)
        "cd~",
        # Alternative approach
        "bash -c 'cd /tmp && pwd'"
    ]
    
    for cmd in test_cases:
        url = f"http://localhost:5000/api/containers/{container_id}/exec"
        headers = {"Content-Type": "application/json"}
        data = {"command": cmd}
        
        try:
            print(f"\n===== Testing: {cmd} =====")
            response = requests.post(url, headers=headers, json=data)
            print(f"Status code: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"Exit code: {result.get('exit_code')}")
                print(f"Output:\n{result.get('output')}")
            else:
                print(f"Error: {response.text}")
        except Exception as e:
            print(f"Request failed: {str(e)}")

if __name__ == "__main__":
    # Get container list
    containers = list_containers()
    
    if not containers:
        print("No containers found!")
        sys.exit(1)
    
    # Use specified container or the first one
    container_id = None
    if len(sys.argv) > 1:
        container_id = sys.argv[1]
    else:
        container_id = containers[0]['id']
        print(f"Using first container: {containers[0]['name']} (ID: {container_id})")
    
    # Test cd commands
    test_cd_commands(container_id)