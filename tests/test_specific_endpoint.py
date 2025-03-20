#!/usr/bin/env python3
import requests
import json
import sys

def test_specific_endpoint(container_id, command):
    """Test a specific container exec endpoint with the given command"""
    url = f"http://localhost:5000/api/containers/{container_id}/exec"
    headers = {"Content-Type": "application/json"}
    data = {"command": command}
    
    print(f"Testing endpoint: {url}")
    print(f"Command: {command}")
    
    try:
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
    if len(sys.argv) < 2:
        print("Usage: python3 test_specific_endpoint.py CONTAINER_ID [COMMAND]")
        print("Example: python3 test_specific_endpoint.py afd82a8d-4b19-4138-8944-76b618e471d2 'cd && pwd'")
        sys.exit(1)
    
    container_id = sys.argv[1]
    command = sys.argv[2] if len(sys.argv) > 2 else "cd && pwd"
    
    test_specific_endpoint(container_id, command)