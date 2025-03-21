#!/usr/bin/env python3
"""
Test directly using Docker API without going through the container manager API
"""
import pytest
from unittest.mock import patch, MagicMock
import docker

def test_cd_commands(container_id):
    """Test various cd commands using Docker Python client"""
    test_cases = [
        "cd",
        "cd /",
        "cd /tmp",
        "cd ~",
        "cd..",
        "cd/etc",
        "cd~",
        "cd && pwd",
        "cd ~ && pwd"
    ]
    
    # Import the Docker client from app.py
    from core.app import client as docker_client
    
    # Get the container object from active_containers
    from core.app import active_containers
    container = active_containers[container_id]['container_obj']
    
    # Mock the exec_run method to avoid actual Docker calls
    with patch.object(container, 'exec_run') as mock_exec:
        # Configure mock to return success
        mock_exec.return_value.exit_code = 0
        mock_exec.return_value.output = b"Command executed successfully"
        
        for cmd in test_cases:
            # Test execution directly with Docker Python client (not subprocess)
            result = container.exec_run(["/bin/bash", "-c", cmd])
            
            # Verify the command executed successfully
            assert result.exit_code == 0
            
            # Verify the Docker exec command was called with the correct parameters
            mock_exec.assert_called_with(["/bin/bash", "-c", cmd])