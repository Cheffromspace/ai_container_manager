#!/usr/bin/env python3
"""
Utility functions for the AI Container Manager
"""
import re
import subprocess
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_container_identifier(identifier):
    """
    Validate container identifier format to prevent injection
    
    Args:
        identifier (str): The container identifier to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    # Only allow alphanumeric chars, dashes and underscores
    if not isinstance(identifier, str):
        return False
    # Check for maximum length to prevent DoS vectors
    if len(identifier) > 128:  # Reasonable limit for container identifiers
        return False
    if not re.match(r'^[a-zA-Z0-9_\-]+$', identifier):
        return False
    return True

def find_container_by_id(docker_cmd, container_id, logger_fn=None):
    """
    Generic function to find a container by its ID
    
    Args:
        docker_cmd (str or list): Docker command or path to binary/wrapper
        container_id (str): Container ID to find
        logger_fn (callable, optional): Function to use for logging
        
    Returns:
        tuple: (bool, str) - (True if found, container ID if found)
    """
    log = logger_fn or logger.error
    
    try:
        # Ensure docker_cmd is a list
        cmd = docker_cmd if isinstance(docker_cmd, list) else [docker_cmd]
        cmd.extend(["ps", "-a", "--filter", f"id={container_id}", "--format", "{{.ID}}"])
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        found_id = result.stdout.strip()
        return (found_id != "", found_id)
    except Exception as e:
        log(f"Error checking container by ID: {str(e)}")
        return (False, "")

def find_container_by_name(docker_cmd, container_name, logger_fn=None):
    """
    Generic function to find a container by name
    
    Args:
        docker_cmd (str or list): Docker command or path to binary/wrapper
        container_name (str): Container name to find
        logger_fn (callable, optional): Function to use for logging
        
    Returns:
        tuple: (bool, str) - (True if found, container ID if found)
    """
    log = logger_fn or logger.error
    
    try:
        # Ensure docker_cmd is a list
        cmd = docker_cmd if isinstance(docker_cmd, list) else [docker_cmd]
        cmd.extend(["ps", "-a", "--format", "{{.ID}}|{{.Names}}"])
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Parse the output into a dictionary of names to IDs
        containers = {}
        for line in result.stdout.strip().split('\n'):
            if line and '|' in line:
                parts = line.split('|', 1)
                # Defensive coding: ensure we have both parts before unpacking
                if len(parts) == 2:
                    container_id, container_name_from_cmd = parts
                    # Safety check for empty values
                    if container_id and container_name_from_cmd:
                        containers[container_name_from_cmd] = container_id
        
        # Check for exact name match
        if container_name in containers:
            return (True, containers[container_name])
            
        # Try with ai-container- prefix if not already using it
        if not container_name.startswith("ai-container-"):
            prefixed_name = f"ai-container-{container_name}"
            # Validate the prefixed name as well
            if validate_container_identifier(prefixed_name) and prefixed_name in containers:
                return (True, containers[prefixed_name])
                
        return (False, "")
    except Exception as e:
        log(f"Error checking container by name: {str(e)}")
        return (False, "")

def find_container(docker_cmd, container_identifier, logger_fn=None):
    """
    Generic function to find a container by ID or name
    
    Args:
        docker_cmd (str or list): Docker command or path to binary/wrapper
        container_identifier (str): Container ID or name to find
        logger_fn (callable, optional): Function to use for logging
        
    Returns:
        tuple: (bool, str) - (True if found, container ID if found)
    """
    # Validate the identifier format first
    if not validate_container_identifier(container_identifier):
        if logger_fn:
            logger_fn(f"Invalid container identifier format: {container_identifier}")
        else:
            logger.warning(f"Invalid container identifier format: {container_identifier}")
        return (False, "")
    
    # Try to find by ID first
    found_by_id, container_id = find_container_by_id(docker_cmd, container_identifier, logger_fn)
    if found_by_id:
        return (True, container_id)
    
    # If not found by ID, try to find by name
    found_by_name, container_id = find_container_by_name(docker_cmd, container_identifier, logger_fn)
    if found_by_name:
        return (True, container_id)
    
    # Container not found
    return (False, "")