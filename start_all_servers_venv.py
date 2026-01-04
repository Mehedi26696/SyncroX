"""
Script to start all backend servers using virtual environment Python
"""
import subprocess
import sys
import os
from pathlib import Path

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent
BACKEND_DIR = PROJECT_ROOT / "backend"

# Virtual environment paths (adjust if your venv has a different name)
VENV_DIR = PROJECT_ROOT / "venv"

# Determine Python executable path based on OS
if sys.platform == "win32":
    VENV_PYTHON = VENV_DIR / "Scripts" / "python.exe"
else:
    VENV_PYTHON = VENV_DIR / "bin" / "python"

# Define all server paths
SERVERS = [
    ("TCP Chat Server", BACKEND_DIR / "tcp_chat" / "server.py", 9009),
    ("File Transfer Server", BACKEND_DIR / "file_transfer" / "server.py", 9010),
    ("Collab Server", BACKEND_DIR / "collab" / "server.py", 9011),
    ("Code Exec Server", BACKEND_DIR / "code_exec" / "server.py", 9012),
]

def check_venv():
    """Check if virtual environment exists"""
    if not VENV_DIR.exists():
        print(f"❌ Virtual environment not found at: {VENV_DIR}")
        print("\nTo create a virtual environment, run:")
        print(f"    python -m venv venv")
        print(f"    .\\venv\\Scripts\\activate  (Windows)")
        print(f"    pip install -r requirements.txt")
        return False
    
    if not VENV_PYTHON.exists():
        print(f"❌ Python executable not found at: {VENV_PYTHON}")
        return False
    
    print(f"✓ Virtual environment found: {VENV_DIR}")
    print(f"✓ Python executable: {VENV_PYTHON}")
    return True

def start_servers():
    """Start all servers in separate terminal windows using venv Python"""
    
    if not check_venv():
        sys.exit(1)
    
    print("\n" + "=" * 50)
    print("Starting all backend servers with venv...")
    print("=" * 50 + "\n")
    
    started_count = 0
    
    for name, server_path, port in SERVERS:
        if not server_path.exists():
            print(f"❌ {name}: File not found at {server_path}")
            continue
        
        try:
            if sys.platform == "win32":
                # Windows: Open each server in a new CMD window with venv Python
                cmd = f'start "{name} (Port {port})" cmd /k ""{VENV_PYTHON}" "{server_path}""'
                subprocess.Popen(cmd, shell=True, cwd=str(server_path.parent))
            else:
                # Unix/Linux/Mac: Use gnome-terminal, xterm, or run in background
                subprocess.Popen(
                    [str(VENV_PYTHON), str(server_path)],
                    cwd=str(server_path.parent),
                    start_new_session=True
                )
            
            print(f"✓ {name} (Port {port}): Started")
            started_count += 1
        except Exception as e:
            print(f"❌ {name}: Failed to start - {e}")
    
    print("\n" + "=" * 50)
    print(f"Started {started_count}/{len(SERVERS)} servers")
    print("=" * 50)
    print("\nEach server is running in its own terminal window.")
    print("Close the terminal windows to stop the servers.")
    print("\nServer Ports:")
    print("  - TCP Chat:      http://localhost:9009")
    print("  - File Transfer: http://localhost:9010")
    print("  - Collab:        http://localhost:9011")
    print("  - Code Exec:     http://localhost:9012")

def start_frontend():
    """Optionally start the Streamlit frontend"""
    frontend_path = PROJECT_ROOT / "frontend" / "app.py"
    
    if not frontend_path.exists():
        print(f"\n❌ Frontend not found at: {frontend_path}")
        return
    
    print("\n" + "=" * 50)
    print("Starting Streamlit Frontend...")
    print("=" * 50)
    
    try:
        if sys.platform == "win32":
            # Get streamlit from venv Scripts folder
            streamlit_exe = VENV_DIR / "Scripts" / "streamlit.exe"
            if streamlit_exe.exists():
                cmd = f'start "SyncroX Frontend" cmd /k ""{streamlit_exe}" run "{frontend_path}""'
            else:
                # Fallback: use python -m streamlit
                cmd = f'start "SyncroX Frontend" cmd /k ""{VENV_PYTHON}" -m streamlit run "{frontend_path}""'
            subprocess.Popen(cmd, shell=True, cwd=str(PROJECT_ROOT))
        else:
            subprocess.Popen(
                [str(VENV_PYTHON), "-m", "streamlit", "run", str(frontend_path)],
                cwd=str(PROJECT_ROOT),
                start_new_session=True
            )
        
        print("✓ Streamlit Frontend: Started")
        print("  - URL: http://localhost:8501")
    except Exception as e:
        print(f"❌ Frontend: Failed to start - {e}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Start SyncroX servers with venv")
    parser.add_argument(
        "--with-frontend", "-f",
        action="store_true",
        help="Also start the Streamlit frontend"
    )
    parser.add_argument(
        "--frontend-only",
        action="store_true", 
        help="Only start the Streamlit frontend"
    )
    
    args = parser.parse_args()
    
    if args.frontend_only:
        if check_venv():
            start_frontend()
    else:
        start_servers()
        if args.with_frontend:
            start_frontend()











# Start only backend servers
# python start_all_servers_venv.py

# Start backend servers + frontend
# python start_all_servers_venv.py --with-frontend

# Start only frontend
# python start_all_servers_venv.py --frontend-only