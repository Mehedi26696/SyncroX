import socket
from typing import List, Tuple, Optional
import time
import json
import base64
from pathlib import Path

try:
    from .protocol import CHUNK_SIZE, FileReceiver, FileSender, FileTransferMetrics
except (ImportError, ValueError):
    from protocol import CHUNK_SIZE, FileReceiver, FileSender, FileTransferMetrics

BASE_DIR = Path(__file__).resolve().parents[2]
METRICS_DIR = BASE_DIR / "data" / "metrics"
METRICS_DIR.mkdir(parents=True, exist_ok=True)

try:
    from config import (
        SERVER_HOST, FILE_PORT, SYNCROX_LOSS_PROB,
        HANDSHAKE_TIMEOUT, TERMINATION_TIMEOUT, MAX_RETRIES,
        UDP_RECV_TIMEOUT, TOTAL_DOWNLOAD_TIMEOUT, DEFAULT_RWND
    )
except ImportError:
    SERVER_HOST = "127.0.0.1"
    FILE_PORT = 9010
    SYNCROX_LOSS_PROB = 0.0
    HANDSHAKE_TIMEOUT = 5.0
    TERMINATION_TIMEOUT = 3.0
    MAX_RETRIES = 5
    UDP_RECV_TIMEOUT = 1.0
    TOTAL_DOWNLOAD_TIMEOUT = 30.0
    DEFAULT_RWND = 32

UDP_PORT = FILE_PORT + 1


