#!/usr/bin/env python3
import subprocess
import json
import time
import sys
import os

def get_api_container_status():
    """Get the container ID of the ai-container-manager"""
    try:
        result = subprocess.run(
            ['docker', 'ps', '--filter', 'name=ai-container-manager', '--format', '{{.ID}}'],
            capture_output=True, text=True, check=True
        )
        container_id = result.stdout.strip()
        if container_id:
            return container_id
        else:
            return None
    except subprocess.CalledProcessError as e:
        print(f"Error getting API container: {e}")
        return None

def restart_api_container():
    """Restart the AI container manager"""
    container_id = get_api_container_status()
    if not container_id:
        print("API container not found!")
        return False
    
    try:
        print(f"Restarting API container {container_id}...")
        result = subprocess.run(
            ['docker', 'restart', container_id],
            capture_output=True, text=True, check=True
        )
        print(result.stdout.strip())
        print("Waiting 10 seconds for API to start...")
        time.sleep(10)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error restarting API container: {e}")
        return False

def update_api_code():
    """Write a modified handle_existing_containers function to the app.py file in the container"""
    container_id = get_api_container_status()
    if not container_id:
        print("API container not found!")
        return False
    
    # Create a temporary file with the improved code
    temp_file = "/tmp/handle_existing_containers.py"
    with open(temp_file, "w") as f:
        f.write("""
def handle_existing_containers():
    \"\"\"Find and track existing AI containers\"\"\"
    try:
        # Reset active containers tracking at startup
        global active_containers
        active_containers.clear()
        
        # Debug logs
        logger.info("Starting container tracking process...")
        
        # Get all containers with our naming pattern (including stopped ones) - skip the manager itself
        all_containers = client.containers.list(all=True, filters={"name": "ai-container-"})
        logger.info(f"Found {len(all_containers)} containers with naming pattern 'ai-container-'")
        
        # Log all container names found
        for c in all_containers:
            logger.info(f"Container found: {c.name} (status: {c.status})")
            
            # Skip the manager container
            if c.name == "ai-container-manager":
                continue
                
            container_id = c.name.split('-')[-1]
                
            try:
                # Get container info for age determination
                container_info = client.api.inspect_container(c.id)
                creation_time_str = container_info.get('Created', '')
                creation_timestamp = time.time()  # Default to current time
                
                # Parse Docker timestamp if available
                try:
                    # Docker timestamps are in ISO 8601 format
                    dt = datetime.fromisoformat(creation_time_str.replace('Z', '+00:00'))
                    creation_timestamp = dt.timestamp()
                except Exception as e:
                    logger.error(f"Error parsing container creation time, using current time: {str(e)}")
                
                # Track ALL containers regardless of status
                # Get port information for SSH
                port_bindings = container_info['HostConfig']['PortBindings'] or {}
                ssh_port = None
                
                # Extract host port for SSH
                for container_port, host_bindings in port_bindings.items():
                    if container_port.startswith('22/'):
                        if host_bindings and len(host_bindings) > 0:
                            ssh_port = host_bindings[0].get('HostPort')
                            break
                
                # Add to our tracking dict
                active_containers[container_id] = {
                    'id': container_id,
                    'name': c.name,
                    'container_obj': c,
                    'status': c.status,
                    'created_at': creation_timestamp,
                    'ssh_port': ssh_port
                }
                logger.info(f"Tracking container {c.name} with ID {container_id}")
                
            except Exception as e:
                logger.error(f"Failed to process container {c.name}: {str(e)}")
                
        logger.info(f"Startup tracking completed. Added {len(active_containers)} existing containers to tracking.")
    except Exception as e:
        logger.error(f"Error during container tracking: {str(e)}")
""")
    
    # Copy the file to the container
    try:
        print("Copying modified code to container...")
        result = subprocess.run(
            ['docker', 'cp', temp_file, f"{container_id}:/tmp/handle_existing_containers.py"],
            capture_output=True, text=True, check=True
        )
        
        # Execute command to update the app.py file in the container
        print("Updating app.py in the container...")
        update_cmd = """
        cd /app && 
        cat /tmp/handle_existing_containers.py > /tmp/handle_existing_containers_func.py && 
        python3 -c "
import re
with open('/app/app.py', 'r') as f:
    content = f.read()
with open('/tmp/handle_existing_containers_func.py', 'r') as f:
    new_func = f.read()
pattern = r'def handle_existing_containers\\(\\):[\\s\\S]*?(?=\\n\\# Run container tracking)'
updated = re.sub(pattern, new_func.strip(), content)
with open('/app/app.py', 'w') as f:
    f.write(updated)
print('File updated successfully')
"
        """
        
        result = subprocess.run(
            ['docker', 'exec', container_id, 'bash', '-c', update_cmd],
            capture_output=True, text=True, check=True
        )
        print(result.stdout.strip())
        
        # Restart the container
        print("Restarting API container...")
        restart_api_container()
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error updating code: {e}")
        print(f"Error output: {e.stderr}")
        return False

