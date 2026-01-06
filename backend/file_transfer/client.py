import socket
from typing import List, Tuple, Optional, Union
import time
import csv
import json
import random
from pathlib import Path

# --- Configuration ---
CHUNK_SIZE = 4096
ALPHA = 0.125  # EWMA smoothing
BETA = 0.25   # for RTT variance

BASE_DIR = Path(__file__).resolve().parents[2]
METRICS_DIR = BASE_DIR / "data" / "metrics"
METRICS_DIR.mkdir(parents=True, exist_ok=True)

try:
    from .protocol import CHUNK_SIZE, ALPHA, BETA, FileReceiver, FileSender, FileTransferMetrics
except (ImportError, ValueError):
    from protocol import CHUNK_SIZE, ALPHA, BETA, FileReceiver, FileSender, FileTransferMetrics

try:
    from config import SERVER_HOST, FILE_PORT, SYNCROX_LOSS_PROB
except ImportError:
    SERVER_HOST = "127.0.0.1"
    FILE_PORT = 9010
    SYNCROX_LOSS_PROB = 0.0

# UDP Port is TCP Port + 1 by convention in our server.py
UDP_PORT = FILE_PORT + 1

# Shared Reliable UDP classes removed, now importing from protocol.py

class SyncroXFileClient:
    """
    Unified file client: 
    - Uploads using Reliable UDP (port 9011)
    - Lists and Downloads using TCP (port 9010)
    """
    def __init__(self, host=None, port=None, algo="reno"):
        self.host = host if host is not None else SERVER_HOST
        self.tcp_port = port if port is not None else FILE_PORT
        self.udp_port = self.tcp_port + 1
        self.algo = algo.lower()
        
        # TCP Setup (for metadata and downloads)
        self.tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_sock.connect((self.host, self.tcp_port))
        self.file = self.tcp_sock.makefile("rb")
        
        # UDP Setup (for uploads)
        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_sock.settimeout(1.0)

    def _send_tcp_line(self, line: str):
        self.tcp_sock.sendall((line + "\n").encode("utf-8"))

    def upload_bytes(self, room: str, filename: str, data: bytes) -> str:
        """UDP Upload with unified symmetry logic."""
        # 1. 3-way Handshake
        handshake_done = False
        start_h = time.time()
        while time.time() - start_h < 5:
            syn = {"type": "SYN", "room": room, "filename": filename}
            self.udp_sock.sendto(json.dumps(syn).encode("utf-8"), (self.host, self.udp_port))
            try:
                self.udp_sock.settimeout(1.0)
                resp, _ = self.udp_sock.recvfrom(65536)
                msg = json.loads(resp.decode("utf-8"))
                if msg.get("type") == "SYN-ACK" and msg.get("filename") == filename:
                    ack = {"type": "ACK", "room": room, "filename": filename}
                    self.udp_sock.sendto(json.dumps(ack).encode("utf-8"), (self.host, self.udp_port))
                    handshake_done = True
                    print(f"[UDP Handshake] Established with {self.host}:{self.udp_port}")
                    break
            except socket.timeout:
                continue
        if not handshake_done: return "ERROR Handshake failed"

        metrics = FileTransferMetrics(room, filename, METRICS_DIR, algo=self.algo, direction="upload")
        sender = FileSender(room, filename, data, (self.host, self.udp_port), self.udp_sock, metrics, loss_prob=SYNCROX_LOSS_PROB)
        
        next_seq = 1
        rwnd = 32 # Initial
        
        while metrics.last_ack < sender.total_packets:
            next_seq = sender.send_window(next_seq, metrics.last_ack + 1, rwnd)
            
            try:
                self.udp_sock.settimeout(0.2)
                resp, _ = self.udp_sock.recvfrom(65536)
                ack = json.loads(resp.decode("utf-8"))
                if ack.get("type") == "ACK" and ack.get("filename") == filename:
                    ack_val = ack["ack"]
                    rwnd = ack.get("rwnd", rwnd)
                    sent_t = sender.sent_times.get(ack_val)
                    if sent_t is None:
                        sent_t = sender.sent_times.get(metrics.last_ack + 1, time.time())
                    
                    rtt_ms = (time.time() - sent_t) * 1000.0
                    
                    if metrics.on_ack(ack_val, CHUNK_SIZE, rtt_ms):
                        # Fast Retransmit missing
                        missing = metrics.last_ack + 1
                        if missing <= sender.total_packets:
                            offset = (missing - 1) * CHUNK_SIZE
                            pkt = {
                                "type": "DATA", "room": room, "filename": filename,
                                "seq": missing, "total": sender.total_packets, "payload_hex": data[offset:offset+CHUNK_SIZE].hex()
                            }
                            self.udp_sock.sendto(json.dumps(pkt).encode("utf-8"), (self.host, self.udp_port))
                            # Fast retransmit manually sent, but we don't advance next_seq here
                    next_seq = max(next_seq, metrics.last_ack + 1)
            except socket.timeout:
                pass
            
            base = metrics.last_ack + 1
            if base in sender.sent_times:
                new_next, ok = sender.handle_timeout(base, 5)
            else:
                new_next, ok = (-1, True)
            if not ok:
                metrics.close()
                return "ERROR Max retries exceeded"
            if new_next != -1: next_seq = new_next
            
        # 2. Termination (Wait for FIN from server receiver)
        start_term = time.time()
        while time.time() - start_term < 3:
            try:
                self.udp_sock.settimeout(1.0)
                resp, _ = self.udp_sock.recvfrom(65536)
                msg = json.loads(resp.decode("utf-8"))
                if msg.get("type") == "FIN" and msg.get("filename") == filename:
                    ack = {"type": "FIN-ACK", "room": room, "filename": filename}
                    self.udp_sock.sendto(json.dumps(ack).encode("utf-8"), (self.host, self.udp_port))
                    print(f"[UDP Termination] Session closed for {filename}")
                    break
            except socket.timeout:
                pass

        metrics.close()
        return "OK SAVED"

    def list_files(self, room: str) -> List[Tuple[str, int, str]]:
        """TCP List."""
        self._send_tcp_line(f"LIST {room}")
        header = self.file.readline().decode("utf-8").strip()
        if not header.startswith("FILES"): return []
        try:
            n = int(header.split()[1])
        except: return []

        result = []
        for _ in range(n):
            line = self.file.readline().decode("utf-8").strip()
            if not line: continue
            parts = line.split(maxsplit=2)
            if len(parts) < 3: continue
            result.append((parts[2], int(parts[0]), parts[1]))
        return result

    def download_bytes(self, room: str, filename: str) -> Optional[bytes]:
        """UDP Download with reliability and cumulative ACKs."""
        # 1. 3-way Handshake for Download
        handshake_done = False
        start_h = time.time()
        while time.time() - start_h < 5:
            pkt = {"type": "DOWNLOAD", "room": room, "filename": filename, "algo": self.algo}
            self.udp_sock.sendto(json.dumps(pkt).encode("utf-8"), (self.host, self.udp_port))
            try:
                self.udp_sock.settimeout(1.0)
                resp, _ = self.udp_sock.recvfrom(65536)
                msg = json.loads(resp.decode("utf-8"))
                if msg.get("type") == "SYN-ACK" and msg.get("filename") == filename:
                    ack = {"type": "ACK", "room": room, "filename": filename}
                    self.udp_sock.sendto(json.dumps(ack).encode("utf-8"), (self.host, self.udp_port))
                    handshake_done = True
                    print(f"[UDP Download Handshake] Established with {self.host}:{self.udp_port}")
                    break
            except socket.timeout:
                continue
        if not handshake_done: 
            print("[UDP] Download handshake failed")
            return None
        
        receiver = None
        max_wait = 5.0
        start_t = time.time()
        
        while True:
            try:
                self.udp_sock.settimeout(1.0)
                resp, _ = self.udp_sock.recvfrom(65536)
                msg = json.loads(resp.decode("utf-8"))
                
                if msg.get("type") == "DATA" and msg.get("filename") == filename:
                    if receiver is None:
                        receiver = FileReceiver(msg["total"])
                    
                    receiver.add_chunk(msg["seq"], bytes.fromhex(msg["payload_hex"]))
                    
                    # Send ACK
                    ack = {
                        "type": "ACK", "room": room, "filename": filename,
                        "ack": receiver.get_ack_seq(), "rwnd": receiver.rwnd
                    }
                    self.udp_sock.sendto(json.dumps(ack).encode("utf-8"), (self.host, self.udp_port))
                    
                    if receiver.is_complete():
                        # Initiation termination
                        fin = {"type": "FIN", "room": room, "filename": filename}
                        self.udp_sock.sendto(json.dumps(fin).encode("utf-8"), (self.host, self.udp_port))
                        
                        # Wait for FIN-ACK
                        start_fa = time.time()
                        while time.time() - start_fa < 2:
                            try:
                                self.udp_sock.settimeout(0.5)
                                resp, _ = self.udp_sock.recvfrom(65536)
                                msg = json.loads(resp.decode("utf-8"))
                                if msg.get("type") == "FIN-ACK":
                                    print(f"[UDP Termination] Session closed for {filename}")
                                    break
                            except: pass
                        
                        return receiver.finalize_to_bytes()
                
                elif msg.get("type") == "ERROR":
                    print(f"[UDP] Download error: {msg.get('msg')}")
                    return None
                    
            except socket.timeout:
                if receiver is None and time.time() - start_t > max_wait:
                    print("[UDP] Download request timed out")
                    return None
                if receiver and receiver.is_complete(): # Insurance
                    return receiver.finalize_to_bytes()
                # Re-send DOWNLOAD request if we haven't received anything yet
                if receiver is None:
                    self.udp_sock.sendto(json.dumps(pkt).encode("utf-8"), (self.host, self.udp_port))

    def close(self):
        try: self._send_tcp_line("BYE")
        except: pass
        try: self.file.close()
        except: pass
        try: self.tcp_sock.close()
        except: pass
        try: self.udp_sock.close()
        except: pass

# Aliases for backward compatibility in frontend if needed
TcpFileClient = SyncroXFileClient
UdpFileClient = SyncroXFileClient
