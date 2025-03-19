import os
import time
import uuid
import json
import docker
import logging
import threading
from datetime import datetime, timedelta
from flask import Flask, request, jsonify

app = Flask(__name__)
client = docker.from_env()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Track active containers
active_containers = {}

# Container expiration time in hours
CONTAINER_EXPIRY_HOURS = 2

# Check for expired containers every X minutes
def check_expired_containers():
    while True:
        try:
            current_time = time.time()
            expired = []
            
            for container_id, info in active_containers.items():
                creation_time = info.get('created_at', 0)
                expiry_time = creation_time + (CONTAINER_EXPIRY_HOURS * 3600)
                
                if current_time > expiry_time:
                    expired.append(container_id)
            
            # Remove expired containers
            for container_id in expired:
                try:
                    logger.info(f"Auto-removing expired container {container_id}")
                    container_info = active_containers[container_id]
                    container = container_info['container_obj']
                    container.stop()
                    container.remove()
                    del active_containers[container_id]
                except Exception as e:
                    logger.error(f"Failed to remove expired container {container_id}: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Error in expiry checker: {str(e)}")
        
        # Check every 10 minutes
        time.sleep(600)

# Start expiry checker thread
expiry_thread = threading.Thread(target=check_expired_containers, daemon=True)
expiry_thread.start()

