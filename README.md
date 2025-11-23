<p align="center">
  <img src="assets/logo.png" alt="SyncroX Logo" width="180"/>
</p>

# SyncroX

**A Unified Real-Time Collaboration & Communication Platform**  
_Course: CSE 3111 - Computer Networking Lab_

**Authors:**  
H.M. Mehedi Hasan (13)  
MD. Abu Bakar Siddique (47)

---

## Overview
SyncroX is a comprehensive, modular platform for real-time collaboration, file sharing, and code execution. It is designed to demonstrate advanced networking concepts, custom protocol design, and secure, scalable system architecture. SyncroX is built with Python, Streamlit, and a suite of custom TCP servers, providing a robust environment for teamwork and experimentation in computer networking.

---

## Networking Principles and Architecture

### Custom TCP Protocols
- **Chat Server (Port 9009):**
  - Implements a stateful protocol with commands: HELLO, CREATE_ROOM, JOIN_ROOM, MSG, LIST_ROOMS, BYE.
  - Supports room-based message broadcasting, username tracking, and rate limiting.
  - Each client is mapped to a username and room, with all messages scoped to the current room.
- **File Transfer Server (Port 9010):**
  - Uses size-prefixed chunking for binary-safe file uploads and downloads.
  - Per-chunk acknowledgments (ACK) enable precise RTT measurement and congestion window adjustment.
  - Supports Tahoe and Reno congestion control algorithms, with metrics logged for each transfer.
  - Files are isolated per room, and all file operations are atomic and validated for integrity.
- **Collaborative Editor Server (Port 9011):**
  - Real-time document synchronization using JOIN, SET, DOC, USERS commands.
  - Implements last-write-wins conflict resolution and periodic polling for updates.
  - Tracks active users and synchronizes document state across all clients in a room.
- **Code Execution Server (Port 9012):**
  - Accepts EXECUTE commands with language and code, runs in Docker containers for isolation.
  - Returns RESULT with stdout, stderr, return code, and execution time.
  - Supports Python, C, C++, and Java, with resource limits and no network access for security.

### Room-Based Isolation
- All features are scoped to 4-digit room codes, ensuring strict separation of data and users.
- Each room maintains its own state for chat, files, documents, and metrics.
- Empty rooms are automatically cleaned up to conserve resources.

### Congestion Control and RTT Estimation
- **Tahoe/Reno Algorithms:**
  - Implements slow start, congestion avoidance, and fast retransmit.
  - On packet loss, Tahoe resets the congestion window to 1 and halves the threshold; Reno sets the window to the threshold for faster recovery.
- **RTT Estimation:**
  - Uses Exponential Weighted Moving Average (EWMA) for smoothed RTT calculation.
  - Adaptive retransmission timeouts are computed from SRTT and RTTVAR.
- **Chunking and Flow Control:**
  - Fixed 4KB chunk size, sequence numbering, and window-based flow control.
  - Per-chunk ACKs and real-time window adjustment.

### Reliability and Security
- **Request-Response Pattern:** Every client command receives an explicit OK or ERROR response.
- **Error Handling:** Detailed error messages and graceful degradation on disconnects or failures.
- **Docker Sandbox:** All code execution is performed in isolated containers with strict resource limits, no network, and non-root users.
- **Rate Limiting:** Chat server enforces a maximum of 5 messages per 2 seconds per client.
- **Data Integrity:** Files are written atomically, filenames are sanitized, and all transfers are binary-safe.
- **Path and Storage Isolation:** Each room's files are stored in a separate directory, preventing cross-room access.

---

## Features
- **Real-Time Chat:** Room-based instant messaging with rate limiting and user tracking.
- **Collaborative Code Editor:** Live code editing with real-time synchronization and multi-language execution (Python, C, C++, Java).
- **File Manager:** Secure file upload and download, Tahoe/Reno congestion control, per-room file storage, and integrity validation.
- **Dashboard:** Real-time server status, RTT and congestion window metrics, and detailed visualizations of network behavior.
- **Room Management:** Create and join rooms, session state management, and strict user/data isolation.

