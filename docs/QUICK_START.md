# AI Container Manager Quick Start Guide

This guide will help you quickly get started with the AI Container Manager for n8n.

## Setting Up

1. **Build the container images:**

```bash
cd ai_container_manager
chmod +x build-images.sh
./build-images.sh
```

2. **Start the service:**

```bash
cd /home/jonflatt/n8n
docker-compose up -d ai-container-manager
```

3. **Verify it's working:**

```bash
curl http://localhost:5000/api/containers
```

## Using the n8n Workflow

1. In n8n, import the workflow from `ai_container_manager/n8n-example-workflow.json`
2. Save and activate the workflow
3. Use the buttons to interact with containers:
   - **Spin up AI Container**: Creates a new container
   - **Run Command**: Executes a command in a container
   - **Delete Container**: Removes a container when done
   - **Container Stats**: Shows stats about active containers
   - **Container Cleanup**: Removes all active containers

## Common Tasks

### Creating a Container

```bash
# Original endpoint
curl -X POST http://localhost:5000/api/containers

# Alternative endpoint
curl -X POST http://localhost:5000/api/containers/create
```

This returns container details including SSH connection information.

### Running a Command

For simple commands:

```bash
# Original endpoint
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"command":"echo hello"}' \
  http://localhost:5000/api/containers/{container_identifier}/exec

# Alternative endpoint 
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"command":"echo hello"}' \
  http://localhost:5000/api/containers/exec/{container_identifier}

# Note: container_identifier can be either the container ID or name
```

For shell builtin commands or complex shell operations:

```bash
# Using shell builtin commands (cd, source, etc.)
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"command":"/bin/bash -c \"cd ~ && pwd\""}' \
  http://localhost:5000/api/containers/{container_identifier}/exec

# Using environment variables
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"command":"/bin/bash -c \"echo $HOME\""}' \
  http://localhost:5000/api/containers/{container_identifier}/exec
  
# Complex multi-step commands
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"command":"/bin/bash -c \"cd /workspace && mkdir -p test && cd test && echo hello > file.txt && cat file.txt\""}' \
  http://localhost:5000/api/containers/{container_identifier}/exec
```

**IMPORTANT:** For commands using:
- Shell builtins (`cd`, `source`, `export`, etc.)
- Environment variables (`$HOME`, `$PATH`, etc.)
- Pipes or redirections (`|`, `>`, `>>`)
- Command chaining (`&&`, `;`)
- Loops or conditionals (`for`, `if`, etc.)

You MUST wrap the command with `/bin/bash -c` as shown in the examples above.

Replace `{container_identifier}` with either the container ID or name.

### Deleting a Container

```bash
# Original endpoint
curl -X DELETE http://localhost:5000/api/containers/{container_identifier}

# Alternative endpoint
curl -X DELETE http://localhost:5000/api/containers/delete/{container_identifier}
```

Replace `{container_identifier}` with either the container ID or name.

### Getting Container Stats

```bash
# Original endpoint
curl http://localhost:5000/api/containers/stats

# Alternative endpoint (simpler)
curl http://localhost:5000/api/stats
```

Returns statistics about active containers including count, ages, and expiry times.

### Cleaning Up All Containers

```bash
# Original endpoint
curl -X POST http://localhost:5000/api/containers/cleanup

# Alternative endpoint (simpler)
curl -X POST http://localhost:5000/api/cleanup
```

Removes all active containers at once.

### Connecting via SSH

```bash
ssh root@localhost -p {ssh_port}
```

Replace `{ssh_port}` with the port number returned when creating the container.
Default password: `password`

## Next Steps

For more detailed information, see the full [DOCUMENTATION.md](DOCUMENTATION.md).