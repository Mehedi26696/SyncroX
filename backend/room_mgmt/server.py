import socket
import threading
import json
import random
import time
import os
import sys
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

HOST = "0.0.0.0"
PORT = 9013  # Room management port

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
ROOMS_FILE = DATA_DIR / "rooms.json"
os.makedirs(DATA_DIR, exist_ok=True)

# Centralized room store
# format: { "code": { "created_at": timestamp, "created_by": username } }
rooms = {}
lock = threading.Lock()

def load_rooms():
    if ROOMS_FILE.exists():
        try:
            with open(ROOMS_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_rooms():
    with open(ROOMS_FILE, "w") as f:
        json.dump(rooms, f, indent=2)

rooms = load_rooms()

def generate_code():
    while True:
        code = f"{random.randint(1000, 9999)}"
        if code not in rooms:
            return code

def handle_client(conn, addr):
    print(f"[ROOM_MGMT] Connection from {addr}")
    try:
        f = conn.makefile("rwb")
        while True:
            line = f.readline()
            if not line: break
            line = line.decode("utf-8").strip()
            if not line: continue

            parts = line.split()
            cmd = parts[0].upper()

            if cmd == "CREATE":
                # CREATE <username>
                username = parts[1] if len(parts) > 1 else "unknown"
                code = generate_code()
                with lock:
                    rooms[code] = {
                        "created_by": username,
                        "created_at": time.time()
                    }
                    save_rooms()
                conn.sendall(f"ROOM {code}\n".encode("utf-8"))
                print(f"[ROOM_MGMT] Created room {code} for {username}")

            elif cmd == "EXISTS":
                # EXISTS <code>
                if len(parts) < 2:
                    conn.sendall(b"ERROR Missing code\n")
                    continue
                code = parts[1]
                if code in rooms:
                    conn.sendall(b"OK\n")
                else:
                    conn.sendall(b"ERROR NotFound\n")

            elif cmd == "BYE":
                conn.sendall(b"OK Bye\n")
                break
    except Exception as e:
        print(f"[ROOM_MGMT] Error: {e}")
    finally:
        conn.close()

def main():
    print(f"[ROOM_MGMT] Server starting on {HOST}:{PORT}")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen(10)
        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    main()
