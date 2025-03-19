# AI Container Manager for n8n - Documentation

This documentation provides comprehensive instructions on how to set up, configure, and use the AI Container Manager with n8n.

## Table of Contents

1. [Overview](#overview)
2. [Setup and Installation](#setup-and-installation)
3. [API Reference](#api-reference)
4. [Using with n8n](#using-with-n8n)
5. [SSH Access to Containers](#ssh-access-to-containers)
6. [Best Practices](#best-practices)
7. [Troubleshooting](#troubleshooting)

## Overview

The AI Container Manager allows n8n AI agents to:
- Create Docker containers on demand
- Maintain persistent shell sessions
- Execute commands within containers
- Manage multiple containers simultaneously
- Delete containers when no longer needed

Each container has its own isolated environment with persistent storage, making it ideal for AI agent workspaces.

## Setup and Installation

### Prerequisites

- Docker and Docker Compose installed
- n8n instance running (included in the docker-compose.yml)

### Step 1: Clone the Repository

If you haven't already, clone the repository containing the AI Container Manager:

```bash
git clone <repository-url>
cd n8n
```

### Step 2: Build the Container Images

```bash
cd ai_container_manager
chmod +x build-images.sh
./build-images.sh
```

This script builds two Docker images:
- `ai-container-manager`: The API service
- `ai-container-image`: The base image for spawned containers

### Step 3: Configure Docker Compose

The docker-compose.yml file has already been configured. It includes:

```yaml
ai-container-manager:
  build:
    context: ./ai_container_manager
    dockerfile: Dockerfile
  restart: always
  container_name: ai-container-manager
  ports:
    - "5000:5000"  # API port
  environment:
    - TZ=${TZ:-America/Chicago}
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock  # Allow container creation
    - ai_container_manager_data:/app
  networks:
    - default
  depends_on:
    - n8n
```

### Step 4: Start the Services

```bash
cd /home/jonflatt/n8n
docker-compose up -d
```

To start just the AI Container Manager:

```bash
docker-compose up -d ai-container-manager
```

### Step 5: Verify Installation

Check if the service is running:

```bash
docker-compose ps ai-container-manager
```

Test the API:

```bash
curl http://localhost:5000/api/containers
```

Should return an empty array `[]` if no containers are running.

## API Reference

### List Containers

**Endpoint:** `GET /api/containers`

**Response:**
```json
[
  {
    "id": "3a4b1c8e-1234-5678-90ab-cdef12345678",
    "name": "ai-container-3a4b1c8e",
    "status": "running",
    "created_at": 1647789012.345,
    "ssh_port": 11001
  }
]
```

### Create a Container

**Endpoint:** `POST /api/containers`

**Response:**
```json
{
  "id": "3a4b1c8e-1234-5678-90ab-cdef12345678",
  "name": "ai-container-3a4b1c8e",
  "status": "running",
  "ssh_port": 11001,
  "ssh_command": "ssh root@localhost -p 11001"
}
```

### Delete a Container

**Endpoint:** `DELETE /api/containers/{container_id}`

**Response:**
```json
{
  "message": "Container 3a4b1c8e-1234-5678-90ab-cdef12345678 deleted successfully"
}
```

### Execute a Command in a Container

**Endpoint:** `POST /api/containers/{container_id}/exec`

**Request Body:**
```json
{
  "command": "echo 'Hello, world!'"
}
```

**Response:**
```json
{
  "exit_code": 0,
  "output": "Hello, world!"
}
```

**IMPORTANT: Executing Shell Builtin Commands**

For shell builtin commands like `cd`, `source`, `export`, or commands using shell features like pipes (`|`), redirections (`>`), or environment variables (`$VAR`), you **MUST** wrap the command with `/bin/bash -c` as follows:

```json
{
  "command": "/bin/bash -c 'cd ~ && pwd'"
}
```

Examples of commands that require this wrapping:
- Shell builtins: `cd`, `source`, `export`, `alias`, etc.
- Environment variables: `$HOME`, `$PATH`, etc.
- Pipes and redirections: `|`, `>`, `>>`, `<`
- Command chaining: `&&`, `||`, `;`
- Loops and conditionals: `for`, `if`, `while`

Example in JavaScript:
```javascript
// Execute a command with shell builtins
const result = await $http.post(
  `http://ai-container-manager:5000/api/containers/${containerId}/exec`, 
  { command: "/bin/bash -c 'cd /workspace && ls -la'" }
);
```

### Container Stats

**Endpoint:** `GET /api/containers/stats`

Returns statistics about container usage, including counts and age information.

**Response:**
```json
{
  "active_count": 3,
  "expiry_hours": 2,
  "containers": [
    {
      "id": "3a4b1c8e-1234-5678-90ab-cdef12345678",
      "name": "ai-container-3a4b1c8e",
      "age_hours": 1.5,
      "expires_in_hours": 0.5
    }
  ]
}
```

### Cleanup Containers

**Endpoint:** `POST /api/containers/cleanup`

Stops and removes all active containers.

**Response:**
```json
{
  "message": "Cleanup completed. 3 containers removed, 0 failed.",
  "success_count": 3,
  "fail_count": 0
}
```

## Using with n8n

### Importing the Example Workflow

1. In n8n, go to **Workflows** → **Import from File**
2. Select the `n8n-example-workflow.json` file from the ai_container_manager directory
3. Save the workflow

### Using the Workflow

The example workflow provides three main actions:

#### Creating a Container

1. Click the "Spin up AI Container" button
2. The workflow will create a new container
3. Note the SSH connection details and Container ID

#### Executing Commands

1. Click the "Run Command" button
2. Enter the Container ID and the command you want to execute
3. View the command output

#### Deleting a Container

1. Click the "Delete Container" button
2. Enter the Container ID of the container to delete
3. Confirm the deletion

### Creating Custom Workflows

You can also create custom workflows to interact with containers:

1. Use HTTP Request nodes to call the Container Manager API
2. For creating containers: `POST` to `http://ai-container-manager:5000/api/containers`
3. For executing commands: `POST` to `http://ai-container-manager:5000/api/containers/{container_id}/exec`
4. For deleting containers: `DELETE` to `http://ai-container-manager:5000/api/containers/{container_id}`

### Integrating with AI Agents

To allow n8n AI agents to use containers:

1. Create a new workflow or function node
2. Use HTTP Request nodes to interact with the Container Manager API
3. Pass the Container ID and commands between nodes
4. Store Container IDs in n8n variables or in a database for persistence

Example Code in Function Node:
```javascript
// Create a new container
const response = await $http.post('http://ai-container-manager:5000/api/containers');
const containerId = response.data.id;

// Execute a simple command
const result1 = await $http.post(
  `http://ai-container-manager:5000/api/containers/${containerId}/exec`, 
  { command: 'python -c "print(\'Hello from AI agent\')"' }
);

// Execute a shell command with builtins (using /bin/bash -c wrapping)
const result2 = await $http.post(
  `http://ai-container-manager:5000/api/containers/${containerId}/exec`, 
  { command: "/bin/bash -c 'cd /workspace && mkdir -p test && cd test && echo \"Hello from AI agent\" > test.txt && cat test.txt'" }
);

// Return the results
return { 
  containerId, 
  simpleOutput: result1.data.output,
  shellOutput: result2.data.output 
};
```

## SSH Access to Containers

### Connecting to a Container

When a container is created, you'll receive SSH connection details:

```
ssh root@localhost -p {ssh_port}
```

Default credentials:
- Username: `root`
- Password: `password`

### Working with Container Shell

Once connected:
- The working directory is `/workspace`
- This is a persistent volume that survives container restarts
- All installed tools are available (git, curl, python, etc.)
- Use the shell as you would any Linux environment

## Best Practices

### Resource Management

- Always delete containers when they are no longer needed
- Create a cleanup workflow that runs periodically to delete abandoned containers
- Consider setting resource limits for containers in production

### Security

- For production, modify the container image to use random passwords
- Implement authentication for the API
- Consider using a firewall to restrict access to SSH ports

### Persistence

- Store important data in the `/workspace` directory
- Consider implementing container backup solutions for critical data
- Document container IDs and purposes for tracking

## Troubleshooting

### Container Creation Fails

If container creation fails:

1. Check Docker daemon status: `docker info`
2. Verify the images are built correctly: `docker images | grep ai-container`
3. Check Container Manager logs: `docker-compose logs ai-container-manager`
4. Ensure the Docker socket is accessible: `ls -l /var/run/docker.sock`

### API Connection Issues

If you can't connect to the API:

1. Verify the Container Manager is running: `docker-compose ps`
2. Check if the port is accessible: `curl http://localhost:5000/api/containers`
3. Check network configuration in docker-compose.yml

### SSH Connection Problems

If SSH connections fail:

1. Verify the container is running: `docker ps | grep ai-container`
2. Check if the SSH port is mapped correctly: `docker port <container_name>`
3. Try connecting with verbose output: `ssh -v root@localhost -p <port>`
4. Check container logs: `docker logs <container_name>`

### Command Execution Issues

If command execution fails:

1. Verify the container is running: `GET /api/containers`
2. Try a simple command first (e.g., `echo hello`)
3. Check for missing dependencies in the container
4. Check the Container Manager logs for errors

**Shell Builtin Command Issues:**

If commands involving `cd`, shell features, or environment variables fail:

1. Make sure you're wrapping the command with `/bin/bash -c`, e.g.:
   ```json
   { "command": "/bin/bash -c 'cd ~ && pwd'" }
   ```
2. Escape quotes properly within the shell command:
   ```json
   { "command": "/bin/bash -c 'echo \"Hello, world!\"'" }
   ```
3. For complex commands with multiple quotes, consider alternative quoting:
   ```json
   { "command": "/bin/bash -c 'find . -name \"*.txt\" -exec grep \"search term\" {} \\;'" }
   ```
4. Remember that commands are executed in a new shell instance each time (no state is maintained between commands)