import os
import sys
import time
import socket
from pathlib import Path

# --- Make project root importable ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import streamlit as st
from PIL import Image

try:
    import pandas as pd
    import matplotlib.pyplot as plt
    HAS_PLOTTING = True
except ImportError:
    HAS_PLOTTING = False

# ============================================================================
# DASHBOARD PAGE
# ============================================================================

# Load custom icon
icon_path = os.path.join(PROJECT_ROOT, "assets", "image.png")
page_icon = Image.open(icon_path) if os.path.exists(icon_path) else "📊"

st.set_page_config(page_title="Dashboard - SyncroX", page_icon=page_icon, layout="wide")

# Apply custom CSS for Raleway font, black background & SyncroX theme
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Raleway:wght@300;400;500;600;700&display=swap');
    
    * {
        font-family: 'Raleway', sans-serif !important;
    }
    
    .stApp {
        background-color: #000000;
    }
    
    .main {
        background-color: #000000;
    }
    
    [data-testid="stSidebar"] {
        background-color: #0a0a0a;
        border-right: 1px solid rgba(3, 192, 132, 0.25);
    }
    
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Raleway', sans-serif !important;
        color: #f9fafb !important;
    }

    p, div, span, label {
        font-family: 'Raleway', sans-serif !important;
        color: #e5e7eb;
    }

    /* Sidebar headings */
    [data-testid="stSidebar"] h3 {
        color: #03C084 !important;
        font-weight: 700 !important;
    }

    /* Sidebar info box */
    .stAlert {
        background-color: #0d0d0d !important;
        border-left: 4px solid #03C084 !important;
        color: #e5e7eb !important;
    }

    /* Sidebar navigation buttons */
    [data-testid="stSidebar"] button {
        background-color: #03C084 !important;
        color: #020617 !important;
        border-radius: 8px !important;
        border: none !important;
        font-weight: 700 !important;
        margin-bottom: 8px !important;
        padding: 0.45rem 0.8rem !important;
    }
    [data-testid="stSidebar"] button:hover {
        background-color: #02a673 !important;
        color: #f9fafb !important;
    }

    /* Disabled nav (current page) */
    [data-testid="stSidebar"] button[disabled] {
        background-color: #064e3b !important;
        color: #9ca3af !important;
        opacity: 0.9 !important;
    }

    /* Logout secondary button */
    button[kind="secondary"] {
        background-color: #111827 !important;
        color: #e5e7eb !important;
        border: 1px solid #374151 !important;
    }
    button[kind="secondary"]:hover {
        border-color: #03C084 !important;
        background-color: #1f2933 !important;
    }

    /* Global primary buttons (if any) */
    div.stButton > button {
        background-color: #03C084 !important;
        color: #020617 !important;
        border-radius: 8px !important;
        border: none !important;
        font-weight: 800 !important;
    }
    div.stButton > button:hover {
        background-color: #02a673 !important;
        color: #f9fafb !important;
    }

    /* Expander styling (for error details, metrics, concepts) */
    details {
        border-radius: 10px;
        border: 1px solid rgba(55, 65, 81, 0.9);
        background-color: #020617;
        margin-bottom: 8px;
    }
    summary {
        color: #e5e7eb !important;
        font-weight: 500;
    }
    details[open] {
        border-color: #03C084;
        box-shadow: 0 0 14px rgba(3, 192, 132, 0.35);
    }

    /* Captions / subtle text */
    .stCaption, .stMarkdown small {
        color: #9ca3af !important;
    }

