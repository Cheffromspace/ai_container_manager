#!/usr/bin/env python3
"""
Test specific container exec endpoint with a given command
"""
import pytest
from unittest.mock import patch, MagicMock

def test_specific_endpoint(container_id, api_client):
    """Test the container exec endpoint with various commands"""
    # Define a set of commands to test
    test_commands = [
        "cd && pwd",
        "echo 'Hello World'",
        "ls -la",
        "whoami"
    ]
    
    # Get the container object from active_containers
    from core.app import active_containers
    container = active_containers[container_id]['container_obj']
    
    # Mock the exec_run method to avoid actual Docker calls
    with patch.object(container, 'exec_run') as mock_exec:
        # Configure mock to return success
        mock_exec.return_value.exit_code = 0
        mock_exec.return_value.output = (b"Command output", b"")
        
        for command in test_commands:
            # Make a request to the API using the Flask test client
            response = api_client.post(
                f'/api/containers/{container_id}/exec',
                json={"command": command},
                content_type='application/json'
            )
            
            # Check that the API responded correctly
            assert response.status_code == 200
            result = response.json
            assert 'exit_code' in result
            assert 'output' in result
            
            # For all our test commands, expect success
            assert result['exit_code'] == 0