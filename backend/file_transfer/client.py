import socket
from typing import List, Tuple


class TcpFileClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 9010):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
        self.file = self.sock.makefile("rwb")

    def _send_line(self, text: str):
        self.file.write((text + "\n").encode("utf-8"))
        self.file.flush()

    def upload_bytes(self, room: str, filename: str, data: bytes) -> str:
        size = len(data)
        self._send_line(f"UPLOAD {room} {filename} {size}")
        # send raw bytes
        self.file.write(data)
        self.file.flush()
        # read response
        resp = self.file.readline().decode("utf-8").strip()
        return resp

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
