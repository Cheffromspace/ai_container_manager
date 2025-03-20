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

def restart_container(container_id):
    """Restart a container by ID"""
    url = f"http://localhost:5000/api/containers/{container_id}/restart"
    headers = {"Content-Type": "application/json"}
    
    try:
        print(f"\nRestarting container {container_id}...")
        response = requests.post(url, headers=headers)
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Request failed: {str(e)}")
        return False

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
    
    if not containers:
        print("No containers found. Exiting.")
        sys.exit(1)
    
    print(f"Found {len(containers)} active containers:")
    for idx, container in enumerate(containers):
        print(f"{idx+1}. ID: {container.get('id')} - Name: {container.get('name')} - Status: {container.get('status')}")
        
    if containers:
        # Get the first container
        first_container = containers[0]
        container_id = first_container.get('id')
        
        # Test execing a command
        print(f"\nTesting exec on first container (ID: {container_id})...")
        test_container_exec(container_id, "echo 'Hello before restart!'")
        
        # Try restarting it
        if restart_container(container_id):
            print("\nWaiting 5 seconds for restart to complete...")
            time.sleep(5)
            
            # List containers again to see new status
            print("\nListing containers after restart...")
            new_containers = list_containers()
            for idx, container in enumerate(new_containers):
                if container.get('id') == container_id:
                    print(f"Container {container_id} new status: {container.get('status')}")
            
            # Test exec again
            test_container_exec(container_id, "echo 'Hello after restart!'")
        else:
            print("Failed to restart container. Check the logs for details.")