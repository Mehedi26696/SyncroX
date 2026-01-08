<!-- Animated Header Banner -->
<p align="center">
  <img src="assets/logo.png" alt="SyncroX Logo" width="180"/>
</p>

<h1 align="center">
  <img src="https://readme-typing-svg.herokuapp.com?font=Fira+Code&weight=600&size=28&pause=1000&color=6366F1&center=true&vCenter=true&random=false&width=435&lines=🚀+SyncroX;Real-Time+Collaboration;Built+with+Python+Sockets" alt="Typing SVG" />
</h1>

<p align="center">
  <strong>🌐 Advanced Real-Time Collaboration System</strong>
  <br/>
  <sub>A distributed networking system showcasing custom protocol implementations</sub>
</p>

<p align="center">
  <a href="#-quick-start"><img src="https://img.shields.io/badge/Quick_Start-→-6366F1?style=for-the-badge" alt="Quick Start"/></a>
  <a href="#-screenshots"><img src="https://img.shields.io/badge/Screenshots-→-10B981?style=for-the-badge" alt="Screenshots"/></a>
  <a href="https://github.com/Abs-Futy7/SyncroX"><img src="https://img.shields.io/badge/View_on_GitHub-→-181717?style=for-the-badge&logo=github" alt="GitHub"/></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Streamlit-1.36.0-FF4B4B?style=flat-square&logo=streamlit&logoColor=white" alt="Streamlit">
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker&logoColor=white" alt="Docker">
  <img src="https://img.shields.io/badge/Protocol-Reliable_UDP-FF6B35?style=flat-square" alt="Reliable UDP">
  <img src="https://img.shields.io/badge/TCP-Chat_Protocol-00C853?style=flat-square" alt="TCP">
</p>

<br/>

<!-- Fancy Divider -->
<p align="center">
  <img src="https://user-images.githubusercontent.com/73097560/115834477-dbab4500-a447-11eb-908a-139a6edaec5c.gif" width="100%">
</p>

## 🎯 What is SyncroX?

**SyncroX** is a **real-time collaborative and communication platform** demonstrating advanced networking concepts including custom TCP protocols, Tahoe/Reno congestion control, RTT estimation, and secure Docker-based code execution — all built entirely from scratch using Python sockets. It features reliable file sharing, instant messaging with image CDN, and synchronous collaborative editing.

<p align="center">
  <img src="App_Screenshots/Landing Page.png" alt="SyncroX Landing Page" width="85%"/>
</p>

<br/>

## ⚡ Key Features

<table>
<tr>
<td width="50%">

### 📡 Reliable UDP Protocol
- Custom **RDT 3.0+** implementation
- Sliding windows with cumulative ACKs
- **Tahoe** & **Reno** congestion control
- Real-time RTT estimation

</td>
<td width="50%">

### 💬 Real-time Chat System
- Custom TCP application layer protocol
- **Image CDN** with lazy loading
- Instant message broadcast
- Persistent chat history

</td>
</tr>
<tr>
<td width="50%">

### 📝 Collaborative Code Editor
- Live document synchronization
- Multi-user editing support
- 500ms update frequency
- Last-Write-Wins conflict resolution

</td>
<td width="50%">

### 🐳 Secure Code Execution
- Docker-sandboxed environment
- Network isolation (`--network=none`)
- Resource limits (CPU, RAM, PIDs)
- Ephemeral containers

</td>
</tr>
</table>

<br/>

<p align="center">
  <img src="https://user-images.githubusercontent.com/73097560/115834477-dbab4500-a447-11eb-908a-139a6edaec5c.gif" width="100%">
</p>

## 📸 Screenshots

<details open>
<summary><strong>🖥️ Application Interface</strong></summary>
<br/>

<table align="center">
<tr>
<td align="center" width="50%">
<img src="App_Screenshots/Home Page.png" alt="Dashboard" width="100%"/>
<br/><strong>🏠 Home Dashboard</strong>
</td>
<td align="center" width="50%">
<img src="App_Screenshots/File Transfer.png" alt="File Transfer" width="100%"/>
<br/><strong>📁 File Transfer</strong>
</td>
</tr>
<tr>
<td align="center" width="50%">
<img src="App_Screenshots/Code Editor Part 1.png" alt="Code Editor" width="100%"/>
<br/><strong>💻 Code Editor</strong>
</td>
<td align="center" width="50%">
<img src="App_Screenshots/Code Editor Part 2.png" alt="Execution" width="100%"/>
<br/><strong>⚡ Code Execution</strong>
</td>
</tr>
</table>

