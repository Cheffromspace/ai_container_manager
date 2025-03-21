#!/usr/bin/env python3
"""
API proxy to replace the container manager's exec endpoint
This will intercept requests to the exec endpoint and use direct Docker commands instead
"""
import argparse
import json
import subprocess
import http.server
import socketserver
import urllib.parse
from urllib.request import Request, urlopen
import re
import threading
import logging
from core.utils import validate_container_identifier

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global settings
PROXY_PORT = 5001
TARGET_API = "http://localhost:5000"

def find_docker_binary():
    """
    Find the docker binary path
    
    Returns:
        str or None: Path to the docker binary if found, None otherwise
    """
    docker_paths = ["/usr/bin/docker", "/usr/local/bin/docker", "docker"]
    for path in docker_paths:
        try:
            result = subprocess.run([path, "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                return path
        except FileNotFoundError:
            continue
    return None

# Using validate_container_identifier from core.utils

class DirectExecutor:
    @staticmethod
    def exec_command(container_identifier, command):
        """Execute a command in a container using Docker directly
        
        Args:
            container_identifier: Either a container ID or name
            command: The command to execute
        """
        # Validate the identifier
        if not validate_container_identifier(container_identifier):
            logger.warning(f"Invalid container identifier format: {container_identifier}")
            return {
                "exit_code": 1,
                "output": f"Error: Invalid container identifier format: {container_identifier}"
            }
        
        # Always use bash -c to ensure shell builtins work
        # Find docker binary path
        docker_path = find_docker_binary()
        if not docker_path:
            return {
                "exit_code": 1,
                "output": "Error: Docker command not found. Please ensure Docker is installed and in the PATH."
            }
        
        # First determine if we're dealing with a container ID or name
        container_exists_by_id = False
        container_exists_by_name = False
        actual_container_id = container_identifier
        
        # Check if the container exists by ID first
        try:
            check_cmd = [docker_path, "ps", "-a", "--filter", f"id={container_identifier}", "--format", "{{.ID}}"]
            result = subprocess.run(check_cmd, capture_output=True, text=True)
            if result.stdout.strip():
                container_exists_by_id = True
        except Exception as e:
            logger.error(f"Error checking container by ID: {str(e)}")
            # Continue to next method
                
        # If not found by ID, try to find by name with exact matching
        if not container_exists_by_id:
            try:
                # Get all container IDs and names for exact matching
                check_cmd = [docker_path, "ps", "-a", "--format", "{{.ID}}|{{.Names}}"]
                result = subprocess.run(check_cmd, capture_output=True, text=True)
                
                # Parse the output into a dictionary of names to IDs
                containers = {}
                for line in result.stdout.strip().split('\n'):
                    if line and '|' in line:
                        container_id, container_name = line.split('|', 1)
                        containers[container_name] = container_id
                
                # Check for exact name match
                if container_identifier in containers:
                    container_exists_by_name = True
                    actual_container_id = containers[container_identifier]
                # Try with ai-container- prefix if not already using it
                elif not container_identifier.startswith("ai-container-"):
                    prefixed_name = f"ai-container-{container_identifier}"
                    if prefixed_name in containers:
                        container_exists_by_name = True
                        actual_container_id = containers[prefixed_name]
            except Exception as e:
                logger.error(f"Error checking container by name: {str(e)}")
                # Continue to next method
                    
        # If container not found by any method, return error
        if not container_exists_by_id and not container_exists_by_name:
            return {
                "exit_code": 1,
                "output": f"Error: Container '{container_identifier}' not found."
            }
                    
        # Execute the command using the determined container identifier
        try:
            exec_cmd = [docker_path, "exec", actual_container_id, "/bin/bash", "-c", command]
            result = subprocess.run(exec_cmd, capture_output=True, text=True)
            
            # Format the response like the API would
            return {
                "exit_code": result.returncode,
                "output": result.stdout if result.stdout else result.stderr if result.stderr else ""
            }
        except FileNotFoundError:
            return {
                "exit_code": 1,
                "output": "Error: Docker command not found. Please ensure Docker is installed and in the PATH."
            }
        except Exception as e:
            return {
                "exit_code": 1,
                "output": f"Error: {str(e)}"
            }

class APIProxyHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        """Forward GET requests to the target API"""
        self.proxy_request("GET")
    
    def do_POST(self):
        """Handle POST requests - intercept exec endpoints, forward others"""
        # Check if this is an exec endpoint
        exec_pattern = r'/api/containers/(?:exec/)?([^/]+)/exec'
        match = re.match(exec_pattern, self.path)
        
        if match:
            # This is an exec endpoint, handle it directly
            container_id = match.group(1)
            self.handle_exec(container_id)
        else:
            # Forward to the original API
            self.proxy_request("POST")
    
    def handle_exec(self, container_id):
        """Handle the exec endpoint directly using Docker"""
        # Get the request body
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length).decode('utf-8')
        
        try:
            # Parse the JSON body
            data = json.loads(body)
            command = data.get("command")
            
            if not command:
                self.send_error(400, "Command is required")
                return
            
            # Execute the command
            logger.info(f"Executing command in container {container_id}: {command}")
            result = DirectExecutor.exec_command(container_id, command)
            
            # Send the response
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode('utf-8'))
            
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON body")
        except Exception as e:
            self.send_error(500, f"Internal server error: {str(e)}")
    
    def proxy_request(self, method):
        """Forward a request to the target API"""
        # Construct the target URL
        target_url = f"{TARGET_API}{self.path}"
        
        # Get headers and body if needed
        headers = {key: value for key, value in self.headers.items()}
        body = None
        
        if method == "POST" and 'Content-Length' in self.headers:
            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length)
        
        # Create and send the request
        req = Request(target_url, data=body, headers=headers, method=method)
        
        try:
            with urlopen(req) as response:
                # Copy response status and headers
                self.send_response(response.status)
                for header, value in response.getheaders():
                    self.send_header(header, value)
                self.end_headers()
                
                # Copy response body
                self.wfile.write(response.read())
        except Exception as e:
            self.send_error(502, f"Error forwarding request: {str(e)}")

