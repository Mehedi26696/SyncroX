
import subprocess
import time
import os
import sys
from pathlib import Path
import hashlib

# Add the current directory to sys.path so we can import client
sys.path.append(str(Path(__file__).parent))

from client import SyncroXFileClient

def calculate_sha256(data):
    return hashlib.sha256(data).hexdigest()

def test_transfer(algo="reno", loss_prob=0.1):
    print(f"\n--- Testing {algo.upper()} with Loss Prob {loss_prob} ---")
    
    # 1. Create a dummy file (approx 100KB)
    file_data = os.urandom(1024 * 100)
    filename = f"test_file_{algo}_{int(time.time())}.bin"
    room = "1234"
    
    # 2. Start server
    server_process = subprocess.Popen(
        [sys.executable, "server.py"],
        cwd=Path(__file__).parent,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1 # Line buffered
    )
    
    def log_server():
        for line in server_process.stdout:
            print(f"[SERVER] {line.strip()}")
            
    import threading
    threading.Thread(target=log_server, daemon=True).start()
    
    time.sleep(2) # Wait for server to start
    
    try:
        client = SyncroXFileClient(algo=algo)
        
        # 3. Upload
        print(f"Uploading {filename}...")
        start_time = time.time()
        result = client.upload_bytes(room, filename, file_data)
        upload_duration = time.time() - start_time
        print(f"Upload result: {result} (took {upload_duration:.2f}s)")
        
        if "OK" not in result:
            print("Upload failed!")
            return False
            
        # 4. List files
        files = client.list_files(room)
        print(f"Files in room {room}: {files}")
        
        # 5. Download
        print(f"Downloading {filename}...")
        start_time = time.time()
        downloaded_data = client.download_bytes(room, filename)
        download_duration = time.time() - start_time
        
        if downloaded_data is None:
            print("Download failed!")
            return False
            
        print(f"Download complete (took {download_duration:.2f}s)")
        
        # 6. Verify
        original_hash = calculate_sha256(file_data)
        downloaded_hash = calculate_sha256(downloaded_data)
        
        if original_hash == downloaded_hash:
            print("SUCCESS: Hashes match!")
            return True
        else:
            print(f"FAILURE: Hash mismatch!")
            print(f"Original: {original_hash}")
            print(f"Downloaded: {downloaded_hash}")
            return False
            
    finally:
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_process.kill()
        
        # Cleanup uploaded file if it exists
        upload_path = Path(__file__).parents[2] / "data" / "uploads" / room / filename
        if upload_path.exists():
            upload_path.unlink()

if __name__ == "__main__":
    # Test Reno
    reno_success = test_transfer(algo="reno", loss_prob=0.1)
    
    # Test Tahoe
    tahoe_success = test_transfer(algo="tahoe", loss_prob=0.1)
    
    print("\n=== Final Summary ===")
    print(f"Reno: {'PASSED' if reno_success else 'FAILED'}")
    print(f"Tahoe: {'PASSED' if tahoe_success else 'FAILED'}")
    
    if reno_success and tahoe_success:
        sys.exit(0)
    else:
        sys.exit(1)