</details>

<details>
<summary><strong>📊 Congestion Control Analytics</strong></summary>
<br/>

<table align="center">
<tr>
<td align="center" width="50%">
<img src="App_Screenshots/Congestion Control Part 1.png" alt="RTT and CWND" width="100%"/>
<br/><strong>📈 RTT vs Chunk Sequence & CWND vs Event Sequence</strong>
</td>
<td align="center" width="50%">
<img src="App_Screenshots/Congestion Control Part 2.png" alt="Window Size" width="100%"/>
<br/><strong>📈 Window Size vs Transmission Round</strong>
</td>
</tr>
</table>

</details>

<br/>

## 🏗️ Architecture

<p align="center">
  <img src="App_Screenshots/Architecture.png" alt="System Architecture" width="90%"/>
</p>

<details>
<summary><strong>📋 Service Details</strong></summary>
<br/>

| Service | Port | Protocol | Description |
|:--------|:----:|:--------:|:------------|
| 🖥️ **Frontend** | `8501` | HTTP | Streamlit UI Gateway |
| 🔑 **Room Manager** | `9013` | TCP | Room lifecycle management |
| 💬 **Chat Service** | `9009` | TCP | Messaging & image CDN |
| 📂 **File Control** | `9010` | TCP | File listing & signaling |
| 📡 **File Data** | `9011` | UDP | Reliable data transfer |
| 📝 **Collab Service** | `9011` | TCP | Document synchronization |
| 🐳 **Exec Service** | `9012` | TCP | Docker code execution |

</details>

<br/>

<p align="center">
  <img src="https://user-images.githubusercontent.com/73097560/115834477-dbab4500-a447-11eb-908a-139a6edaec5c.gif" width="100%">
</p>

## 📡 Technical Deep Dives

<details>
<summary><strong>🔧 Reliable UDP Protocol</strong></summary>
<br/>

### Packet Structure (JSON over UDP)
```json
{
  "type": "DATA",           // SYN | SYN-ACK | ACK | DATA | FIN | FIN-ACK
  "seq": 105,               // Sequence Number
  "ack": 105,               // Acknowledgement Number
  "rwnd": 64,               // Receiver Window Size
  "room": "ABCD",           // Room context
  "filename": "doc.pdf",    // File context
  "payload_b64": "...",     // Base64 encoded chunk (4KB)
  "session_id": "a1b2c3d4"  // Session token
}
```

### RTT Estimation (Jacobson/Karels)
| Parameter | Formula | Value |
|:----------|:--------|:-----:|
| Smoothed RTT | `(1-α)·SRTT + α·RTTsample` | α = 0.125 |
| RTT Variance | `(1-β)·RTTVAR + β·|SRTT - RTTsample|` | β = 0.25 |
| RTO | `SRTT + 4·RTTVAR` | Min: 200ms |

### Congestion Control
| Event | Tahoe 🐢 | Reno 🦊 |
|:------|:---------|:--------|
| **Timeout** | CWND = 1, Slow Start | Same |
| **3 Dup ACKs** | CWND = 1, Slow Start | CWND = ssthresh + 3, Fast Recovery |

</details>

<details>
<summary><strong>💬 TCP Chat Protocol</strong></summary>
<br/>

### Command Reference
| Command | Direction | Description |
|:--------|:---------:|:------------|
| `HELLO <user> <room>` | C → S | Join room |
| `MSG <content>` | C → S | Send message |
| `IMG <filename> <b64>` | C → S | Upload image |
| `GET_IMG <filename>` | C → S | Fetch image |
| `BYE` | C → S | Disconnect |

### CDN Lazy Loading
| Step | Action | Description |
|:----:|:------:|:------------|
| **1** | 📤 Broadcast | Server sends metadata only |
| **2** | 🖼️ Render | Client shows placeholder |
| **3** | 📥 Fetch | On-demand binary request |
| **4** | 💾 Cache | Store in `backend/data/cdn/` |

