# SSH Key Management for AI Containers

This document explains two methods for managing SSH keys for AI containers.

## Method 1: Baking SSH Keys into Container Images

This method embeds the SSH keys into the container image during build time. It's secure because:
- Keys are only temporarily copied to a gitignored directory
- Keys are never committed to the repository
- Container images are built locally and not pushed to public registries

### How to Use:

1. Run the build script which will automatically prepare the SSH keys:
   ```bash
   cd /home/jonflatt/n8n/ai_container_manager/docker
   ./build-images.sh
   ```

2. The script will:
   - Copy SSH keys from your ~/.ssh directory to a temporary location
   - Build the container images with the keys included
   - Set proper permissions on the keys

### How it Works:

- `prepare_ssh_keys.sh` - Copies SSH keys to docker/ssh_keys_tmp/ (gitignored)
- Dockerfile.container - Includes COPY instructions for the SSH keys
- build-images.sh - Runs the preparation script before building images

## Method 2: Direct SSH Key Copying

This method copies SSH keys directly from the host to running containers. This is useful for:
- Adding SSH keys to containers that were created without keys
- Updating SSH keys in existing containers
- Using from n8n workflows to ensure containers can access Git repositories

### How to Use from Command Line:

```bash
cd /home/jonflatt/n8n/ai_container_manager/utils
./host_ssh_copy.sh container_name
```

### How to Use from Python:

```python
from ai_container_manager.utils.copy_ssh_keys import copy_ssh_keys

result = copy_ssh_keys("container_name")
if result["success"]:
    print("Keys copied successfully")
else:
    print(f"Error: {result['error']}")
```

### How to Use from n8n:

1. Create an Execute Command node
2. Set the command to:
   ```
   python /home/jonflatt/n8n/ai_container_manager/utils/copy_ssh_keys.py {{$node["Get Container Info"].json["container_name"]}}
   ```

## Troubleshooting

### Permissions Issues

If you encounter permissions issues:

1. Check that the SSH keys have the right ownership and permissions on the host:
   ```bash
   ls -la ~/.ssh/github-personal
   ```
   They should be owned by your user and have permissions 600.

2. Verify the container can access the keys:
   ```bash
   docker exec container_name ls -la /root/.ssh/
   ```

3. If keys are present but not working, check the SSH config in the container:
   ```bash
   docker exec container_name cat /root/.ssh/config
   ```

### Testing SSH Keys in Container

To test if the SSH keys are working correctly:

```bash
docker exec container_name ssh -T git@github.com
```

This should return a message like "Hi username! You've successfully authenticated..."