# Check for orphaned containers on startup and kill them
def handle_existing_containers():
    try:
        # Reset active containers tracking at startup
        active_containers.clear()
        
        # Debug logs
        logger.info("Starting container tracking process...")
        
        # Get all containers with our naming pattern (including stopped ones) - skip the manager itself
        all_containers = client.containers.list(all=True, filters={"name": "ai-container-"})
        logger.info(f"Found {len(all_containers)} containers with naming pattern 'ai-container-'")
        
        # Log all container names found
        for c in all_containers:
            logger.info(f"Container found: {c.name} (status: {c.status})")
            
        tracked_count = 0
        cleaned_count = 0
        orphaned_count = 0
        max_container_age_hours = 24  # Consider containers older than this as orphaned
        
        current_time = time.time()
        max_age_timestamp = current_time - (max_container_age_hours * 3600)
        
        # First pass: identify orphaned containers
        orphaned_containers = []
        
        for container in all_containers:
            # Skip the manager container
            if container.name == "ai-container-manager":
                continue
                
            container_id = container.name.split('-')[-1]
            
            try:
                # Get container info for age determination
                container_info = client.api.inspect_container(container.id)
                creation_time_str = container_info.get('Created', '')
                creation_timestamp = current_time  # Default to current time
                
                # Parse Docker timestamp if available
                try:
                    # Docker timestamps are in ISO 8601 format
                    dt = datetime.fromisoformat(creation_time_str.replace('Z', '+00:00'))
                    creation_timestamp = dt.timestamp()
                except Exception as e:
                    logger.error(f"Error parsing container creation time, using current time: {str(e)}")
                
                # Check if container is orphaned (old or not running)
                is_orphaned = False
                
                # Consider old containers as orphaned
                if creation_timestamp < max_age_timestamp:
                    logger.info(f"Container {container.name} is older than {max_container_age_hours} hours, marking as orphaned")
                    is_orphaned = True
                    orphaned_count += 1
                
                # Consider dead containers as orphaned, but not just exited ones
                # This allows containers to be restarted without being orphaned
                if container.status in ['dead']:
                    logger.info(f"Container {container.name} is in {container.status} state, marking as orphaned")
                    is_orphaned = True
                    orphaned_count += 1
                    
                # For exited containers, check if they've been in that state for more than 10 minutes
                elif container.status in ['exited', 'created']:
                    # Get the finished time from container inspection
                    try:
                        finish_time_str = container_info.get('State', {}).get('FinishedAt', '')
                        if finish_time_str and finish_time_str != '0001-01-01T00:00:00Z':
                            finish_dt = datetime.fromisoformat(finish_time_str.replace('Z', '+00:00'))
                            finish_timestamp = finish_dt.timestamp()
                            time_since_exit = current_time - finish_timestamp
                            
                            # If exited more than 10 minutes ago
                            if time_since_exit > 600:  # 10 minutes in seconds
                                # Try to restart the container if it's not too old
                                if creation_timestamp > (current_time - 24*3600):  # Less than 24 hours old
                                    try:
                                        logger.info(f"Attempting to restart container {container.name} that exited {time_since_exit:.1f} seconds ago")
                                        container.restart(timeout=10)
                                        logger.info(f"Successfully restarted container {container.name}")
                                        # Don't mark as orphaned since we're trying to restart it
                                        container.reload()  # Refresh container status
                                        logger.info(f"Container {container.name} new status: {container.status}")
                                        if container.status == 'running':
                                            logger.info(f"Container {container.name} is now running after restart")
                                        else:
                                            logger.warning(f"Container {container.name} failed to enter running state after restart, status: {container.status}")
                                            is_orphaned = True
                                            orphaned_count += 1
                                    except Exception as restart_err:
                                        logger.error(f"Failed to restart container {container.name}: {str(restart_err)}")
                                        # If restart fails, mark as orphaned
                                        logger.info(f"Container {container.name} has been {container.status} for {time_since_exit:.1f} seconds and restart failed, marking as orphaned")
                                        is_orphaned = True
                                        orphaned_count += 1
                                else:
                                    # If too old, mark as orphaned
                                    logger.info(f"Container {container.name} has been {container.status} for {time_since_exit:.1f} seconds and is too old, marking as orphaned")
                                    is_orphaned = True
                                    orphaned_count += 1
                            else:
                                logger.info(f"Container {container.name} is in {container.status} state but exited only {time_since_exit:.1f} seconds ago, not marking as orphaned")
                        else:
                            # If we can't determine finish time, use a more conservative approach
                            logger.info(f"Container {container.name} is in {container.status} state with unknown finish time, not marking as orphaned")
                    except Exception as e:
                        logger.error(f"Error checking exit time for container {container.name}: {str(e)}")
                        # In case of error, don't mark as orphaned to be safe
                        logger.info(f"Container {container.name} is in {container.status} state but keeping due to error checking exit time")
                    
                    
                if is_orphaned:
                    orphaned_containers.append(container)
                else:
                    # Track active container
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
                        'name': container.name,
                        'container_obj': container,
                        'status': container.status,
                        'created_at': creation_timestamp,
                        'ssh_port': ssh_port
                    }
                    tracked_count += 1
                    logger.info(f"Tracking container {container.name} with ID {container_id}")
            except Exception as e:
                logger.error(f"Failed to process container {container.name}: {str(e)}")
                # Mark as orphaned if we can't process it
                orphaned_containers.append(container)
                orphaned_count += 1
        
        # Second pass: clean up orphaned containers
        for container in orphaned_containers:
            try:
                logger.info(f"Removing orphaned container {container.name}")
                if container.status not in ['exited', 'dead']:
                    container.stop(timeout=5)
                container.remove(force=True)
                cleaned_count += 1
            except Exception as e:
                logger.error(f"Failed to remove orphaned container {container.name}: {str(e)}")
        
        logger.info(f"Startup cleanup completed. Removed {cleaned_count}/{orphaned_count} orphaned containers.")
        logger.info(f"Startup tracking completed. Added {tracked_count} existing containers to tracking.")
    except Exception as e:
        logger.error(f"Error during container cleanup and tracking: {str(e)}")

# Run container tracking on startup
handle_existing_containers()

@app.route('/api/containers', methods=['GET'])
@app.route('/api/containers/list', methods=['GET'])  # Added alternative endpoint
def list_containers():
    """List all active AI containers"""
    containers = []
    
    # Get containers from active_containers dictionary
    for container_id, info in active_containers.items():
        containers.append({
            'id': container_id,
            'name': info.get('name'),
            'status': info.get('status'),
            'created_at': info.get('created_at'),
            'ssh_port': info.get('ssh_port')
        })
    
    # Also check for running containers that might not be in active_containers
    try:
        all_containers = client.containers.list(filters={"name": "ai-container-"})
        for container in all_containers:
            container_id = container.name.split('-')[-1]
            # Skip if already in our list
            if container_id in active_containers:
                continue
                
            # Get port information
            container_info = client.api.inspect_container(container.id)
            port_bindings = container_info['HostConfig']['PortBindings'] or {}
            ssh_port = None
            
            # Extract host port for SSH
            for container_port, host_bindings in port_bindings.items():
                if container_port.startswith('22/'):
                    if host_bindings and len(host_bindings) > 0:
                        ssh_port = host_bindings[0].get('HostPort')
                        break
            
            # Add to our list
            containers.append({
                'id': container_id,
                'name': container.name,
                'status': container.status,
                'created_at': container_info.get('Created'),
                'ssh_port': ssh_port,
                'untracked': True
            })
    except Exception as e:
        logger.error(f"Error listing untracked containers: {str(e)}")
    
    return jsonify(containers)

