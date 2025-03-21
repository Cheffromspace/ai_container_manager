import pytest
import sys
import os
import uuid
import time
from unittest.mock import MagicMock, patch

# Add the parent directory to the path so we can import the core modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock the docker module before importing app
docker_mock = MagicMock()
sys.modules['docker'] = docker_mock

# Create mock Docker client
mock_client = MagicMock()
docker_mock.from_env.return_value = mock_client

# Now import app with mocked docker
from core.app import app, active_containers

@pytest.fixture
def api_client():
    """Create a test client for the API"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def container_id():
    """
    Creates a mock container ID for testing.
    In real tests, we'd create a Docker container, but for unit tests
    we'll just return a mock ID and mock the container interactions.
    """
    # Generate a UUID that can be used as a container ID
    mock_id = str(uuid.uuid4())
    
    # Create a mock container object
    mock_container = MagicMock()
    mock_container.name = f"ai-container-{mock_id[:8]}"
    mock_container.status = "running"
    mock_container.exec_run.return_value.exit_code = 0
    mock_container.exec_run.return_value.output = (b"Mock command output", b"")
    
    # Add to active containers
    active_containers[mock_id] = {
        'id': mock_id,
        'name': mock_container.name,
        'container_obj': mock_container,
        'status': 'running',
        'created_at': time.time(),
        'ssh_port': 11001
    }
    
    yield mock_id
    
    # Clean up after the test
    if mock_id in active_containers:
        del active_containers[mock_id]