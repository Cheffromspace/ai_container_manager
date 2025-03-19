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
        print(f"Restarting container {container_id}...")
        response = requests.post(url, headers=headers)
        if response.status_code == 200:
            result = response.json()
            print(f"Success! Container {container_id} restarted.")
            print(f"Status changed from '{result.get('previous_status')}' to '{result.get('current_status')}'")
            return True
        else:
            print(f"Error: {response.text}")
            return False
    except Exception as e:
        print(f"Request failed: {str(e)}")
        return False

def restart_all_containers():
    """Restart all containers"""
    containers = list_containers()
    
    if not containers:
        print("No containers found to restart.")
        return False
    
    success_count = 0
    fail_count = 0
    
    for container in containers:
        container_id = container.get('id')
        container_name = container.get('name')
        status = container.get('status')
        
        print(f"\nRestarting container: {container_name} (ID: {container_id}, Status: {status})")
        if restart_container(container_id):
            success_count += 1
        else:
            fail_count += 1
    
    print(f"\nRestart summary: {success_count} containers restarted successfully, {fail_count} failed.")
    return success_count > 0

if __name__ == "__main__":
    # Check if container ID was provided
    if len(sys.argv) > 1:
        # Get container ID from command line
        container_id = sys.argv[1]
        restart_container(container_id)
    else:
        # Show list of containers and let user choose
        containers = list_containers()
        
        if not containers:
            print("No containers found. Exiting.")
            sys.exit(1)
        
        print(f"Found {len(containers)} active containers:")
        for idx, container in enumerate(containers):
            print(f"{idx+1}. {container.get('name')} (ID: {container.get('id')}, Status: {container.get('status')})")
        
        print("\nOptions:")
        print("  [number] - Restart specific container by number")
        print("  all      - Restart all containers")
        print("  q        - Quit")
        
        choice = input("\nEnter your choice: ")
        
        if choice.lower() == 'q':
            print("Exiting.")
            sys.exit(0)
        elif choice.lower() == 'all':
            restart_all_containers()
        else:
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(containers):
                    container = containers[idx]
                    restart_container(container.get('id'))
                else:
                    print("Invalid container number. Exiting.")
            except ValueError:
                print("Invalid input. Exiting.")