@app.route('/api/containers', methods=['POST'])
@app.route('/api/containers/create', methods=['POST'])  # Added alternative endpoint
def create_container():
    """Create a new AI container"""
    try:
        # Generate a unique ID for this container
        container_id = str(uuid.uuid4())
        container_name = f"ai-container-{container_id[:8]}"
        
        # Find an available port for SSH
        ssh_port = find_available_port(11001, 12000)
        
        # Create and start the container
        container = client.containers.run(
            'ai-container-image:latest',  # The image should be built from the Dockerfile
            name=container_name,
            detach=True,
            ports={'22/tcp': ssh_port},
            volumes={
                f'{container_name}-workspace': {'bind': '/workspace', 'mode': 'rw'}
            },
            environment={
                'CONTAINER_ID': container_id
            }
        )
        
        # Store container info
        container_info = {
            'id': container_id,
            'name': container_name,
            'container_obj': container,
            'status': 'running',
            'created_at': time.time(),
            'ssh_port': ssh_port
        }
        active_containers[container_id] = container_info
        
        # Return container details
        return jsonify({
            'id': container_id,
            'name': container_name,
            'status': 'running',
            'ssh_port': ssh_port,
            'ssh_command': f'ssh root@localhost -p {ssh_port}'
        }), 201
        
    except Exception as e:
        logger.error(f"Failed to create container: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/containers/<container_id>', methods=['DELETE'])
@app.route('/api/containers/delete/<container_id>', methods=['DELETE'])  # Added alternative endpoint
def delete_container(container_id):
    """Stop and remove a container"""
    if container_id not in active_containers:
        return jsonify({'error': 'Container not found'}), 404
    
    try:
        # Get container info
        container_info = active_containers[container_id]
        container = container_info['container_obj']
        
        # Stop and remove the container
        container.stop()
        container.remove()
        
        # Remove from active containers
        del active_containers[container_id]
        
        return jsonify({'message': f'Container {container_id} deleted successfully'}), 200
    
    except Exception as e:
        logger.error(f"Failed to delete container {container_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/containers/<container_id>/restart', methods=['POST'])
@app.route('/api/containers/restart/<container_id>', methods=['POST'])  # Added alternative endpoint
def restart_container(container_id):
    """Restart a specific container"""
    if container_id not in active_containers:
        # Check if the container exists in Docker but is not tracked
        try:
            all_containers = client.containers.list(all=True, filters={"name": f"ai-container-{container_id}"})
            if not all_containers:
                return jsonify({'error': 'Container not found'}), 404
                
            # Use the first container that matches the pattern
            container = all_containers[0]
            container_name = container.name
            
            # Attempt to restart the container
            logger.info(f"Restarting untracked container {container_name}")
            container.restart(timeout=10)
            
            # Trigger a refresh of container tracking
            handle_existing_containers()
            
            # Check if the container is now tracked
            if container_id in active_containers:
                return jsonify({'message': f'Container {container_id} restarted successfully and is now being tracked'}), 200
            else:
                return jsonify({'warning': f'Container {container_id} restarted but is not being tracked properly, please refresh tracking'}), 200
                
        except Exception as e:
            logger.error(f"Failed to restart untracked container {container_id}: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    try:
        # Get container info
        container_info = active_containers[container_id]
        container = container_info['container_obj']
        container_name = container_info['name']
        
        # Get current status
        old_status = container.status
        
        # Restart the container
        logger.info(f"Restarting container {container_name} (current status: {old_status})")
        container.restart(timeout=10)
        
        # Refresh container status
        container.reload()
        new_status = container.status
        
        # Update tracked status
        container_info['status'] = new_status
        
        return jsonify({
            'message': f'Container {container_id} restarted successfully',
            'name': container_name,
            'previous_status': old_status,
            'current_status': new_status
        }), 200
    
    except Exception as e:
        logger.error(f"Failed to restart container {container_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/containers/<container_id>/exec', methods=['POST'])
@app.route('/api/containers/exec/<container_id>', methods=['POST'])  # Added alternative endpoint
def exec_command(container_id):
    """Execute a command in a container"""
    if container_id not in active_containers:
        # Log detailed information about the missing container
        logger.error(f"Container ID {container_id} not found in active_containers")
        logger.info(f"Available container IDs: {list(active_containers.keys())}")
        return jsonify({'error': 'Container not found'}), 404
    
    data = request.json
    command = data.get('command')
    
    if not command:
        return jsonify({'error': 'Command is required'}), 400
    
    try:
        # Get container
        container_info = active_containers[container_id]
        container = container_info['container_obj']
        
        # SIMPLER APPROACH: Always use a shell to execute commands
        # This ensures shell builtins like 'cd' always work properly
        logger.info(f"Executing command: {command}")
        logger.info(f"Using shell for all commands")
        
        # Always use bash explicitly with the command as an argument
        exec_result = container.exec_run(
            ["/bin/bash", "-c", command],
            demux=True,  # Split stdout and stderr 
            tty=True     # Use a TTY for interactive commands
        )
        
        # Process the output
        exit_code = exec_result.exit_code
        output = ""
        
        # Handle output differently based on whether demux worked
        if isinstance(exec_result.output, tuple) and len(exec_result.output) == 2:
            # We have separate stdout and stderr
            stdout, stderr = exec_result.output
            
            if stdout:
                output += stdout.decode('utf-8', errors='replace')
            if stderr:
                stderr_text = stderr.decode('utf-8', errors='replace')
                if stderr_text.strip():  # Only add if not empty
                    output += f"\nSTDERR: {stderr_text}"
        else:
            # Combined output
            if exec_result.output:
                output = exec_result.output.decode('utf-8', errors='replace')
        
        # Log the result for debugging
        logger.info(f"Command execution result: exit_code={exit_code}, output_length={len(output)}")
        
        return jsonify({
            'exit_code': exit_code,
            'output': output
        })
    
    except Exception as e:
        logger.error(f"Failed to execute command in container {container_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

def find_available_port(start_port, end_port):
    """Find an available port in the given range"""
    # Check if port is already in use by any container
    used_ports = set()
    for _, info in active_containers.items():
        used_ports.add(info.get('ssh_port'))
    
    # Also check for ports in use by Docker
    try:
        # Get all containers (not just our managed ones)
        all_containers = client.containers.list()
        for container in all_containers:
            # Get port mappings
            container_info = client.api.inspect_container(container.id)
            port_bindings = container_info['HostConfig']['PortBindings'] or {}
            
            # Extract host ports
            for container_port, host_bindings in port_bindings.items():
                if host_bindings:
                    for binding in host_bindings:
                        if 'HostPort' in binding and binding['HostPort']:
                            try:
                                host_port = int(binding['HostPort'])
                                used_ports.add(host_port)
                            except (ValueError, TypeError):
                                pass
    except Exception as e:
        logger.warning(f"Error checking container ports: {str(e)}")
    
    # Find first available port
    for port in range(start_port, end_port):
        if port not in used_ports:
            return port
    
    raise Exception("No available ports found")

@app.route('/api/containers/refresh', methods=['GET', 'POST'])
def refresh_containers():
    """Reset container tracking and rediscover all containers"""
    try:
        # Save existing container tracking information for comparison
        previous_containers = {}
        for container_id, info in active_containers.items():
            # Skip the container object which can't be copied
            previous_containers[container_id] = {
                'id': info.get('id'),
                'name': info.get('name'),
                'status': info.get('status'),
                'ssh_port': info.get('ssh_port')
            }
        
        # Run the handle_existing_containers function
        handle_existing_containers()
        
        # Check for containers that were previously tracked but no longer are
        lost_tracking = []
        for container_id, info in previous_containers.items():
            if container_id not in active_containers:
                lost_tracking.append({
                    'id': container_id,
                    'name': info.get('name'),
                    'status': info.get('status', 'unknown')
                })
        
        # Return information about tracked containers
        containers = []
        for container_id, info in active_containers.items():
            containers.append({
                'id': container_id,
                'name': info.get('name'),
                'status': info.get('status')
            })
        
        # Extra details about lost tracking
        message = f'Container tracking refreshed. Now tracking {len(containers)} containers.'
        if lost_tracking:
            message += f' Note: {len(lost_tracking)} previously tracked containers are no longer tracked.'
            logger.warning(f"Lost tracking of {len(lost_tracking)} containers during refresh: {[c['name'] for c in lost_tracking]}")
            
        return jsonify({
            'message': message,
            'containers': containers,
            'lost_tracking': lost_tracking if lost_tracking else None
        }), 200
    except Exception as e:
        logger.error(f"Failed to refresh container tracking: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/containers/cleanup', methods=['POST'])
@app.route('/api/cleanup', methods=['POST'])  # Added simpler alternative endpoint
def cleanup_containers():
    """Stop and remove all containers"""
    try:
        cleanup_count = 0
        failed_count = 0
        
        # First, clean up containers tracked in active_containers
        container_ids = list(active_containers.keys())
        for container_id in container_ids:
            try:
                # Get container info
                container_info = active_containers[container_id]
                container = container_info['container_obj']
                
                # Stop and remove the container
                container.stop()
                container.remove()
                
                # Remove from active containers
                del active_containers[container_id]
                cleanup_count += 1
                
            except Exception as e:
                logger.error(f"Failed to clean up container {container_id}: {str(e)}")
                failed_count += 1
        
        # Then clean up any containers with our naming pattern that may not be tracked
        try:
            # Get all containers with our pattern, including stopped ones
            all_containers = client.containers.list(all=True, filters={"name": "ai-container-"})
            
            # Skip the manager container (important!)
            for container in all_containers:
                if container.name == "ai-container-manager":
                    continue
                    
                try:
                    logger.info(f"Removing container {container.name} that was not tracked")
                    # Force removal to handle any edge cases
                    container.stop(timeout=5)
                    container.remove(force=True)
                    cleanup_count += 1
                except Exception as e:
                    logger.error(f"Failed to remove container {container.name}: {str(e)}")
                    failed_count += 1
        except Exception as e:
            logger.error(f"Error listing untracked containers: {str(e)}")
        
        return jsonify({
            'message': f'Cleanup completed. {cleanup_count} containers removed, {failed_count} failed.',
            'success_count': cleanup_count,
            'fail_count': failed_count
        }), 200
    
    except Exception as e:
        logger.error(f"Failed to perform cleanup: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/containers/stats', methods=['GET'])
@app.route('/api/stats', methods=['GET'])  # Added simpler alternative endpoint
def container_stats():
    """Get statistics about container usage"""
    try:
        # Get all containers with our naming pattern
        all_containers = []
        
        # Get containers from active_containers dictionary
        for container_id, info in active_containers.items():
            creation_time = info.get('created_at', 0)
            age_hours = (time.time() - creation_time) / 3600
            all_containers.append({
                'id': container_id,
                'name': info.get('name'),
                'age_hours': round(age_hours, 2),
                'expires_in_hours': round(CONTAINER_EXPIRY_HOURS - age_hours, 2),
                'tracked': True
            })
        
        # Also check for running containers that might not be in active_containers
        try:
            docker_containers = client.containers.list(filters={"name": "ai-container-"})
            for container in docker_containers:
                container_id = container.name.split('-')[-1]
                # Skip if already in our list
                if container_id in active_containers:
                    continue
                
                # Get creation time from Docker API
                container_info = client.api.inspect_container(container.id)
                creation_time_str = container_info.get('Created', '')
                
                # Parse Docker timestamp
                try:
                    # Docker timestamps are in ISO 8601 format
                    dt = datetime.fromisoformat(creation_time_str.replace('Z', '+00:00'))
                    creation_timestamp = dt.timestamp()
                    age_hours = (time.time() - creation_timestamp) / 3600
                    
                    all_containers.append({
                        'id': container_id,
                        'name': container.name,
                        'age_hours': round(age_hours, 2),
                        'expires_in_hours': round(CONTAINER_EXPIRY_HOURS - age_hours, 2),
                        'tracked': False
                    })
                except Exception as e:
                    logger.error(f"Error parsing container creation time: {str(e)}")
        except Exception as e:
            logger.error(f"Error listing untracked containers in stats: {str(e)}")
        
        # Sort by age (oldest first)
        all_containers.sort(key=lambda x: x['age_hours'], reverse=True)
        
        return jsonify({
            'active_count': len(all_containers),
            'expiry_hours': CONTAINER_EXPIRY_HOURS,
            'containers': all_containers
        }), 200
    
    except Exception as e:
        logger.error(f"Failed to get container stats: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)