import socket
import threading
import json
import datetime
from pathlib import Path
import os

# --- Configuration ---
HOST = "0.0.0.0"
TCP_PORT = 9010
UDP_PORT = 9011
CHUNK_SIZE = 4096

BASE_DIR = Path(__file__).resolve().parents[2]
ROOT_UPLOAD_DIR = BASE_DIR / "data" / "uploads"
os.makedirs(ROOT_UPLOAD_DIR, exist_ok=True)

from typing import List, Tuple, Optional, Union
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
                room_dir = get_room_dir(room)
                if room_dir is None:
                    conn.sendall(b"ERROR Invalid room code\n")
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
                room_dir = get_room_dir(room)
                if room_dir is None:
                    conn.sendall(b"ERROR Invalid room code\n")
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

class FileReceiver:
    def __init__(self, room, filename, total_packets):
        self.room = room
        self.filename = filename
        self.total_packets = total_packets
        self.chunks = {}
        self.received = set()
        self.next_expected = 1
        self.rwnd = 32  # Advertiser window (max buffer/flow control)
        self.finalized = False

    def add_chunk(self, seq, data):
        if seq not in self.received and seq >= self.next_expected:
            self.chunks[seq] = data
            self.received.add(seq)
            # Update cumulative ACK
            while self.next_expected in self.received:
                self.next_expected += 1

    def get_ack_seq(self):
        # We ACK the last packet received in order
        return self.next_expected - 1

    def is_complete(self):
        return len(self.received) == self.total_packets

    def finalize(self, dest_path):
        if self.finalized: return
        with open(dest_path, "wb") as f:
            for seq in range(1, self.total_packets + 1):
                f.write(self.chunks.get(seq, b""))
        self.finalized = True

def udp_server():
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_sock.bind((HOST, UDP_PORT))
    print(f"[UDP FILE] Server listening on {HOST}:{UDP_PORT}")
    
    transfers = {} # (room, filename, addr) -> FileReceiver

    while True:
        try:
            packet, addr = server_sock.recvfrom(65536)
            try:
                msg = json.loads(packet.decode("utf-8"))
            except:
                continue

            if msg.get("type") == "DATA":
                room = msg["room"]
                filename = msg["filename"]
                seq = msg["seq"]
                total = msg["total"]
                payload = bytes.fromhex(msg["payload_hex"])
                key = (room, filename, addr)
                
                room_dir = get_room_dir(room)
                if not room_dir: continue
                
                if key not in transfers:
                    transfers[key] = FileReceiver(room, filename, total)
                
                receiver = transfers[key]
                receiver.add_chunk(seq, payload)
                
                # Send Cumulative ACK with advertised window (rwnd)
                ack = {
                    "type": "ACK", 
                    "room": room, 
                    "filename": filename, 
                    "ack_seq": receiver.get_ack_seq(),
                    "rwnd": receiver.rwnd
                }
                server_sock.sendto(json.dumps(ack).encode("utf-8"), addr)
                
                if receiver.is_complete():
                    receiver.finalize(room_dir / filename)
                    print(f"[UDP FILE] Saved {filename} in room {room} from {addr}")
                    del transfers[key]
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
