<p align="center">
  <img src="assets/logo.png" alt="SyncroX Logo" width="220"/>
</p>

# SyncroX: Advanced Real-Time Collaboration System
**Technical Reference Manual & Project Report**

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue.svg?style=flat-square" alt="Python">
  <img src="https://img.shields.io/badge/Streamlit-1.36.0-FF4B4B.svg?style=flat-square" alt="Streamlit">
  <img src="https://img.shields.io/badge/Docker-Required-2496ED.svg?style=flat-square" alt="Docker">
  <img src="https://img.shields.io/badge/Protocol-Reliable_UDP-orange.svg?style=flat-square" alt="Reliable UDP">
</p>

**SyncroX** is a distributed system demonstrating advanced networking principles. It features a custom **Reliable UDP** protocol with Tahoe/Reno congestion control, a **TCP Chat** system with a custom Application Layer Protocol, a **Collaborative Code Editor** using centralized state synchronization, and a secure **Docker-based Code Execution Engine**.

---

## 📚 Table of Contents

1. [System Architecture](#-system-architecture)
2. [Deep Dive: Reliable UDP Protocol](#-deep-dive-reliable-udp-protocol)
   - [Packet Structure & Header](#packet-structure)
   - [RTT Estimation (Jacobson/Karels Algorithm)](#rtt-estimation-mathematics)
   - [Congestion Control State Machine](#congestion-control-state-machine)
3. [Deep Dive: TCP Chat Protocol](#-deep-dive-tcp-chat-protocol)
   - [Command Reference](#chat-command-reference)
   - [CDN & Lazy Loading](#cdn-architecture)
4. [Deep Dive: Collaborative Editor](#-deep-dive-collaborative-editor)
   - [Synchronization & Concurrency](#synchronization-protocol)
5. [Deep Dive: Secure Code Execution](#-deep-dive-secure-code-execution)
   - [Docker Security Audit](#docker-security-audit)
6. [Deep Dive: Room Management](#-deep-dive-room-management)
7. [Installation & Setup](#-installation--setup)
8. [Authors & Attribution](#-authors--attribution)

---

## 🏗 System Architecture

The system follows a microservices-pattern where independent servers handle distinct domains, minimizing failure domains.

### Service Map
| Service | Port | Transport | Role |
|:---|:---|:---|:---|
| **Frontend** | 8501 | HTTP | Streamlit Gateway (User Interface) |
| **Room Manager** | 9013 | TCP | **Single Source of Truth** for room lifecycle/validity |
| **Chat Svc** | 9009 | TCP | Messaging, History, Image Broadcast |
| **File Control** | 9010 | TCP | Listing files, signaling transfer Intent |
| **File Data** | 9011 | UDP | High-speed Reliable Data Transfer (RDT) |
| **Collab Svc** | 9011 | TCP | Doc sync, identifying active users |
| **Exec Svc** | 9012 | TCP | Docker spawning, stdout/stderr streaming |

---

## 📡 Deep Dive: Reliable UDP Protocol

We implemented a **Reliable Data Transfer (RDT 3.0+)** protocol over UDP, simulating TCP features like sliding windows, cumulative ACKs, and congestion control.

### Packet Structure
All packets are UTF-8 JSON encoded.

```json
{
  "type": "DATA",           // Packet Type: SYN, SYN-ACK, ACK, DATA, FIN, FIN-ACK
  "seq": 105,               // Sequence Number
  "ack": 105,               // Acknowledgement Number (Next Expected Byte)
  "rwnd": 64,               // Flow Control: Receiver Window Size (chunks)
  "room": "ABCD",           // Routing context
  "filename": "doc.pdf",    // Context
  "payload_b64": "...",     // Base64 Encoded Binary Chunk (4KB)
  "session_id": "a1b2c3d4"  // Session Security Token
}
```

### RTT Estimation Mathematics
We use the **Jacobson/Karels Algorithm** to calculate Key Timeout values.

1.  **Sample RTT**: Measured time from `SEND` to `ACK`.
2.  **Smoothed RTT (SRTT)**:
    $$SRTT = (1 - \alpha) \cdot SRTT + \alpha \cdot RTT_{sample}$$
    *Where $\alpha = 0.125$*
3.  **RTT Variation (RTTVAR)**:
    $$RTTVAR = (1 - \beta) \cdot RTTVAR + \beta \cdot |SRTT - RTT_{sample}|$$
    *Where $\beta = 0.25$*
4.  **Retransmission Timeout (RTO)**:
    $$RTO = SRTT + 4 \cdot RTTVAR$$
    *(Clamped to min 200ms)*

### Congestion Control State Machine

The protocol supports real-time switching between **Tahoe** and **Reno**.

#### Common States
*   **State 1: Slow Start**: $CWND < ssthresh$.
    *   Action: $CWND += 1$ per ACK (Exponential Growth).
*   **State 2: Congestion Avoidance**: $CWND \ge ssthresh$.
    *   Action: $CWND += 1 / CWND$ per ACK (Linear Growth).

#### Loss Handling (The Difference)

| Event | Algorithm | Action |
|:---|:---|:---|
| **Timeout** | **Both** | `ssthresh = CWND / 2`<br>`CWND = 1` (Hard Reset)<br>Enter *Slow Start* |
| **3 Duplicate ACKs** | **Tahoe** | `ssthresh = CWND / 2`<br>`CWND = 1` (Hard Reset)<br>Enter *Slow Start* |
| **3 Duplicate ACKs** | **Reno** | `ssthresh = CWND / 2`<br>`CWND = ssthresh + 3` (Fast Recovery)<br>Enter *Congestion Avoidance* |

---

## 💬 Deep Dive: TCP Chat Protocol

A robust Application Layer Protocol on top of TCP.

### Chat Command Reference

| Command | Arguments | Direction | Description |
|:---|:---|:---|:---|
| `HELLO` | `<username> <room>` | C -> S | Authenticate and register socket. |
| `MSG` | `<content>` | C -> S | Send text message. |
| `IMG` | `<filename> <b64>` | C -> S | Upload image to server CDN. |
| `GET_IMG` | `<filename>` | C -> S | Request binary data for an image. |
| `BYE` | None | C -> S | Graceful disconnect. |

### CDN Architecture
To optimize bandwidth, images are **lazy-loaded**.
1.  **Broadcast**: Server sends `{"type": "IMG", "filename": "cat.png"}` (No binary data).
2.  **Rendering**: Client UI sees the placeholder.
3.  **Fetch**: Client opens a specific `GET_IMG` request *only* if it needs to render the pixel data.
4.  **Disk Storage**: Images are stored in `backend/data/cdn/` as raw binaries, not DB blobs.

---

## 📝 Deep Dive: Collaborative Editor

Real-time document synchronization engine.

### Synchronization Protocol
*   **Update Frequency**: 500ms (Client Polling/Push).
*   **Payload**:
    ```json
    {
      "type": "SET",
      "room": "ABCD",
      "content": "def hello_world():\n    print('Hi')",
      "user": "Alice"
    }
    ```
*   **Conflict Resolution**: **Last-Write-Wins (LWW)** architecture. The server accepts the latest `SET` command timestamp as the Single Source of Truth to simplify concurrency in lab environments.

---

## 🛡 Deep Dive: Secure Code Execution

The `code_exec` server acts as a gateway to an ephemeral Docker environment.

### Docker Security Audit
We use the following security profile for every execution container:

| Flag | Value | Purpose |
|:---|:---|:---|
| `--network` | `none` | **Total Isolation**. Prevents reverse shells or pip installs. |
| `--memory` | `256m` | Prevents RAM exhaustion (Fork bombs). |
| `--cpus` | `0.5` | Throttles CPU to prevent neighbor noise. |
| `--pids-limit`| `64` | Prevents process table exhaustion. |
| `--rm` | `true` | **Ephemeral**. Container executes and vanishes. |
| Volume | `/tmp/...` | Code is mounted read-only where possible, output written to temp. |

---

## 🔑 Deep Dive: Room Management

The **Room Management Service (`9013`)** solves the "Ghost Room" problem.

*   **Registry**: A thread-safe Set of active room codes.
*   **Validation API**:
    *   `CHECK <room>` -> `YES` / `NO`
    *   Other servers (Chat, Filestore) query this TCP port before accepting a `JOIN`.
*   **Lifecycle**:
    *   `CREATE` -> Registers room, sets timestamp.
    *   **GC (Garbage Collector)**: Background thread scans for empty rooms > 10m inactive and deletes them.

---

## 🚀 Installation & Setup

### Prerequisites
*   **Python 3.10+** (Required for match-case syntax)
*   **Docker Desktop** (Must be running for Exec server)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start Servers
We provide a unified launcher script.
```bash
python start_all_servers.py
```
*Expected Output: 4 Terminals spawning (Chat, Files, Collab, Exec).*

### 3. Launch Frontend
```bash
streamlit run frontend/streamlit_app/app.py
```
*Port 8501 will open automatically.*

### 4. Verification
1.  **Create Room**: Click "Create New Room". Copy the 4-digit code.
2.  **Join**: Open a new tab, use the code to join as a second user.
3.  **Chat**: Send a message. Verify it appears instantly in Tab 2.
4.  **File Transfer**: Upload a file. Check the "Dashboard" tab to see the "Sawtooth" congestion graph.

---

## 👥 Authors & Attribution

**Course**: CSE 3111 - Computer Networking Lab

*   **H.M. Mehedi Hasan** (Roll: 13)
*   **MD. Abu Bakar Siddique** (Roll: 47)

Built with ❤️ using **Python sockets** and **Streamlit**.
