import socket
import threading
import time
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.collab.client import TcpCollabClient

HOST = "127.0.0.1"
PORT = 9011
ROOM = "9999"

def stress_test():
    print(f"Connecting to {HOST}:{PORT}...")
    try:
        client = TcpCollabClient(HOST, PORT, "tester")
    except Exception as e:
        print(f"Failed to connect: {e}")
        return

    print("Joining room...")
    client.join_room(ROOM)
    time.sleep(1)

    running = True
    errors = []

    def reader_check():
        while running:
            # simulation of reading updates
            doc = client.get_latest_doc()
            if doc:
                # print(f"Received doc update: {len(doc)} chars")
                pass
            time.sleep(0.01)
            if not client.alive:
                errors.append("Client died unexpectedly during read")
                break

    t = threading.Thread(target=reader_check)
    t.start()

    print("Starting write loop...")
    for i in range(50):
        if not running: break
        msg = f"Line {i} " * 10
        try:
            client.set_code(ROOM, msg)
            # print(f"Sent update {i}")
        except Exception as e:
            errors.append(f"Write failed: {e}")
            break
        time.sleep(0.05)

    running = False
    t.join()
    client.close()

    if errors:
        print("❌ Test FAILED with errors:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("✅ Test PASSED: No concurrency errors detected")

if __name__ == "__main__":
    stress_test()
