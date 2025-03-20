#!/usr/bin/env python3
"""
This script provides two approaches to fix Docker command execution:
1. Container modification: Changes app.py inside the container to always use bash -c
2. External proxy: Uses a wrapper script and API proxy for Docker command handling
"""
import subprocess
import sys
import tempfile
import os
import time
import signal
import json
import requests
import shutil
from threading import Thread
import socket
import urllib.request

def run_command(cmd, capture=True):
    """Run a command and return the output"""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=capture, text=True)
    if result.returncode != 0:
        print(f"Command failed with code {result.returncode}")
        if result.stderr:
            print(f"Error: {result.stderr}")
        return None
    return result.stdout if capture else None

def fix_container_manager():
    """Copy the app.py file from the container, modify it, and copy it back"""
    # Temporary file to store app.py
    with tempfile.NamedTemporaryFile(delete=False, suffix='.py') as temp_file:
        temp_filename = temp_file.name
    
    try:
        # Copy app.py from the container
        print("Copying app.py from the container...")
        run_command(['docker', 'cp', 'ai-container-manager:/app/app.py', temp_filename], capture=False)
        
        # Read the file
        with open(temp_filename, 'r') as f:
            content = f.read()
        
        # Look for the exec function and the needs_shell logic
        exec_route = '@app.route(\'/api/containers/<container_id>/exec\''
        old_pattern = """        # Check for shell builtin commands like cd, source, etc.
        # or complex commands with shell operators
        shell_builtins = ['cd ', 'cd\\n', ' cd ', 'source ', 'export ', 'unset ', 'alias ', 'echo $', 'cd;', 'cd)']
        shell_operators = ['&&', '||', ';', '|', '>', '<', '<<', '>>', '`']
        
        # Check if command needs a shell
        needs_shell = command == 'cd' or any(builtin in command for builtin in shell_builtins) or any(op in command for op in shell_operators)
        
        logger.info(f"Executing command: {command}")
        logger.info(f"Needs shell: {needs_shell}")
        
        if needs_shell:
            # This is a shell builtin or a complex command that needs a shell interpreter
            logger.info(f"Executing as shell command using bash -c: {command}")
            # Use bash explicitly with the command as an argument
            exec_result = container.exec_run(
                ["/bin/bash", "-c", command],
                demux=True,  # Split stdout and stderr 
                tty=True     # Use a TTY for interactive commands
            )
        else:
            # Regular command without shell features
            logger.info(f"Executing as regular command: {command}")
            # For regular commands, we can either pass them directly or with shell=True
            exec_result = container.exec_run(
                command,
                demux=True,
                tty=True
            )"""
        
        # New simplified code that always uses bash -c
        new_pattern = """        # SIMPLIFIED: Always use bash -c for all commands
        # This ensures shell builtins like 'cd' always work properly
        logger.info(f"Executing command: {command}")
        
        # Always use bash explicitly with the command as an argument
        exec_result = container.exec_run(
            ["/bin/bash", "-c", command],
            demux=True,  # Split stdout and stderr 
            tty=True     # Use a TTY for interactive commands
        )"""
        
        # Check if the file contains the old pattern or something similar
        if old_pattern in content:
            print("Found the exact pattern to replace")
            new_content = content.replace(old_pattern, new_pattern)
        else:
            print("Could not find the exact pattern to replace")
            # Look for the pattern more flexibly
            if "needs_shell =" in content and "if needs_shell:" in content:
                print("Found the needs_shell logic, proceeding with manual replacement")
                
                # Find the beginning of the command execution logic
                start_idx = content.find("        # Get container")
                if start_idx == -1:
                    print("Could not find the start of the command execution logic")
                    return False
                
                # Find the end of the command execution logic (before output processing)
                end_idx = content.find("        # Process the output", start_idx)
                if end_idx == -1:
                    print("Could not find the end of the command execution logic")
                    return False
                
                # Replace the entire section
                new_content = content[:start_idx] + """        # Get container
        container_info = active_containers[container_id]
        container = container_info['container_obj']
        
        # SIMPLIFIED: Always use bash -c for all commands
        # This ensures shell builtins like 'cd' always work properly
        logger.info(f"Executing command: {command}")
        
        # Always use bash explicitly with the command as an argument
        exec_result = container.exec_run(
            ["/bin/bash", "-c", command],
            demux=True,  # Split stdout and stderr 
            tty=True     # Use a TTY for interactive commands
        )
""" + content[end_idx:]
            else:
                print("Could not find the command execution logic to replace")
                return False
        
        # Write the modified content back to the file
        with open(temp_filename, 'w') as f:
            f.write(new_content)
        
        # Copy the modified file back to the container
        print("Copying modified app.py back to the container...")
        run_command(['docker', 'cp', temp_filename, 'ai-container-manager:/app/app.py'], capture=False)
        
        # Restart the container
        print("Restarting container manager...")
        run_command(['docker', 'restart', 'ai-container-manager'], capture=False)
        
        print("\nFix applied successfully!")
        print("The container manager now always uses bash -c for executing commands.")
        print("This should fix the issue with cd and other shell builtin commands.")
        
        return True
    
    except Exception as e:
        print(f"Error: {e}")
        return False
    
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_filename):
            os.unlink(temp_filename)

