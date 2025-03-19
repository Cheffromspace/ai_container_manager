#!/usr/bin/env python3
"""
Direct executor for container commands, bypassing the API
Works directly with Docker to ensure shell builtins like 'cd' work correctly
"""
import subprocess
import json
import sys
import argparse

def run_command(cmd, capture=True):
    """Run a command and return the output"""
    try:
        if capture:
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode, result.stdout, result.stderr
        else:
            result = subprocess.run(cmd)
            return result.returncode, None, None
    except Exception as e:
        return 1, None, str(e)

def get_container_id_from_name(container_name):
    """Get full container ID from name"""
    code, stdout, stderr = run_command(["docker", "ps", "-q", "-f", f"name={container_name}"])
    if code != 0 or not stdout:
        print(f"Error finding container: {stderr}")
        return None
    return stdout.strip()

def exec_container_command(container_id, command):
    """Execute a command in a container"""
    # Always use bash -c to ensure shell builtins work
    exec_cmd = ["docker", "exec", container_id, "/bin/bash", "-c", command]
    print(f"Executing: {' '.join(exec_cmd)}")
    
    code, stdout, stderr = run_command(exec_cmd)
    
    print(f"Exit code: {code}")
    if stdout:
        print(f"STDOUT:\n{stdout}")
    if stderr:
        print(f"STDERR:\n{stderr}")
    
    # Format the response like the API would
    response = {
        "exit_code": code,
        "output": stdout if stdout else stderr if stderr else ""
    }
    
    if args.json:
        # Only output the JSON response
        print(json.dumps(response))
    
    return code == 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Execute commands in Docker containers with proper shell support")
    parser.add_argument("container", help="Container ID or name")
    parser.add_argument("command", nargs="+", help="Command to execute")
    parser.add_argument("--json", action="store_true", help="Output in JSON format like the API")
    
    args = parser.parse_args()
    
    # Join the command parts back together
    command = " ".join(args.command)
    container_id = args.container
    
    # If it looks like a short name, try to get the full ID
    if not container_id.startswith("sha256:") and len(container_id) < 32:
        # Check if it's the full container name
        if not container_id.startswith("ai-container-"):
            container_name = f"ai-container-{container_id}"
        else:
            container_name = container_id
            
        print(f"Looking up container ID for {container_name}...")
        full_id = get_container_id_from_name(container_name)
        if full_id:
            container_id = full_id
            print(f"Using container ID: {container_id}")
    
    exec_container_command(container_id, command)