#!/usr/bin/env python3
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

def exec_command(container_id, command):
    """Execute a command in a container - always run through bash -c"""
    url = f"http://localhost:5000/api/containers/{container_id}/exec"
    headers = {"Content-Type": "application/json"}
    
    # Always send commands in the form that works with shell builtins
    wrapped_command = f"/bin/bash -c '{command}'"
    data = {"command": wrapped_command}
    
    try:
        print(f"\n===== Testing: {command} =====")
        print(f"Sending as: {wrapped_command}")
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

def main():
    # Get container list
    print("Fetching container list...")
    containers = list_containers()
    
    if not containers:
        print("No containers found!")
        return
    
    # Use the first container
    container = containers[0]
    container_id = container['id']
    print(f"Using container: {container['name']} (ID: {container_id})")
    
    # Test commands that use shell builtins
    test_cases = [
        "pwd",                         # Simple command
        "cd ~ && pwd",                 # Shell builtin with follow-up command
        "cd /etc && ls | grep host",   # Shell builtin with pipe
        "echo $HOME",                  # Environment variable expansion
        "for i in 1 2 3; do echo $i; done",  # Loop
        "mkdir -p /tmp/test && cd /tmp/test && touch file.txt && ls -la"  # Multiple commands
    ]
    
    for cmd in test_cases:
        exec_command(container_id, cmd)

if __name__ == "__main__":
    main()