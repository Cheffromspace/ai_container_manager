# AI Container Manager - Project Reorganization Plan

## Scripts to Keep

### Core Functionality
- `app.py` - Main container management service
- `api_proxy.py` - API proxy service

### Execution and Command Handling
- `direct_executor.py` - Direct command execution utility
- `direct_restart.py` - Direct container restart utility

### Container Management Utilities
- `create_container.py` - Container creation script
- `force_register.py` - Force container registration
- `sync_containers.py` - Synchronize container tracking
- `restart_all.py` - Restart all containers
- `fix_orphaned_containers.py` - Fix orphaned containers
- `kill_containers.py` - Kill containers utility

### Testing Scripts
- `test_cd_cases.py` - Test container commands (specifically 'cd' functionality)
- `test_docker_direct.py` - Test direct Docker execution
- `test_fixed.py` - Test fixed container functionality
- `test_commands.py` - Test container commands
- `test_restart.py` - Test container restart functionality
- `test_specific_endpoint.py` - Test specific API endpoints

### Debugging and Utilities
- `check_api.py` - Check API functionality
- `debug_api.py` - Debug API functionality

## Scripts to Remove

The following scripts appear to be redundant or their functionality is covered by other scripts:

1. `fix_exec.py` - This functionality should be baked into the main `app.py` code
2. Any scripts not listed in the "Scripts to Keep" section

## Project Organization Plan

### Proposed Directory Structure
```
/ai_container_manager/
  /core/
    - app.py
    - api_proxy.py
  /utils/
    - direct_executor.py
    - create_container.py
    - sync_containers.py
    - force_register.py
    - restart_all.py
    - fix_orphaned_containers.py
    - kill_containers.py
    - direct_restart.py
  /tests/
    - test_cd_cases.py
    - test_docker_direct.py
    - test_fixed.py
    - test_commands.py
    - test_restart.py
    - test_specific_endpoint.py
  /debug/
    - check_api.py
    - debug_api.py
  /docker/
    - Dockerfile
    - Dockerfile.container
    - Dockerfile.proxy
    - build-images.sh
  /docs/
    - README.md
    - QUICK_START.md
    - ADVANCED_WORKFLOWS.md
    - INTEGRATION_GUIDE.md
    - DOCUMENTATION.md
    - CD_COMMAND_FIX.md
```

### Implementation Steps

1. Create the directory structure
2. Move scripts to appropriate directories
3. Update import statements in scripts to reflect new structure
4. Update any scripts that reference other scripts by path
5. Create a proper test suite with pytest
6. Add a requirements.txt file in the root directory

## API Module Organization

Consider refactoring `app.py` into multiple modules:

```
/core/
  - app.py (main Flask app and routes)
  - container_manager.py (container management logic)
  - utils.py (utility functions)
  - models.py (data structures)
```

## Test Suite Implementation

Create a proper test suite structure using pytest:

```
/tests/
  - conftest.py (shared fixtures)
  - test_api.py (API tests)
  - test_container_ops.py (Container operations tests)
  - test_direct_execution.py (Direct execution tests)
```

## Documentation Improvement

1. Add docstrings to all functions
2. Update README with comprehensive installation and usage instructions
3. Create a developer documentation guide
4. Add API documentation

## Implementation Script

Below is a shell script that can be used to reorganize the project according to this plan:

```bash
#!/bin/bash
# Script to reorganize the AI Container Manager project

# Create directory structure
mkdir -p core utils tests debug docker docs

# Move core files
mv app.py core/
mv api_proxy.py core/

# Move utility files
mv direct_executor.py utils/
mv create_container.py utils/
mv sync_containers.py utils/
mv force_register.py utils/
mv restart_all.py utils/
mv fix_orphaned_containers.py utils/
mv kill_containers.py utils/
mv direct_restart.py utils/

# Move test files
mv test_cd_cases.py tests/
mv test_docker_direct.py tests/
mv test_fixed.py tests/
mv test_commands.py tests/
mv test_restart.py tests/
mv test_specific_endpoint.py tests/

# Move debug files
mv check_api.py debug/
mv debug_api.py debug/

# Move Docker files
mv Dockerfile docker/
mv Dockerfile.container docker/
mv Dockerfile.proxy docker/
mv build-images.sh docker/

# Move documentation
mv README.md docs/
mv QUICK_START.md docs/
mv ADVANCED_WORKFLOWS.md docs/
mv INTEGRATION_GUIDE.md docs/
mv DOCUMENTATION.md docs/
mv CD_COMMAND_FIX.md docs/
mv PROJECT_REORGANIZATION.md docs/

# Create a basic test suite setup
cat > tests/conftest.py << 'EOF'
import pytest
import sys
import os

# Add the parent directory to the path so we can import the core modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture
def api_client():
    """Create a test client for the API"""
    from core.app import app
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client
EOF

# Create a basic test suite
cat > tests/__init__.py << 'EOF'
# Tests package
EOF

# Create a README for tests
cat > tests/README.md << 'EOF'
# AI Container Manager Tests

This directory contains tests for the AI Container Manager.

## Running Tests

```bash
# Install pytest if not already installed
pip install pytest

# Run all tests
pytest

# Run specific test file
pytest test_api.py

# Run with verbosity
pytest -v
```

## Test Categories

- `test_api.py` - Tests for the API endpoints
- `test_container_ops.py` - Tests for container operations
- `test_direct_execution.py` - Tests for direct execution
EOF

# Create __init__.py files for packages
touch core/__init__.py
touch utils/__init__.py
touch debug/__init__.py

# Create package READMEs
cat > core/README.md << 'EOF'
# Core Module

This directory contains the core functionality of the AI Container Manager.

- `app.py` - Main Flask application and API endpoints
- `api_proxy.py` - API proxy service
EOF

cat > utils/README.md << 'EOF'
# Utilities

This directory contains utility scripts for the AI Container Manager.

- `direct_executor.py` - Direct command execution utility
- `create_container.py` - Container creation script
- `sync_containers.py` - Synchronize container tracking
- And more...
EOF

cat > debug/README.md << 'EOF'
# Debug Tools

This directory contains debugging tools for the AI Container Manager.

- `check_api.py` - Check API functionality
- `debug_api.py` - Debug API functionality
EOF

cat > docker/README.md << 'EOF'
# Docker Configuration

This directory contains Docker configuration files for the AI Container Manager.

- `Dockerfile` - Main container manager Dockerfile
- `Dockerfile.container` - Container image Dockerfile
- `Dockerfile.proxy` - API proxy Dockerfile
- `build-images.sh` - Script to build Docker images
EOF

echo "Project reorganization structure created!"
```