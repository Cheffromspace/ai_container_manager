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
import os
import sys
import shutil

# Global settings
PROXY_PORT = 5001
TARGET_API = "http://localhost:5000"

class DirectExecutor:
    @staticmethod
    def exec_command(container_id, command):
        """Execute a command in a container using Docker directly"""
        # Get the current directory where this script is located
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # Create path to the docker_wrapper.sh script
        wrapper_script = os.path.join(script_dir, "docker_wrapper.sh")
        
        try:
            # Ensure the wrapper script is executable
            os.chmod(wrapper_script, 0o755)
            
            # Use the wrapper script to execute docker commands
            exec_cmd = [wrapper_script, "exec", container_id, "/bin/bash", "-c", command]
            print(f"Executing via wrapper: {' '.join(exec_cmd)}")
            result = subprocess.run(exec_cmd, capture_output=True, text=True)
            
            # Format the response like the API would
            return {
                "exit_code": result.returncode,
                "output": result.stdout if result.stdout else result.stderr if result.stderr else ""
            }
        except FileNotFoundError as e:
            # The wrapper script or docker wasn't found
            print(f"Wrapper script error: {str(e)}")
            return {
                "exit_code": 1,
                "output": f"Error: Docker wrapper script not found or executable: {str(e)}"
            }
        except Exception as e:
            print(f"Execution error: {str(e)}")
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
            print(f"Executing command in container {container_id}: {command}")
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

def check_container_exists(container_id):
    """Check if a container exists"""
    # Get the current directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Create path to the docker_wrapper.sh script
    wrapper_script = os.path.join(script_dir, "docker_wrapper.sh")
    
    try:
        # Ensure the wrapper script is executable
        os.chmod(wrapper_script, 0o755)
        
        # Use the wrapper script to check if container exists
        cmd = [wrapper_script, "ps", "-a", "--filter", f"id={container_id}", "--format", "{{.ID}}"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout.strip() != ""
    except Exception as e:
        print(f"Error checking container existence: {str(e)}")
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
    
    # Debug info
    print(f"Starting API proxy with Docker wrapper support")
    
    # Check and validate the wrapper script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    wrapper_script = os.path.join(script_dir, "docker_wrapper.sh")
    
    if os.path.exists(wrapper_script):
        print(f"Docker wrapper script found at: {wrapper_script}")
        try:
            os.chmod(wrapper_script, 0o755)
            print("Made wrapper script executable")
            
            # Test the wrapper script
            test_cmd = [wrapper_script, "version"]
            print(f"Testing wrapper script with: {' '.join(test_cmd)}")
            try:
                result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    print("Wrapper script test successful!")
                    print(f"Docker version output: {result.stdout[:100]}...")
                else:
                    print(f"Wrapper script test failed with exit code {result.returncode}")
                    print(f"Error output: {result.stderr}")
            except Exception as e:
                print(f"Error testing wrapper script: {str(e)}")
        except Exception as e:
            print(f"Error setting permissions on wrapper script: {str(e)}")
    else:
        print(f"WARNING: Docker wrapper script not found at {wrapper_script}")
        print("The proxy may not function correctly without this script")
    
    # Also check regular docker command
    try:
        docker_path = shutil.which("docker")
        if docker_path:
            print(f"Docker binary found at: {docker_path}")
        else:
            print("Docker binary not found in PATH")
    except Exception as e:
        print(f"Error checking docker binary: {str(e)}")
    
    # Start the proxy server
    with socketserver.TCPServer(("", PROXY_PORT), APIProxyHandler) as httpd:
        print_usage_instructions()
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down the proxy...")
            httpd.shutdown()
