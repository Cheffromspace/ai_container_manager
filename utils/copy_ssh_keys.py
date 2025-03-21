#!/usr/bin/env python3
"""
Utility script to copy SSH keys from host to container.
This script can be called from n8n to execute the host-side script.
"""
import sys
import os
import subprocess
import logging

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('ssh_key_copy')

def copy_ssh_keys(container_name):
    """Copy SSH keys from host to the specified container."""
    if not container_name:
        logger.error("Container name not provided")
        return {"success": False, "error": "Container name is required"}
    
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "host_ssh_copy.sh")
    
    try:
        logger.info(f"Copying SSH keys to container {container_name}")
        result = subprocess.run([script_path, container_name], 
                               capture_output=True, text=True, check=True)
        logger.info(f"SSH key copy completed: {result.stdout}")
        return {"success": True, "message": result.stdout}
    except subprocess.CalledProcessError as e:
        logger.error(f"Error copying SSH keys: {e.stderr}")
        return {"success": False, "error": e.stderr}
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python copy_ssh_keys.py container_name")
        sys.exit(1)
    
    result = copy_ssh_keys(sys.argv[1])
    if result["success"]:
        print(result["message"])
        sys.exit(0)
    else:
        print(f"Error: {result['error']}")
        sys.exit(1)