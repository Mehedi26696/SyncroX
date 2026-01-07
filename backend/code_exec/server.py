import socket
import threading
import tempfile
import subprocess
import time
import re
from pathlib import Path
import os
import sys

# Add project root to path for imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import SERVER_HOST, ROOM_MGMT_PORT
from backend.room_mgmt.client import RoomMgmtClient
from backend.code_exec.exec_history import get_history_manager

# Global room mgmt client
room_client = RoomMgmtClient(host=SERVER_HOST, port=ROOM_MGMT_PORT)
# Initialize history manager
exec_history = get_history_manager()

HOST = "0.0.0.0"
PORT = 9012           # execution server TCP port
SANDBOX_IMAGE = "syncrox-sandbox"

# Simple helper to run a command inside the Docker sandbox
def run_in_docker(cmd_inside: list[str], workdir: Path, stdin_data: bytes = b"", timeout: int = 3):
    """
    cmd_inside: command to run inside container, e.g. ["python", "main.py"]
    workdir: local temp dir to mount as /sandbox
    stdin_data: bytes to send to stdin of the process
    """
    print(f"[DOCKER] Running command: {' '.join(cmd_inside)}")
    cmd = [
        "docker", "run", "--rm", "-i",
        "-m", "256m", "--cpus=0.5",
        "-v", f"{workdir}:/sandbox",
        SANDBOX_IMAGE,
        *cmd_inside,
    ]

    start = time.time()
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        # pass stdin_data (if empty, send None)
        input_bytes = stdin_data if stdin_data else None
        stdout, stderr = proc.communicate(input=input_bytes, timeout=timeout)
        success = proc.returncode == 0
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()
        success = False
        stderr += b"\n[Timed out]"
    end = time.time()
    ms = int((end - start) * 1000)
    print(f"[DOCKER] Command complete: success={success}, rc={proc.returncode}, time={ms}ms")
    return success, stdout, stderr, proc.returncode, ms


def extract_java_class_name(code: str) -> str:
    """
    Extract the public class name from Java code.
    Returns the class name or None if not found.
    """
    # Look for 'public class ClassName' pattern
    # Handles: public class Foo, public class Foo extends Bar, public class Foo implements Baz
    match = re.search(r'\bpublic\s+class\s+(\w+)', code)
    if match:
        return match.group(1)
    
    # If no public class, look for any class definition
    match = re.search(r'\bclass\s+(\w+)', code)
    if match:
        return match.group(1)
    
    return None


def execute_code(language: str, code: bytes, stdin_data: bytes):
    with tempfile.TemporaryDirectory() as tmpdir_str:
        tmpdir = Path(tmpdir_str)

        if language == "python":
            src = tmpdir / "main.py"
            src.write_bytes(code)
            return run_in_docker(["python", "/sandbox/main.py"], tmpdir, stdin_data)

        elif language == "c":
            src = tmpdir / "main.c"
            src.write_bytes(code)

            ok, out, err, rc, _ = run_in_docker(
                ["bash", "-c", "cd /sandbox && gcc main.c -O2 -o main"],
                tmpdir,
                timeout=5,
            )
            if not ok:
                return False, b"", err, rc, 0

            return run_in_docker(["/sandbox/main"], tmpdir, stdin_data)

        elif language == "cpp":
            src = tmpdir / "main.cpp"
            src.write_bytes(code)

            ok, out, err, rc, _ = run_in_docker(
                ["bash", "-c", "cd /sandbox && g++ main.cpp -O2 -o main"],
                tmpdir,
                timeout=5,
            )
            if not ok:
                return False, b"", err, rc, 0

            return run_in_docker(["/sandbox/main"], tmpdir, stdin_data)

        elif language == "java":
            # Extract public class name from code
            code_str = code.decode("utf-8", errors="replace")
            class_name = extract_java_class_name(code_str)
            
            if not class_name:
                return False, b"", b"Error: Could not find a public class in Java code.\nMake sure you have 'public class ClassName' in your code.", -1, 0
            
            print(f"[JAVA] Detected class name: {class_name}")
            
            # Save file with the correct class name
            src = tmpdir / f"{class_name}.java"
            src.write_bytes(code)

            # Java compilation - give more time for javac
            ok, out, err, rc, _ = run_in_docker(
                ["bash", "-c", f"cd /sandbox && javac {class_name}.java"],
                tmpdir,
                timeout=15,  # Increased: javac can be slow
            )
            if not ok:
                return False, b"", err, rc, 0

            # Java execution - JVM startup is slow, need more time
            return run_in_docker(
                ["bash", "-c", f"cd /sandbox && java {class_name}"],
                tmpdir,
                stdin_data,
                timeout=10,  # Increased: JVM startup takes 2-5 seconds
            )

        else:
            msg = f"Unsupported language: {language}".encode("utf-8")
            return False, b"", msg, -1, 0



