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

def test_commands():
    """Test a series of commands to diagnose container exec issues"""
    # Get container list
    containers = list_containers()
    
    if not containers:
        print("No containers found!")
        return
    
    # Use the first container
    container = containers[0]
    container_id = container['id']
    print(f"Using container: {container['name']} (ID: {container_id})")
    
    # Test different command variations to see what works
    test_cases = [
        "echo $HOME",
        "/bin/bash -c 'echo $HOME'",
        "/bin/bash -c 'cd ~ && pwd'",
        "/bin/bash -c 'cd /etc && ls'",
        "ls -la /etc",
        "whoami"
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
    test_commands()