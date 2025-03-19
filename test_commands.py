#!/usr/bin/env python3
import requests
import json
import sys
import time

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

def test_commands():
    """Test a series of shell builtin commands to diagnose container exec issues"""
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
    
    # Test different types of shell commands to see how they're handled
    test_cases = [
        "pwd",                                   # Simple command
        "ls -la",                                # Simple command with args
        "cd ~",                                  # Shell builtin alone
        "cd ~ && pwd",                           # Shell builtin with follow-up
        "cd /etc && ls -la",                     # Shell builtin with follow-up
        "echo $HOME",                            # Environment variable
        "for i in 1 2 3; do echo $i; done",      # Complex shell syntax
        "if [ -d /etc ]; then echo exists; fi",  # If statement
        "mkdir -p /tmp/test/nested && echo created", # Create nested directory
        "cd /tmp/test/nested && pwd && touch testfile && ls" # Change dir and create file
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
                
            # Add a small delay between requests
            time.sleep(0.5)
        except Exception as e:
            print(f"Request failed: {str(e)}")

if __name__ == "__main__":
    test_commands()