import socket
from typing import Tuple, Optional



try:
    from config import SERVER_HOST, EXEC_PORT
except ImportError:
    SERVER_HOST = "127.0.0.1"
    EXEC_PORT = 9012

class TcpExecClient:
    def __init__(self, host: str = None, port: int = None):
        self.host = host if host is not None else SERVER_HOST
        self.port = port if port is not None else EXEC_PORT
        self._connect()

    def _connect(self):
        """Establish connection to exec server"""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
        self.f = self.sock.makefile("rwb")

    def _reconnect(self):
        """Reconnect to exec server (used after protocol errors)"""
        print("[CLIENT] Reconnecting to exec server...")
        try:
            self.f.close()
        except Exception:
            pass
        try:
            self.sock.close()
        except Exception:
            pass
        self._connect()
        print("[CLIENT] Reconnected successfully")

    def _send_line(self, text: str):
        self.f.write((text + "\n").encode("utf-8"))
        self.f.flush()

    def execute(
        self,
        room: str,
        language: str,
        code: str,
        stdin_text: str = "",
    ) -> Tuple[bool, str, str, int, int]:
        """
        Returns: (success, stdout_text, stderr_text, return_code, time_ms)
        """
        print(f"[CLIENT] Executing {language} code in room {room}, code_len={len(code)}")
        code_bytes = code.encode("utf-8")
        stdin_bytes = stdin_text.encode("utf-8")
        self._send_line(
            f"EXECUTE {room} {language} {len(code_bytes)} {len(stdin_bytes)}"
        )
        self.f.write(code_bytes)
        self.f.write(stdin_bytes)
        self.f.flush()
        print(f"[CLIENT] Request sent, waiting for response...")

        header = self.f.readline()
        print(f"[CLIENT] Received header: {header}")
        if not header:
            return False, "", "No response from exec server", -1, 0

        header = header.decode("utf-8").strip()
        parts = header.split()
        if len(parts) < 1 or parts[0] != "RESULT" or len(parts) != 6:
            # Protocol error - connection stream is likely corrupted
            # Reconnect to get a fresh connection
            try:
                self._reconnect()
            except Exception as e:
                print(f"[CLIENT] Reconnect failed: {e}")
            return False, "", f"Malformed response: {header}", -1, 0

        success_flag = parts[1]
        rc = int(parts[2])
        out_size = int(parts[3])
        err_size = int(parts[4])
        time_ms = int(parts[5])

        print(f"[CLIENT] Parsed: success={success_flag}, rc={rc}, out_size={out_size}, err_size={err_size}, time={time_ms}ms")

        # read stdout
        stdout = b""
        remaining = out_size
        while remaining > 0:
            chunk = self.f.read(min(4096, remaining))
            if not chunk:
                break
            stdout += chunk
            remaining -= len(chunk)

        # read stderr
        stderr = b""
        remaining = err_size
        while remaining > 0:
            chunk = self.f.read(min(4096, remaining))
            if not chunk:
                break
            stderr += chunk
            remaining -= len(chunk)

        success = success_flag == "1"
        stdout_text = stdout.decode("utf-8", errors="replace")
        stderr_text = stderr.decode("utf-8", errors="replace")
        print(f"[CLIENT] Output received: stdout='{stdout_text}', stderr='{stderr_text}'")
        return success, stdout_text, stderr_text, rc, time_ms

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
