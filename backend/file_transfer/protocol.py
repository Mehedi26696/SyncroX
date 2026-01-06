import time
import json
import csv
import random
import socket
import threading
from pathlib import Path
from typing import Optional, Tuple

# --- Shared Constants ---
CHUNK_SIZE = 4096
ALPHA = 0.125
BETA = 0.25


class FileTransferMetrics:
    """Tracks EWMA RTT, RTO and Tahoe/Reno cwnd."""

    def __init__(self, room: str, filename: str, metrics_dir: Path,
                 algo: str = "reno", direction: str = "upload"):
        self.room = room
        self.filename = filename
        self.metrics_dir = metrics_dir
        self.algo = algo.lower()
        self.direction = direction

        self.cwnd = 1.0
        self.ssthresh = 16.0
        self.srtt = None
        self.rttvar = None
        self.rto = 1000.0  # ms

        self.seq = 0
        self.last_ack = 0
        self.dup_acks = 0
        self.in_fast_recovery = False
        self.phase = "SLOW_START"

        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        self.csv_path = self.metrics_dir / f"room_{room}_file_metrics.csv"
        self.csv_file = self.csv_path.open("a", newline="", encoding="utf-8")
        self.writer = csv.writer(self.csv_file)

        if self.csv_file.tell() == 0:
            self.writer.writerow([
                "ts", "room", "file", "direction", "seq", "bytes",
                "rtt_ms", "srtt_ms", "rto_ms", "cwnd",
                "ssthresh", "event", "algo"
            ])

    def _log(self, bytes_transferred: int, rtt_ms: Optional[float], event: str):
        ts = time.time()
        self.writer.writerow([
            ts, self.room, self.filename, self.direction,
            self.seq, bytes_transferred,
            rtt_ms if rtt_ms is not None else "",
            self.srtt if self.srtt is not None else "",
            self.rto, self.cwnd, self.ssthresh,
            event, self.algo
        ])
        self.csv_file.flush()

    def _update_phase(self):
        new_phase = (
            "FAST_RECOVERY" if self.in_fast_recovery
            else "SLOW_START" if self.cwnd < self.ssthresh
            else "CONG_AVOID"
        )
        if new_phase != self.phase:
            print(f"[{self.algo.upper()} {self.direction.upper()}] "
                  f"PHASE CHANGE: {self.phase} → {new_phase}")
            self.phase = new_phase

    def on_ack(self, ack_seq: int, bytes_transferred: int, rtt_ms: float) -> bool:
        """Returns True if fast retransmit is triggered."""
        self.seq += 1

        # RTT / RTO update (RFC-style EWMA)
        if self.srtt is None:
            self.srtt = rtt_ms
            self.rttvar = rtt_ms / 2.0
        else:
            self.rttvar = (1 - BETA) * self.rttvar + BETA * abs(self.srtt - rtt_ms)
            self.srtt = (1 - ALPHA) * self.srtt + ALPHA * rtt_ms
        self.rto = self.srtt + 4 * self.rttvar
        self.rto = max(self.rto, 200.0)   # minimum 200ms to avoid spurious timeouts

        # New ACK
        if ack_seq > self.last_ack:
            old_cwnd = self.cwnd

            if self.in_fast_recovery:
                self.cwnd = self.ssthresh
                self.in_fast_recovery = False

            if self.cwnd < self.ssthresh:
                self.cwnd += 1.0
                rule = "SLOW_START (+1/ACK)"
            else:
                self.cwnd += 1.0 / self.cwnd
                rule = "CONG_AVOID (+1/cwnd)"

            self.last_ack = ack_seq
            self.dup_acks = 0

            print(
                f"[{self.algo.upper()} {self.direction.upper()}] "
                f"NEW_ACK={ack_seq} | cwnd {old_cwnd:.2f}→{self.cwnd:.2f} | "
                f"ssthresh={self.ssthresh:.2f} | "
                f"RTT={rtt_ms:.2f}ms RTO={self.rto:.2f}ms | {rule}"
            )

            self._update_phase()
            self._log(bytes_transferred, rtt_ms, "ACK")
            return False

        # Duplicate ACK
        else:
            self.dup_acks += 1
            print(
                f"[{self.algo.upper()} {self.direction.upper()}] "
                f"DUP_ACK #{self.dup_acks} for ACK={ack_seq}"
            )

            if self.dup_acks == 3:
                self.ssthresh = max(self.cwnd / 2.0, 2.0)

                if self.algo == "tahoe":
                    self.cwnd = 1.0
                    self.in_fast_recovery = False
                    action = "RESET_TO_1 (Tahoe)"
                else:
                    self.cwnd = self.ssthresh + 3.0
                    self.in_fast_recovery = True
                    action = "FAST_RECOVERY (Reno)"

                print(
                    f"[{self.algo.upper()} {self.direction.upper()}] "
                    f"FAST_RETRANSMIT | lost_seq={self.last_ack + 1} | "
                    f"cwnd={self.cwnd:.2f} | ssthresh={self.ssthresh:.2f} | {action}"
                )

                self._update_phase()
                self._log(0, None, f"FAST_RETRANSMIT_{self.algo.upper()}")
                return True

            elif self.in_fast_recovery:
                self.cwnd += 1.0
                self._log(0, None, "DUP_ACK_RECOVERY")

            return False

    def on_loss(self):
        self.seq += 1
        self.ssthresh = max(self.cwnd / 2.0, 2.0)
        self.cwnd = 1.0
        self.in_fast_recovery = False
        self.dup_acks = 0
        self.rto = min(self.rto * 2.0, 30000.0)

        print(
            f"[{self.algo.upper()} {self.direction.upper()}] "
            f"TIMEOUT | base_seq={self.last_ack + 1} | "
            f"new_RTO={self.rto:.2f}ms | "
            f"cwnd={self.cwnd:.2f} | ssthresh={self.ssthresh:.2f}"
        )

        self.phase = "SLOW_START"
        self._log(0, None, "TIMEOUT")

    def close(self):
        try:
            self.csv_file.close()
        except:
            pass


