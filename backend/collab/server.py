import socket
import threading
from collections import defaultdict
from pathlib import Path
import os

HOST = "0.0.0.0"
PORT = 9011  # collab server port

BASE_DIR = Path(__file__).resolve().parents[2]
DOC_DIR = BASE_DIR / "data" / "collab_docs"
os.makedirs(DOC_DIR, exist_ok=True)

# room -> current document text
docs: dict[str, str] = {}
# room -> set of client sockets
room_clients: dict[str, set[socket.socket]] = defaultdict(set)
# client -> username
clients: dict[socket.socket, str] = {}

lock = threading.Lock()


def valid_room(room: str) -> bool:
    return len(room) == 4 and room.isdigit()


def load_doc(room: str) -> str:
    path = DOC_DIR / f"{room}.txt"
    if path.exists():
        return path.read_text(encoding="utf-8")
    # default initial content
    return "# Welcome to collaborative coding!\n# Start writing your code here...\n"


def save_doc(room: str, content: str) -> None:
    path = DOC_DIR / f"{room}.txt"
    path.write_text(content, encoding="utf-8")


def send_line(conn: socket.socket, text: str):
    try:
        conn.sendall((text + "\n").encode("utf-8"))
    except OSError:
        pass


def broadcast_doc(room: str, content: str, exclude: socket.socket | None = None):
    data = content.encode("utf-8")
    header = f"DOC {room} {len(data)}\n".encode("utf-8")

    with lock:
        targets = list(room_clients.get(room, set()))

    for sock in targets:
        if sock is exclude:
            continue
        try:
            sock.sendall(header)
            sock.sendall(data)
        except OSError:
            pass


def handle_client(conn: socket.socket, addr):
    print(f"[COLLAB] New connection from {addr}")
    f = conn.makefile("rwb")
    current_room: str | None = None

    try:
        # Optional HELLO <username>
        header = f.readline()
        if not header:
            return
        header = header.decode("utf-8").strip()
        parts = header.split(maxsplit=1)
        if len(parts) == 2 and parts[0].upper() == "HELLO":
            username = parts[1].strip()
        else:
            username = "user"
        with lock:
            clients[conn] = username
        send_line(conn, f"OK Hello {username}")

        while True:
            line = f.readline()
            if not line:
                break
            line = line.decode("utf-8").strip()
            if not line:
                continue

            parts = line.split()
            cmd = parts[0].upper()

            if cmd == "JOIN":
                # JOIN <room>
                if len(parts) < 2:
                    send_line(conn, "ERROR JOIN needs room")
                    continue
                room = parts[1]
                if not valid_room(room):
                    send_line(conn, "ERROR Invalid room code")
                    continue

                with lock:
                    # load or create doc
                    if room not in docs:
                        docs[room] = load_doc(room)
                    room_clients[room].add(conn)
                    current_room = room

                send_line(conn, f"OK Joined {room}")
                # send current document
                content = docs[room]
                data = content.encode("utf-8")
                header = f"DOC {room} {len(data)}\n".encode("utf-8")
                try:
                    conn.sendall(header)
                    conn.sendall(data)
                except OSError:
                    break
                print(f"[COLLAB] {username} joined room {room}")

            elif cmd == "SET":
                # SET <room> <size>
                if len(parts) < 3:
                    send_line(conn, "ERROR SET needs room and size")
                    continue
                room = parts[1]
                if not valid_room(room):
                    send_line(conn, "ERROR Invalid room code")
                    continue
                try:
                    size = int(parts[2])
                except ValueError:
                    send_line(conn, "ERROR Invalid size")
                    continue

                # read exactly 'size' bytes of code
                remaining = size
                chunks: list[bytes] = []
                while remaining > 0:
                    chunk = f.read(min(4096, remaining))
                    if not chunk:
                        break
                    chunks.append(chunk)
                    remaining -= len(chunk)
                if remaining != 0:
                    send_line(conn, "ERROR Incomplete SET data")
                    continue

                content = b"".join(chunks).decode("utf-8", errors="replace")

                with lock:
                    docs[room] = content
                    save_doc(room, content)

                send_line(conn, f"OK SAVED {room}")
                broadcast_doc(room, content, exclude=conn)
                print(f"[COLLAB] Updated document in room {room} (from {username})")

            elif cmd == "GET":
                # GET <room>
                if len(parts) < 2:
                    send_line(conn, "ERROR GET needs room")
                    continue
                room = parts[1]
                if not valid_room(room):
                    send_line(conn, "ERROR Invalid room code")
                    continue
                with lock:
                    if room not in docs:
                        docs[room] = load_doc(room)
                    content = docs[room]
                data = content.encode("utf-8")
                header = f"DOC {room} {len(data)}\n".encode("utf-8")
                try:
                    conn.sendall(header)
                    conn.sendall(data)
                except OSError:
                    break

            elif cmd == "BYE":
                send_line(conn, "OK Bye")
                break

            else:
                send_line(conn, f"ERROR Unknown command {cmd}")

    except Exception as e:
        print(f"[COLLAB] Error with client {addr}: {e}")

    finally:
        print(f"[COLLAB] Connection closed from {addr}")
        with lock:
            clients.pop(conn, None)
            for room, members in list(room_clients.items()):
                if conn in members:
                    members.remove(conn)
                    if not members:
                        room_clients.pop(room, None)
        try:
            conn.close()
        except OSError:
            pass


def main():
    print(f"[COLLAB] TCP collab server starting on {HOST}:{PORT}")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen(20)
        print("[COLLAB] Waiting for connections...")
        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()


if __name__ == "__main__":
    main()
