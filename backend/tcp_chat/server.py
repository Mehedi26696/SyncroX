# Main TCP chat server
import socket
import threading
import random
import string
import time
from collections import defaultdict, deque

HOST = "0.0.0.0"
PORT = 9009

# room_code -> set of client sockets
rooms: dict[str, set[socket.socket]] = defaultdict(set)

# client socket -> username
clients: dict[socket.socket, str] = {}

# for very simple rate limiting: client -> timestamps of last messages
msg_times: dict[socket.socket, deque] = defaultdict(deque)

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
                    if room_code not in rooms:
                        send_line(conn, "ERROR Room does not exist")
                        continue
                    rooms[room_code].add(conn)
                room_joined = room_code
                send_line(conn, f"OK Joined {room_code}")
                broadcast(room_code, f"SYSTEM {username} joined the room", exclude=conn)
                print(f"[+] {username} joined room {room_code}")

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

                broadcast(room_joined, f"MSG {room_joined} {username}: {msg}")
                print(f"[ROOM {room_joined}] {username}: {msg}")

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
