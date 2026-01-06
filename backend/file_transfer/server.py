import socket
import threading
import json
import datetime
import time
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
try:
    from .protocol import CHUNK_SIZE, FileReceiver, FileSender, FileTransferMetrics
except (ImportError, ValueError):
    from protocol import CHUNK_SIZE, FileReceiver, FileSender, FileTransferMetrics

METRICS_DIR = BASE_DIR / "data" / "metrics"
METRICS_DIR.mkdir(parents=True, exist_ok=True)

try:
    from config import SYNCROX_LOSS_PROB
except ImportError:
    SYNCROX_LOSS_PROB = 0.0

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

def udp_server():
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_sock.bind((HOST, UDP_PORT))
    print(f"[UDP FILE] Server listening on {HOST}:{UDP_PORT}")
    
    # State tracking
    receivers = {} # (room, filename, addr) -> FileReceiver
    senders = {}   # (room, filename, addr) -> (FileSender, next_seq, metrics)
    pending_downloads = {} # (room, filename, addr) -> {room, filename, algo}

    while True:
        try:
            packet, addr = server_sock.recvfrom(65536)
            try:
                msg = json.loads(packet.decode("utf-8"))
            except:
                continue

            msg_type = msg.get("type")
            room = msg.get("room")
            filename = msg.get("filename")
            key = (room, filename, addr)

            if msg_type == "SYN":
                print(f"[UDP Handshake] SYN from {addr} for {filename}")
                resp = {"type": "SYN-ACK", "room": room, "filename": filename}
                server_sock.sendto(json.dumps(resp).encode("utf-8"), addr)

            elif msg_type == "ACK":
                # Check if it's a handshake ACK or a data ACK
                if "ack_seq" in msg:
                    # Data ACK (for downloads)
                    if key in senders:
                        sender, _, metrics = senders[key]
                        ack_val = msg["ack"]
                        rwnd = msg.get("rwnd", 32)
                        sent_t = sender.sent_times.get(ack_val)
                        if sent_t is None:
                            sent_t = sender.sent_times.get(metrics.last_ack + 1, time.time())
                        
                        rtt_ms = (time.time() - sent_t) * 1000.0
                        
                        metrics.on_ack(ack_val, CHUNK_SIZE, rtt_ms)
                else:
                    # Handshake ACK
                    if key in pending_downloads:
                        d_info = pending_downloads.pop(key)
                        room = d_info["room"]
                        filename = d_info["filename"]
                        algo = d_info["algo"]
                        
                        room_dir = get_room_dir(room)
                        if not room_dir: continue
                        path = room_dir / filename
                        if not path.exists():
                            server_sock.sendto(json.dumps({"type": "ERROR", "msg": "NotFound"}).encode("utf-8"), addr)
                            continue
                        
                        with open(path, "rb") as f:
                            data = f.read()
                        
                        metrics = FileTransferMetrics(room, filename, METRICS_DIR, algo=algo, direction="download")
                        sender = FileSender(room, filename, data, addr, server_sock, metrics, loss_prob=SYNCROX_LOSS_PROB)
                        senders[key] = (sender, 1, metrics)
                        
                        print(f"[UDP Download Handshake] Established for {filename}, starting transmission")
                        
                        # Final confirmation ACK to client
                        confirm = {"type": "ACK", "room": room, "filename": filename}
                        server_sock.sendto(json.dumps(confirm).encode("utf-8"), addr)

                        def run_sender(k, s, m):
                            next_s = 1
                            while m.last_ack < s.total_packets:
                                next_s = max(next_s, m.last_ack + 1)
                                next_s = s.send_window(next_s, m.last_ack + 1, 32)
                                time.sleep(0.01) # Avoid tight loop
                                base = m.last_ack + 1
                                if base in s.sent_times:
                                    new_next, ok = s.handle_timeout(base, 5)
                                else:
                                    new_next, ok = (-1, True)
                                if not ok: break
                                if new_next != -1: next_s = new_next
                            m.close()
                            if k in senders: del senders[k]

                        threading.Thread(target=run_sender, args=(key, sender, metrics), daemon=True).start()
                    else:
                        print(f"[UDP Handshake] ACK from {addr} for {filename}")

            elif msg_type == "DATA":
                seq = msg["seq"]
                total = msg["total"]
                payload = bytes.fromhex(msg["payload_hex"])
                
                room_dir = get_room_dir(room)
                if not room_dir: continue
                
                if key not in receivers:
                    receivers[key] = FileReceiver(total)
                
                receiver = receivers[key]
                receiver.add_chunk(seq, payload)
                
                ack = {
                    "type": "ACK", "room": room, "filename": filename, 
                    "ack": receiver.get_ack_seq(), "rwnd": receiver.rwnd
                }
                server_sock.sendto(json.dumps(ack).encode("utf-8"), addr)
                
                if receiver.is_complete():
                    receiver.finalize_to_file(room_dir / filename)
                    print(f"[UDP FILE] Upload complete: {filename} in {room} from {addr}")
                    # Initiation termination
                    fin = {"type": "FIN", "room": room, "filename": filename}
                    server_sock.sendto(json.dumps(fin).encode("utf-8"), addr)
                    del receivers[key]

            elif msg_type == "DOWNLOAD":
                print(f"[UDP Download] Request from {addr} for {filename}")
                room_dir = get_room_dir(room)
                if not room_dir: continue
                path = room_dir / filename
                if not path.exists():
                    server_sock.sendto(json.dumps({"type": "ERROR", "msg": "NotFound"}).encode("utf-8"), addr)
                    continue
                
                # Start handshake
                pending_downloads[key] = {"room": room, "filename": filename, "algo": msg.get("algo", "reno")}
                resp = {"type": "SYN-ACK", "room": room, "filename": filename}
                server_sock.sendto(json.dumps(resp).encode("utf-8"), addr)

            elif msg_type == "FIN":
                print(f"[UDP Termination] FIN from {addr} for {filename}")
                resp = {"type": "FIN-ACK", "room": room, "filename": filename}
                server_sock.sendto(json.dumps(resp).encode("utf-8"), addr)

            elif msg_type == "FIN-ACK":
                print(f"[UDP Termination] Session closed for {filename} with {addr}")

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
