#!/usr/bin/env python3
import requests
import json

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

def test_container_exec(container_id, command="echo 'Hello'"):
    """Test container exec with the given ID"""
    url = f"http://localhost:5000/api/containers/{container_id}/exec"
    data = {"command": command}
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(url, json=data, headers=headers)
        print(f"\nTesting exec on container {container_id} with command: {command}")
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Request failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("Fetching active containers...")
    containers = list_containers()
    
    print(f"Found {len(containers)} active containers:")
    for idx, container in enumerate(containers):
        print(f"{idx+1}. ID: {container.get('id')} - Name: {container.get('name')} - Status: {container.get('status')}")
        
    if containers:
        # Test exec on first container
        first_container = containers[0]
        container_id = first_container.get('id')
        
        print(f"\nTesting exec on first container (ID: {container_id})...")
        
        # Test simple echo command
        test_container_exec(container_id, "echo 'Hello from container!'")
        
        # Test cd command
        test_container_exec(container_id, "cd ~ && pwd")