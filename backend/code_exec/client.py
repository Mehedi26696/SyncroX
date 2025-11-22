import socket
from typing import Tuple, Optional


class TcpExecClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 9012):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
        self.f = self.sock.makefile("rwb")

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
        if parts[0] != "RESULT" or len(parts) != 6:
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
