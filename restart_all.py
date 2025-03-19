#!/usr/bin/env python3
import subprocess
import json
import time
import sys

def restart_container(container_id):
    """Restart a container using Docker CLI"""
    try:
        print(f"Attempting to restart container {container_id}...")
        result = subprocess.run(
            ['docker', 'restart', container_id],
            capture_output=True, text=True, check=True
        )
        print(result.stdout.strip())
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error restarting container: {e}")
        print(f"Error output: {e.stderr}")
        return False

def list_all_ai_containers():
    """List all AI containers using Docker CLI"""
    try:
        # Get all containers with detailed info
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
        print(f"Error output: {e.stderr}")
        return []

def get_container_status(container_id):
    """Get container status using Docker CLI"""
    try:
        result = subprocess.run(
            ['docker', 'inspect', '--format', '{{.State.Status}}', container_id],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error getting container status: {e}")
        print(f"Error output: {e.stderr}")
        return "unknown"

def start_container(container_id):
    """Start a container using Docker CLI"""
    try:
        print(f"Starting container {container_id}...")
        result = subprocess.run(
            ['docker', 'start', container_id],
            capture_output=True, text=True, check=True
        )
        print(result.stdout.strip())
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error starting container: {e}")
        print(f"Error output: {e.stderr}")
        return False

def restart_api_manager():
    """Restart the API manager container"""
    try:
        print("Restarting the AI container manager...")
        result = subprocess.run(
            ['docker', 'restart', 'ai-container-manager'],
            capture_output=True, text=True, check=True
        )
        print(result.stdout.strip())
        print("Waiting 10 seconds for API manager to start up...")
        time.sleep(10)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error restarting API manager: {e}")
        print(f"Error output: {e.stderr}")
        return False

if __name__ == "__main__":
    print("Listing all AI containers...")
    containers = list_all_ai_containers()
    
    if not containers:
        print("No AI containers found. Exiting.")
        sys.exit(1)
    
    print(f"Found {len(containers)} AI containers:")
    for idx, container in enumerate(containers):
        container_id = container['ID']
        container_name = container['Names']
        container_status = container['State']
        print(f"{idx+1}. {container_name} (ID: {container_id[:12]}, Status: {container_status})")
    
    # Auto-restart all containers
    print("\nAuto-restarting all containers...")
    success_count = 0
    for container in containers:
        container_id = container['ID']
        container_name = container['Names']
        container_status = container['State']
        
        print(f"\nProcessing {container_name} (current status: {container_status})")
        
        if container_status == "running":
            if restart_container(container_id):
                new_status = get_container_status(container_id)
                print(f"Container {container_name} restarted successfully! New status: {new_status}")
                success_count += 1
        else:
            if start_container(container_id):
                new_status = get_container_status(container_id)
                print(f"Container {container_name} started successfully! New status: {new_status}")
                success_count += 1
        
    print(f"\nProcessed {success_count}/{len(containers)} containers successfully.")
    
    # Finally, restart the API manager to re-track all containers
    print("\nRestarting the API manager to re-track all containers...")
    restart_api_manager()