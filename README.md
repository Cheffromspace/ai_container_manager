# AI Container Manager

A Flask-based API for managing Docker containers for AI workloads.

## Project Structure

The project has been reorganized into a more maintainable structure:

- `core/` - Core application logic
  - `app.py` - Main Flask application
  - `api_proxy.py` - API proxy functionality
- `utils/` - Utility scripts for container management
  - `create_container.py` - Create new containers
  - `sync_containers.py` - Sync container tracking
  - `direct_executor.py` - Direct Docker command execution
  - `restart_all.py` - Restart all containers
  - `kill_containers.py` - Kill running containers
  - And more utility scripts
- `tests/` - Test suite
  - `test_cd_cases.py` - Test CD command functionality
  - `test_fixed.py` - Test fixes
  - `test_docker_direct.py` - Test direct Docker execution
  - And more test scripts
- `debug/` - Debugging tools
  - `check_api.py` - Check API functionality
  - `debug_api.py` - Debug API issues
- `docker/` - Docker configuration
  - `Dockerfile` - Main application Dockerfile
  - `Dockerfile.container` - Container image Dockerfile
  - `Dockerfile.proxy` - API proxy Dockerfile
- `docs/` - Documentation
  - Various markdown files with documentation

## Quick Start

1. Build the Docker images:
   ```
   ./docker/build-images.sh
   ```

2. Start the container manager:
   ```
   python run.py
   ```

3. Create a new container:
   ```
   python utils/create_container.py
   ```

4. Check active containers:
   ```
   python debug/check_api.py
   ```

## Testing

Run the tests with:
```
pytest
```

## Documentation

See the `docs/` directory for detailed documentation:
- [Quick Start Guide](docs/QUICK_START.md)
- [Advanced Workflows](docs/ADVANCED_WORKFLOWS.md)
- [Integration Guide](docs/INTEGRATION_GUIDE.md)