class FileReceiver:
    """Receiver with cumulative ACKs."""

    def __init__(self, total_packets: int):
        self.total_packets = total_packets
        self.chunks = {}
        self.received = set()
        self.next_expected = 1
        self.rwnd = 32

    def add_chunk(self, seq: int, data: bytes):
        if seq not in self.received and seq >= self.next_expected:
            self.chunks[seq] = data
            self.received.add(seq)
            while self.next_expected in self.received:
                self.next_expected += 1

    def get_ack_seq(self) -> int:
        return self.next_expected - 1

    def is_complete(self) -> bool:
        return len(self.received) == self.total_packets

    def finalize_to_bytes(self) -> bytes:
        return b"".join(self.chunks.get(i, b"") for i in range(1, self.total_packets + 1))

    def finalize_to_file(self, path: Path):
        with open(path, "wb") as f:
            for i in range(1, self.total_packets + 1):
                f.write(self.chunks.get(i, b""))


class FileSender:
    """Sliding-window sender with loss simulation."""

    def __init__(self, room: str, filename: str, data: bytes,
                 addr: Tuple[str, int], sock: socket.socket,
                 metrics: FileTransferMetrics, loss_prob: float = 0.0):
        self.room = room
        self.filename = filename
        self.data = data
        self.addr = addr
        self.sock = sock
        self.metrics = metrics
        self.loss_prob = loss_prob

        self.total_packets = (len(data) + CHUNK_SIZE - 1) // CHUNK_SIZE
        self.sent_times = {}
        self.retries = {}
        self.lock = threading.Lock()

    def send_window(self, next_seq: int, window_base: int, rwnd: int) -> int:
        with self.lock:
            current_window = min(int(self.metrics.cwnd), rwnd)
            requested_next = next_seq
            start_seq = max(next_seq, window_base)
            next_seq = start_seq
            
            while next_seq < window_base + current_window and next_seq <= self.total_packets:
                offset = (next_seq - 1) * CHUNK_SIZE
                chunk = self.data[offset:offset + CHUNK_SIZE]

                pkt = {
                    "type": "DATA",
                    "room": self.room,
                    "filename": self.filename,
                    "seq": next_seq,
                    "total": self.total_packets,
                    "payload_hex": chunk.hex()
                }

                if random.random() >= self.loss_prob:
                    try:
                        self.sock.sendto(json.dumps(pkt).encode("utf-8"), self.addr)
                    except:
                        pass

                self.sent_times[next_seq] = time.time()
                self.retries[next_seq] = self.retries.get(next_seq, 0)
                next_seq += 1

            end_seq = next_seq - 1
            if end_seq >= start_seq:
                print(
                    f"[{self.metrics.algo.upper()} {self.metrics.direction.upper()}] "
                    f"SEND base={window_base} next_in={requested_next} "
                    f"sent={start_seq}-{end_seq} "
                    f"(cwnd={self.metrics.cwnd:.2f}, rwnd={rwnd})"
                )

            return next_seq

    def handle_timeout(self, window_base: int, max_retries: int) -> Tuple[int, bool]:
        rto_s = self.metrics.rto / 1000.0
        if time.time() - self.sent_times.get(window_base, time.time()) > rto_s:
            if self.retries.get(window_base, 0) < max_retries:
                self.metrics.on_loss()

                offset = (window_base - 1) * CHUNK_SIZE
                pkt = {
                    "type": "DATA",
                    "room": self.room,
                    "filename": self.filename,
                    "seq": window_base,
                    "total": self.total_packets,
                    "payload_hex": self.data[offset:offset + CHUNK_SIZE].hex()
                }

                try:
                    self.sock.sendto(json.dumps(pkt).encode("utf-8"), self.addr)
                except:
                    pass

                self.sent_times[window_base] = time.time()
                self.retries[window_base] += 1
                return window_base + 1, True

            return window_base, False

        return -1, True