def handle_client(conn: socket.socket, addr):
    """
    Protocol:

    Client -> Server:
        EXECUTE <room> <language> <code_size> <input_size>\n
        <code_bytes...>
        <stdin_bytes...>

    Server -> Client:
        RESULT <success> <return_code> <out_size> <err_size> <time_ms>\n
        <stdout_bytes...>
        <stderr_bytes...>
    """
    print(f"[EXEC] New connection from {addr}")
    f = conn.makefile("rwb")

    try:
        while True:
            header = f.readline()
            if not header:
                break
            header = header.decode("utf-8").strip()
            if not header:
                continue

            parts = header.split()
            cmd = parts[0].upper()

            if cmd == "EXECUTE":
                if len(parts) != 5:
                    f.write(b"RESULT 0 -1 0 0 0\n")
                    f.flush()
                    continue

                room, language, code_size_str, input_size_str = parts[1:]
                
                # Validate room exists in central service
                if not room_client.room_exists(room):
                    f.write(b"RESULT 0 -1 0 0 0\n")
                    f.write(b"RoomNotFound\n") # Optional: send as error message
                    f.flush()
                    continue

                try:
                    code_size = int(code_size_str)
                    input_size = int(input_size_str)
                except ValueError:
                    f.write(b"RESULT 0 -1 0 0 0\n")
                    f.flush()
                    continue

                # Read code
                remaining = code_size
                code_chunks: list[bytes] = []
                while remaining > 0:
                    chunk = f.read(min(4096, remaining))
                    if not chunk:
                        break
                    code_chunks.append(chunk)
                    remaining -= len(chunk)
                if remaining != 0:
                    f.write(b"RESULT 0 -1 0 0 0\n")
                    f.flush()
                    continue
                code = b"".join(code_chunks)

                # Read stdin
                remaining = input_size
                in_chunks: list[bytes] = []
                while remaining > 0:
                    chunk = f.read(min(4096, remaining))
                    if not chunk:
                        break
                    in_chunks.append(chunk)
                    remaining -= len(chunk)
                if remaining != 0:
                    f.write(b"RESULT 0 -1 0 0 0\n")
                    f.flush()
                    continue
                stdin_data = b"".join(in_chunks)

                print(f"[EXEC] Room {room}, language={language}, code_size={code_size}")
                print(f"[EXEC] Starting execution...")

                success, stdout, stderr, rc, time_ms = execute_code(
                    language, code, stdin_data
                )

                # Record to history
                exec_history.add_execution(
                    room=room,
                    user="Unknown", # Could be passed in protocol if we want
                    language=language,
                    code=code.decode("utf-8", errors="replace"),
                    stdin=stdin_data.decode("utf-8", errors="replace"),
                    stdout=stdout.decode("utf-8", errors="replace"),
                    stderr=stderr.decode("utf-8", errors="replace"),
                    return_code=rc,
                    success=success,
                    time_ms=time_ms
                )

                print(f"[EXEC] Execution complete: success={success}, rc={rc}, stdout_len={len(stdout)}, stderr_len={len(stderr)}, time={time_ms}ms")

                out_size = len(stdout)
                err_size = len(stderr)
                header_resp = f"RESULT {1 if success else 0} {rc} {out_size} {err_size} {time_ms}\n"
                print(f"[EXEC] Sending response: {header_resp.strip()}")
                f.write(header_resp.encode("utf-8"))
                f.write(stdout)
                f.write(stderr)
                f.flush()
                print(f"[EXEC] Response sent successfully")

            elif cmd == "BYE":
                f.write(b"OK Bye\n")
                f.flush()
                break

            else:
                f.write(b"RESULT 0 -1 0 0 0\n")
                f.flush()

    except Exception as e:
        print(f"[EXEC] Error with client {addr}: {e}")
    finally:
        print(f"[EXEC] Connection closed from {addr}")
        try:
            conn.close()
        except OSError:
            pass


def main():
    print(f"[EXEC] TCP code exec server on {HOST}:{PORT}")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen(10)
        print("[EXEC] Waiting for connections...")
        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()


if __name__ == "__main__":
    main()
