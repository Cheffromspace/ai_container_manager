#!/usr/bin/env python3
import requests
import json
import sys

def create_container():
    """Create a new AI container via API"""
    url = "http://localhost:5000/api/containers"
    headers = {"Content-Type": "application/json"}
    
    try:
        print(f"Creating new container via API: {url}")
        response = requests.post(url, headers=headers)
        print(f"Create response status: {response.status_code}")
        
        if response.status_code == 201:
            container = response.json()
            print(f"Container created successfully:")
            print(f"  ID: {container.get('id')}")
            print(f"  Name: {container.get('name')}")
            print(f"  Status: {container.get('status')}")
            print(f"  SSH Port: {container.get('ssh_port')}")
            print(f"  SSH Command: {container.get('ssh_command')}")
            return container.get('id')
        else:
            print(f"Container creation failed: {response.text}")
            return None
    except Exception as e:
        print(f"Request failed: {str(e)}")
        return None

if __name__ == "__main__":
    print("Creating a new AI container...")
    container_id = create_container()
    
    if container_id:
        print(f"\nNew container created with ID: {container_id}")
        print(f"You can now use this container for testing with: python3 test_cd_cases.py {container_id}")
    else:
        print("\nFailed to create container. Check if the API is running properly.")
        sys.exit(1)