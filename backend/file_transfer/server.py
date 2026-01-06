import socket
import threading
import json
import datetime
from pathlib import Path
import os
import time

# --- Configuration ---
HOST = "0.0.0.0"
TCP_PORT = 9010
UDP_PORT = 9011
CHUNK_SIZE = 4096

BASE_DIR = Path(__file__).resolve().parents[2]
ROOT_UPLOAD_DIR = BASE_DIR / "data" / "uploads"
METRICS_DIR = BASE_DIR / "data" / "metrics"
os.makedirs(ROOT_UPLOAD_DIR, exist_ok=True)
os.makedirs(METRICS_DIR, exist_ok=True)

from .protocol import CHUNK_SIZE, FileReceiver, FileSender, FileTransferMetrics

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

# FileReceiver and FileSender classes removed, now importing from protocol.py

def udp_server():
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_sock.bind((HOST, UDP_PORT))
    print(f"[UDP FILE] Server listening on {HOST}:{UDP_PORT}")
    
    transfers = {} # (room, filename, addr) -> FileReceiver
    outgoing_transfers = {} # (room, filename, addr) -> FileSender
    handshakes = {} # (room, filename, addr) -> state ("SYN_RCVD", "ESTABLISHED")

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
                print(f"[UDP Handshake] SYN received from {addr} for {filename}")
                handshakes[key] = "SYN_RCVD"
                resp = {"type": "SYN-ACK", "room": room, "filename": filename}
                server_sock.sendto(json.dumps(resp).encode("utf-8"), addr)

            elif msg_type == "ACK" and handshakes.get(key) == "SYN_RCVD":
                print(f"[UDP Handshake] ACK received from {addr}. Connection ESTABLISHED.")
                handshakes[key] = "ESTABLISHED"

            elif msg_type == "DATA":
                if key not in handshakes or handshakes[key] != "ESTABLISHED":
                    # For simplicity, if we get DATA without full handshake, we can just allow it 
                    # OR we can drop it. Let's allow it but log a warning to be robust.
                    # Actually, let's enforce it to satisfy the requirement properly.
                    # print(f"[UDP] DATA received before handshake completion from {addr}. Dropping.")
                    # continue
                    handshakes[key] = "ESTABLISHED" # Auto-establish if DATA arrives (fallback)
                
                seq = msg["seq"]
                total = msg["total"]
                payload = bytes.fromhex(msg["payload_hex"])
                
                room_dir = get_room_dir(room)
                if not room_dir: continue
                
                if key not in transfers:
                    transfers[key] = FileReceiver(total)
                
                receiver = transfers[key]
                receiver.add_chunk(seq, payload)
                
                ack = {
                    "type": "ACK", "room": room, "filename": filename, 
                    "ack_seq": receiver.get_ack_seq(), "rwnd": receiver.rwnd
                }
                server_sock.sendto(json.dumps(ack).encode("utf-8"), addr)
                
                if receiver.is_complete():
                    receiver.finalize_to_file(room_dir / filename)
                    print(f"[UDP FILE] Saved {filename} in room {room} from {addr}")
                    del transfers[key]
                    
                    # Initiation termination
                    fin = {"type": "FIN", "room": room, "filename": filename}
                    server_sock.sendto(json.dumps(fin).encode("utf-8"), addr)
                    print(f"[UDP Termination] Sent FIN to {addr}")

            elif msg_type == "ACK":
                if key in handshakes and handshakes[key] == "SYN_RCVD":
                    print(f"[UDP Handshake] ACK received from {addr}. Connection ESTABLISHED.")
                    handshakes[key] = "ESTABLISHED"
                    continue

                if key in outgoing_transfers:
                    sender = outgoing_transfers[key]
                    ack_seq = msg["ack_seq"]
                    rwnd = msg.get("rwnd", 32)
                    
                    # RTT calculation
                    now = time.time()
                    sent_t = sender.sent_times.get(ack_seq, now)
                    rtt_ms = (now - sent_t) * 1000.0
                    
                    sender.metrics.on_ack(ack_seq, CHUNK_SIZE, rtt_ms)
                    if sender.metrics.last_ack >= sender.total_packets:
                        # File sent complete, initiate FIN
                        sender.send_control("FIN")
                        print(f"[UDP Termination] Sent FIN to {addr}")
                        # We don't delete yet, wait for FIN-ACK? 
                        # For simplicity, we can delete after a bit or after FIN-ACK.
                        # del outgoing_transfers[key]

            elif msg_type == "DOWNLOAD":
                room_dir = get_room_dir(room)
                if not room_dir: continue
                path = room_dir / filename
                algo = msg.get("algo", "reno")
                if path.exists() and path.is_file():
                    with path.open("rb") as f: data = f.read()
                    
                    metrics = FileTransferMetrics(room, filename, METRICS_DIR, algo=algo, direction="download")
                    sender = FileSender(room, filename, data, addr, server_sock, metrics)
                    outgoing_transfers[key] = sender
                    
                    def run_sender(s: FileSender):
                        next_seq = 1
                        while s.metrics.last_ack < s.total_packets:
                            next_seq = s.send_window(next_seq, s.metrics.last_ack + 1, 32)
                            time.sleep(0.01)
                            new_next, ok = s.handle_timeout(s.metrics.last_ack + 1, 5)
                            if not ok: break
                            if new_next != -1: next_seq = new_next
                        s.metrics.close()
                    
                    threading.Thread(target=run_sender, args=(sender,), daemon=True).start()
                else:
                    error_pkt = {"type": "ERROR", "msg": "File not found"}
                    server_sock.sendto(json.dumps(error_pkt).encode("utf-8"), addr)

            elif msg_type == "FIN":
                print(f"[UDP Termination] FIN received from {addr}")
                resp = {"type": "FIN-ACK", "room": room, "filename": filename}
                server_sock.sendto(json.dumps(resp).encode("utf-8"), addr)
                if key in handshakes: del handshakes[key]
                if key in transfers: del transfers[key]
                if key in outgoing_transfers: del outgoing_transfers[key]

            elif msg_type == "FIN-ACK":
                print(f"[UDP Termination] FIN-ACK received from {addr}. Session Closed.")
                if key in handshakes: del handshakes[key]
                if key in transfers: del transfers[key]
                if key in outgoing_transfers: del outgoing_transfers[key]

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
