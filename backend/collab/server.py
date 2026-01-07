import socket
import threading
from collections import defaultdict
from pathlib import Path
import os
import time
import sys

# Add project root to path for imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import SERVER_HOST, ROOM_MGMT_PORT
from backend.room_mgmt.client import RoomMgmtClient

# Global room mgmt client
room_client = RoomMgmtClient(host=SERVER_HOST, port=ROOM_MGMT_PORT)

HOST = "0.0.0.0"
PORT = 9011  # collab server port

BASE_DIR = Path(__file__).resolve().parents[2]
DOC_DIR = BASE_DIR / "data" / "collab_docs"
os.makedirs(DOC_DIR, exist_ok=True)

# room -> current document text
docs: dict[str, str] = {}
# room_lang -> document text (e.g., "1234_python" -> code)
lang_docs: dict[str, str] = {}
# room -> set of client sockets
room_clients: dict[str, set[socket.socket]] = defaultdict(set)
# client -> username
clients: dict[socket.socket, str] = {}
# room -> username -> last time they did a SET (used to detect "typing")
room_user_last_set: dict[str, dict[str, float]] = defaultdict(dict)

lock = threading.Lock()

VALID_LANGUAGES = {"python", "c", "cpp", "java"}


def valid_room(room: str) -> bool:
    return len(room) == 4 and room.isdigit()


def valid_language(lang: str) -> bool:
    return lang.lower() in VALID_LANGUAGES


def get_doc_key(room: str, lang: str) -> str:
    """Get the key for room+language combination."""
    return f"{room}_{lang.lower()}"


def load_doc(room: str, lang: str = None) -> str:
    """Load document content for a room (and optionally language) from disk or return default text."""
    if lang:
        path = DOC_DIR / f"{room}_{lang.lower()}.txt"
        if path.exists():
            return path.read_text(encoding="utf-8")
        # Return language-specific default
        defaults = {
            "python": "# Python code\n# Start writing your code here...\n",
            "c": "// C code\n#include <stdio.h>\n\nint main() {\n    // Start writing your code here\n    return 0;\n}\n",
            "cpp": "// C++ code\n#include <iostream>\nusing namespace std;\n\nint main() {\n    // Start writing your code here\n    return 0;\n}\n",
            "java": "// Java code\npublic class Main {\n    public static void main(String[] args) {\n        // Start writing your code here\n    }\n}\n",
        }
        return defaults.get(lang.lower(), "# Start writing your code here...\n")
    
    # Legacy: load without language (for backward compatibility)
    path = DOC_DIR / f"{room}.txt"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return "# Welcome to collaborative coding!\n# Start writing your code here...\n"


def save_doc(room: str, content: str, lang: str = None) -> None:
    """Persist document content for a room (and optionally language) to disk."""
    if lang:
        path = DOC_DIR / f"{room}_{lang.lower()}.txt"
    else:
        path = DOC_DIR / f"{room}.txt"
    path.write_text(content, encoding="utf-8")


def send_line(conn: socket.socket, text: str):
    try:
        conn.sendall((text + "\n").encode("utf-8"))
    except OSError:
        pass


def broadcast_doc(
    room: str,
    content: str,
    editor: str,
    lang: str = "python",
    exclude: socket.socket | None = None,
):
    """
    Send updated document to all clients in a room, tagging who edited it.
    DOC <room> <lang> <size> <editor>\n
    <code_bytes>
    """
    data = content.encode("utf-8")
    header = f"DOC {room} {lang} {len(data)} {editor}\n".encode("utf-8")

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


def remove_conn_from_all_rooms(conn):
    """Ensure a connection is removed from any rooms they were previously in."""
    empty = []
    with lock:
        for r, conns in room_clients.items():
            if conn in conns:
                conns.discard(conn)
                if not conns:
                    empty.append(r)
        for r in empty:
            room_clients.pop(r, None)
            room_user_last_set.pop(r, None)


