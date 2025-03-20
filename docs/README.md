# AI Container Manager for n8n

This service allows n8n AI agents to create, manage, and interact with Docker containers on demand.

## Features

- Create containers on demand via REST API
- Each container has a persistent SSH session
- Execute commands within containers
- Manage multiple containers simultaneously
- Containers have persistent storage
- Automatic container expiration after 2 hours
- Container usage statistics and monitoring
- Bulk container cleanup

## Setup

1. Build the container manager service:

```bash
cd ai_container_manager
docker build -t ai-container-manager .
```

2. Build the AI container image:

```bash
cd ai_container_manager
docker build -t ai-container-image -f Dockerfile.container .
```

3. Start the container manager:

```bash
docker run -d --name ai-container-manager \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -p 5000:5000 \
  ai-container-manager
```

## API Reference

### List Containers

```
GET /api/containers
```

Returns a list of all active containers.

### Create Container

```
POST /api/containers
```

Creates a new container and returns its details including SSH connection info.

### Delete Container

```
DELETE /api/containers/{container_id}
```

Stops and removes the specified container.

### Execute Command

```
POST /api/containers/{container_id}/exec
```

Request body:
```json
{
  "command": "echo 'Hello, world!'"
}
```

Executes a command in the container and returns the result.

### Container Stats

```
GET /api/containers/stats
```

Returns statistics about container usage, including counts, ages, and expiration times.

Response:
```json
{
  "active_count": 3,
  "expiry_hours": 2,
  "containers": [
    {
      "id": "container-uuid",
      "name": "ai-container-12345678",
      "age_hours": 1.5,
      "expires_in_hours": 0.5
    }
  ]
}
```

### Cleanup Containers

```
POST /api/containers/cleanup
```

Stops and removes all active containers.

Response:
```json
{
  "message": "Cleanup completed. 3 containers removed, 0 failed.",
  "success_count": 3,
  "fail_count": 0
}
```

## Integration with n8n

An example workflow is provided in the `n8n-example-workflow.json` file. Import this into your n8n instance to get started.

Use the HTTP Request node in n8n to interact with the Container Manager API. For example:

1. To create a container:
   - Method: POST
   - URL: http://localhost:5000/api/containers

2. To execute a command:
   - Method: POST
   - URL: http://localhost:5000/api/containers/{container_id}/exec
   - Body: {"command": "your_command_here"}

3. To delete a container:
   - Method: DELETE
   - URL: http://localhost:5000/api/containers/{container_id}
   
4. To get container stats:
   - Method: GET
   - URL: http://localhost:5000/api/containers/stats

5. To clean up all containers:
   - Method: POST
   - URL: http://localhost:5000/api/containers/cleanup

## Security Considerations

- Container passwords are fixed for simplicity but should be randomized in production
- Consider implementing authentication for the API
- Container resource limits should be implemented for production use# ai_container_manager