def check_container_exists(container_identifier):
    """Check if a container exists by ID or name
    
    Args:
        container_identifier: Either a container ID or name
        
    Returns:
        bool: True if container exists, False otherwise
    """
    # Validate the identifier
    if not validate_container_identifier(container_identifier):
        logger.warning(f"Invalid container identifier format: {container_identifier}")
        return False
    
    # Find the docker binary
    docker_path = find_docker_binary()
    if not docker_path:
        logger.error("Docker binary not found")
        return False
    
    # Try to find by ID first - this is already exact matching
    try:
        cmd = [docker_path, "ps", "-a", "--filter", f"id={container_identifier}", "--format", "{{.ID}}"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.stdout.strip() != "":
            return True
    except FileNotFoundError:
        logger.error("Docker command not found")
        return False
    except Exception as e:
        logger.error(f"Error checking container by ID: {str(e)}")
        # Continue to next method
    
    # If not found by ID, get all containers and check for exact name matches
    try:
        # Get all container IDs and names
        cmd = [docker_path, "ps", "-a", "--format", "{{.Names}}"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        container_names = [name.strip() for name in result.stdout.strip().split('\n') if name.strip()]
        
        # Check for exact name match
        if container_identifier in container_names:
            return True
            
        # Try with ai-container- prefix if not already using it
        if not container_identifier.startswith("ai-container-"):
            prefixed_name = f"ai-container-{container_identifier}"
            if prefixed_name in container_names:
                return True
    except Exception as e:
        logger.error(f"Error checking container by name: {str(e)}")
    
    # If we get here, the container wasn't found
    return False

def print_usage_instructions():
    print(f"\nAPI Proxy is running on port {PROXY_PORT}")
    print(f"Forwarding to {TARGET_API} for all endpoints except container exec")
    print(f"Container exec requests will be handled directly using Docker\n")
    print("Usage:")
    print(f"  1. Change your API calls to use port {PROXY_PORT} instead of 5000")
    print(f"  2. Example: http://localhost:{PROXY_PORT}/api/containers/YOUR_CONTAINER_ID/exec")
    print("  3. Commands will be executed using /bin/bash -c to ensure shell builtins work\n")
    print("To stop the proxy, press Ctrl+C")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="API proxy for the container manager")
    parser.add_argument("--port", type=int, default=5001, help=f"Port to run the proxy on (default: {PROXY_PORT})")
    parser.add_argument("--target", default=TARGET_API, help=f"Target API URL (default: {TARGET_API})")
    
    args = parser.parse_args()
    PROXY_PORT = args.port
    TARGET_API = args.target
    
    # Start the proxy server
    with socketserver.TCPServer(("", PROXY_PORT), APIProxyHandler) as httpd:
        print_usage_instructions()
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down the proxy...")
            httpd.shutdown()