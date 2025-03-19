#!/usr/bin/env python3
"""
This script modifies the app.py file inside the ai-container-manager container
to always use bash -c for command execution.
"""
import subprocess
import sys
import tempfile
import os

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

if __name__ == "__main__":
    print("Starting direct fix for container exec issue...")
    success = fix_container_manager()
    
    if success:
        print("\nFix applied successfully. The container manager has been restarted.")
        print("Please test again with:")
        print("  python3 test_cd_cases.py")
    else:
        print("\nFailed to apply the fix. Please check the error messages above.")
        sys.exit(1)