def handle_client(conn: socket.socket, addr):
    print(f"[COLLAB] New connection from {addr}")
    f = conn.makefile("rwb")
    current_room: str | None = None
    username = "user"

    try:
        # Optional HELLO <username>
        header = f.readline()
        if not header:
            return
        header = header.decode("utf-8").strip()
        parts = header.split(maxsplit=1)
        if len(parts) == 2 and parts[0].upper() == "HELLO":
            username = parts[1].strip()

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
                # JOIN <room> [lang]
                if len(parts) < 2:
                    send_line(conn, "ERROR JOIN needs room")
                    continue
                room = parts[1]
                lang = parts[2].lower() if len(parts) >= 3 and valid_language(parts[2]) else "python"
                if not valid_room(room):
                    send_line(conn, "ERROR Invalid room code")
                    continue

                # Validate room exists in central service
                if not room_client.room_exists(room):
                    send_line(conn, f"ERROR RoomNotFound {room}")
                    continue

                doc_key = get_doc_key(room, lang)
                remove_conn_from_all_rooms(conn)
                with lock:
                    # load or create doc for this room+language
                    if doc_key not in lang_docs:
                        lang_docs[doc_key] = load_doc(room, lang)
                    room_clients[room].add(conn)
                    current_room = room
                    # touch last_set dict so USERS has an entry
                    _ = room_user_last_set[room]

                send_line(conn, f"OK Joined {room}")
                # send current document for this language
                content = lang_docs[doc_key]
                data = content.encode("utf-8")
                # when you first join, treat 'server' as editor
                header = f"DOC {room} {lang} {len(data)} server\n".encode("utf-8")
                try:
                    conn.sendall(header)
                    conn.sendall(data)
                except OSError:
                    break
                print(f"[COLLAB] {username} joined room {room} (lang={lang})")

            elif cmd == "SET":
                # SET <room> <lang> <size>
                if len(parts) < 4:
                    send_line(conn, "ERROR SET needs room, lang, and size")
                    continue
                room = parts[1]
                lang = parts[2].lower()
                if not valid_room(room):
                    send_line(conn, "ERROR Invalid room code")
                    continue
                if not valid_language(lang):
                    send_line(conn, "ERROR Invalid language")
                    continue
                try:
                    size = int(parts[3])
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

                doc_key = get_doc_key(room, lang)
                with lock:
                    lang_docs[doc_key] = content
                    save_doc(room, content, lang)
                    editor = clients.get(conn, "someone")
                    room_user_last_set[room][editor] = time.time()

                send_line(conn, f"OK SAVED {room} {lang}")
                broadcast_doc(room, content, editor=editor, lang=lang, exclude=conn)
                print(f"[COLLAB] Updated {lang} document in room {room} (from {editor})")

            elif cmd == "GET":
                # GET <room> <lang>
                if len(parts) < 3:
                    send_line(conn, "ERROR GET needs room and lang")
                    continue
                room = parts[1]
                lang = parts[2].lower()
                if not valid_room(room):
                    send_line(conn, "ERROR Invalid room code")
                    continue
                if not valid_language(lang):
                    send_line(conn, "ERROR Invalid language")
                    continue
                
                doc_key = get_doc_key(room, lang)
                with lock:
                    if doc_key not in lang_docs:
                        lang_docs[doc_key] = load_doc(room, lang)
                    content = lang_docs[doc_key]
                data = content.encode("utf-8")
                header = f"DOC {room} {lang} {len(data)} server\n".encode("utf-8")
                try:
                    conn.sendall(header)
                    conn.sendall(data)
                except OSError:
                    break

            elif cmd == "USERS":
                # USERS <room>
                if len(parts) < 2:
                    send_line(conn, "ERROR USERS needs room")
                    continue
                room = parts[1]
                if not valid_room(room):
                    send_line(conn, "ERROR Invalid room code")
                    continue

                with lock:
                    now = time.time()
                    members = room_clients.get(room, set())
                    entries: list[str] = []
                    for c in members:
                        uname = clients.get(c, "user")
                        last_set = room_user_last_set[room].get(uname, 0.0)
                        typing = (now - last_set) < 3.0  # last 3s -> typing
                        status = "typing" if typing else "idle"
                        entries.append(f"{uname}:{status}")
                    payload = ",".join(entries)

                send_line(conn, f"USERS {room} {payload}")

            elif cmd == "BYE":
                send_line(conn, "OK Bye")
                break

            else:
                send_line(conn, f"ERROR Unknown command {cmd}")

    except Exception as e:
        print(f"[COLLAB] Error with client {addr}: {e}")

    finally:
        print(f"[COLLAB] Connection closed from {addr}")
        remove_conn_from_all_rooms(conn)
        with lock:
            clients.pop(conn, None)
        try:
            conn.close()
        except OSError:
            pass


def main():
    print(f"[COLLAB] TCP collab server starting on {HOST}:{PORT}")
    print(f"[COLLAB] Docs directory: {DOC_DIR}")
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
