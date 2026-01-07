"""
Script to start all backend servers simultaneously
"""
import subprocess
import sys
import os
from pathlib import Path

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent
BACKEND_DIR = PROJECT_ROOT / "backend"

# Define all server paths
SERVERS = [
    ("TCP Chat Server", BACKEND_DIR / "tcp_chat" / "server.py"),
    ("File Transfer Server", BACKEND_DIR / "file_transfer" / "server.py"),
    ("Collab Server", BACKEND_DIR / "collab" / "server.py"),
    ("Code Exec Server", BACKEND_DIR / "code_exec" / "server.py"),
    ("Room MGMT Server", BACKEND_DIR / "room_mgmt" / "server.py"),
]

def start_servers():
    """Start all servers in separate terminal windows"""
    processes = []
    
    print("Starting all backend servers...")
    print("-" * 50)
    
    for name, server_path in SERVERS:
        if not server_path.exists():
            print(f"❌ {name}: File not found at {server_path}")
            continue
        
        try:
            # For Windows, use 'start' command to open in new cmd window
            if sys.platform == "win32":
                cmd = f'start cmd /k "python {server_path}"'
                subprocess.Popen(cmd, shell=True, cwd=server_path.parent)
            else:
                # For Unix-like systems
                subprocess.Popen(
                    [sys.executable, str(server_path)],
                    cwd=str(server_path.parent)
                )
            
            print(f"✓ {name}: Started")
        except Exception as e:
            print(f"❌ {name}: Failed to start - {e}")
    
    print("-" * 50)
    print("All servers have been launched!")
    print("Each server is running in its own terminal window.")
    print("Close the terminal windows to stop the servers.")

if __name__ == "__main__":
    start_servers()
