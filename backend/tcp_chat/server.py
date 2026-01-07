# Main TCP chat server
import socket
import threading
import random
import string
import time
import sys
import os
import base64
from collections import defaultdict, deque

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from datetime import datetime
import base64

# Add project root to path for imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.tcp_chat.chat_history import get_chat_history_manager
from config import SERVER_HOST, ROOM_MGMT_PORT
from backend.room_mgmt.client import RoomMgmtClient

# Global room mgmt client
room_client = RoomMgmtClient(host=SERVER_HOST, port=ROOM_MGMT_PORT)

HOST = "0.0.0.0"
PORT = 9009

# Directory for CDN (static images/files) - moved to main data folder
CDN_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data", "cdn"
)
os.makedirs(CDN_DIR, exist_ok=True)

# Initialize chat history manager
chat_history = get_chat_history_manager()

# room_code -> set of client sockets
rooms: dict[str, set[socket.socket]] = defaultdict(set)

# client socket -> username
clients: dict[socket.socket, str] = {}

# for very simple rate limiting: client -> timestamps of last messages
msg_times: dict[socket.socket, deque] = defaultdict(deque)

# Message ID counter per room
msg_counters: dict[str, int] = defaultdict(int)

lock = threading.Lock()


def send_line(conn: socket.socket, text: str):
    try:
        conn.sendall((text + "\n").encode("utf-8"))
    except OSError:
        pass


def broadcast(room_code: str, text: str, exclude: socket.socket | None = None):
    """Send text to all clients in a room."""
    with lock:
        targets = list(rooms.get(room_code, set()))

    for sock in targets:
        if sock is exclude:
            continue
        send_line(sock, text)


def remove_conn_from_all_rooms(conn):
    """Ensure a connection is removed from any rooms they were previously in."""
    empty = []
    with lock:
        for r, conns in rooms.items():
            if conn in conns:
                conns.discard(conn)
                if not conns:
                    empty.append(r)
        for r in empty:
            del rooms[r]


