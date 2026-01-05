# Main TCP chat server
import socket
import threading
import random
import string
import time
import sys
import os
from collections import defaultdict, deque

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from chat_history import get_chat_history_manager

HOST = "0.0.0.0"
PORT = 9009

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

# Seen tracking: room_code -> msg_id -> set of usernames who have seen it
msg_seen: dict[str, dict[int, set[str]]] = defaultdict(lambda: defaultdict(set))

# Track last N message IDs per room for seen status (limit memory usage)
MAX_TRACKED_MESSAGES = 100
msg_ids_by_room: dict[str, deque] = defaultdict(lambda: deque(maxlen=MAX_TRACKED_MESSAGES))

lock = threading.Lock()


def generate_room_code() -> str:
    """Generate a unique 4-digit room code."""
    while True:
        code = "".join(random.choices(string.digits, k=4))
        with lock:
            if code not in rooms:
                return code


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
                room_code = generate_room_code()
                with lock:
                    rooms[room_code].add(conn)
                room_joined = room_code
                send_line(conn, f"ROOM {room_code}")
                print(f"[+] {username} created and joined room {room_code}")

            elif cmd == "JOIN_ROOM":
                if not rest:
                    send_line(conn, "ERROR JOIN_ROOM requires room code")
                    continue
                room_code = rest[0].strip()
                with lock:
                    # Auto-create room if it doesn't exist (for flexible room codes)
                    if room_code not in rooms:
                        rooms[room_code] = set()
                    rooms[room_code].add(conn)
                room_joined = room_code
                send_line(conn, f"OK Joined {room_code}")
                broadcast(room_code, f"SYSTEM {username} joined the room", exclude=conn)
                print(f"[+] {username} joined room {room_code}")
                
                # Save system message to history
                chat_history.add_message(room_code, username, f"{username} joined the room", msg_type="system")

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

                # Generate message ID
                with lock:
                    msg_counters[room_joined] += 1
                    msg_id = msg_counters[room_joined]
                    msg_ids_by_room[room_joined].append(msg_id)
                    # Sender has seen their own message
                    msg_seen[room_joined][msg_id].add(username)
                
                broadcast(room_joined, f"MSG {room_joined} {msg_id} {username}: {msg}")
                print(f"[ROOM {room_joined}] #{msg_id} {username}: {msg}")
                
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
                # We broadcast: IMG <room_code> <msg_id> <username> <base64_string>
                img_data = rest[0]
                
                # Generate message ID
                with lock:
                    msg_counters[room_joined] += 1
                    msg_id = msg_counters[room_joined]
                    msg_ids_by_room[room_joined].append(msg_id)
                    msg_seen[room_joined][msg_id].add(username)
                
                broadcast(room_joined, f"IMG {room_joined} {msg_id} {username} {img_data}")
                print(f"[ROOM {room_joined}] #{msg_id} {username} sent an image ({len(img_data)} chars)")
                
                # Save image to history (store base64 data)
                chat_history.add_message(room_joined, username, img_data, msg_type="image")

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
                    msg_type = msg.get("type", "text")
                    sender = msg.get("username", "unknown")
                    content = msg.get("message", "")
                    timestamp = msg.get("datetime", "").replace(" ", "_")  # Replace space to avoid parsing issues
                    # Format: HIST <type> <timestamp> <sender> <content>
                    # Note: sender and content are separated by ": " which is parsed on client
                    send_line(conn, f"HIST {msg_type} {timestamp} {sender} {content}")
                send_line(conn, "HISTORY_END")
                print(f"[+] Sent {len(messages)} history messages to {username} in room {room_joined}")

            elif cmd == "SEEN":
                # SEEN <msg_id> - Mark a message as seen by this user
                if room_joined is None:
                    send_line(conn, "ERROR You are not in a room")
                    continue
                if not rest:
                    send_line(conn, "ERROR SEEN requires message ID")
                    continue
                try:
                    msg_id = int(rest[0].strip())
                except ValueError:
                    send_line(conn, "ERROR Invalid message ID")
                    continue
                
                with lock:
                    if msg_id in [m for m in msg_ids_by_room[room_joined]]:
                        already_seen = username in msg_seen[room_joined][msg_id]
                        msg_seen[room_joined][msg_id].add(username)
                        seen_by = list(msg_seen[room_joined][msg_id])
                
                # Broadcast seen update to everyone in room (only if new)
                if not already_seen:
                    broadcast(room_joined, f"SEEN_BY {room_joined} {msg_id} {','.join(seen_by)}")

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
        with lock:
            if conn in clients:
                username = clients.pop(conn)
            # remove from rooms
            for code, members in list(rooms.items()):
                if conn in members:
                    members.remove(conn)
                    if not members:
                        rooms.pop(code, None)
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
