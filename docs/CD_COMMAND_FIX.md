# Container 'cd' Command Fix

This document provides solutions for the issue with the `cd` command not working in the container manager API.

## Problem

When executing commands like `cd` through the container manager API, you receive an error:

```json
{
  "exit_code": 127,
  "output": "OCI runtime exec failed: exec failed: unable to start container process: exec: \"cd\": executable file not found in $PATH: unknown\n"
}
```

This happens because `cd` is a shell builtin command, not an executable, and Docker is trying to execute it directly.

## Solutions

### Option 1: Direct Executor (Recommended)

The `direct_executor.py` script provides a direct way to execute commands in containers using Docker's exec command with the correct shell wrapping.

```bash
# Usage
python3 direct_executor.py CONTAINER_ID "cd && pwd"

# For json output like the API
python3 direct_executor.py CONTAINER_ID "cd && pwd" --json
```

### Option 2: API Proxy (Advanced)

The `api_proxy.py` script creates a proxy server that intercepts exec requests and executes them properly with bash.

```bash
# Start the proxy
python3 api_proxy.py

# Use port 5001 instead of 5000 in your API calls
curl -X POST -H "Content-Type: application/json" \
  -d '{"command":"cd && pwd"}' \
  http://localhost:5001/api/containers/YOUR_CONTAINER_ID/exec
```

### Option 3: Container Manager Patch (For admins)

The patching scripts attempt to modify the container manager API code:

- `patch.sh` - Simple sed replacement
- `robust_patch.sh` - More complex awk-based replacement
- `rebuild_with_fix.sh` - Creates a new Docker image with the fix

These might require admin access and could have variable results.

## Testing

You can test the different approaches using the provided testing scripts:

- `test_cd_cases.py` - Tests various `cd` commands via the API
- `test_specific_endpoint.py` - Tests a specific endpoint with a specific command
- `test_docker_direct.py` - Tests commands directly using Docker's API

## Solution Details

The key to fixing this issue is to always execute commands using:

```
docker exec CONTAINER_ID /bin/bash -c "YOUR_COMMAND"
```

This ensures all shell builtins like `cd`, `source`, etc. work properly.