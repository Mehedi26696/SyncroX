# SyncroX - Complete Technical Documentation

## Table of Contents
1. [Project Overview](#project-overview)
2. [System Architecture](#system-architecture)
3. [Networking Concepts Used](#networking-concepts-used)
4. [Custom TCP Protocols](#custom-tcp-protocols)
5. [Feature Implementation Details](#feature-implementation-details)
6. [Code Locations Reference](#code-locations-reference)

---

## Project Overview

**SyncroX** is a real-time collaborative platform built to demonstrate advanced networking concepts. It consists of 4 independent TCP servers communicating with a Streamlit-based frontend.

### Technology Stack
| Component | Technology |
|-----------|------------|
| Backend Servers | Python (socket, threading) |
| Frontend | Streamlit |
| Code Execution | Docker (sandboxed) |
| Data Storage | JSON, CSV, Text files |

### Port Allocation
| Service | Port | Protocol |
|---------|------|----------|
| TCP Chat | 9009 | Custom Text-based TCP |
| File Transfer | 9010 | Custom Binary TCP |
| Collaborative Editor | 9011 | Custom Text+Binary TCP |
| Code Execution | 9012 | Custom Text+Binary TCP |
| Streamlit UI | 8501 | HTTP |

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      STREAMLIT FRONTEND                         │
│                     (Port 8501 - HTTP)                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │Dashboard │ │  Chat    │ │  Code    │ │   File   │           │
│  │  Page    │ │  Page    │ │  Editor  │ │ Manager  │           │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘           │
└───────┼────────────┼────────────┼────────────┼──────────────────┘
        │            │            │            │
        │ TCP        │ TCP        │ TCP        │ TCP
        │            │            │            │
┌───────▼────┐ ┌─────▼──────┐ ┌───▼─────┐ ┌───▼─────┐
│  Chat      │ │  Collab    │ │  Exec   │ │  File   │
│  Server    │ │  Server    │ │ Server  │ │ Server  │
│  :9009     │ │  :9011     │ │ :9012   │ │ :9010   │
└────────────┘ └────────────┘ └────┬────┘ └─────────┘
                                   │
                              ┌────▼────┐
                              │ Docker  │
                              │ Sandbox │
                              └─────────┘
```

### Server Components

| Server | File | Purpose |
|--------|------|---------|
| Chat Server | `backend/tcp_chat/server.py` | Room-based messaging |
| Collab Server | `backend/collab/server.py` | Real-time code sync |
| Exec Server | `backend/code_exec/server.py` | Sandboxed code execution |
| File Server | `backend/file_transfer/server.py` | File upload/download with congestion control |

---

## Networking Concepts Used

### 1. TCP Socket Programming
**Location:** All server files  
**Concept:** Connection-oriented, reliable byte stream communication

```python
# Server socket creation (backend/tcp_chat/server.py:178-182)
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen(20)
```

**Key Features:**
- `SO_REUSEADDR`: Allows immediate port reuse after server restart
- `listen(20)`: Backlog of 20 pending connections
- Thread-per-client model for concurrent handling

---

### 2. Congestion Control (Tahoe & Reno)
**Location:** `backend/file_transfer/client.py` (Lines 16-123)  
**Concept:** Application-layer simulation of TCP congestion control

#### Implementation Details:

| Parameter | Initial Value | Purpose |
|-----------|--------------|---------|
| `cwnd` | 1.0 segments | Congestion window |
| `ssthresh` | 8.0 segments | Slow start threshold |
| `rto` | 1000 ms | Retransmission timeout |

#### Algorithm Behavior:

**Slow Start Phase** (cwnd < ssthresh):
```python
# Exponential growth - double cwnd each RTT
self.cwnd += 1.0  # +1 per ACK = doubles per RTT
```

**Congestion Avoidance Phase** (cwnd >= ssthresh):
```python
# Linear growth - +1 per RTT
self.cwnd += 1.0 / self.cwnd
```

**On Packet Loss (Timeout):**

| Algorithm | ssthresh | cwnd |
|-----------|----------|------|
| **Tahoe** | cwnd/2 | 1 (restart slow start) |
| **Reno** | cwnd/2 | ssthresh (fast recovery) |

```python
# backend/file_transfer/client.py:103-112
def on_loss(self, bytes_sent: int):
    if self.algo == "tahoe":
        self.ssthresh = max(self.cwnd / 2.0, 1.0)
        self.cwnd = 1.0  # Reset to slow start
    else:  # reno
        self.ssthresh = max(self.cwnd / 2.0, 1.0)
        self.cwnd = self.ssthresh  # Fast recovery
```

---

### 3. RTT Estimation (EWMA)
**Location:** `backend/file_transfer/client.py` (Lines 79-92)  
**Concept:** Exponentially Weighted Moving Average for smooth RTT tracking

#### Constants (RFC 6298 standard):
```python
ALPHA = 0.125  # Smoothing factor for SRTT
BETA = 0.25    # Smoothing factor for RTTVAR
```

#### Calculation:
```python
# First measurement
if self.srtt is None:
    self.srtt = rtt_ms
    self.rttvar = rtt_ms / 2.0
else:
    # Subsequent measurements
    self.rttvar = (1 - BETA) * self.rttvar + BETA * abs(self.srtt - rtt_ms)
    self.srtt = (1 - ALPHA) * self.srtt + ALPHA * rtt_ms

# RTO calculation
self.rto = self.srtt + 4 * self.rttvar
```

---

### 4. Rate Limiting
**Location:** `backend/tcp_chat/server.py` (Lines 110-120)  
**Concept:** Prevent flooding/DoS by limiting message frequency

```python
# Sliding window rate limiter: max 5 messages per 2 seconds
window = 2.0  # seconds
limit = 5     # max messages

times = msg_times[conn]  # deque of timestamps
while times and now - times[0] > window:
    times.popleft()  # Remove old timestamps

if len(times) >= limit:
    send_line(conn, "ERROR RATE_LIMIT please slow down")
    continue
times.append(now)
```

---

### 5. Multithreading for Concurrent Connections
**Location:** All servers  
**Concept:** Thread-per-client model for handling multiple simultaneous connections

```python
# backend/tcp_chat/server.py:186-188
while True:
    conn, addr = s.accept()
    t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
    t.start()
```

**Thread Safety:**
```python
# Using locks for shared data structures
lock = threading.Lock()

with lock:
    rooms[room_code].add(conn)
```

---

### 6. Connection Keep-Alive & Reconnection
**Location:** `backend/code_exec/client.py` (Lines 17-30)  
**Concept:** Automatic reconnection on protocol errors

```python
def _reconnect(self):
    """Reconnect to exec server (used after protocol errors)"""
    try:
        self.f.close()
    except Exception:
        pass
    try:
        self.sock.close()
    except Exception:
        pass
    self._connect()
```

---

## Custom TCP Protocols

### Protocol 1: TCP Chat Protocol

**Port:** 9009  
**Type:** Line-based text protocol  
**Delimiter:** `\n` (newline)
**Features:** Persistent message history (room-wise and user-wise)

#### Client → Server Commands:

| Command | Format | Description |
|---------|--------|-------------|
| HELLO | `HELLO <username>\n` | Initial handshake (required first) |
| CREATE_ROOM | `CREATE_ROOM\n` | Create new 4-digit room |
| JOIN_ROOM | `JOIN_ROOM <code>\n` | Join existing room |
| MSG | `MSG <text>\n` | Send message to current room |
| IMG_SEND | `IMG_SEND <base64_data>\n` | Send image (base64 encoded) |
| HISTORY | `HISTORY [limit]\n` | Request chat history (default 50) |
| LIST_ROOMS | `LIST_ROOMS\n` | List all active rooms |
| BYE | `BYE\n` | Disconnect |

#### Server → Client Responses:

| Response | Format | Description |
|----------|--------|-------------|
| OK | `OK <message>\n` | Success confirmation |
| ROOM | `ROOM <code>\n` | Room created with code |
| MSG | `MSG <room> <user>: <text>\n` | Broadcast message |
| SYSTEM | `SYSTEM <text>\n` | System notification |
| IMG | `IMG <room> <user> <base64>\n` | Broadcast image |
| HISTORY | `HISTORY <room> <count>\n` | Start of history response |
| HIST | `HIST <type> <timestamp> <sender>: <content>\n` | History message |
| HISTORY_END | `HISTORY_END\n` | End of history response |
| ROOMS | `ROOMS <code1> <code2> ...\n` | Room list |
| ERROR | `ERROR <reason>\n` | Error message |

#### Chat History Storage:
- **Room-wise:** `data/chat_history/room_<code>_chat.json`
- **User-wise:** `data/chat_history/user_<name>_chat.json`
- **Max messages:** 1000 per room (oldest auto-removed)

---

### Protocol 2: File Transfer Protocol

**Port:** 9010  
**Type:** Text header + Binary data  
**Features:** Per-chunk ACK, RTT measurement, Congestion control

#### Upload Sequence:
```
Client: UPLOAD <room> <filename> <size>\n
        <chunk_1 bytes>
Server: ACK <room> 1\n
Client: <chunk_2 bytes>
Server: ACK <room> 2\n
        ... (repeat for all chunks)
Server: OK SAVED\n
```

#### Download Sequence:
```
Client: DOWNLOAD <room> <filename>\n
Server: OK <size>\n
        <file_bytes>
```

#### List Files:
```
Client: LIST <room>\n
Server: FILES <count>\n
        <size1> <created1> <filename1>\n
        <size2> <created2> <filename2>\n
        ...
```

#### Metrics Logging:
Each transfer logs to `data/metrics/room_<id>_file_metrics.csv`:
- Timestamp, RTT, SRTT, RTO, CWND, ssthresh, event (ACK/LOSS), algorithm

---

### Protocol 3: Collaborative Editor Protocol

**Port:** 9011  
**Type:** Text header + Binary code data  
**Features:** Room-based, multi-language support

#### Client → Server:

| Command | Format | Description |
|---------|--------|-------------|
| HELLO | `HELLO <username>\n` | Initial handshake |
| JOIN | `JOIN <room> [lang]\n` | Join room with language |
| GET | `GET <room> <lang>\n` | Request current document |
| SET | `SET <room> <lang> <size>\n<code_bytes>` | Update document |
| USERS | `USERS <room>\n` | Request active users |

#### Server → Client:

| Response | Format | Description |
|----------|--------|-------------|
| DOC | `DOC <room> <lang> <size> <editor>\n<code_bytes>` | Document content |
| USERS | `USERS <room> <count>\n<user1> <status1>\n...` | Active users list |

---

### Protocol 4: Code Execution Protocol

**Port:** 9012  
**Type:** Text header + Binary code + Binary I/O  
**Features:** Multi-language, stdin support, Docker sandboxing

#### Request:
```
EXECUTE <room> <language> <code_size> <input_size>\n
<code_bytes>
<stdin_bytes>
```

#### Response:
```
RESULT <success:0|1> <return_code> <stdout_size> <stderr_size> <time_ms>\n
<stdout_bytes>
<stderr_bytes>
```

**Supported Languages:**
| Language | Compilation | Execution |
|----------|-------------|-----------|
| Python | None | `python main.py` |
| C | `gcc main.c -O2 -o main` | `./main` |
| C++ | `g++ main.cpp -O2 -o main` | `./main` |
| Java | `javac <ClassName>.java` | `java <ClassName>` |

**Docker Sandbox Limits:**
- Memory: 256 MB
- CPU: 0.5 cores
- Network: Disabled
- Timeout: 10 seconds (15 for Java compilation)

---

## Feature Implementation Details

### Feature 1: Real-Time Chat

**Files:**
- Server: `backend/tcp_chat/server.py`
- Client: `backend/tcp_chat/client.py`, `backend/tcp_chat/streamlit_client.py`
- UI: `frontend/streamlit_app/pages/chat.py`

**Networking Concepts:**
1. **TCP Sockets** - Reliable message delivery
2. **Broadcasting** - Send to all room members
3. **Rate Limiting** - 5 msgs/2s sliding window
4. **Thread-per-client** - Concurrent connections

**Data Flow:**
```
User A types → Client → TCP → Server → Broadcast → TCP → All Clients
```

---

### Feature 2: Collaborative Code Editor

**Files:**
- Server: `backend/collab/server.py`
- Client: `backend/collab/client.py`
- UI: `frontend/streamlit_app/pages/code_editor.py`

**Networking Concepts:**
1. **Persistent TCP Connection** - Maintained throughout session
2. **Binary Framing** - Size-prefixed code blocks
3. **Polling + Push** - Hybrid sync model
4. **Room Isolation** - Separate documents per room

**Sync Mechanism:**
```
1. Client polls server every 1.5s (GET command)
2. On local edit (after 2s idle), client sends SET
3. Server broadcasts DOC to all room clients
4. Clients merge if no local changes
```

---

### Feature 3: File Transfer with Congestion Control

**Files:**
- Server: `backend/file_transfer/server.py`
- Client: `backend/file_transfer/client.py`
- UI: `frontend/streamlit_app/pages/file_manager.py`

**Networking Concepts:**
1. **Chunked Transfer** - 4KB segments
2. **Per-Chunk ACK** - Reliability & RTT measurement
3. **EWMA RTT** - Smooth round-trip estimation
4. **Tahoe/Reno Congestion Control** - Flow control
5. **RTO Calculation** - Adaptive timeout

**Upload Flow:**
```
┌────────┐         ┌────────┐
│ Client │         │ Server │
└───┬────┘         └───┬────┘
    │ UPLOAD room file size│
    │─────────────────────>│
    │                      │
    │ chunk 1 (4KB)        │
    │─────────────────────>│
    │      ACK room 1      │  ← RTT measured
    │<─────────────────────│
    │                      │
    │ chunk 2 (cwnd grows) │
    │─────────────────────>│
    │      ACK room 2      │
    │<─────────────────────│
    │                      │
    │ [timeout = loss]     │  ← cwnd reduced (Tahoe/Reno)
    │                      │
    │      OK SAVED        │
    │<─────────────────────│
```

---

### Feature 4: Sandboxed Code Execution

**Files:**
- Server: `backend/code_exec/server.py`
- Client: `backend/code_exec/client.py`
- Dockerfile: `backend/code_exec/Dockerfile`
- UI: `frontend/streamlit_app/pages/code_editor.py`

**Networking Concepts:**
1. **Request-Response Protocol** - Single exchange per execution
2. **Binary Framing** - Size-prefixed code and I/O
3. **Connection Reuse** - Persistent TCP connection
4. **Auto-Reconnection** - Recovery from protocol errors

**Execution Flow:**
```
Client                    Server                    Docker
  │                         │                         │
  │ EXECUTE room py 50 0    │                         │
  │────────────────────────>│                         │
  │ <code bytes>            │                         │
  │────────────────────────>│                         │
  │                         │ docker run ...          │
  │                         │────────────────────────>│
  │                         │     stdout/stderr       │
  │                         │<────────────────────────│
  │ RESULT 1 0 12 0 150     │                         │
  │<────────────────────────│                         │
  │ <stdout bytes>          │                         │
  │<────────────────────────│                         │
```

---

## Code Locations Reference

### Core Networking Code

| Concept | File | Lines | Description |
|---------|------|-------|-------------|
| TCP Server Socket | `backend/tcp_chat/server.py` | 178-188 | Socket bind, listen, accept |
| Thread-per-client | `backend/tcp_chat/server.py` | 186-188 | Thread creation for each connection |
| Rate Limiting | `backend/tcp_chat/server.py` | 110-120 | Sliding window limiter |
| EWMA RTT | `backend/file_transfer/client.py` | 79-92 | RTT smoothing |
| Tahoe/Reno | `backend/file_transfer/client.py` | 93-112 | Congestion control |
| Per-chunk ACK | `backend/file_transfer/server.py` | 111-113 | ACK for RTT measurement |
| Binary Framing | `backend/collab/server.py` | 195-210 | Size-prefixed binary data |
| Broadcasting | `backend/tcp_chat/server.py` | 42-50 | Send to all room members |
| Connection Recovery | `backend/code_exec/client.py` | 17-30 | Auto-reconnection |

### Protocol Implementations

| Protocol | Server File | Client File |
|----------|-------------|-------------|
| Chat | `backend/tcp_chat/server.py` | `backend/tcp_chat/streamlit_client.py` |
| File Transfer | `backend/file_transfer/server.py` | `backend/file_transfer/client.py` |
| Collaboration | `backend/collab/server.py` | `backend/collab/client.py` |
| Code Execution | `backend/code_exec/server.py` | `backend/code_exec/client.py` |

### Configuration

| Setting | File | Value |
|---------|------|-------|
| Server Host | `config.py` | `SERVER_HOST` |
| Chat Port | `config.py` | 9009 |
| File Port | `config.py` | 9010 |
| Collab Port | `config.py` | 9011 |
| Exec Port | `config.py` | 9012 |
| Chunk Size | `backend/file_transfer/client.py` | 4096 bytes |
| EWMA Alpha | `backend/file_transfer/client.py` | 0.125 |
| EWMA Beta | `backend/file_transfer/client.py` | 0.25 |
| Rate Limit | `backend/tcp_chat/server.py` | 5 msgs/2s |

---

## Summary

SyncroX demonstrates the following networking concepts:

| Concept | Implementation | Location |
|---------|----------------|----------|
| TCP Socket Programming | 4 custom TCP servers | All `server.py` files |
| Custom Application Protocols | Text + Binary framing | All protocol commands |
| Congestion Control (Tahoe/Reno) | CWND, ssthresh, slow start | File transfer client |
| RTT Estimation (EWMA) | Smoothed RTT, RTO calculation | File transfer client |
| Rate Limiting | Sliding window | Chat server |
| Concurrent Connection Handling | Thread-per-client | All servers |
| Binary Data Framing | Size-prefixed transfers | Collab, Exec, File |
| Connection Management | Keep-alive, reconnection | Exec client |
| Room-based Isolation | Per-room data structures | All servers |
| Sandboxed Execution | Docker with resource limits | Exec server |

---

*Document generated for CSE 3111 - Computer Networking Lab*  
*Authors: H.M. Mehedi Hasan (13) • MD. Abu Bakar Siddique (47)*
