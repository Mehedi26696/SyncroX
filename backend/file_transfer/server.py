import socket
import threading
import json
import datetime
from pathlib import Path
import os
import sys

# Add project root to path for imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# --- Configuration ---
from config import SERVER_HOST, ROOM_MGMT_PORT
from backend.room_mgmt.client import RoomMgmtClient

# Global room mgmt client
room_client = RoomMgmtClient(host=SERVER_HOST, port=ROOM_MGMT_PORT)

HOST = "0.0.0.0"
TCP_PORT = 9010
UDP_PORT = 9011
CHUNK_SIZE = 4096

BASE_DIR = Path(__file__).resolve().parents[2]
ROOT_UPLOAD_DIR = BASE_DIR / "data" / "uploads"
os.makedirs(ROOT_UPLOAD_DIR, exist_ok=True)

from typing import List, Tuple, Optional, Union
import uuid
import base64

from backend.file_transfer.protocol import FileReceiver

def get_room_dir(room: str) -> Optional[Path]:
    """Validate room code and return its directory path."""
    if len(room) != 4 or not room.isdigit():
        return None
    room_dir = ROOT_UPLOAD_DIR / room
    room_dir.mkdir(parents=True, exist_ok=True)
    return room_dir

# --- TCP Server Logic ---

def handle_tcp_client(conn: socket.socket, addr):
    print(f"[TCP FILE] New connection from {addr}")
    buffer = b""
    try:
        while True:
            if b"\n" not in buffer:
                try:
                    data = conn.recv(CHUNK_SIZE)
                except ConnectionResetError:
                    break
                if not data:
                    break
                buffer += data
            
            if b"\n" not in buffer:
                continue
                
            line_end = buffer.index(b"\n")
            line_bytes = buffer[:line_end]
            buffer = buffer[line_end + 1:]
            
            try:
                line = line_bytes.decode("utf-8").strip()
            except UnicodeDecodeError:
                print(f"[TCP FILE] Invalid encoding from {addr}")
                buffer = b""
                conn.sendall(b"ERROR Invalid command encoding\n")
                continue
            
            if not line:
                continue

            print(f"[TCP FILE] Command from {addr}: {line[:80]}")
            parts = line.split()
            cmd = parts[0].upper()

            if cmd == "LIST":
                if len(parts) < 2:
                    conn.sendall(b"ERROR LIST needs room code\n")
                    continue
                room = parts[1]
                # Validate room exists in central service
                if not room_client.room_exists(room):
                    conn.sendall(b"ERROR RoomNotFound\n")
                    continue
                
                room_dir = get_room_dir(room)
                if room_dir is None:
                    conn.sendall(b"ERROR Invalid room configuration\n")
                    continue

                files = []
                for p in room_dir.iterdir():
                    if p.is_file():
                        st = p.stat()
                        created = datetime.datetime.fromtimestamp(st.st_ctime).isoformat(timespec="seconds")
                        files.append((p.name, st.st_size, created))
                files.sort(key=lambda x: x[2], reverse=True)
                
                header = f"FILES {len(files)}\n"
                conn.sendall(header.encode("utf-8"))
                for name, size, created in files:
                    line = f"{size} {created} {name}\n"
                    conn.sendall(line.encode("utf-8"))

            elif cmd == "DOWNLOAD":
                if len(parts) < 3:
                    conn.sendall(b"ERROR DOWNLOAD needs room and filename\n")
                    continue
                room = parts[1]
                # Validate room exists in central service
                if not room_client.room_exists(room):
                    conn.sendall(b"ERROR RoomNotFound\n")
                    continue

                room_dir = get_room_dir(room)
                if room_dir is None:
                    conn.sendall(b"ERROR Invalid room configuration\n")
                    continue

                filename = " ".join(parts[2:])
                path = room_dir / filename
                if not path.exists() or not path.is_file():
                    conn.sendall(b"ERROR NotFound\n")
                    continue
                
                size = path.stat().st_size
                header = f"OK {size}\n"
                conn.sendall(header.encode("utf-8"))
                
                with path.open("rb") as f:
                    while True:
                        chunk = f.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        conn.sendall(chunk)

            elif cmd == "BYE":
                conn.sendall(b"OK Bye\n")
                break
            else:
                conn.sendall(b"ERROR Unknown command\n")

    except Exception as e:
        print(f"[TCP FILE] Error with client {addr}: {e}")
    finally:
        conn.close()

