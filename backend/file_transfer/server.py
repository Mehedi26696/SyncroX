import socket
import threading
from pathlib import Path
import os
import datetime

HOST = "0.0.0.0"
PORT = 9010

BASE_DIR = Path(__file__).resolve().parents[2]
ROOT_UPLOAD_DIR = BASE_DIR / "data" / "uploads"
os.makedirs(ROOT_UPLOAD_DIR, exist_ok=True)


def get_room_dir(room: str) -> Path | None:
    """Validate room code and return its directory path."""
    if len(room) != 4 or not room.isdigit():
        return None
    room_dir = ROOT_UPLOAD_DIR / room
    room_dir.mkdir(parents=True, exist_ok=True)
    return room_dir


def handle_client(conn: socket.socket, addr):
    print(f"[FILE] New connection from {addr}")
    file = conn.makefile("rb")  # binary read

    try:
        while True:
            line = file.readline()
            if not line:
                break
            line = line.decode("utf-8").strip()
            if not line:
                continue

            parts = line.split()
            cmd = parts[0].upper()

            if cmd == "UPLOAD":
                # UPLOAD <room> <filename> <size>
                if len(parts) < 4:
                    conn.sendall(b"ERROR Invalid UPLOAD syntax\n")
                    continue
                room = parts[1]
                room_dir = get_room_dir(room)
                if room_dir is None:
                    conn.sendall(b"ERROR Invalid room code\n")
                    continue

                filename = parts[2]
                try:
                    size = int(parts[3])
                except ValueError:
                    conn.sendall(b"ERROR Invalid size\n")
                    continue

                dest = room_dir / filename
                remaining = size
                try:
                    with dest.open("wb") as f:
                        # receive file in chunks
                        while remaining > 0:
                            chunk = file.read(min(4096, remaining))
                            if not chunk:
                                break
                            f.write(chunk)
                            remaining -= len(chunk)
                    if remaining != 0:
                        conn.sendall(b"ERROR Incomplete upload\n")
                        # optionally remove partial file
                        if dest.exists():
                            dest.unlink()
                    else:
                        conn.sendall(b"OK SAVED\n")
                        print(f"[FILE] Saved {filename} ({size} bytes) in room {room} from {addr}")
                except Exception as e:
                    print(f"[FILE] Error saving {filename}: {e}")
                    conn.sendall(b"ERROR Save failed\n")

            elif cmd == "LIST":
                # LIST <room>
                if len(parts) < 2:
                    conn.sendall(b"ERROR LIST needs room code\n")
                    continue
                room = parts[1]
                room_dir = get_room_dir(room)
                if room_dir is None:
                    conn.sendall(b"ERROR Invalid room code\n")
                    continue

                files = []
                for p in room_dir.iterdir():
                    if p.is_file():
                        st = p.stat()
                        created = datetime.datetime.fromtimestamp(st.st_ctime).isoformat(timespec="seconds")
                        files.append((p.name, st.st_size, created))
                # sort newest first
                files.sort(key=lambda x: x[2], reverse=True)
                header = f"FILES {len(files)}\n"
                conn.sendall(header.encode("utf-8"))
                for name, size, created in files:
                    line = f"{name} {size} {created}\n"
                    conn.sendall(line.encode("utf-8"))

            elif cmd == "DOWNLOAD":
                # DOWNLOAD <room> <filename>
                if len(parts) < 3:
                    conn.sendall(b"ERROR DOWNLOAD needs room and filename\n")
                    continue
                room = parts[1]
                room_dir = get_room_dir(room)
                if room_dir is None:
                    conn.sendall(b"ERROR Invalid room code\n")
                    continue

                filename = parts[2]
                path = room_dir / filename
                if not path.exists() or not path.is_file():
                    conn.sendall(b"ERROR NotFound\n")
                    continue
                size = path.stat().st_size
                header = f"OK {size}\n"
                conn.sendall(header.encode("utf-8"))
                with path.open("rb") as f:
                    while True:
                        chunk = f.read(4096)
                        if not chunk:
                            break
                        conn.sendall(chunk)
                print(f"[FILE] Sent {filename} ({size} bytes) from room {room} to {addr}")

            elif cmd == "BYE":
                conn.sendall(b"OK Bye\n")
                break

            else:
                conn.sendall(b"ERROR Unknown command\n")

    except Exception as e:
        print(f"[FILE] Error with client {addr}: {e}")
    finally:
        print(f"[FILE] Connection closed from {addr}")
        try:
            conn.close()
        except OSError:
            pass


def main():
    print(f"[FILE] TCP file server starting on {HOST}:{PORT}")
    print(f"[FILE] Root upload dir: {ROOT_UPLOAD_DIR}")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen(5)
        print("[FILE] Waiting for connections...")
        while True:
            conn, addr = s.accept()
            t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            t.start()


if __name__ == "__main__":
    main()