</style>
""", unsafe_allow_html=True)

# Check if user is logged in
if not st.session_state.get("is_logged_in", False):
    st.error("⚠️ Please login first!")
    if st.button("Go to Home"):
        st.switch_page("app.py")
    st.stop()

# Sidebar - User info and navigation
with st.sidebar:
    st.markdown("### 👤 User Information")
    st.info(f"**Name:** {st.session_state.username}\n\n**Room:** `{st.session_state.current_room}`")
    
    st.markdown("---")
    
    st.markdown("### 🧭 Navigation")
    st.caption("Select a feature below:")
    
    # Navigation buttons
    if st.button("💬 Chat", use_container_width=True):
        st.switch_page("pages/chat.py")
    
    if st.button("🤝 Code Editor", use_container_width=True):
        st.switch_page("pages/code_editor.py")
    
    if st.button("📁 File Manager", use_container_width=True):
        st.switch_page("pages/file_manager.py")
    
    if st.button("📊 Dashboard", use_container_width=True, disabled=True):
        st.switch_page("pages/dashboard_page.py")
    
    st.markdown("---")
    
    # Logout button
    if st.button("🚪 Leave Room & Logout", use_container_width=True, type="secondary"):
        st.session_state.is_logged_in = False
        st.session_state.username = ""
        st.session_state.current_room = ""
        # Clear all client connections
        for key in list(st.session_state.keys()):
            if key.endswith('_client'):
                st.session_state.pop(key)
        st.switch_page("app.py")

st.header("📊 System Dashboard")
st.caption(f"Room: `{st.session_state.current_room}` • User: `{st.session_state.username}`")


def check_tcp_server(host: str, port: int, timeout: float = 0.5):
    """Check if a TCP server is reachable"""
    start = time.time()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            latency_ms = (time.time() - start) * 1000.0
            return True, latency_ms, ""
    except OSError as e:
        return False, None, str(e)


# ---- Server Status Section ----
st.subheader("🖥️ Server Status")

host = "127.0.0.1"
services = [
    ("💬 Chat Server", "Real-time messaging over TCP", host, 9009),
    ("📁 File Server", "File transfer with congestion control", host, 9010),
    ("🤝 Collab Server", "Shared code editor and sync", host, 9011),
    ("⚙️ Exec Server", "Docker-sandboxed code execution", host, 9012),
]

cols = st.columns(2)
for i, (name, desc, h, p) in enumerate(services):
    with cols[i % 2]:
        ok, latency_ms, err = check_tcp_server(h, p, timeout=0.7)
        
        with st.container():
            st.markdown(f"**{name}**")
            st.caption(f"`{h}:{p}` • {desc}")
            
            if ok:
                st.success(f"🟢 Online • {latency_ms:.1f}ms latency")
            else:
                st.error("🔴 Offline")
                if err:
                    with st.expander("Error details"):
                        st.code(err)

st.markdown("---")

# ---- Metrics Section ----
if HAS_PLOTTING:
    st.subheader("📈 File Transfer Metrics")
    
    metrics_dir = Path("data") / "metrics"
    if not metrics_dir.exists() or not list(metrics_dir.glob("*.csv")):
        st.info("📊 No metrics available yet. Upload files to generate performance data.")
    else:
        files = sorted(metrics_dir.glob("room_*_file_metrics.csv"))
        
        if files:
            # Find metrics for current room
            current_room_files = [f for f in files if f"room_{st.session_state.current_room}_" in f.name]
            
            if current_room_files:
                fp = current_room_files[0]
                
                try:
                    df = pd.read_csv(fp)
                    
                    st.write(f"**Current Room Metrics:** `{fp.name}`")
                    st.write(f"Total events: {len(df)}")
                    
                    # Show recent events
                    with st.expander("📋 Recent Events"):
                        st.dataframe(df.tail(20), use_container_width=True)
                    
                    # Plot RTT if available
                    ack_df = df[df["event"] == "ACK"].copy()
                    if not ack_df.empty:
                        ack_df["rel_seq"] = ack_df["seq"] - ack_df["seq"].min() + 1
                        
                        col_chart1, col_chart2 = st.columns(2)
                        
                        with col_chart1:
                            st.markdown("**RTT Performance**")
                            fig1, ax1 = plt.subplots(figsize=(6, 4))
                            ax1.plot(ack_df["rel_seq"], ack_df["rtt_ms"], marker="o", label="RTT sample", alpha=0.7)
                            ax1.plot(ack_df["rel_seq"], ack_df["srtt_ms"], marker=".", label="EWMA RTT", linewidth=2)
                            ax1.set_xlabel("Chunk Sequence")
                            ax1.set_ylabel("RTT (ms)")
                            ax1.set_title("Round-Trip Time")
                            ax1.legend()
                            ax1.grid(True, alpha=0.3)
                            st.pyplot(fig1)
                        
                        with col_chart2:
                            st.markdown("**Congestion Window**")
                            fig2, ax2 = plt.subplots(figsize=(6, 4))
                            ax2.plot(df["seq"], df["cwnd"], marker="o", color="green", alpha=0.7, label="CWND")
                            ax2.set_xlabel("Event Sequence")
                            ax2.set_ylabel("CWND (segments)")
                            algo = df["algo"].iloc[0] if "algo" in df.columns else "unknown"
                            ax2.set_title(f"Congestion Control ({algo.upper()})")
                            ax2.grid(True, alpha=0.3)
                            ax2.legend()
                            st.pyplot(fig2)
                    
                    # Detailed Congestion Window vs Transmission Round plot
                    st.markdown("---")
                    st.markdown("**📈 Congestion Window Evolution**")
                    
                    if not df.empty and "cwnd" in df.columns and "ssthresh" in df.columns:
                        # Create transmission round (use sequence number as proxy)
                        df_plot = df.copy()
                        df_plot["round"] = range(1, len(df_plot) + 1)
                        
                        fig3, ax3 = plt.subplots(figsize=(12, 6))
                        
                        # Plot CWND
                        ax3.plot(df_plot["round"], df_plot["cwnd"], 
                                marker="o", color="blue", linewidth=2, 
                                label="Congestion Window (CWND)", markersize=4)
                        
                        # Plot ssthresh
                        ax3.plot(df_plot["round"], df_plot["ssthresh"], 
                                color="red", linestyle="--", linewidth=2, 
                                label="Slow Start Threshold (ssthresh)", alpha=0.7)
                        
                        # Shade regions
                        ax3.fill_between(df_plot["round"], 0, df_plot["ssthresh"], 
                                        alpha=0.1, color="green", label="Slow Start Region")
                        ax3.fill_between(df_plot["round"], df_plot["ssthresh"], 
                                        df_plot["cwnd"].max() * 1.1, 
                                        alpha=0.1, color="orange", label="Congestion Avoidance Region")
                        
                        ax3.set_xlabel("Transmission Round", fontsize=12)
                        ax3.set_ylabel("Window Size (segments)", fontsize=12)
                        ax3.set_title(f"TCP {algo.upper()} Congestion Control Dynamics", fontsize=14, fontweight="bold")
                        ax3.legend(loc="best", fontsize=10)
                        ax3.grid(True, alpha=0.3, linestyle=":", linewidth=0.5)
                        ax3.set_xlim(0, len(df_plot) + 1)
                        ax3.set_ylim(0, max(df_plot["cwnd"].max(), df_plot["ssthresh"].max()) * 1.1)
                        
                        st.pyplot(fig3)
                        
                        # Statistics
                        col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
                        with col_stat1:
                            st.metric("Max CWND", f"{df_plot['cwnd'].max():.2f}")
                        with col_stat2:
                            st.metric("Final CWND", f"{df_plot['cwnd'].iloc[-1]:.2f}")
                        with col_stat3:
                            st.metric("Final ssthresh", f"{df_plot['ssthresh'].iloc[-1]:.2f}")
                        with col_stat4:
                            avg_cwnd = df_plot['cwnd'].mean()
                            st.metric("Avg CWND", f"{avg_cwnd:.2f}")
                    
                except Exception as e:
                    st.error(f"Error loading metrics: {e}")
            else:
                st.info(f"📊 No metrics for room `{st.session_state.current_room}` yet. Upload a file to generate data.")
                
                # Show other rooms
                if files:
                    st.write("**Other rooms with metrics:**")
                    for f in files[:5]:
                        room_num = f.stem.split('_')[1]
                        st.caption(f"• Room {room_num}")
else:
    st.warning("⚠️ Install pandas and matplotlib to view metrics: `pip install pandas matplotlib`")

st.markdown("---")

# ---- Networking Concepts Section ----
st.subheader("🎓 Networking Concepts Demonstrated")

with st.expander("📡 Custom TCP Protocols", expanded=True):
    st.markdown("""
    #### Chat Protocol (Port 9009)
    - **HELLO <username>**: Initial handshake to establish client identity
    - **CREATE_ROOM**: Server generates unique 4-digit room code and assigns client
    - **JOIN_ROOM <code>**: Join existing room (auto-creates if doesn't exist)
    - **MSG <text>**: Broadcast message to all room members with automatic echo
    - **LIST_ROOMS**: Query all active room codes on server
    - **BYE**: Graceful disconnect with cleanup of client resources
    - **Room Broadcasting**: Messages are multicast to all sockets in the room set
    - **Username Tracking**: Server maintains client→username mapping for attribution
    
    #### File Transfer Protocol (Port 9010)
    - **UPLOAD <filename> <filesize> <room> <algo>**: Initiate file upload with metadata
    - **Size-prefixed chunks**: Each chunk sent as `<4-byte-size><data>` for framing
    - **Per-chunk ACK**: Server responds with `ACK <seq> <timestamp>` for RTT measurement
    - **Checksum validation**: Optional integrity checking on received chunks
    - **DOWNLOAD <filename> <room>**: Request file retrieval from room storage
    - **LIST <room>**: Enumerate all uploaded files in specific room
    - **Binary safe**: Uses raw socket buffers, no text encoding on file data
    
    #### Collaborative Editor Protocol (Port 9011)
    - **JOIN <room> <username>**: Subscribe to document updates for room
    - **SET <content>**: Push local document changes to server
    - **DOC <content>**: Server broadcasts synchronized document state
    - **USERS <count>**: Server notifies clients of active collaborators
    - **Last-write-wins**: Simple conflict resolution, no operational transforms
    - **Auto-sync**: Clients poll for DOC updates every 500ms for real-time feel
    
    #### Code Execution Protocol (Port 9012)
    - **EXECUTE <lang> <code> [stdin]**: Submit code with language and optional input
    - **Docker isolation**: Each execution runs in ephemeral container with resource limits
    - **RESULT <stdout> <stderr> <rc> <time_ms>**: Return execution output and metrics
    - **Multi-language support**: Python, C, C++, Java with appropriate runtimes
    - **Security constraints**: 256MB memory, 0.5 CPU cores, 30s timeout per execution
    - **Compilation handling**: Transparent gcc/g++/javac compilation before execution
    """)

with st.expander("🔄 Flow & Congestion Control", expanded=True):
    st.markdown("""
    #### TCP Congestion Control Simulation
    - **Slow Start Phase**: CWND grows exponentially (doubles per RTT) until ssthresh
    - **Congestion Avoidance**: Linear growth (+1 MSS per RTT) above ssthresh
    - **Tahoe Algorithm**: On loss, ssthresh = cwnd/2, cwnd resets to 1 MSS
    - **Reno Algorithm**: On loss, ssthresh = cwnd/2, cwnd = ssthresh (faster recovery)
    - **Fast Retransmit**: Detect loss from duplicate ACKs without timeout
    - **Initial ssthresh**: Set to 8 segments at connection start
    
    #### RTT Estimation
    - **Sample RTT**: Measure time between chunk send and ACK receipt
    - **EWMA Smoothing**: `SRTT = (1-α)×SRTT + α×RTT` where α=0.125
    - **Adaptive timeout**: RTO calculated from SRTT + 4×RTTVAR
    - **Timestamp-based**: Server echoes send timestamp in ACK for accurate measurement
    
    #### Chunking Strategy
    - **Fixed chunk size**: 4096 bytes (4KB) per segment for predictable behavior
    - **Sequential numbering**: Each chunk gets sequence number for ordering
    - **Size prefixing**: 4-byte big-endian integer before each chunk
    - **Pipeline depth**: Window size determines in-flight chunks
    - **Flow control**: Receiver can slow sender via window advertisements
    
    #### Metrics Logging
    - **Per-transfer CSV**: Records seq, event, cwnd, ssthresh, rtt_ms, srtt_ms
    - **Room isolation**: Metrics tagged with room code for multi-tenant analytics
    - **Real-time plotting**: Dashboard visualizes CWND evolution and threshold crossings
    """)

with st.expander("🔒 Reliability & Security", expanded=True):
    st.markdown("""
    #### Protocol Reliability
    - **Request-Response Pattern**: Every client command receives OK/ERROR acknowledgment
    - **Command echoing**: Server echoes validated commands back to client
    - **Error propagation**: Detailed error messages (e.g., "Room does not exist")
    - **Graceful degradation**: Clients handle server disconnects and reconnect
    - **Timeout handling**: Both client and server implement read/write timeouts
    - **Connection cleanup**: finally blocks ensure socket closure and resource release
    
    #### Room-Based Isolation
    - **Namespace separation**: 4-digit room codes partition all resources
    - **No cross-room leakage**: Files, messages, and documents scoped to room
    - **Concurrent rooms**: Server maintains separate state per room via dictionaries
    - **Room cleanup**: Empty rooms auto-deleted when last member disconnects
    - **Code reusability**: Room pattern consistent across all services
    
    #### Docker Sandbox Security
    - **Process isolation**: Each execution in separate container, no shared state
    - **Resource limits**: CPU, memory, and time constraints prevent DoS
    - **No network access**: Containers run with `--network none` flag
    - **Read-only filesystem**: Code directory mounted as read-only
    - **Temporary artifacts**: Build outputs in ephemeral /tmp directory
    - **UID mapping**: Non-root user inside container for privilege separation
    - **Image scanning**: Base images from trusted registries (python:3.11-slim, gcc, openjdk)
    
    #### Rate Limiting & DoS Prevention
    - **Chat rate limit**: Max 5 messages per 2-second window per client
    - **Sliding window**: Uses deque to track message timestamps
    - **RATE_LIMIT error**: Client receives explicit backpressure signal
    - **Connection limits**: Server can cap total connections via listen backlog
    - **Timeout enforcement**: Idle connections closed after inactivity period
    
    #### Data Integrity
    - **Binary preservation**: Files transferred bit-for-bit with no encoding corruption
    - **Size validation**: Received file size checked against declared size
    - **Atomic writes**: Files written to temp location, then renamed atomically
    - **Path sanitization**: Uploaded filenames sanitized to prevent directory traversal
    - **Storage isolation**: Each room's files stored in separate directory
    """)

st.markdown("---")
st.caption("💡 This dashboard shows real-time status of all TCP services and performance metrics")