class SyncroXFileClient:
    def __init__(self, host=None, port=None, algo="reno"):
        self.host = host if host is not None else SERVER_HOST
        self.tcp_port = port if port is not None else FILE_PORT
        self.udp_port = self.tcp_port + 1
        self.algo = algo.lower()

        self.tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_sock.connect((self.host, self.tcp_port))
        self.file = self.tcp_sock.makefile("rb")

        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_sock.settimeout(1.0)

    def _send_tcp_line(self, line: str):
        self.tcp_sock.sendall((line + "\n").encode("utf-8"))

    def upload_bytes(self, room: str, filename: str, data: bytes) -> str:
        handshake_done = False
        session_id = None

        start_h = time.time()
        while time.time() - start_h < HANDSHAKE_TIMEOUT:
            syn = {"type": "SYN", "room": room, "filename": filename}
            self.udp_sock.sendto(json.dumps(syn).encode("utf-8"), (self.host, self.udp_port))
            try:
                self.udp_sock.settimeout(1.0)
                resp, _ = self.udp_sock.recvfrom(65536)
                msg = json.loads(resp.decode("utf-8"))
                if msg.get("type") == "SYN-ACK" and msg.get("filename") == filename:
                    session_id = msg.get("session_id")
                    ack = {"type": "ACK", "room": room, "filename": filename, "session_id": session_id}
                    self.udp_sock.sendto(json.dumps(ack).encode("utf-8"), (self.host, self.udp_port))
                    handshake_done = True
                    break
            except socket.timeout:
                continue

        if not handshake_done or not session_id:
            return "ERROR Handshake failed"

        metrics = FileTransferMetrics(room, filename, METRICS_DIR, algo=self.algo, direction="upload")
        sender = FileSender(room, filename, data, (self.host, self.udp_port), self.udp_sock, metrics, loss_prob=SYNCROX_LOSS_PROB, session_id=session_id)

        next_seq = 1
        rwnd = DEFAULT_RWND

        while metrics.last_ack < sender.total_packets:
            next_seq = sender.send_window(next_seq, metrics.last_ack + 1, rwnd)

            try:
                self.udp_sock.settimeout(0.2)
                resp, _ = self.udp_sock.recvfrom(65536)
                ack = json.loads(resp.decode("utf-8"))
                if ack.get("type") == "ACK" and ack.get("filename") == filename and ack.get("session_id") == session_id and "ack" in ack:
                    ack_val = int(ack["ack"])
                    rwnd = int(ack.get("rwnd", rwnd))
                    sent_t = sender.sent_times.get(ack_val)
                    if sent_t is None:
                        sent_t = sender.sent_times.get(metrics.last_ack + 1, time.time())
                    rtt_ms = (time.time() - sent_t) * 1000.0

                    if metrics.on_ack(ack_val, CHUNK_SIZE, rtt_ms):
                        missing = metrics.last_ack + 1
                        if missing <= sender.total_packets:
                            offset = (missing - 1) * CHUNK_SIZE
                            pkt = {
                                "type": "DATA",
                                "room": room,
                                "filename": filename,
                                "seq": missing,
                                "total": sender.total_packets,
                                "payload_b64": base64.b64encode(data[offset:offset + CHUNK_SIZE]).decode("ascii"),
                                "session_id": session_id
                            }
                            self.udp_sock.sendto(json.dumps(pkt).encode("utf-8"), (self.host, self.udp_port))

                    next_seq = max(next_seq, metrics.last_ack + 1)

            except socket.timeout:
                pass

            base = metrics.last_ack + 1
            if base in sender.sent_times:
                new_next, ok = sender.handle_timeout(base, MAX_RETRIES)
            else:
                new_next, ok = (-1, True)

            if not ok:
                metrics.close()
                return "ERROR Max retries exceeded"

            if new_next != -1:
                next_seq = new_next

        start_term = time.time()
        while time.time() - start_term < TERMINATION_TIMEOUT:
            try:
                self.udp_sock.settimeout(1.0)
                resp, _ = self.udp_sock.recvfrom(65536)
                msg = json.loads(resp.decode("utf-8"))
                if msg.get("type") == "FIN" and msg.get("filename") == filename and msg.get("session_id") == session_id:
                    ack = {"type": "FIN-ACK", "room": room, "filename": filename, "session_id": session_id}
                    self.udp_sock.sendto(json.dumps(ack).encode("utf-8"), (self.host, self.udp_port))
                    break
            except socket.timeout:
                pass

        metrics.close()
        return "OK SAVED"

    def list_files(self, room: str) -> List[Tuple[str, int, str]]:
        self._send_tcp_line(f"LIST {room}")
        header = self.file.readline().decode("utf-8").strip()
        if not header.startswith("FILES"):
            return []
        try:
            n = int(header.split()[1])
        except:
            return []

        result = []
        for _ in range(n):
            line = self.file.readline().decode("utf-8").strip()
            if not line:
                continue
            parts = line.split(maxsplit=2)
            if len(parts) < 3:
                continue
            result.append((parts[2], int(parts[0]), parts[1]))
        return result

    def download_bytes(self, room: str, filename: str) -> Optional[bytes]:
        handshake_done = False
        session_id = None

        start_h = time.time()
        while time.time() - start_h < HANDSHAKE_TIMEOUT:
            pkt = {"type": "DOWNLOAD", "room": room, "filename": filename, "algo": self.algo}
            self.udp_sock.sendto(json.dumps(pkt).encode("utf-8"), (self.host, self.udp_port))
            try:
                self.udp_sock.settimeout(1.0)
                resp, _ = self.udp_sock.recvfrom(65536)
                msg = json.loads(resp.decode("utf-8"))
                if msg.get("type") == "SYN-ACK" and msg.get("filename") == filename:
                    session_id = msg.get("session_id")
                    ack = {"type": "ACK", "room": room, "filename": filename, "session_id": session_id}
                    self.udp_sock.sendto(json.dumps(ack).encode("utf-8"), (self.host, self.udp_port))
                    handshake_done = True
                    break
            except socket.timeout:
                continue

        if not handshake_done or not session_id:
            return None

        receiver = None
        start_t = time.time()
        max_wait = 5.0

        while True:
            try:
                self.udp_sock.settimeout(1.0)
                resp, _ = self.udp_sock.recvfrom(65536)
                msg = json.loads(resp.decode("utf-8"))

                if msg.get("type") == "DATA" and msg.get("filename") == filename and msg.get("session_id") == session_id:
                    if receiver is None:
                        receiver = FileReceiver(int(msg["total"]), max_buf=DEFAULT_RWND)

                    payload = base64.b64decode(msg["payload_b64"].encode("ascii"))
                    receiver.add_chunk(int(msg["seq"]), payload)

                    ack = {
                        "type": "ACK",
                        "room": room,
                        "filename": filename,
                        "ack": receiver.get_ack_seq(),
                        "rwnd": receiver.rwnd,
                        "session_id": session_id
                    }
                    self.udp_sock.sendto(json.dumps(ack).encode("utf-8"), (self.host, self.udp_port))

                    if receiver.is_complete():
                        fin = {"type": "FIN", "room": room, "filename": filename, "session_id": session_id}
                        self.udp_sock.sendto(json.dumps(fin).encode("utf-8"), (self.host, self.udp_port))

                        start_fa = time.time()
                        while time.time() - start_fa < 2:
                            try:
                                self.udp_sock.settimeout(0.5)
                                resp, _ = self.udp_sock.recvfrom(65536)
                                msg2 = json.loads(resp.decode("utf-8"))
                                if msg2.get("type") == "FIN-ACK" and msg2.get("session_id") == session_id:
                                    break
                            except:
                                pass

                        return receiver.finalize_to_bytes()

                elif msg.get("type") == "ERROR":
                    return None

            except socket.timeout:
                if receiver is None and time.time() - start_t > max_wait:
                    return None
                if receiver and receiver.is_complete():
                    return receiver.finalize_to_bytes()
                
                # Check for total transfer timeout
                if time.time() - start_t > TOTAL_DOWNLOAD_TIMEOUT:
                    print(f"[UDP CLIENT] Download timed out after {TOTAL_DOWNLOAD_TIMEOUT}s")
                    return None
                    
                if receiver is None:
                    self.udp_sock.sendto(json.dumps(pkt).encode("utf-8"), (self.host, self.udp_port))

    def close(self):
        try:
            self._send_tcp_line("BYE")
        except:
            pass
        try:
            self.file.close()
        except:
            pass
        try:
            self.tcp_sock.close()
        except:
            pass
        try:
            self.udp_sock.close()
        except:
            pass


TcpFileClient = SyncroXFileClient
UdpFileClient = SyncroXFileClient
