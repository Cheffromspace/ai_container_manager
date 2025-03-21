#!/usr/bin/env python3
"""
Test container restart functionality and command execution
"""
import pytest
from unittest.mock import patch, MagicMock

def test_container_exec(container_id, api_client, command="echo 'Hello'"):
    """Test container exec with the given ID using the Flask test client"""
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
    
    # For a simple echo command, expect success
    assert result['exit_code'] == 0
    
    # We've mocked the output in the fixture, so we don't check the actual content

def test_container_restart_flow(container_id, api_client):
    """Test the full flow of restarting a container and running commands before and after"""
    # Import container handling from app
    from core.app import active_containers
    container = active_containers[container_id]['container_obj']
    
    # Mock the container's restart method to avoid actual Docker calls
    with patch.object(container, 'restart') as mock_restart:
        # First, test executing a command before restart
        test_container_exec(container_id, api_client, command="echo 'Hello before restart!'")
        
        # Now restart the container
        response = api_client.post(f'/api/containers/{container_id}/restart')
        
        # Check that the API responded correctly
        assert response.status_code == 200
        assert 'message' in response.json
        
        # Verify the restart method was called
        mock_restart.assert_called_once()
        
        # Test executing a command after restart
        test_container_exec(container_id, api_client, command="echo 'Hello after restart!'")
        
        # Verify the container is still in the active_containers dictionary
        assert container_id in active_containers