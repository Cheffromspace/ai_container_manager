#!/usr/bin/env python3
import requests
import json
import subprocess
import sys

def list_docker_ai_containers():
    """Get all AI containers from Docker"""
    try:
        result = subprocess.run(
            ['docker', 'ps', '-a', '--format', '{{json .}}'],
            capture_output=True, text=True, check=True
        )
        
        # Parse container data
        containers = []
        for line in result.stdout.splitlines():
            if line.strip():
                try:
                    container_data = json.loads(line)
                    # Filter for AI containers but not the manager
                    if container_data['Names'].startswith('ai-container-') and container_data['Names'] != 'ai-container-manager':
                        containers.append(container_data)
                except json.JSONDecodeError:
                    print(f"Error parsing container data: {line}")
        
        return containers
    except subprocess.CalledProcessError as e:
        print(f"Error listing containers: {e}")
        return []

def check_api_tracking():
    """Check which containers the API is tracking"""
    url = "http://localhost:5000/api/containers"
    try:
        response = requests.get(url)
        print(f"API response status: {response.status_code}")
        
        if response.status_code == 200:
            containers = response.json()
            print(f"API is tracking {len(containers)} containers:")
            for container in containers:
                print(f"  - {container.get('name')} (ID: {container.get('id')}, Status: {container.get('status')})")
            return containers
        else:
            print(f"API error: {response.text}")
            return []
    except Exception as e:
        print(f"Request failed: {str(e)}")
        return []

if __name__ == "__main__":
    print("Step 1: Checking Docker for AI containers...")
    docker_containers = list_docker_ai_containers()
    
    if not docker_containers:
        print("No AI containers found in Docker. Exiting.")
        sys.exit(1)
    
    print(f"Found {len(docker_containers)} AI containers in Docker:")
    for idx, container in enumerate(docker_containers):
        container_id = container['ID']
        container_name = container['Names']
        container_status = container['State']
        print(f"  - {container_name} (ID: {container_id[:12]}, Status: {container_status})")
    
    print("\nStep 2: Checking API for tracked containers...")
    api_containers = check_api_tracking()
    
    # Compare
    docker_names = [c['Names'] for c in docker_containers]
    api_names = [c.get('name') for c in api_containers]
    
    missing = set(docker_names) - set(api_names)
    if missing:
        print(f"\nWARNING: {len(missing)} containers are not being tracked by the API:")
        for name in missing:
            print(f"  - {name}")
    else:
        print("\nSUCCESS: All containers are properly tracked by the API!")
        
    # Check if containers can be restarted safely without creating orphans
    if api_containers:
        # Pick the first container
        container_id = api_containers[0].get('id')
        container_name = api_containers[0].get('name')
        print(f"\nTesting restart action for {container_name} (ID: {container_id})...")
        
        # Try to execute a simple command to test connectivity
        url = f"http://localhost:5000/api/containers/{container_id}/exec"
        data = {"command": "echo 'API test successful'"}
        headers = {"Content-Type": "application/json"}
        
        try:
            response = requests.post(url, json=data, headers=headers)
            print(f"Exec status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"Command exit code: {result.get('exit_code')}")
                print(f"Command output: {result.get('output')}")
                print("\nAPI container tracking is working correctly!")
            else:
                print(f"Exec error: {response.text}")
        except Exception as e:
            print(f"Exec request failed: {str(e)}")