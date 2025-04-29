#!/usr/bin/env python3
"""
Fallback Docker CLI implementation when the Docker Python SDK doesn't work
"""
import subprocess
import json
import logging
import time
from typing import Dict, List, Optional, Tuple, Any

# Configure logging
logger = logging.getLogger(__name__)

class DockerCLIClient:
    """Docker CLI wrapper class for Docker operations when the SDK fails"""
    
    def __init__(self, docker_binary: str = "docker"):
        """Initialize with the docker binary path"""
        self.docker_binary = docker_binary
        self.api_version = self._get_api_version()
        
    def _get_api_version(self) -> str:
        """Get the Docker API version"""
        try:
            result = subprocess.run(
                [self.docker_binary, "version", "--format", "{{.Server.APIVersion}}"],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except Exception as e:
            logger.error(f"Failed to get Docker API version: {str(e)}")
            return "unknown"
    
    def run_command(self, args: List[str], check: bool = True) -> subprocess.CompletedProcess:
        """Run a Docker command and return the result"""
        cmd = [self.docker_binary] + args
        logger.debug(f"Running Docker command: {' '.join(cmd)}")
        return subprocess.run(cmd, capture_output=True, text=True, check=check)
    
    def list_containers(self, all: bool = False, filters: Dict[str, str] = None) -> List[Dict[str, Any]]:
        """List containers with similar interface to Docker SDK"""
        args = ["ps", "--format", "{{json .}}"]
        
        if all:
            args.append("-a")
            
        if filters:
            for key, value in filters.items():
                args.extend(["--filter", f"{key}={value}"])
                
        try:
            result = self.run_command(args)
            
            containers = []
            for line in result.stdout.splitlines():
                if line.strip():
                    try:
                        container_data = json.loads(line)
                        # Convert to format similar to Docker SDK
                        container = {
                            "id": container_data.get("ID", ""),
                            "name": container_data.get("Names", ""),
                            "status": container_data.get("Status", "").lower(),
                            "image": container_data.get("Image", ""),
                            "command": container_data.get("Command", ""),
                            "created_at": container_data.get("CreatedAt", ""),
                        }
                        containers.append(container)
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse container JSON: {line}")
                        
            return containers
        except Exception as e:
            logger.error(f"Error listing containers with Docker CLI: {str(e)}")
            return []
    
    def get_container(self, container_id: str) -> Optional[Dict[str, Any]]:
        """Get a container by ID or name"""
        args = ["inspect", container_id]
        try:
            result = self.run_command(args)
            container_data = json.loads(result.stdout)
            if container_data and len(container_data) > 0:
                return container_data[0]
            return None
        except Exception as e:
            logger.error(f"Failed to get container {container_id}: {str(e)}")
            return None
            
    def stop_container(self, container_id: str, timeout: int = 10) -> bool:
        """Stop a container"""
        args = ["stop", f"--time={timeout}", container_id]
        try:
            self.run_command(args)
            return True
        except Exception as e:
            logger.error(f"Failed to stop container {container_id}: {str(e)}")
            return False
            
    def remove_container(self, container_id: str, force: bool = False) -> bool:
        """Remove a container"""
        args = ["rm"]
        if force:
            args.append("--force")
        args.append(container_id)
        
        try:
            self.run_command(args)
            return True
        except Exception as e:
            logger.error(f"Failed to remove container {container_id}: {str(e)}")
            return False
            
    def restart_container(self, container_id: str, timeout: int = 10) -> bool:
        """Restart a container"""
        args = ["restart", f"--time={timeout}", container_id]
        try:
            self.run_command(args)
            return True
        except Exception as e:
            logger.error(f"Failed to restart container {container_id}: {str(e)}")
            return False
            
    def exec_run(self, container_id: str, cmd: List[str]) -> Tuple[int, str]:
        """Run a command in a container"""
        args = ["exec", container_id] + cmd
        try:
            result = self.run_command(args, check=False)
            output = result.stdout
            if result.stderr:
                output += f"\nSTDERR: {result.stderr}"
            return result.returncode, output
        except Exception as e:
            logger.error(f"Failed to exec in container {container_id}: {str(e)}")
            return 1, str(e)
            
    def create_container(self, image: str, name: str = None, detach: bool = True, 
                       ports: Dict[str, Any] = None, volumes: Dict[str, Dict[str, str]] = None,
                       environment: Dict[str, str] = None, user: str = None) -> Optional[Dict[str, Any]]:
        """Create and run a container using Docker CLI
        
        Args:
            image: The image to use
            name: Optional container name
            detach: Run in detached mode
            ports: Port mapping dict like {'5000/tcp': 11001}
            volumes: Volume mapping dict
            environment: Environment variables
            user: User to run as
            
        Returns:
            Container info dict or None if failed
        """
        # Build docker run command
        args = ["run"]
        
        # Add detach flag
        if detach:
            args.append("-d")
            
        # Add name if provided
        if name:
            args.extend(["--name", name])
            
        # Add port mappings
        if ports:
            for container_port, host_port in ports.items():
                args.extend(["-p", f"{host_port}:{container_port}"])
                
        # Add volume mappings
        if volumes:
            for volume_name, volume_config in volumes.items():
                # Handle named volumes vs bind mounts
                if ':' in volume_name:
                    # This is already a bind format like "/host/path:/container/path"
                    args.extend(["-v", volume_name])
                else:
                    # This is a named volume configuration
                    bind_path = volume_config.get('bind')
                    mode = volume_config.get('mode', 'rw')
                    if bind_path:
                        args.extend(["-v", f"{volume_name}:{bind_path}:{mode}"])
                    else:
                        # Just a named volume without specific bind
                        args.extend(["-v", volume_name])
                        
        # Add environment variables
        if environment:
            for key, value in environment.items():
                args.extend(["-e", f"{key}={value}"])
                
        # Add user if provided
        if user:
            args.extend(["--user", user])
            
        # Add image as the last parameter
        args.append(image)
        
        # Run the container
        try:
            logger.info(f"Creating container from image {image} with name {name}")
            result = self.run_command(args)
            
            # Get the container ID from result
            container_id = result.stdout.strip()
            
            if not container_id:
                logger.error(f"Failed to create container - no container ID returned")
                return None
                
            # Inspect the created container to return info
            container_info = self.get_container(container_id)
            if container_info:
                # Create a simpler result structure
                return {
                    'id': container_info.get('Id', ''),
                    'name': container_info.get('Name', '').lstrip('/'),  # Docker prefixes names with /
                    'status': container_info.get('State', {}).get('Status', 'unknown'),
                    'created_at': container_info.get('Created'),
                }
            return None
            
        except Exception as e:
            logger.error(f"Failed to create container: {str(e)}")
            return None
            
    def find_available_port(self, start_port: int, end_port: int) -> int:
        """Find an available port in the given range using Docker CLI
        
        Args:
            start_port: The port to start checking from
            end_port: The port to check up to
            
        Returns:
            An available port number
            
        Raises:
            Exception: If no available port is found
        """
        import socket
        
        # Get list of currently used ports by Docker
        used_ports = set()
        
        # List all containers 
        containers = self.list_containers(all=True)
        
        # Extract used ports from container inspection
        for container in containers:
            container_id = container.get('id')
            if container_id:
                container_info = self.get_container(container_id)
                if container_info:
                    # Extract port bindings from HostConfig
                    port_bindings = container_info.get('HostConfig', {}).get('PortBindings', {})
                    
                    for _, host_bindings in port_bindings.items():
                        if host_bindings:
                            for binding in host_bindings:
                                host_port = binding.get('HostPort')
                                if host_port:
                                    try:
                                        used_ports.add(int(host_port))
                                    except (ValueError, TypeError):
                                        pass
        
        # Also check system ports using socket
        for port in range(start_port, end_port):
            # Skip if already identified as in use by Docker
            if port in used_ports:
                continue
                
            # Check if port is in use by the system
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(('localhost', port)) != 0:
                    # Port is available
                    return port
                    
        # If we get here, no port is available
        raise Exception(f"No available port found in range {start_port}-{end_port}")
    
    def containers(self):
        """Container compatibility object for Docker SDK"""
        return ContainersManager(self)

class ContainersManager:
    """Container manager to provide a similar interface to Docker SDK's containers collection"""
    
    def __init__(self, client):
        """Initialize with a DockerCLIClient instance"""
        self.client = client
        
    def get(self, container_id):
        """Get a container by ID or name"""
        container_info = self.client.get_container(container_id)
        if container_info:
            return Container(self.client, container_info)
        return None
        
    def list(self, all=False, filters=None):
        """List containers"""
        containers = []
        for container_data in self.client.list_containers(all=all, filters=filters):
            # Create Container wrapper objects
            container_id = container_data.get('id')
            if container_id:
                # Get full container info
                container_info = self.client.get_container(container_id)
                if container_info:
                    containers.append(Container(self.client, container_info))
        return containers
        
    def run(self, image, name=None, detach=True, ports=None, volumes=None, environment=None, user=None):
        """Create and run a container"""
        container_info = self.client.create_container(
            image=image,
            name=name,
            detach=detach,
            ports=ports,
            volumes=volumes,
            environment=environment,
            user=user
        )
        
        if container_info:
            return Container(self.client, container_info)
        return None
        
class Container:
    """Container class to provide a similar interface to Docker SDK's Container class"""
    
    def __init__(self, client, container_info):
        """Initialize with a DockerCLIClient instance and container info"""
        self.client = client
        self.id = container_info.get('Id', container_info.get('id', ''))
        self.name = container_info.get('Name', container_info.get('name', '')).lstrip('/')
        self.status = container_info.get('State', {}).get('Status', container_info.get('status', 'unknown'))
        self._info = container_info
        
    def reload(self):
        """Reload container info"""
        container_info = self.client.get_container(self.id)
        if container_info:
            self._info = container_info
            self.status = container_info.get('State', {}).get('Status', 'unknown')
            
    def stop(self, timeout=10):
        """Stop the container"""
        return self.client.stop_container(self.id, timeout)
        
    def remove(self, force=False):
        """Remove the container"""
        return self.client.remove_container(self.id, force)
        
    def restart(self, timeout=10):
        """Restart the container"""
        return self.client.restart_container(self.id, timeout)
        
    def exec_run(self, cmd, **kwargs):
        """Run a command in the container"""
        if isinstance(cmd, str):
            cmd = [cmd]
        exit_code, output = self.client.exec_run(self.id, cmd)
        # Create a simple object to match the SDK interface
        return type('ExecResult', (), {'exit_code': exit_code, 'output': output})

# Create a global instance for easy import
docker_cli = DockerCLIClient()