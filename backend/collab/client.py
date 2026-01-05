import socket
import threading
import queue
from typing import Optional, List, Tuple


class TcpCollabClient:
    def __init__(self, host: str, port: int, username: str):
        self.host = host
        self.port = port
        self.username = username

        # Debug logging
        import logging
        self.logger = logging.getLogger("CollabClient")
        self.logger.setLevel(logging.INFO)
        # Avoid adding multiple handlers if re-initialized
        if not self.logger.handlers:
            fh = logging.FileHandler("client_debug.txt", mode='w')
            fh.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
            self.logger.addHandler(fh)
        
        self.logger.info(f"Connected to {host}:{port} as {username}")

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
        # Use makefile only for reading, to avoid buffering conflicts with sends
        self.f = self.sock.makefile("rb")

        # send HELLO
        self._send_line(f"HELLO {self.username}")

        self.room: Optional[str] = None
        self.current_doc: str = ""
        self.current_lang: str = "python"
        self.last_editor: Optional[str] = None

        # queues for async updates - now contains (text, lang) tuples
        self._doc_updates: "queue.Queue[Tuple[str, str]]" = queue.Queue()
        self._users_updates: "queue.Queue[List[Tuple[str, str]]]" = queue.Queue()

        # latest snapshots
        self.active_users: List[Tuple[str, str]] = []  # list of (name, status)
        self.alive = True

        t = threading.Thread(target=self._recv_loop, daemon=True)
        t.start()

    # ------------- basic sending helpers -------------

    def _send_line(self, text: str):
        try:
            self.sock.sendall((text + "\n").encode("utf-8"))
        except OSError:
            self.alive = False

    def join_room(self, room: str, lang: str = "python"):
        self._send_line(f"JOIN {room} {lang}")

    def request_doc(self, room: str, lang: str = "python"):
        self._send_line(f"GET {room} {lang}")

    def request_users(self, room: str):
        """Ask server for active users in a room."""
        self._send_line(f"USERS {room}")

    def set_code(self, room: str, code: str, lang: str = "python"):
        data = code.encode("utf-8")
        self._send_line(f"SET {room} {lang} {len(data)}")
        try:
            self.sock.sendall(data)
        except OSError:
            self.alive = False

    # ------------- receiving loop -------------

    def _recv_loop(self):
        try:
            while True:
                header = self.f.readline()
                if not header:
                    break
                header = header.decode("utf-8").strip()
                if not header:
                    self.logger.info("Empty header line, continuing")
                    continue
                
                # self.logger.info(f"Received header: {header}") 

                parts = header.split()
                if parts[0] == "OK":
                    continue
                if parts[0] == "ERROR":
                    self.logger.error(f"Server error: {header}")
                    continue

                # DOC <room> <lang> <size> <editor>
                if parts[0] == "DOC":
                    self.logger.info(f"Received DOC header: {header}")
                    if len(parts) < 4:
                        continue
                    room = parts[1]
                    lang = parts[2]
                    size = int(parts[3])
                    editor = parts[4] if len(parts) >= 5 else "unknown"

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
                    self.last_editor = editor
                    self.current_lang = lang
                    self._doc_updates.put((text, lang))
                    self.logger.info(f"Put doc update in queue. Lang: {lang}, Size: {len(text)}. Queue size: {self._doc_updates.qsize()}")

                # USERS <room> name1:status1,name2:status2,...
                elif parts[0] == "USERS":
                    if len(parts) < 3:
                        self.active_users = []
                        self._users_updates.put(self.active_users)
                        continue
                    room = parts[1]
                    payload = " ".join(parts[2:])
                    entries = payload.split(",") if payload else []
                    parsed: List[Tuple[str, str]] = []
                    for e in entries:
                        if not e:
                            continue
                        if ":" in e:
                            name, status = e.split(":", 1)
                        else:
                            name, status = e, "idle"
                        parsed.append((name, status))
                    self.active_users = parsed
                    self._users_updates.put(parsed)

                # else: ignore unknown headers
        finally:
            self.alive = False
            try:
                self.sock.close()
            except OSError:
                pass

    # ------------- helpers used by Streamlit -------------

    def get_latest_doc(self, for_lang: str = None) -> Optional[Tuple[str, str]]:
        """
        Return the latest document update as (text, lang) if there is one, else None.
        If for_lang is specified, only return updates for that language.
        """
        latest = None
        while True:
            try:
                item = self._doc_updates.get_nowait()
                text, lang = item
                # If filtering by language, only accept matching updates
                if for_lang is None or lang == for_lang:
                    latest = item
            except queue.Empty:
                break
        return latest

    def get_latest_users(self) -> Optional[List[Tuple[str, str]]]:
        """Return the latest users list if updated, else None."""
        latest = None
        while True:
            try:
                item = self._users_updates.get_nowait()
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
