#!/usr/bin/env python3
import requests
import json
import sys

def force_refresh():
    """Force a refresh of containers tracking via API"""
    url = "http://localhost:5000/api/containers/refresh"
    headers = {"Content-Type": "application/json"}
    
    try:
        print(f"Forcing refresh via API: {url}")
        # Try GET method
        response = requests.get(url, headers=headers)
        print(f"Refresh response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Refresh message: {result.get('message')}")
            print(f"Containers now tracked: {len(result.get('containers', []))}")
            
            # Show container details
            for container in result.get('containers', []):
                print(f"  - {container.get('name')} (ID: {container.get('id')})")
                
            return True
        else:
            print(f"Refresh failed: {response.text}")
            return False
    except Exception as e:
        print(f"Request failed: {str(e)}")
        return False

def list_containers():
    """Get list of active containers from the API"""
    url = "http://localhost:5000/api/containers"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            containers = response.json()
            print(f"API reports {len(containers)} containers:")
            for container in containers:
                print(f"  - {container.get('name')} (ID: {container.get('id')}, Status: {container.get('status')})")
            return containers
        else:
            print(f"Error listing containers: {response.text}")
            return []
    except Exception as e:
        print(f"Request failed: {str(e)}")
        return []

if __name__ == "__main__":
    print("Forcing refresh of container tracking...")
    if force_refresh():
        print("\nChecking containers after refresh:")
        containers = list_containers()
        
        if containers:
            container_id = containers[0]['id']
            print(f"\nYou can test with: python3 test_cd_cases.py {container_id}")
        else:
            print("\nNo containers found after refresh.")
    else:
        print("Failed to refresh container tracking.")