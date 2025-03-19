#!/usr/bin/env python3
import subprocess
import docker
import time
import sys
import json

def restart_container(container_id):
    """Restart a container directly using Docker API"""
    try:
        print(f"Attempting to restart container {container_id}...")
        client = docker.from_env()
        container = client.containers.get(container_id)
        container.restart(timeout=10)
        print(f"Container {container.name} restarted successfully!")
        return True
    except Exception as e:
        print(f"Error restarting container: {e}")
        return False

def list_all_ai_containers():
    """List all AI containers using Docker API"""
    try:
        client = docker.from_env()
        all_containers = client.containers.list(all=True, filters={"name": "ai-container-"})
        
        # Filter out the manager container
        containers = [c for c in all_containers if c.name != "ai-container-manager"]
        
        return containers
    except Exception as e:
        print(f"Error listing containers: {e}")
        return []

def restart_container_by_name(container_name):
    """Restart a container by its name"""
    try:
        client = docker.from_env()
        container = client.containers.get(container_name)
        old_status = container.status
        print(f"Container {container_name} current status: {old_status}")
        
        if old_status != "running":
            print(f"Starting container {container_name}...")
            container.start()
        else:
            print(f"Restarting container {container_name}...")
            container.restart(timeout=10)
            
        # Wait for container to settle
        time.sleep(3)
        container.reload()
        print(f"Container {container_name} new status: {container.status}")
        return True
    except Exception as e:
        print(f"Error with container {container_name}: {e}")
        return False

if __name__ == "__main__":
    print("Listing all AI containers...")
    containers = list_all_ai_containers()
    
    if not containers:
        print("No AI containers found. Exiting.")
        sys.exit(1)
    
    print(f"Found {len(containers)} AI containers:")
    for idx, container in enumerate(containers):
        print(f"{idx+1}. {container.name} (ID: {container.id[:12]}, Status: {container.status})")
    
    print("\nOptions:")
    print("  [number] - Restart specific container by number")
    print("  all      - Restart all containers")
    print("  q        - Quit")
    
    choice = input("\nEnter your choice: ")
    
    if choice.lower() == 'q':
        print("Exiting.")
        sys.exit(0)
    elif choice.lower() == 'all':
        success_count = 0
        for container in containers:
            if restart_container_by_name(container.name):
                success_count += 1
        print(f"\nRestarted {success_count}/{len(containers)} containers successfully.")
    else:
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(containers):
                container = containers[idx]
                restart_container_by_name(container.name)
            else:
                print("Invalid container number. Exiting.")
        except ValueError:
            print("Invalid input. Exiting.")