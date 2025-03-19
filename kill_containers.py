#!/usr/bin/env python3
"""
This script forcefully removes Docker containers that match the AI container pattern.
"""
import subprocess
import json
import sys

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

def list_all_ai_containers():
    """List all AI containers using Docker CLI"""
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

def force_remove_container(container_id, container_name):
    """Force remove a container"""
    print(f"Force removing container {container_name} ({container_id[:12]})...")
    
    # First try to kill it if it's running
    if run_command(['docker', 'kill', container_id], check=False):
        print(f"Container {container_name} killed.")
    
    # Then force remove it
    if run_command(['docker', 'rm', '-f', container_id], check=False):
        print(f"Container {container_name} forcefully removed.")
        return True
    else:
        print(f"Failed to remove container {container_name}.")
        return False

if __name__ == "__main__":
    print("Checking for AI containers to remove...")
    containers = list_all_ai_containers()
    
    if not containers:
        print("No AI containers found. Exiting.")
        sys.exit(1)
    
    print(f"Found {len(containers)} AI containers:")
    for idx, container in enumerate(containers):
        print(f"{idx+1}. {container['Names']} (ID: {container['ID'][:12]}, Status: {container['State']})")
    
    # Skip confirmation if script argument is passed
    if len(sys.argv) > 1 and sys.argv[1] == '--force':
        choice = 'y'
    else:
        # Ask for confirmation
        try:
            choice = input("\nForce remove all AI containers? This cannot be undone. [y/N]: ")
        except EOFError:
            # If we can't get input (e.g., when run in subprocess), assume yes
            print("\nAssuming yes...")
            choice = 'y'
    
    if choice.lower() != 'y':
        print("Operation cancelled. Exiting.")
        sys.exit(0)
    
    # Process containers
    success_count = 0
    for idx, container in enumerate(containers):
        container_id = container['ID']
        container_name = container['Names']
        print(f"\n[{idx+1}/{len(containers)}] Processing {container_name}...")
        
        if force_remove_container(container_id, container_name):
            success_count += 1
    
    print(f"\nSuccessfully removed {success_count}/{len(containers)} containers")