def manually_sync_containers():
    """Force-sync all AI containers by directly modifying the API container"""
    try:
        # Get the API container ID
        api_container_id = get_api_container_status()
        if not api_container_id:
            print("API container not found!")
            return False
        
        # Get all AI containers
        result = subprocess.run(
            ['docker', 'ps', '-a', '--filter', 'name=ai-container-', '--format', '{{.ID}} {{.Names}}'],
            capture_output=True, text=True, check=True
        )
        
        containers = []
        for line in result.stdout.splitlines():
            if line.strip():
                parts = line.split()
                if len(parts) >= 2:
                    container_id = parts[0]
                    container_name = ' '.join(parts[1:])
                    if container_name != 'ai-container-manager':
                        containers.append((container_id, container_name))
        
        if not containers:
            print("No AI containers found!")
            return False
        
        print(f"Found {len(containers)} AI containers to sync:")
        for c_id, c_name in containers:
            print(f"  - {c_name} (ID: {c_id})")
        
        # Create Python script to add containers to tracking
        sync_script = "/tmp/sync_containers.py"
        with open(sync_script, "w") as f:
            f.write("""
import docker
client = docker.from_env()
import time
from datetime import datetime
import json

# Print actual container list from Docker
containers = client.containers.list(all=True, filters={"name": "ai-container-"})
print(f"Docker shows {len(containers)} containers with 'ai-container-' pattern")
for c in containers:
    print(f"  - {c.name} (status: {c.status})")

# Access the active_containers dict from the app
from app import active_containers

# Clear existing tracking
print("\\nClearing existing container tracking...")
active_containers.clear()

# Re-add all containers
print("\\nAdding containers to tracking...")
for container in containers:
    # Skip the manager container
    if container.name == "ai-container-manager":
        continue
        
    container_id = container.name.split('-')[-1]
    
    try:
        # Get container info
        container_info = client.api.inspect_container(container.id)
        creation_time_str = container_info.get('Created', '')
        creation_timestamp = time.time()  # Default to current time
        
        # Parse Docker timestamp if available
        try:
            # Docker timestamps are in ISO 8601 format
            dt = datetime.fromisoformat(creation_time_str.replace('Z', '+00:00'))
            creation_timestamp = dt.timestamp()
        except Exception as e:
            print(f"Error parsing creation time: {e}")
        
        # Get port information for SSH
        port_bindings = container_info['HostConfig']['PortBindings'] or {}
        ssh_port = None
        
        # Extract host port for SSH
        for container_port, host_bindings in port_bindings.items():
            if container_port.startswith('22/'):
                if host_bindings and len(host_bindings) > 0:
                    ssh_port = host_bindings[0].get('HostPort')
                    break
        
        # Add to tracking dict
        active_containers[container_id] = {
            'id': container_id,
            'name': container.name,
            'container_obj': container,
            'status': container.status,
            'created_at': creation_timestamp,
            'ssh_port': ssh_port
        }
        print(f"  - Added {container.name} (ID: {container_id}, Status: {container.status})")
    except Exception as e:
        print(f"  - Error processing {container.name}: {e}")

print("\\nContainer tracking updated")
print(f"Now tracking {len(active_containers)} containers:")
for container_id, info in active_containers.items():
    print(f"  - {info.get('name')} (ID: {container_id}, Status: {info.get('status')})")
""")
        
        # Copy the script to the container
        print("Copying sync script to container...")
        result = subprocess.run(
            ['docker', 'cp', sync_script, f"{api_container_id}:/tmp/sync_containers.py"],
            capture_output=True, text=True, check=True
        )
        
        # Execute the script
        print("Running sync script in container...")
        result = subprocess.run(
            ['docker', 'exec', api_container_id, 'cd', '/app', '&&', 'python3', '/tmp/sync_containers.py'],
            capture_output=True, text=True, check=True
        )
        print(result.stdout)
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error syncing containers: {e}")
        print(f"Error output: {e.stderr}")
        return False

if __name__ == "__main__":
    print("Starting container sync process...")
    
    # First, try to sync containers by direct modification
    print("\nSTEP 1: Manually syncing containers...")
    if manually_sync_containers():
        print("Manual sync completed successfully!")
    else:
        print("Manual sync failed, trying code update...")
        
        # If that fails, try to update the code
        print("\nSTEP 2: Updating API container code...")
        if update_api_code():
            print("Code update completed successfully!")
        else:
            print("Code update failed!")
            
        # Final restart
        print("\nSTEP 3: Restarting API container one more time...")
        restart_api_container()
    
    print("\nSync process completed. Please check API tracking with check_api.py")