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

CHUNK_SIZE = 4096


def get_room_dir(room: str) -> Path | None:
    """Validate room code and return its directory path."""
    if len(room) != 4 or not room.isdigit():
        return None
    room_dir = ROOT_UPLOAD_DIR / room
    room_dir.mkdir(parents=True, exist_ok=True)
    return room_dir


def handle_client(conn: socket.socket, addr):
    print(f"[FILE] New connection from {addr}")
    
    # Use a buffer to accumulate bytes until we find a complete line
    buffer = b""
    
    try:
        while True:
            # Only recv if buffer doesn't have a complete command line
            if b"\n" not in buffer:
                try:
                    data = conn.recv(4096)
                except ConnectionResetError:
                    # Client disconnected abruptly (common with Streamlit reruns)
                    break
                if not data:
                    break
                buffer += data
            
            # Look for a complete line (ending with \n)
            if b"\n" not in buffer:
                continue
                
            line_end = buffer.index(b"\n")
            line_bytes = buffer[:line_end]
            buffer = buffer[line_end + 1:]  # Remove the processed line
            
            try:
                line = line_bytes.decode("utf-8").strip()
            except UnicodeDecodeError:
                # Binary data received where command expected - likely client error
                print(f"[FILE] Invalid encoding from {addr}")
                print(f"[FILE] Raw bytes (first 100): {line_bytes[:100]}")
                buffer = b""  # Clear corrupted buffer
                conn.sendall(b"ERROR Invalid command encoding\n")
                continue
            
            print(f"[FILE] Command from {addr}: {line[:80]}")  # Debug: show command
            
            if not line:
                continue

            parts = line.split()
            cmd = parts[0].upper()

            if cmd == "UPLOAD":
                # UPLOAD <room> <filename> <size>
                # Note: filename may contain spaces, so size is always the LAST part
                if len(parts) < 4:
                    conn.sendall(b"ERROR Invalid UPLOAD syntax\n")
                    continue
                room = parts[1]
                room_dir = get_room_dir(room)
                if room_dir is None:
                    conn.sendall(b"ERROR Invalid room code\n")
                    continue

                # Size is the last part, filename is everything between room and size
                try:
                    size = int(parts[-1])
                except ValueError:
                    conn.sendall(b"ERROR Invalid size\n")
                    continue
                
                # Filename is parts[2] through parts[-2] joined with spaces
                filename = " ".join(parts[2:-1])
                if not filename:
                    conn.sendall(b"ERROR Missing filename\n")
                    continue

                dest = room_dir / filename
                remaining = size
                seq = 1
                try:
                    # Set a timeout so server doesn't block forever if client drops chunk
                    conn.settimeout(30.0)  # 30 second timeout per chunk
                    
                    with dest.open("wb") as f:
                        # receive file in chunks and ACK each chunk
                        while remaining > 0:
                            # First check if we have data in buffer
                            if buffer:
                                chunk = buffer[:min(CHUNK_SIZE, remaining)]
                                buffer = buffer[len(chunk):]
                            else:
                                # Read from socket
                                try:
                                    chunk = conn.recv(min(CHUNK_SIZE, remaining))
                                except (ConnectionResetError, socket.timeout):
                                    break
                                if not chunk:
                                    break
                            
                            f.write(chunk)
                            remaining -= len(chunk)
                            # per-chunk ACK so client can measure RTT
                            ack_line = f"ACK {room} {seq}\n".encode("utf-8")
                            conn.sendall(ack_line)
                            seq += 1
                    
                    # Reset timeout for other commands
                    conn.settimeout(None)

                    if remaining != 0:
                        conn.sendall(b"ERROR Incomplete upload\n")
                        # optionally remove partial file
                        if dest.exists():
                            dest.unlink()
                        print(f"[FILE] Incomplete upload for {filename} from {addr}")
                    else:
                        conn.sendall(b"OK SAVED\n")
                        print(
                            f"[FILE] Saved {filename} ({size} bytes) "
                            f"in room {room} from {addr}"
                        )
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
                        created = datetime.datetime.fromtimestamp(
                            st.st_ctime
                        ).isoformat(timespec="seconds")
                        files.append((p.name, st.st_size, created))
                # sort newest first
                files.sort(key=lambda x: x[2], reverse=True)
                header = f"FILES {len(files)}\n"
                conn.sendall(header.encode("utf-8"))
                for name, size, created in files:
                    # Format: <size> <created> <filename>
                    # Size and created first (no spaces), filename last (may have spaces)
                    line = f"{size} {created} {name}\n"
                    conn.sendall(line.encode("utf-8"))

            elif cmd == "DOWNLOAD":
                # DOWNLOAD <room> <filename>
                # Note: filename may contain spaces, so it's everything after room
                if len(parts) < 3:
                    conn.sendall(b"ERROR DOWNLOAD needs room and filename\n")
                    continue
                room = parts[1]
                room_dir = get_room_dir(room)
                if room_dir is None:
                    conn.sendall(b"ERROR Invalid room code\n")
                    continue

                # Filename is everything after room (parts[2:] joined)
                filename = " ".join(parts[2:])
                path = room_dir / filename
                if not path.exists() or not path.is_file():
                    conn.sendall(b"ERROR NotFound\n")
                    continue
                size = path.stat().st_size
                header = f"OK {size}\n"
                conn.sendall(header.encode("utf-8"))
                import random
                try:
                    from config import SYNCROX_LOSS_PROB
                except ImportError:
                    SYNCROX_LOSS_PROB = 0.0
                with path.open("rb") as f:
                    while True:
                        chunk = f.read(4096)
                        if not chunk:
                            break
                        # Note: No loss simulation on download - would require
                        # client-side retry protocol which isn't implemented
                        conn.sendall(chunk)
                print(
                    f"[FILE] Sent {filename} ({size} bytes) "
                    f"from room {room} to {addr}"
                )

            elif cmd == "BYE":
                conn.sendall(b"OK Bye\n")
                break

            else:
                conn.sendall(b"ERROR Unknown command\n")

    except ConnectionResetError:
        # Client disconnected abruptly - this is normal with Streamlit
        pass
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
