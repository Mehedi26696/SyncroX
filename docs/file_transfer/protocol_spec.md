# SyncroX Protocol Specification (v1.0)

This document provides a technical breakdown of the SyncroX Reliable UDP packet structure and the state machine used for handshakes and data transfer.

---

## 📦 Packet Structure

All communication occurs via JSON-encoded packets over UDP. This choice ensures binary safety (via base64) and ease of extensibility.

### 1. SYN Packet (Initiation)
Sent by the client to request a transfer session.
```json
{
    "type": "SYN",
    "room": "1234",
    "filename": "document.pdf"
}
```

### 2. SYN-ACK Packet (Response)
Sent by the server to acknowledge the request and provide a unique `session_id`.
```json
{
    "type": "SYN-ACK",
    "room": "1234",
    "filename": "document.pdf",
    "session_id": "a1b2c3d4e5f6g7h8"
}
```

### 3. DATA Packet (Transfer)
Carries the actual file content chunks.
```json
{
    "type": "DATA",
    "room": "1234",
    "filename": "document.pdf",
    "seq": 42,
    "total": 100,
    "payload_b64": "SGVsbG8gV29ybGQ...",
    "session_id": "a1b2c3d4e5f6g7h8"
}
```

### 4. ACK Packet (Acknowledgment)
Provides feedback to the sender about received data.
```json
{
    "type": "ACK",
    "room": "1234",
    "filename": "document.pdf",
    "ack": 42,
    "rwnd": 32,
    "session_id": "a1b2c3d4e5f6g7h8"
}
```

---

## ⚙️ State Machine logic

### Handshake Sequence
The protocol uses a **3-way handshake** to prevent "half-open" connections and ensure that both sides agree on the `session_id`.

1.  **Client** sends `SYN`.
2.  **Server** receives `SYN`, generates a token, and sends `SYN-ACK`.
3.  **Client** receives `SYN-ACK`, and sends a final `ACK` to confirm receipt.
4.  **Transfer Begins**: Only after this 3rd step does the sender start pushing `DATA` packets.

### Cumulative Acknowledgment Strategy
SyncroX uses **Cumulative ACKs**. An ACK for sequence `N` confirms that all packets from `1` to `N` have been successfully received and stored.

**Example Scenario:**
*   Sender sends packets 1, 2, 3, 4, 5.
*   Packet 3 is lost in the network.
*   Receiver gets 1, 2, (gap), 4, 5.
*   Receiver ACKs: `ACK 1`, `ACK 2`, `ACK 2`, `ACK 2`, `ACK 2`.
*   Sender detects 3 duplicate ACKs for `2` and triggers **Fast Retransmit** for packet `3`.