</details>

<details>
<summary><strong>🛡️ Docker Security Profile</strong></summary>
<br/>

| Flag | Value | Purpose |
|:-----|:------|:--------|
| `--network` | `none` | Total network isolation |
| `--memory` | `256m` | Prevent RAM exhaustion |
| `--cpus` | `0.5` | Fair CPU scheduling |
| `--pids-limit` | `64` | Prevent fork bombs |
| `--rm` | `true` | Auto-cleanup containers |

</details>

<br/>

<p align="center">
  <img src="https://user-images.githubusercontent.com/73097560/115834477-dbab4500-a447-11eb-908a-139a6edaec5c.gif" width="100%">
</p>

## 🚀 Quick Start

### Prerequisites

```
✅ Python 3.10+     (required for match-case syntax)
✅ Docker Desktop   (must be running for code execution)
✅ pip              (for dependency management)
```

### Installation

```bash
# Clone the repository
git clone https://github.com/Abs-Futy7/SyncroX.git
cd SyncroX

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Build Docker image
docker build -t syncro-sandbox ./backend/code_exec/

# Start servers
python start_all_servers_venv.py

# Launch frontend (new terminal)
streamlit run frontend/streamlit_app/app.py
```

> ⚠️ **Note:** Ensure Docker Desktop is running before starting the servers.

### Verify Installation

| Step | Action | Expected |
|:----:|:-------|:---------|
| 1 | Click "Create New Room" | 4-digit code appears |
| 2 | Open new tab, enter code | Join as second user |
| 3 | Send chat message | Instant delivery |
| 4 | Upload file | See congestion graph |
| 5 | Run code | Docker execution works |

<br/>

## 📁 Project Structure

```
SyncroX/
├── 📂 backend/
│   ├── 📂 code_exec/          # 🐳 Docker execution engine
│   ├── 📂 collab/             # 📝 Collaborative editor
│   ├── 📂 file_transfer/      # 📡 UDP file transfer
│   ├── 📂 room_mgmt/          # 🔑 Room management
│   └── 📂 tcp_chat/           # 💬 Chat protocol
├── 📂 frontend/               # 🖥️ Streamlit UI
├── 📂 App_Screenshots/        # 📸 Screenshots
├── 📂 assets/                 # 🎨 Branding
├── 📄 config.py               # ⚙️ Configuration
├── 📄 requirements.txt        # 📦 Dependencies
└── 📄 start_all_servers_venv.py  # 🚀 Launcher
```

<br/>

<p align="center">
  <img src="https://user-images.githubusercontent.com/73097560/115834477-dbab4500-a447-11eb-908a-139a6edaec5c.gif" width="100%">
</p>

## 👨‍💻 Authors

<p align="center">
  <a href="https://github.com/Mehedi26696">
    <img src="https://github.com/Mehedi26696.png" width="100" height="100" style="border-radius:50%"/>
  </a>
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
  <a href="https://github.com/Abs-Futy7">
    <img src="https://github.com/Abs-Futy7.png" width="100" height="100" style="border-radius:50%"/>
  </a>
</p>

<p align="center">
  <a href="https://github.com/Mehedi26696"><strong>H.M. Mehedi Hasan</strong></a>
  &nbsp;&nbsp;•&nbsp;&nbsp;
  <a href="https://github.com/Abs-Futy7"><strong>MD. Abu Bakar Siddique</strong></a>
</p>

<p align="center">
  <a href="https://github.com/Mehedi26696">
    <img src="https://img.shields.io/badge/GitHub-Mehedi26696-181717?style=flat-square&logo=github" alt="GitHub"/>
  </a>
  &nbsp;
  <a href="https://github.com/Abs-Futy7">
    <img src="https://img.shields.io/badge/GitHub-Abs--Futy7-181717?style=flat-square&logo=github" alt="GitHub"/>
  </a>
</p>

<br/>

---

<p align="center">
  <strong>Built with ❤️ using Python Sockets & Streamlit</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Made_with-Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Sockets-TCP_&_UDP-10B981?style=for-the-badge" alt="Sockets">
  <img src="https://img.shields.io/badge/UI-Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white" alt="Streamlit">
</p>

<p align="center">
  <sub>⭐ Star this repository if you found it helpful!</sub>
</p>
