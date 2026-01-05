# 🎓 Networking Concepts Demonstrated in SyncroX

This document explains the networking concepts and protocols implemented in SyncroX.

---

## 📡 Custom TCP Protocols

### Chat Protocol (Port 9009)
- **HELLO \<username\>**: Initial handshake to establish client identity
- **CREATE_ROOM**: Server generates unique 4-digit room code and assigns client
- **JOIN_ROOM \<code\>**: Join existing room (auto-creates if doesn't exist)
- **MSG \<text\>**: Broadcast message to all room members with automatic echo
- **LIST_ROOMS**: Query all active room codes on server
- **BYE**: Graceful disconnect with cleanup of client resources
- **Room Broadcasting**: Messages are multicast to all sockets in the room set
- **Username Tracking**: Server maintains client→username mapping for attribution

### File Transfer Protocol (Port 9010)
- **UPLOAD \<filename\> \<filesize\> \<room\> \<algo\>**: Initiate file upload with metadata
- **Size-prefixed chunks**: Each chunk sent as `<4-byte-size><data>` for framing
- **Per-chunk ACK**: Server responds with `ACK <seq> <timestamp>` for RTT measurement
- **Checksum validation**: Optional integrity checking on received chunks
- **DOWNLOAD \<filename\> \<room\>**: Request file retrieval from room storage
- **LIST \<room\>**: Enumerate all uploaded files in specific room
- **Binary safe**: Uses raw socket buffers, no text encoding on file data

### Collaborative Editor Protocol (Port 9011)
- **JOIN \<room\> \<username\>**: Subscribe to document updates for room
- **SET \<content\>**: Push local document changes to server
- **DOC \<content\>**: Server broadcasts synchronized document state
- **USERS \<count\>**: Server notifies clients of active collaborators
- **Last-write-wins**: Simple conflict resolution, no operational transforms
- **Auto-sync**: Clients poll for DOC updates every 500ms for real-time feel

### Code Execution Protocol (Port 9012)
- **EXECUTE \<lang\> \<code\> [stdin]**: Submit code with language and optional input
- **Docker isolation**: Each execution runs in ephemeral container with resource limits
- **RESULT \<stdout\> \<stderr\> \<rc\> \<time_ms\>**: Return execution output and metrics
- **Multi-language support**: Python, C, C++, Java with appropriate runtimes
- **Security constraints**: 256MB memory, 0.5 CPU cores, 30s timeout per execution
- **Compilation handling**: Transparent gcc/g++/javac compilation before execution

---

## 🔄 Flow & Congestion Control

### TCP Congestion Control Simulation
- **Slow Start Phase**: CWND grows exponentially (doubles per RTT) until ssthresh
- **Congestion Avoidance**: Linear growth (+1 MSS per RTT) above ssthresh
- **Tahoe Algorithm**: On loss, ssthresh = cwnd/2, cwnd resets to 1 MSS
- **Reno Algorithm**: On loss, ssthresh = cwnd/2, cwnd = ssthresh (faster recovery)

### RTT Estimation
- **Sample RTT**: Measure time between chunk send and ACK receipt
- **EWMA Smoothing**: `SRTT = (1-α)×SRTT + α×RTT` where α=0.125
- **Adaptive timeout**: RTO calculated from SRTT + 4×RTTVAR

### Chunking Strategy
- **Fixed chunk size**: 4096 bytes (4KB) per segment for predictable behavior
- **Sequential numbering**: Each chunk gets sequence number for ordering

### Metrics Logging
- **Per-transfer CSV**: Records seq, event, cwnd, ssthresh, rtt_ms, srtt_ms
- **Room isolation**: Metrics tagged with room code and filename
- **Real-time plotting**: Dashboard visualizes CWND evolution and threshold crossings

---

## 🔒 Reliability & Security

### Protocol Reliability
- **Request-Response Pattern**: Every client command receives OK/ERROR acknowledgment
- **Error propagation**: Detailed error messages
- **Timeout handling**: Client and server enforce timeouts

### Room-Based Isolation
- **Namespace separation**: 4-digit room codes partition all resources
- **No cross-room leakage**: Files, messages, and documents scoped to room

### Docker Sandbox Security
- **Process isolation**: Each execution in separate container, no shared state
- **Resource limits**: CPU, memory, and time constraints prevent DoS

### Rate Limiting & DoS Prevention
- **Chat rate limit**: Max messages per time window per client

---

## Summary

SyncroX demonstrates key networking concepts including:
- Custom application-layer TCP protocols
- Congestion control algorithms (Tahoe/Reno)
- RTT estimation and adaptive timeouts
- Reliable data transfer with ACKs
- Room-based resource isolation
- Docker-based sandboxed code execution
