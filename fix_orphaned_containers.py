#!/usr/bin/env python3
"""
This script fixes orphaned containers by:
1. Getting all running AI containers from Docker
2. Manually removing and recreating them with the same configuration
   but under a new container ID to avoid leaving orphans
"""
import subprocess
import json
import sys
import time
import random
import uuid

def run_command(cmd, capture=True, check=True):
    """Run a command and return the output"""
    print(f"Running: {' '.join(cmd)}")
    try:
        if capture:
            result = subprocess.run(cmd, capture_output=True, text=True, check=check)
            return result.stdout
        else:
            subprocess.run(cmd, check=check)
            return None
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {e}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        return None

def get_ai_containers():
    """Get all AI containers from Docker"""
    output = run_command(['docker', 'ps', '-a', '--format', '{{json .}}'])
    if not output:
        return []
    
    containers = []
    for line in output.splitlines():
        if not line.strip():
            continue
        try:
            data = json.loads(line)
            if data['Names'].startswith('ai-container-') and data['Names'] != 'ai-container-manager':
                containers.append(data)
        except json.JSONDecodeError:
            print(f"Error parsing container data: {line}")
    
    return containers

def get_container_inspect(container_id):
    """Get detailed information about a container"""
    output = run_command(['docker', 'inspect', container_id])
    if not output:
        return None
    
    try:
        data = json.loads(output)
        if data and len(data) > 0:
            return data[0]
        return None
    except json.JSONDecodeError:
        print(f"Error parsing inspect output for {container_id}")
        return None

def recreate_container(container_id, container_name):
    """Recreate an AI container with the same configuration but new ID"""
    # Get container details
    print(f"Getting details for container {container_name}...")
    inspect_data = get_container_inspect(container_id)
    if not inspect_data:
        print(f"Failed to get details for {container_name}")
        return False
    
    # Extract key configuration
    try:
        # Get SSH port mapping
        port_bindings = inspect_data.get('HostConfig', {}).get('PortBindings', {})
        ssh_port = None
        for container_port, host_bindings in port_bindings.items():
            if container_port.startswith('22/'):
                if host_bindings and len(host_bindings) > 0:
                    ssh_port = host_bindings[0].get('HostPort')
                    break
        
        if not ssh_port:
            # Generate a random port between 12001 and 13000
            ssh_port = str(random.randint(12001, 13000))
            print(f"No SSH port found, using random port {ssh_port}")
        
        # Get volume mapping
        volume_name = None
        for mount in inspect_data.get('Mounts', []):
            if mount.get('Destination') == '/workspace':
                volume_name = mount.get('Name')
                break
        
        if not volume_name:
            # Create a new volume name based on a new container name
            new_container_id = str(uuid.uuid4())[:8]
            new_container_name = f"ai-container-{new_container_id}"
            volume_name = f"{new_container_name}-workspace"
            print(f"No volume found, using new volume {volume_name}")
        else:
            # Extract container ID from the volume name
            new_container_id = volume_name.replace('ai-container-', '').replace('-workspace', '')
            new_container_name = f"ai-container-{new_container_id}"
            print(f"Using existing volume {volume_name}")
        
        # Stop and remove the old container
        print(f"Stopping container {container_name}...")
        run_command(['docker', 'stop', container_id], capture=False)
        
        print(f"Removing container {container_name}...")
        run_command(['docker', 'rm', container_id], capture=False)
        
        # Create the new container
        print(f"Creating new container {new_container_name}...")
        create_cmd = [
            'docker', 'run', '-d',
            '--name', new_container_name,
            '-p', f"{ssh_port}:22/tcp",
            '-v', f"{volume_name}:/workspace:rw",
            '-e', f"CONTAINER_ID={new_container_id}",
            'ai-container-image:latest'
        ]
        
        output = run_command(create_cmd)
        if not output:
            print(f"Failed to create new container {new_container_name}")
            return False
        
        print(f"Successfully recreated container {container_name} as {new_container_name}")
        print(f"SSH port: {ssh_port}")
        return True
    
    except Exception as e:
        print(f"Error recreating container {container_name}: {e}")
        return False

def restart_api_manager():
    """Restart the API manager container"""
    print("Restarting the AI container manager...")
    run_command(['docker', 'restart', 'ai-container-manager'], capture=False)
    print("Waiting for API manager to start up...")
    time.sleep(10)

if __name__ == "__main__":
    print("Checking for AI containers to fix...")
    containers = get_ai_containers()
    
    if not containers:
        print("No AI containers found. Exiting.")
        sys.exit(1)
    
    print(f"Found {len(containers)} AI containers:")
    for idx, container in enumerate(containers):
        print(f"{idx+1}. {container['Names']} (ID: {container['ID'][:12]}, Status: {container['State']})")
    
    # Ask for confirmation
    choice = input("\nReplace all containers to fix orphan issues? This will maintain data but generate new container IDs. [y/N]: ")
    
    if choice.lower() != 'y':
        print("Operation cancelled. Exiting.")
        sys.exit(0)
    
    # Process containers
    success_count = 0
    for idx, container in enumerate(containers):
        container_id = container['ID']
        container_name = container['Names']
        print(f"\n[{idx+1}/{len(containers)}] Processing {container_name}...")
        
        if recreate_container(container_id, container_name):
            success_count += 1
    
    print(f"\nSuccessfully processed {success_count}/{len(containers)} containers")
    
    if success_count > 0:
        print("\nRestarting API manager to track new containers...")
        restart_api_manager()
        print("\nDone! Your containers have been recreated with new IDs to prevent orphaned containers.")
        print("Use python3 check_api.py to verify that the containers are being tracked.")