def handle_client(conn: socket.socket, addr):
    print(f"[+] New connection from {addr}")
    room_joined: str | None = None
    username: str | None = None

    try:
        file = conn.makefile("r", encoding="utf-8")

        # --- First line must be HELLO <username> ---
        line = file.readline()
        print(f"[DEBUG] First line from {addr}: {line.strip()!r}")
        if not line:
            return
        line = line.strip()
        parts = line.split(maxsplit=1)
        if len(parts) != 2 or parts[0].upper() != "HELLO":
            send_line(conn, "ERROR Expected 'HELLO <username>' as first command")
            return
        username = parts[1].strip()

        with lock:
            clients[conn] = username
        send_line(conn, f"OK Hello {username}")
        print(f"[+] {username} connected from {addr}")

        # ----- main loop -----
        for line in file:
            line = line.strip()
            print(f"[DEBUG] Command from {username}: {line!r}")
            if not line:
                continue

            cmd, *rest = line.split(maxsplit=1)
            cmd = cmd.upper()

            if cmd == "CREATE_ROOM":
                # Deprecated: Room creation should go through Room MGMT service
                send_line(conn, "ERROR Use Room Management Service to create rooms")

            elif cmd == "JOIN_ROOM":
                if not rest:
                    send_line(conn, "ERROR JOIN_ROOM requires room code")
                    continue
                room_code = rest[0].strip()
                
                # Validate room exists in central service
                if not room_client.room_exists(room_code):
                    send_line(conn, f"ERROR RoomNotFound {room_code}")
                    continue

                remove_conn_from_all_rooms(conn)
                with lock:
                    rooms[room_code].add(conn)
                room_joined = room_code
                send_line(conn, f"OK Joined {room_code}")
                broadcast(room_code, f"SYSTEM {username} joined the room", exclude=conn)
                print(f"[+] {username} joined room {room_code}")
                
                # Save system message to history
                chat_history.add_message(room_code, "SYSTEM", f"{username} joined the room", msg_type="system")

            elif cmd == "MSG":
                if room_joined is None:
                    send_line(conn, "ERROR You are not in a room")
                    continue
                if not rest:
                    send_line(conn, "ERROR Empty message")
                    continue
                msg = rest[0]

                # --- simple rate limiting: max 5 messages per 2 seconds ---
                now = time.time()
                times = msg_times[conn]
                window = 2.0
                limit = 5
                while times and now - times[0] > window:
                    times.popleft()
                if len(times) >= limit:
                    send_line(conn, "ERROR RATE_LIMIT please slow down")
                    continue
                times.append(now)

                # Generate message ID and timestamp
                now_dt = datetime.now()
                ts_str = now_dt.strftime("%Y-%m-%d_%H:%M:%S")
                
                with lock:
                    msg_counters[room_joined] += 1
                    msg_id = msg_counters[room_joined]
                
                broadcast(room_joined, f"MSG {room_joined} {msg_id} {ts_str} {username}: {msg}")
                print(f"[ROOM {room_joined}] #{msg_id} @ {ts_str} {username}: {msg}")
                
                # Save message to history
                chat_history.add_message(room_joined, username, msg, msg_type="text")

            elif cmd == "IMG_SEND":
                if room_joined is None:
                    send_line(conn, "ERROR You are not in a room")
                    continue
                if not rest:
                    send_line(conn, "ERROR No image data")
                    continue
                # Expecting: IMG_SEND <base64_string>
                # Instead of broadcasting base64, save to CDN and broadcast filename
                img_data = rest[0]
                
                # Generate message ID and timestamp
                now_dt = datetime.now()
                ts_str = now_dt.strftime("%Y-%m-%d_%H:%M:%S")
                
                with lock:
                    msg_counters[room_joined] += 1
                    msg_id = msg_counters[room_joined]
                
                # Create unique filename
                file_ext = "png" # Default, could be improved
                filename = f"chat_img_{room_joined}_{msg_id}.{file_ext}"
                filepath = os.path.join(CDN_DIR, filename)
                
                try:
                    # Decode and save as binary file
                    binary_img = base64.b64decode(img_data)
                    with open(filepath, "wb") as f:
                        f.write(binary_img)
                    
                    # Store only filename in logs and broadcast
                    broadcast(room_joined, f"IMG {room_joined} {msg_id} {ts_str} {username} {filename}")
                    print(f"[ROOM {room_joined}] #{msg_id} @ {ts_str} {username} sent image -> {filename}")
                    
                    # Save image metadata to history
                    chat_history.add_message(room_joined, username, filename, msg_type="image")
                except Exception as e:
                    print(f"[!] Error saving image to CDN: {e}")
                    send_line(conn, f"ERROR Failed to process image: {e}")

            elif cmd == "HISTORY":
                # HISTORY [limit] - Get chat history for current room
                if room_joined is None:
                    send_line(conn, "ERROR You are not in a room")
                    continue
                
                limit = 50  # default
                if rest:
                    try:
                        limit = int(rest[0].strip())
                        limit = min(limit, 200)  # cap at 200
                    except ValueError:
                        pass
                
                messages = chat_history.get_room_history(room_joined, limit=limit)
                send_line(conn, f"HISTORY {room_joined} {len(messages)}")
                for msg in messages:
                    msg_id = msg.get("id", "unknown")
                    msg_type = msg.get("type", "text")
                    sender = msg.get("username", "unknown")
                    content = msg.get("message", "")
                    timestamp = msg.get("datetime", "").replace(" ", "_")  # Replace space to avoid parsing issues
                    # Format: HIST <id> <type> <timestamp> <sender> <content>
                    # Note: sender and content are separated by ": " which is parsed on client
                    send_line(conn, f"HIST {msg_id} {msg_type} {timestamp} {sender} {content}")
                send_line(conn, "HISTORY_END")
                print(f"[+] Sent {len(messages)} history messages to {username} in room {room_joined}")

            elif cmd == "GET_IMG":
                # GET_IMG <filename>
                if not rest:
                    send_line(conn, "ERROR GET_IMG requires filename")
                    continue
                
                filename = rest[0].strip()
                filepath = os.path.join(CDN_DIR, filename)
                
                if not os.path.exists(filepath):
                    send_line(conn, f"ERROR File not found: {filename}")
                    continue
                
                try:
                    with open(filepath, "rb") as f:
                        data = f.read()
                        b64_data = base64.b64encode(data).decode("utf-8")
                        send_line(conn, f"IMG_DATA {filename} {b64_data}")
                except Exception as e:
                    send_line(conn, f"ERROR Could not read image: {e}")

            elif cmd == "LIST_ROOMS":
                with lock:
                    codes = " ".join(sorted(rooms.keys()))
                send_line(conn, f"ROOMS {codes}")

            elif cmd == "BYE":
                send_line(conn, "OK Bye")
                break

            else:
                send_line(conn, f"ERROR Unknown command {cmd}")

    except Exception as e:
        print(f"[!] Error with client {addr}: {e}")

    finally:
        print(f"[-] Connection closed from {addr}")
        remove_conn_from_all_rooms(conn)
        with lock:
            if conn in clients:
                del clients[conn]
        try:
            conn.close()
        except OSError:
            pass


def main():
    print(f"[+] TCP chat server starting on {HOST}:{PORT}")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen(20)
        print("[+] Waiting for connections...")
        while True:
            conn, addr = s.accept()
            t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            t.start()


if __name__ == "__main__":
    main()