---

## System Architecture
- **Frontend:** Streamlit (Python), modular page structure, Raleway font, custom dark theme.
- **Backend:** Four independent TCP servers (chat, file, collab, exec), each on a dedicated port.
- **Docker:** Code execution sandbox with resource and security constraints.
- **Metrics:** Per-transfer CSV logs, real-time plotting with matplotlib and pandas.

---

## Demo Screenshots

<p align="center">
  <img src="App_Screenshots/landing_page.png" alt="Welcome Page" width="full"/>
  <img src="App_Screenshots/dashboard.png" alt="Dashboard" width="full"/>
  <img src="App_Screenshots/chat_interface.png" alt="Chat Page" width="full"/>
  <img src="App_Screenshots/code_editor.png" alt="Code Editor" width="full"/>
  <img src="App_Screenshots/file_transfer.png" alt="Code Editor" width="full"/>
  <img src="App_Screenshots/System_Dashboard.png" alt="File Manager" width="full"/>
  <img src="App_Screenshots/FileTransferMetrices.png" alt="File Manager" width="full"/>
</p>

---

## Networking Concepts in SyncroX

### Custom TCP Protocols
- **Chat:**
  - `HELLO <username>`: Handshake and identity setup
  - `CREATE_ROOM`, `JOIN_ROOM <code>`, `MSG <text>`, `LIST_ROOMS`, `BYE`
  - Room-based broadcasting, username tracking, and rate limiting
- **File Transfer:**
  - `UPLOAD`, `DOWNLOAD`, `LIST`, size-prefixed chunking, per-chunk ACKs
  - Binary-safe, checksum validation, room isolation, and atomic file writes
- **Collaborative Editor:**
  - `JOIN`, `SET`, `DOC`, `USERS`, last-write-wins, auto-sync, and user tracking
- **Code Execution:**
  - `EXECUTE <lang> <code> [stdin]`, Docker isolation, multi-language, resource limits, and secure output

### Congestion Control and RTT
- **Tahoe/Reno Simulation:** Implements slow start, congestion avoidance, fast retransmit, and ssthresh adjustment
- **RTT Estimation:** EWMA smoothing, adaptive timeouts, per-chunk RTT, and timestamp-based ACKs
- **Chunking:** 4KB segments, sequence numbering, window-based flow control, and pipeline depth management

### Reliability and Security
- **Request-Response:** Every command gets OK/ERROR, with detailed error propagation
- **Room Isolation:** No cross-room leakage, auto-cleanup, and concurrent room support
- **Docker Sandbox:** Resource limits, no network, non-root user, and ephemeral containers
- **Rate Limiting:** Prevents flooding, sliding window per client, and explicit RATE_LIMIT errors
- **Data Integrity:** Atomic writes, path sanitization, binary preservation, and storage isolation

---

## Quick Start
1. Clone the repository and install requirements:
   ```bash
   git clone <repo-url>
   cd syncroX
   pip install -r requirements.txt
   ```
2. Start all backend servers (chat, file, collab, exec) in separate terminals:
   ```bash
   python backend/tcp_chat/server.py
   python backend/file_transfer/server.py
   python backend/collab_editor/server.py
   python backend/code_exec/server.py
   ```
3. Launch the frontend:
   ```bash
   streamlit run frontend/streamlit_app/app.py
   ```
4. Open in your browser and use the platform.

---

## Directory Structure
```
syncroX/
├── assets/                # Logo and branding
├── App_Screenshots/       # Demo screenshots
├── backend/
│   ├── tcp_chat/          # Chat server/client
│   ├── file_transfer/     # File server/client
│   ├── collab_editor/     # Collaborative editor server/client
│   └── code_exec/         # Code execution server/client
├── data/metrics/          # Per-room metrics CSVs
├── frontend/
│   └── streamlit_app/
│       ├── app.py         # Main app
│       └── pages/         # Modular feature pages
└── requirements.txt
```

---


<p align="center"><b>SyncroX &copy; 2025</b></p>
