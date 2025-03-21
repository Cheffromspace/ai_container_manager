#!/usr/bin/env python3
"""
SSH Key Manager for AI Containers
This script provides functions to copy SSH keys to containers and manage permissions
"""

import os
import logging
import docker
import subprocess

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_ssh_for_container(container_name):
    """
    Set up SSH keys for a container by copying them from the host
    and setting proper permissions
    
    Args:
        container_name (str): The name of the container to configure
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        client = docker.from_env()
        
        # Get the container
        try:
            container = client.containers.get(container_name)
        except docker.errors.NotFound:
            logger.error(f"Container {container_name} not found")
            return False
            
        logger.info(f"Setting up SSH keys for container {container_name}")
        
        # Common SSH key names to look for
        key_files = [
            'github-personal',
            'github-bot',
            'id_rsa',
            'config'
        ]
        
        # Host .ssh directory
        host_ssh_dir = '/home/jonflatt/.ssh'
        
        # Container path for SSH
        container_ssh_dir = '/root/.ssh'
        
        # Ensure the SSH directory exists in the container
        exec_result = container.exec_run(f"mkdir -p {container_ssh_dir}")
        if exec_result.exit_code != 0:
            logger.error(f"Failed to create SSH directory in container: {exec_result.output.decode()}")
            return False
            
        # Copy each key file if it exists
        for key_file in key_files:
            host_key_path = os.path.join(host_ssh_dir, key_file)
            
            # Copy the key file to the container
            try:
                with open(host_key_path, 'rb') as f:
                    data = f.read()
                    exec_result = container.exec_run(f"cat > {container_ssh_dir}/{key_file}", stdin=True, socket=True)
                    sock = exec_result.output
                    sock.sendall(data)
                    sock.close()
                    logger.info(f"Copied {key_file} to container")
            except Exception as e:
                logger.warning(f"Failed to copy {key_file}: {str(e)}")
                continue
        
        # Set proper permissions for SSH files
        commands = [
            f"chmod 700 {container_ssh_dir}",
            f"chown -R root:root {container_ssh_dir}",
            f"chmod 600 {container_ssh_dir}/id_*",
            f"chmod 600 {container_ssh_dir}/github-*",
            f"chmod 600 {container_ssh_dir}/config",
            f"chmod 644 {container_ssh_dir}/known_hosts",
            f"ls -la {container_ssh_dir}"
        ]
        
        for cmd in commands:
            exec_result = container.exec_run(cmd)
            if exec_result.exit_code != 0:
                logger.warning(f"Command failed: {cmd} - {exec_result.output.decode()}")
            else:
                logger.debug(f"Command succeeded: {cmd}")
                
        # Add github.com to known_hosts if needed
        exec_result = container.exec_run(
            "grep -q github.com /root/.ssh/known_hosts || ssh-keyscan github.com >> /root/.ssh/known_hosts"
        )
        if exec_result.exit_code != 0:
            logger.warning(f"Failed to add github.com to known_hosts: {exec_result.output.decode()}")
        
        logger.info(f"SSH keys set up for container {container_name}")
        return True
        
    except Exception as e:
        logger.error(f"Error setting up SSH for container {container_name}: {str(e)}")
        return False

def verify_ssh_setup(container_name):
    """
    Verify SSH keys were properly set up in the container
    
    Args:
        container_name (str): The name of the container to verify
        
    Returns:
        bool: True if properly set up, False otherwise
    """
    try:
        client = docker.from_env()
        
        # Get the container
        try:
            container = client.containers.get(container_name)
        except docker.errors.NotFound:
            logger.error(f"Container {container_name} not found")
            return False
        
        # Check for key files
        exec_result = container.exec_run("ls -la /root/.ssh/")
        if exec_result.exit_code != 0:
            logger.error(f"Failed to list SSH files: {exec_result.output.decode()}")
            return False
            
        output = exec_result.output.decode()
        logger.info(f"SSH directory contents:\n{output}")
        
        # Check for key files we expect
        missing_keys = []
        for key in ['github-personal', 'id_rsa', 'config']:
            if key not in output:
                missing_keys.append(key)
                
        if missing_keys:
            logger.warning(f"Missing SSH keys: {', '.join(missing_keys)}")
            return False
            
        # All checks passed
        logger.info(f"SSH keys verified for container {container_name}")
        return True
        
    except Exception as e:
        logger.error(f"Error verifying SSH for container {container_name}: {str(e)}")
        return False

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python ssh_key_manager.py <container_name>")
        sys.exit(1)
        
    container_name = sys.argv[1]
    
    # Set up SSH for the container
    if setup_ssh_for_container(container_name):
        logger.info(f"Successfully set up SSH for {container_name}")
    else:
        logger.error(f"Failed to set up SSH for {container_name}")
        sys.exit(1)
        
    # Verify the setup
    if verify_ssh_setup(container_name):
        logger.info(f"SSH verification passed for {container_name}")
    else:
        logger.error(f"SSH verification failed for {container_name}")
        sys.exit(2)