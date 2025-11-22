import socket
from typing import List, Tuple
import time
import csv
from pathlib import Path

CHUNK_SIZE = 4096
ALPHA = 0.125  # EWMA smoothing
BETA = 0.25   # for RTT variance

BASE_DIR = Path(__file__).resolve().parents[2]
METRICS_DIR = BASE_DIR / "data" / "metrics"
METRICS_DIR.mkdir(parents=True, exist_ok=True)


class FileTransferMetrics:
    """
    Tracks EWMA RTT, RTO and Tahoe/Reno cwnd per upload,
    and logs to CSV per room, per file.
    """

    def __init__(self, room: str, filename: str, algo: str = "reno", direction: str = "upload"):
        self.room = room
        self.filename = filename
        self.algo = algo.lower()          # 'reno' or 'tahoe'
        self.direction = direction        # 'upload' (you can extend later with 'download')
        self.cwnd = 1.0                   # in segments
        self.ssthresh = 8.0
        self.srtt = None                  # smoothed RTT (ms)
        self.rttvar = None                # RTT variance (ms)
        self.rto = 1000.0                 # initial RTO (ms)
        self.seq = 0                      # segment index

        self.csv_path = METRICS_DIR / f"room_{room}_file_metrics.csv"
        self.csv_file = self.csv_path.open("a", newline="", encoding="utf-8")
        self.writer = csv.writer(self.csv_file)
        if self.csv_file.tell() == 0:
            self.writer.writerow(
                [
                    "ts",
                    "room",
                    "file",
                    "direction",
                    "seq",
                    "bytes",
                    "rtt_ms",
                    "srtt_ms",
                    "rto_ms",
                    "cwnd",
                    "ssthresh",
                    "event",
                    "algo",
                ]
            )

    def _log(self, bytes_sent: int, rtt_ms: float | None, event: str):
        ts = time.time()
        self.writer.writerow(
            [
                ts,
                self.room,
                self.filename,
                self.direction,
                self.seq,
                bytes_sent,
                rtt_ms if rtt_ms is not None else "",
                self.srtt if self.srtt is not None else "",
                self.rto,
                self.cwnd,
                self.ssthresh,
                event,
                self.algo,
            ]
        )
        self.csv_file.flush()

    def on_ack(self, bytes_sent: int, rtt_ms: float):
        """
        Called when a chunk is ACKed – update EWMA & cwnd (Tahoe/Reno).
        """
        self.seq += 1

        # --- EWMA RTT like real TCP ---
        if self.srtt is None:
            self.srtt = rtt_ms
            self.rttvar = rtt_ms / 2.0
        else:
            self.rttvar = (1 - BETA) * self.rttvar + BETA * abs(self.srtt - rtt_ms)
            self.srtt = (1 - ALPHA) * self.srtt + ALPHA * rtt_ms

        self.rto = self.srtt + 4 * self.rttvar

        # --- congestion control (Tahoe/Reno style) ---
        if self.cwnd < self.ssthresh:
            # slow start: exponential growth
            self.cwnd += 1.0
        else:
            # congestion avoidance: linear growth (~1 per RTT)
            self.cwnd += 1.0 / self.cwnd

        self._log(bytes_sent, rtt_ms, event="ACK")

    def on_loss(self, bytes_sent: int):
        """
        Called when a timeout is treated as a loss.
        """
        self.seq += 1

        # Tahoe vs Reno behaviour
        if self.algo == "tahoe":
            self.ssthresh = max(self.cwnd / 2.0, 1.0)
            self.cwnd = 1.0
        else:  # reno
            self.ssthresh = max(self.cwnd / 2.0, 1.0)
            self.cwnd = self.ssthresh

        # back off RTO
        self.rto *= 2.0

        self._log(bytes_sent, None, event="LOSS")

    def close(self):
        try:
            self.csv_file.close()
        except Exception:
            pass


class TcpFileClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 9010, algo: str = "reno"):
        self.host = host
        self.port = port
        self.algo = algo.lower()  # 'reno' or 'tahoe'
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
        self.file = self.sock.makefile("rwb")

    def _send_line(self, text: str):
        self.file.write((text + "\n").encode("utf-8"))
        self.file.flush()

    def upload_bytes(self, room: str, filename: str, data: bytes) -> str:
        """
        Upload file bytes in CHUNK_SIZE segments, with per-chunk ACK.
        Also measures per-chunk RTT and logs EWMA + cwnd into CSV for this file.
        """
        size = len(data)
        self._send_line(f"UPLOAD {room} {filename} {size}")

        metrics = FileTransferMetrics(room, filename, algo=self.algo, direction="upload")
        remaining = size
        offset = 0

        try:
            while remaining > 0:
                chunk = data[offset : offset + CHUNK_SIZE]
                bytes_to_send = len(chunk)
                if bytes_to_send == 0:
                    break

                # send chunk
                send_time = time.time()
                self.file.write(chunk)
                self.file.flush()

                # RTO-based timeout (minimum 100ms)
                timeout_sec = max(metrics.rto / 1000.0, 0.1)
                self.sock.settimeout(timeout_sec)

                # wait for ACK <room> <seq>
                try:
                    ack_line = self.file.readline().decode("utf-8").strip()
                except socket.timeout:
                    metrics.on_loss(bytes_to_send)
                else:
                    parts = ack_line.split()
                    if len(parts) == 3 and parts[0] == "ACK":
                        # compute RTT
                        rtt_ms = (time.time() - send_time) * 1000.0
                        metrics.on_ack(bytes_to_send, rtt_ms)
                    else:
                        # malformed ACK, log as loss
                        metrics.on_loss(bytes_to_send)

                offset += bytes_to_send
                remaining -= bytes_to_send

            # after file done, read final response (OK SAVED / ERROR ...)
            self.sock.settimeout(None)
            resp = self.file.readline().decode("utf-8").strip()
            return resp
        finally:
            metrics.close()

    def list_files(self, room: str) -> List[Tuple[str, int, str]]:
        self._send_line(f"LIST {room}")
        header = self.file.readline().decode("utf-8").strip()
        parts = header.split()
        if len(parts) != 2 or parts[0] != "FILES":
            return []
        try:
            n = int(parts[1])
        except ValueError:
            return []

        result: List[Tuple[str, int, str]] = []
        for _ in range(n):
            line = self.file.readline().decode("utf-8").strip()
            if not line:
                continue
            name, size_str, created = line.split(maxsplit=2)
            size = int(size_str)
            result.append((name, size, created))
        return result

    def download_bytes(self, room: str, filename: str) -> bytes | None:
        self._send_line(f"DOWNLOAD {room} {filename}")
        header = self.file.readline().decode("utf-8").strip()
        parts = header.split()
        if parts[0] == "ERROR":
            return None
        if len(parts) != 2 or parts[0] != "OK":
            return None
        size = int(parts[1])
        remaining = size
        chunks: list[bytes] = []
        while remaining > 0:
            chunk = self.file.read(min(4096, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        if remaining != 0:
            return None
        return b"".join(chunks)

    def close(self):
        try:
            self._send_line("BYE")
        except Exception:
            pass
        try:
            self.file.close()
        except Exception:
            pass
        try:
            self.sock.close()
        except Exception:
            pass
