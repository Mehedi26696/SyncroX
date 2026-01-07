import socket
import threading
import queue
from typing import List, Optional


class TcpChatClient:
    """
    Minimal TCP client wrapper for Streamlit.

    Protocol:
      - First send:   HELLO <username>
      - Then:
          CREATE_ROOM
          JOIN_ROOM <code>
          MSG <text>
          LIST_ROOMS
          BYE
    """

    def __init__(self, host: str, port: int, username: str):
        self.host = host
        self.port = port
        self.username = username
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))

        # send HELLO
        self.sock.sendall(f"HELLO {self.username}\n".encode("utf-8"))

        # message queue for lines received from server
        self._messages: "queue.Queue[str]" = queue.Queue()
        self.current_room: Optional[str] = None
        self.alive = True

        # background receiver thread
        t = threading.Thread(target=self._recv_loop, daemon=True)
        t.start()

    # ------------------- internal receiver loop -------------------

    def _recv_loop(self):
        try:
            file = self.sock.makefile("r", encoding="utf-8")
            for raw in file:
                line = raw.rstrip("\n")
                self._messages.put(line)

                # auto-track room joining/creation
                parts = line.split()
                if len(parts) >= 2 and parts[0] == "ROOM":
                    # e.g. "ROOM 1234"
                    self.current_room = parts[1]
                elif len(parts) >= 3 and parts[0] == "OK" and parts[1] == "Joined":
                    # e.g. "OK Joined 1234"
                    self.current_room = parts[2]
        except Exception as e:
            self._messages.put(f"SYSTEM error in recv_loop: {e}")
        finally:
            self.alive = False

    # ------------------- public API used by Streamlit -------------------

    def create_room(self):
        self.sock.sendall(b"CREATE_ROOM\n")

    def join_room(self, code: str):
        self.sock.sendall(f"JOIN_ROOM {code}\n".encode("utf-8"))

    def list_rooms(self):
        self.sock.sendall(b"LIST_ROOMS\n")

    def send_message(self, text: str):
        # server remembers which room you're in
        self.sock.sendall(f"MSG {text}\n".encode("utf-8"))

    def send_image(self, base64_data: str):
        self.sock.sendall(f"IMG_SEND {base64_data}\n".encode("utf-8"))

    def request_history(self, limit: int = 50):
        """Request chat history for current room."""
        self.sock.sendall(f"HISTORY {limit}\n".encode("utf-8"))

    def request_image(self, filename: str):
        """Request raw image data for a CDN file."""
        self.sock.sendall(f"GET_IMG {filename}\n".encode("utf-8"))

    def get_new_messages(self) -> List[str]:
        """Drain all messages from queue and return them as a list."""
        lines: List[str] = []
        while True:
            try:
                line = self._messages.get_nowait()
            except queue.Empty:
                break
            else:
                lines.append(line)
        return lines

    def close(self):
        self.alive = False
        try:
            self.sock.sendall(b"BYE\n")
        except OSError:
            pass
        try:
            self.sock.close()
        except OSError:
            pass
