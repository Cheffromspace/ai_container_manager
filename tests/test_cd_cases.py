#!/usr/bin/env python3
"""
Test API container exec functionality
Specifically designed to test the 'cd' command issue
"""
import pytest
import requests
from unittest.mock import patch, MagicMock

def test_cd_commands(container_id, api_client):
    """Test different variations of the cd command"""
    test_cases = [
        # Basic cd command
        "cd",
        # cd with common paths
        "cd /",
        "cd /tmp",
        "cd ~",
        # cd with relative paths
        "cd ..",
        "cd ../",
        # cd with complex commands
        "cd && pwd",
        "cd ~ && pwd",
        "/bin/bash -c 'cd && pwd'",
        "/bin/bash -c 'cd /tmp && pwd'",
        # cd with absolute path (no space)
        "cd/etc",
        "cd/tmp",
        # cd with home path (no space)
        "cd~",
        # Alternative approach
        "bash -c 'cd /tmp && pwd'"
    ]
    
    # Get the container object from active_containers
    from core.app import active_containers
    container = active_containers[container_id]['container_obj']
    
    # Mock the container's exec_run method to avoid actual Docker calls
    with patch.object(container, 'exec_run') as mock_exec:
        # Configure mock to return success
        mock_exec.return_value.exit_code = 0
        mock_exec.return_value.output = (b"Command executed successfully", b"")
        
        for cmd in test_cases:
            # Make a request to the API using the Flask test client
            response = api_client.post(
                f'/api/containers/{container_id}/exec',
                json={"command": cmd},
                content_type='application/json'
            )
            
            # Check that the API responded correctly
            assert response.status_code == 200
            result = response.json
            assert result.get('exit_code') == 0
            
            # Verify the Docker exec command was called properly
            assert mock_exec.called