def tcp_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, TCP_PORT))
        s.listen(5)
        print(f"[TCP FILE] Server listening on {HOST}:{TCP_PORT}")
        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_tcp_client, args=(conn, addr), daemon=True).start()

# --- UDP Server Logic ---
# The FileReceiver class is imported from .protocol

def udp_server():
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_sock.bind((HOST, UDP_PORT))
    print(f"[UDP FILE] Server listening on {HOST}:{UDP_PORT}")
    
    # (addr) -> { "session_id": id, "room": r, "filename": f, "receiver": FileReceiver }
    sessions = {} 

    while True:
        try:
            packet, addr = server_sock.recvfrom(65536)
            try:
                msg = json.loads(packet.decode("utf-8"))
            except:
                continue

            msg_type = msg.get("type")

            if msg_type == "SYN":
                room = msg.get("room")
                filename = msg.get("filename")
                
                if not room_client.room_exists(room):
                    print(f"[UDP FILE] SYN Rejected: Room {room} not found")
                    continue
                
                session_id = str(uuid.uuid4())[:8]
                sessions[addr] = {
                    "session_id": session_id,
                    "room": room,
                    "filename": filename,
                    "receiver": None,
                    "handshake_step": "SYN-ACK_SENT"
                }
                
                resp = {
                    "type": "SYN-ACK",
                    "filename": filename,
                    "session_id": session_id
                }
                server_sock.sendto(json.dumps(resp).encode("utf-8"), addr)
                print(f"[UDP FILE] SYN Received from {addr}: Room={room}, File={filename} -> Session={session_id}")

            elif msg_type == "ACK":
                session_id = msg.get("session_id")
                if addr in sessions and sessions[addr]["session_id"] == session_id:
                    sessions[addr]["handshake_step"] = "READY"
                    print(f"[UDP FILE] Handshake complete for session {session_id} from {addr}")

            elif msg_type == "DATA":
                session_id = msg.get("session_id")
                if addr not in sessions or sessions[addr]["session_id"] != session_id:
                    continue
                
                sess = sessions[addr]
                room = msg["room"]
                filename = msg["filename"]
                seq = msg["seq"]
                total = msg["total"]
                
                # Dynamic initialization of receiver on first data packet or ACK
                if sess["receiver"] is None:
                    sess["receiver"] = FileReceiver(total_packets=total)
                
                try:
                    payload = base64.b64decode(msg["payload_b64"])
                except:
                    continue
                
                receiver = sess["receiver"]
                receiver.add_chunk(seq, payload)
                
                # Send Cumulative ACK
                ack = {
                    "type": "ACK", 
                    "room": room, 
                    "filename": filename, 
                    "session_id": session_id,
                    "ack": receiver.get_ack_seq(),
                    "rwnd": receiver.rwnd
                }
                server_sock.sendto(json.dumps(ack).encode("utf-8"), addr)
                
                if receiver.is_complete():
                    room_dir = get_room_dir(room)
                    if room_dir:
                        receiver.finalize_to_file(room_dir / filename)
                        print(f"[UDP FILE] Saved {filename} in room {room} from {addr} (Session={session_id})")
                        
                        # Initiate termination
                        fin = {
                            "type": "FIN",
                            "filename": filename,
                            "session_id": session_id
                        }
                        server_sock.sendto(json.dumps(fin).encode("utf-8"), addr)
                        sess["handshake_step"] = "FIN_SENT"

            elif msg_type == "FIN-ACK":
                session_id = msg.get("session_id")
                if addr in sessions and sessions[addr]["session_id"] == session_id:
                    print(f"[UDP FILE] Session {session_id} terminated gracefully")
                    del sessions[addr]

        except Exception as e:
            print(f"[UDP FILE] Error: {e}")

# --- Main Entry Point ---

def main():
    print(f"[FILE SERVER] Starting...")
    print(f"[FILE SERVER] Root upload dir: {ROOT_UPLOAD_DIR}")
    
    tcp_thread = threading.Thread(target=tcp_server, daemon=True)
    udp_thread = threading.Thread(target=udp_server, daemon=True)
    
    tcp_thread.start()
    udp_thread.start()
    
    try:
        while True:
            tcp_thread.join(timeout=1.0)
            udp_thread.join(timeout=1.0)
    except KeyboardInterrupt:
        print("[FILE SERVER] Shutting down...")

if __name__ == "__main__":
    main()
