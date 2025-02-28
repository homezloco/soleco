"""
Simple script to restart the server using restart_server.sh
"""

import os
import subprocess
import sys

def restart_server():
    """Execute the restart_server.sh script"""
    try:
        # Get the directory containing this script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Build path to restart_server.sh
        restart_script = os.path.join(script_dir, 'restart_server.sh')
        
        # Use bash to execute the script
        result = subprocess.run(
            ['bash', restart_script],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Print output
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
            
        return result.returncode
        
    except subprocess.CalledProcessError as e:
        print(f"Error executing restart_server.sh: {e}", file=sys.stderr)
        if e.stdout:
            print(e.stdout)
        if e.stderr:
            print(e.stderr, file=sys.stderr)
        return e.returncode
        
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(restart_server())
