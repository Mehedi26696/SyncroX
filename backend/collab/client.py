import socket
import threading
import queue
from typing import Optional


class TcpCollabClient:
    def __init__(self, host: str, port: int, username: str):
        self.host = host
        self.port = port
        self.username = username

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
        self.f = self.sock.makefile("rwb")

        # send HELLO
        self._send_line(f"HELLO {self.username}")

        self.room: Optional[str] = None
        self.current_doc: str = ""
        self._doc_updates: "queue.Queue[str]" = queue.Queue()
        self.alive = True

        t = threading.Thread(target=self._recv_loop, daemon=True)
        t.start()

    def _send_line(self, text: str):
        self.f.write((text + "\n").encode("utf-8"))
        self.f.flush()

    def join_room(self, room: str):
        self._send_line(f"JOIN {room}")

    def request_doc(self, room: str):
        self._send_line(f"GET {room}")

    def set_code(self, room: str, code: str):
        data = code.encode("utf-8")
        self._send_line(f"SET {room} {len(data)}")
        self.f.write(data)
        self.f.flush()

    def _recv_loop(self):
        try:
            while True:
                header = self.f.readline()
                if not header:
                    break
                header = header.decode("utf-8").strip()
                if not header:
                    continue

                parts = header.split()
                if parts[0] == "OK":
                    # simple OK responses, can be logged if needed
                    continue
                if parts[0] == "ERROR":
                    # error messages, you could push to a separate queue
                    continue
                if parts[0] == "DOC":
                    # DOC <room> <size>
                    if len(parts) != 3:
                        continue
                    room = parts[1]
                    size = int(parts[2])
                    remaining = size
                    chunks: list[bytes] = []
                    while remaining > 0:
                        chunk = self.f.read(min(4096, remaining))
                        if not chunk:
                            break
                        chunks.append(chunk)
                        remaining -= len(chunk)
                    if remaining != 0:
                        continue
                    text = b"".join(chunks).decode("utf-8", errors="replace")
                    self.room = room
                    self.current_doc = text
                    self._doc_updates.put(text)
                # else: ignore unknown headers
        finally:
            self.alive = False
            try:
                self.sock.close()
            except OSError:
                pass

    def get_latest_doc(self) -> Optional[str]:
        """Return the latest document content if there is an update, else None."""
        latest = None
        while True:
            try:
                item = self._doc_updates.get_nowait()
                latest = item
            except queue.Empty:
                break
        return latest

    def close(self):
        try:
            self._send_line("BYE")
        except Exception:
            pass
        try:
            self.f.close()
        except Exception:
            pass
        try:
            self.sock.close()
        except Exception:
            pass
        self.alive = False
