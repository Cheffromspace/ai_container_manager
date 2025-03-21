# AI Container Manager Tests

This directory contains tests for the AI Container Manager.

## Test Structure

The test suite uses pytest and focuses on testing the core functionality of the container manager API:

- `test_commands.py`: Basic API functionality tests
- `test_cd_cases.py`: Tests for the "cd" command handling in containers
- `test_docker_direct.py`: Tests for direct Docker API interaction
- `test_restart.py`: Tests for container restart functionality
- `test_specific_endpoint.py`: Tests for specific endpoints with various commands

## Running Tests

```bash
# Install pytest if not already installed
pip install pytest

# Run all tests
pytest

# Run specific test file
pytest tests/test_commands.py

# Run with verbosity
pytest -v
```

## Test Design

The tests use pytest fixtures defined in `conftest.py` to:

1. Create a test Flask client for the API
2. Create a mock container ID for testing
3. Mock Docker container interactions to avoid actual Docker API calls

This approach allows us to test the API's logic without requiring actual Docker containers to be running, making the tests faster, more reliable, and self-contained.

## Key Fixtures

- `api_client`: A Flask test client for making API requests
- `container_id`: A mock container ID that's registered in the active_containers dictionary

## Mocking Strategy

Most tests use the `unittest.mock` library to patch Docker API calls:

1. Container execution is mocked to return predefined outputs
2. Container restart is mocked to avoid actual container restarts
3. Container state is tracked in the app's `active_containers` dictionary

This allows us to test error scenarios and edge cases that would be difficult to reproduce with real containers.