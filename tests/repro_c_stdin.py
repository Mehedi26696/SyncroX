import socket
import json

HOST = "127.0.0.1"
PORT = 9012

CODE = """
#include <stdio.h>

int main() {
    int number;
    scanf("%d", &number);
    printf("You entered: %d\\n", number);
    return 0;
}
"""

STDIN = "42"

def repro():
    print(f"Connecting to {HOST}:{PORT}...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((HOST, PORT))
        f = sock.makefile("rwb")
    except Exception as e:
        print(f"Failed to connect: {e}")
        return

    code_bytes = CODE.encode("utf-8")
    stdin_bytes = STDIN.encode("utf-8")

    # Protocol: EXECUTE <room> <language> <code_size> <input_size>
    header = f"EXECUTE test_room c {len(code_bytes)} {len(stdin_bytes)}\n"
    print(f"Sending: {header.strip()}")
    
    f.write(header.encode("utf-8"))
    f.write(code_bytes)
    f.write(stdin_bytes)
    f.flush()

    print("Waiting for response...")
    resp_header = f.readline().decode("utf-8").strip()
    print(f"Received header: {resp_header}")
    
    parts = resp_header.split()
    if not parts or parts[0] != "RESULT":
        print("Invalid response")
        return

    # RESULT <success> <rc> <out_len> <err_len> <time>
    success = parts[1]
    rc = parts[2]
    out_len = int(parts[3])
    err_len = int(parts[4])

    out = f.read(out_len).decode("utf-8")
    err = f.read(err_len).decode("utf-8")

    print(f"RC: {rc}")
    print(f"Output: {out}")
    print(f"Error: {err}")

    if "You entered: 42" in out:
        print("✅ SUCCESS: scanf read 42 correctly")
    else:
        print("❌ FAILURE: scanf did not read 42 correctly")
        if "You entered:" in out:
             print(f"Got unexpected value in output")

    sock.close()

if __name__ == "__main__":
    repro()
