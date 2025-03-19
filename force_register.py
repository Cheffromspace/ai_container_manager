#!/usr/bin/env python3
import subprocess
import json
import requests
import time
import sys

def get_docker_containers():
    """Get all AI containers directly from Docker"""
    try:
        # Run docker ps command to get container information in JSON format
        result = subprocess.run(
            ['docker', 'ps', '--format', '{{json .}}'],
            capture_output=True, text=True, check=True
        )
        
        # Parse the output
        containers = []
        for line in result.stdout.splitlines():
            try:
                container_data = json.loads(line)
                # Only include containers with ai-container- prefix and exclude the manager
                if container_data['Names'].startswith('ai-container-') and container_data['Names'] != 'ai-container-manager':
                    containers.append(container_data)
            except json.JSONDecodeError:
                print(f"Error parsing container data: {line}")
        
        return containers
    except subprocess.CalledProcessError as e:
        print(f"Error running docker ps: {e}")
        return []

def get_container_details(container_id):
    """Get detailed information about a container using docker inspect"""
    try:
        result = subprocess.run(
            ['docker', 'inspect', container_id],
            capture_output=True, text=True, check=True
        )
        
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error inspecting container {container_id}: {e}")
        return []
    except json.JSONDecodeError as e:
        print(f"Error parsing inspect output for {container_id}: {e}")
        return []

def force_post_refresh():
    """Force a POST refresh of container tracking"""
    url = "http://localhost:5000/api/containers/refresh"
    headers = {"Content-Type": "application/json"}
    
    try:
        print(f"Sending POST request to refresh endpoint: {url}")
        response = requests.post(url, headers=headers)
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Success! {result.get('message')}")
            return True
        else:
            print(f"Error: {response.text}")
            return False
    except Exception as e:
        print(f"Request failed: {str(e)}")
        return False

def restart_container_service():
    """Restart the container manager service"""
    try:
        print("Attempting to restart the AI container manager...")
        result = subprocess.run(
            ['docker', 'restart', 'ai-container-manager'],
            capture_output=True, text=True, check=True
        )
        print(result.stdout)
        print("Waiting for service to become available...")
        time.sleep(10)  # Wait for service to restart
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error restarting container: {e}")
        return False

def check_api_tracking():
    """Check which containers are being tracked by the API"""
    url = "http://localhost:5000/api/containers"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            containers = response.json()
            print(f"API is currently tracking {len(containers)} containers:")
            for container in containers:
                print(f"  - {container.get('name')} (ID: {container.get('id')}, Status: {container.get('status')}")
            return containers
        else:
            print(f"API error: {response.text}")
            return []
    except Exception as e:
        print(f"Error querying API: {str(e)}")
        return []

if __name__ == "__main__":
    print("Step 1: Finding AI containers in Docker")
    docker_containers = get_docker_containers()
    
    if not docker_containers:
        print("No AI containers found in Docker. Exiting.")
        sys.exit(1)
        
    print(f"Found {len(docker_containers)} AI containers in Docker:")
    for container in docker_containers:
        print(f"  - {container['Names']} (ID: {container['ID']}, Status: {container['State']})")
    
    print("\nStep 2: Checking current API tracking")
    tracked_containers = check_api_tracking()
    
    print("\nStep 3: Forcing a refresh with POST request")
    if not force_post_refresh():
        print("\nStep 4: API refresh failed, attempting to restart container manager")
        if restart_container_service():
            print("\nStep 5: Container manager restarted, forcing refresh again")
            force_post_refresh()
        else:
            print("Failed to restart container manager.")
    
    print("\nStep 6: Checking API tracking after refresh")
    new_tracked = check_api_tracking()
    
    if len(new_tracked) == len(docker_containers):
        print("\nSUCCESS: All containers are now being tracked!")
    else:
        print(f"\nWARNING: Only {len(new_tracked)}/{len(docker_containers)} containers are being tracked.")