def setup_wrapper_script():
    """Ensure the docker wrapper script is setup correctly"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    wrapper_path = os.path.join(script_dir, "docker_wrapper.sh")
    
    if not os.path.exists(wrapper_path):
        print(f"ERROR: Wrapper script not found at {wrapper_path}")
        return False
    
    try:
        # Make sure the script is executable
        os.chmod(wrapper_path, 0o755)
        print(f"Made wrapper script executable: {wrapper_path}")
        
        # Test the script
        result = subprocess.run([wrapper_path, "version"], 
                               capture_output=True, 
                               text=True, 
                               timeout=5)
        
        if result.returncode == 0:
            print("✅ Docker wrapper script is working correctly")
            return True
        else:
            print(f"❌ Docker wrapper script test failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error setting up wrapper script: {str(e)}")
        return False

def check_api_proxy():
    """Check if the API proxy is running"""
    try:
        response = requests.get("http://localhost:5001/api/containers", timeout=2)
        if response.status_code == 200:
            print("✅ API proxy is already running")
            return True
    except:
        print("API proxy is not running")
    
    return False

def start_api_proxy():
    """Start the API proxy in the background"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    proxy_script = os.path.join(script_dir, "docker_api_proxy.py")
    
    if not os.path.exists(proxy_script):
        print(f"❌ API proxy script not found at {proxy_script}")
        return False
    
    try:
        print(f"Starting API proxy from {proxy_script}")
        # Start the proxy in the background
        subprocess.Popen([sys.executable, proxy_script], 
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
        
        # Wait for the proxy to start
        for _ in range(5):
            time.sleep(1)
            if check_api_proxy():
                return True
        
        print("❌ Failed to start API proxy")
        return False
    except Exception as e:
        print(f"❌ Error starting API proxy: {str(e)}")
        return False

def apply_proxy_fix():
    """Apply the proxy-based fix"""
    print("\n--- Setting up Docker API Proxy ---\n")
    
    # Setup the wrapper script
    if not setup_wrapper_script():
        print("Failed to setup wrapper script, aborting")
        return False
    
    # Start the API proxy if not running
    if not check_api_proxy():
        if not start_api_proxy():
            print("Failed to start API proxy, aborting")
            return False
    
    print("\n✅ Proxy fix applied successfully!")
    print("The API proxy is running on port 5001")
    print("Use this port for all API requests to ensure Docker commands work")
    print("Example: curl http://localhost:5001/api/containers")
    return True

if __name__ == "__main__":
    print("Starting fix for Docker container exec issue...")
    print("This script offers two fix options:")
    print("1. Direct container fix (modifies app.py inside the container)")
    print("2. Proxy-based fix (starts an API proxy that handles Docker commands)")
    
    while True:
        choice = input("\nWhich fix would you like to apply? (1, 2, or q to quit): ")
        
        if choice == "q":
            print("Exiting without applying any fix.")
            sys.exit(0)
        elif choice == "1":
            success = fix_container_manager()
            break
        elif choice == "2":
            success = apply_proxy_fix()
            break
        else:
            print("Invalid choice. Please enter 1, 2, or q.")
    
    if success:
        print("\nFix applied successfully.")
        print("Please test with:")
        print("  python3 test_cd_cases.py")
    else:
        print("\nFailed to apply the fix. Please check the error messages above.")
        sys.exit(1)