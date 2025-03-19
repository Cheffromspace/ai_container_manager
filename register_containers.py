#!/usr/bin/env python3
import requests
import json
import subprocess
import sys
import time

def get_docker_containers():
    """Get all running Docker containers with ai-container prefix"""
    try:
        # Run docker ps command to get container information
        result = subprocess.run(
            ['docker', 'ps', '--format', '{{.Names}}'],
            capture_output=True, text=True, check=True
        )
        
        # Parse the output
        containers = []
        for line in result.stdout.splitlines():
            if line.startswith('ai-container-') and line != 'ai-container-manager':
                containers.append(line)
        
        return containers
    except subprocess.CalledProcessError as e:
        print(f"Error running docker ps: {e}")
        return []

def refresh_container_tracking():
    """Trigger container tracking refresh via API"""
    url = "http://localhost:5000/api/containers/refresh"
    headers = {"Content-Type": "application/json"}
    
    try:
        # Use POST method as specified in the app.py route
        response = requests.post(url, headers=headers)
        print(f"Refresh API response: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Refresh result: {result['message']}")
            print(f"Tracked containers: {len(result['containers'])}")
            return True
        else:
            print(f"Refresh failed: {response.text}")
            return False
    except Exception as e:
        print(f"Failed to call refresh API: {str(e)}")
        return False

def check_tracked_containers():
    """Check which containers are currently being tracked by the API"""
    url = "http://localhost:5000/api/containers"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            containers = response.json()
            print(f"API is tracking {len(containers)} containers:")
            for container in containers:
                print(f"  - {container.get('name', 'unknown')} (ID: {container.get('id', 'unknown')})")
            return containers
        else:
            print(f"Failed to get tracked containers: {response.text}")
            return []
    except Exception as e:
        print(f"Error checking tracked containers: {str(e)}")
        return []

if __name__ == "__main__":
    print("Checking Docker for AI containers...")
    docker_containers = get_docker_containers()
    
    if not docker_containers:
        print("No AI containers found in Docker.")
        sys.exit(1)
    
    print(f"Found {len(docker_containers)} AI containers in Docker:")
    for container in docker_containers:
        print(f"  - {container}")
    
    print("\nRefreshing container tracking with the API...")
    if refresh_container_tracking():
        print("\nWaiting for API to update...")
        time.sleep(2)  # Wait a moment for the API to update
        
        print("\nChecking which containers are now tracked by the API:")
        tracked_containers = check_tracked_containers()
        
        # Verify all Docker containers are now tracked
        docker_short_ids = [container.split('-')[-1] for container in docker_containers]
        tracked_ids = [container.get('id') for container in tracked_containers]
        
        missing = set(docker_short_ids) - set(tracked_ids)
        if missing:
            print(f"\nWARNING: {len(missing)} containers are not being tracked by the API:")
            for missing_id in missing:
                print(f"  - Container with ID ending in {missing_id}")
        else:
            print("\nSUCCESS: All AI containers are properly tracked by the API.")
    else:
        print("Failed to register containers with the API.")