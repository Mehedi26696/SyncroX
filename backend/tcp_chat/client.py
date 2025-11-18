# TCP client wrapper
import socket
import threading

HOST = "127.0.0.1"
PORT = 9009


def recv_loop(sock: socket.socket):
    try:
        file = sock.makefile("r", encoding="utf-8")
        for line in file:
            print("\n[SERVER]", line.strip())
            print("> ", end="", flush=True)
    except Exception as e:
        print("[!] Receive error:", e)


def main():
    username = input("Enter username: ").strip() or "user"

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((HOST, PORT))

    # send HELLO
    sock.sendall(f"HELLO {username}\n".encode("utf-8"))

    # start background receiver thread
    t = threading.Thread(target=recv_loop, args=(sock,), daemon=True)
    t.start()

    print("Commands:")
    print("  /create           -> create room")
    print("  /join 1234        -> join room 1234")
    print("  /rooms            -> list rooms")
    print("  /quit             -> disconnect")
    print("  normal text       -> send MSG to current room")
    current_room = None

    try:
        while True:
            cmd = input("> ").strip()
            if not cmd:
                continue

            if cmd.startswith("/create"):
                sock.sendall(b"CREATE_ROOM\n")

            elif cmd.startswith("/join"):
                parts = cmd.split()
                if len(parts) != 2:
                    print("Usage: /join 1234")
                    continue
                room = parts[1]
                current_room = room
                sock.sendall(f"JOIN_ROOM {room}\n".encode("utf-8"))

            elif cmd.startswith("/rooms"):
                sock.sendall(b"LIST_ROOMS\n")

            elif cmd.startswith("/quit"):
                sock.sendall(b"BYE\n")
                break

            else:
                # normal message
                if current_room is None:
                    print("You must /create or /join a room first.")
                    continue
                sock.sendall(f"MSG {cmd}\n".encode("utf-8"))

    finally:
        sock.close()


if __name__ == "__main__":
    main()
