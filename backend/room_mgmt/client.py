import socket

class RoomMgmtClient:
    def __init__(self, host="127.0.0.1", port=9013):
        self.host = host
        self.port = port

    def _send_command(self, cmd):
        try:
            with socket.create_connection((self.host, self.port), timeout=5) as s:
                s.sendall(f"{cmd}\n".encode("utf-8"))
                resp = s.recv(1024).decode("utf-8").strip()
                return resp
        except Exception as e:
            return f"ERROR {e}"

    def create_room(self, username):
        resp = self._send_command(f"CREATE {username}")
        if resp.startswith("ROOM "):
            return resp.split()[1]
        return None

    def room_exists(self, code: str) -> bool:
        resp = self._send_command(f"EXISTS {code}")
        return resp == "OK"

    def list_rooms(self) -> list[str]:
        resp = self._send_command("LIST")
        if resp.startswith("ROOMS "):
            return resp[6:].split()
        return []
