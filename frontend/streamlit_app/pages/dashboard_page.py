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
from config import SERVER_HOST, CHAT_PORT, FILE_PORT, COLLAB_PORT, EXEC_PORT

try:
    import pandas as pd
    import matplotlib.pyplot as plt
    import matplotlib
    
    # Configure matplotlib for clean white background
    matplotlib.use('Agg')
    plt.style.use('default')
    
    # Configure matplotlib defaults for professional white background
    plt.rcParams.update({
        'figure.facecolor': 'white',
        'axes.facecolor': 'white',
        'axes.edgecolor': '#333333',
        'axes.labelcolor': '#1f2937',
        'xtick.color': '#4b5563',
        'ytick.color': '#4b5563',
        'text.color': '#1f2937',
        'grid.color': '#d1d5db',
        'grid.alpha': 0.5,
        'lines.linewidth': 2.5,
        'font.size': 10,
        'axes.titlesize': 12,
        'axes.labelsize': 10,
        'xtick.labelsize': 9,
        'ytick.labelsize': 9,
        'legend.fontsize': 9,
        'figure.titlesize': 13,
    })
    
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
        padding-top: 2rem;
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
        margin-bottom: 12px;
        transition: all 0.3s ease;
    }
    summary {
        color: #e5e7eb !important;
        font-weight: 600;
        padding: 0.75rem;
        cursor: pointer;
    }
    summary:hover {
        color: #03C084 !important;
    }
    details[open] {
        border-color: #03C084;
        box-shadow: 0 0 20px rgba(3, 192, 132, 0.25);
    }

    /* Captions / subtle text */
    .stCaption, .stMarkdown small {
        color: #9ca3af !important;
    }
    
    /* Metric cards enhancement */
    [data-testid="stMetricValue"] {
        font-size: 2rem !important;
        font-weight: 700 !important;
        color: #03C084 !important;
    }
    
    [data-testid="stMetricLabel"] {
        font-size: 0.875rem !important;
        font-weight: 500 !important;
        color: #9ca3af !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* Server status card */
    .server-card {
        background: linear-gradient(135deg, #020617 0%, #0a0a0a 100%);
        border: 1px solid rgba(3, 192, 132, 0.2);
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        transition: all 0.3s ease;
    }
    
    .server-card:hover {
        border-color: rgba(3, 192, 132, 0.5);
        box-shadow: 0 4px 20px rgba(3, 192, 132, 0.15);
        transform: translateY(-2px);
    }
    
    /* Chart container styling */
    .chart-container {
        background-color: #020617;
        border: 1px solid rgba(55, 65, 81, 0.5);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
    }
    
    /* Dataframe styling */
    [data-testid="stDataFrame"] {
        border: 1px solid rgba(55, 65, 81, 0.5);
        border-radius: 8px;
        overflow: hidden;
    }
    
    /* Section headers */
    .section-header {
        border-bottom: 2px solid rgba(3, 192, 132, 0.3);
        padding-bottom: 0.5rem;
        margin-bottom: 1.5rem;
    }
    
    /* Info boxes enhancement */
    .stInfo {
        background: linear-gradient(135deg, rgba(3, 192, 132, 0.1) 0%, rgba(3, 192, 132, 0.05) 100%) !important;
        border-left: 4px solid #03C084 !important;
        border-radius: 8px;
    }
    
    /* Success boxes enhancement */
    .stSuccess {
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.15) 0%, rgba(16, 185, 129, 0.05) 100%) !important;
        border-left: 4px solid #10b981 !important;
        border-radius: 8px;
    }
    
    /* Error boxes enhancement */
    .stError {
        background: linear-gradient(135deg, rgba(239, 68, 68, 0.15) 0%, rgba(239, 68, 68, 0.05) 100%) !important;
        border-left: 4px solid #ef4444 !important;
        border-radius: 8px;
    }
    
    /* Selectbox styling */
    [data-testid="stSelectbox"] {
        background-color: #020617 !important;
        border-radius: 8px;
    }
    
    /* Divider styling */
    hr {
        margin: 2rem 0;
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(3, 192, 132, 0.3), transparent);
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
st.markdown('<div class="section-header"><h2>🖥️ Server Status</h2></div>', unsafe_allow_html=True)

services = [
    ("💬 Chat Server", "Real-time messaging over TCP", SERVER_HOST, CHAT_PORT),
    ("📁 File Server", "File transfer with congestion control", SERVER_HOST, FILE_PORT),
    ("🤝 Collab Server", "Shared code editor and sync", SERVER_HOST, COLLAB_PORT),
    ("⚙️ Exec Server", "Docker-sandboxed code execution", SERVER_HOST, EXEC_PORT),
]

cols = st.columns(2)
for i, (name, desc, h, p) in enumerate(services):
    with cols[i % 2]:
        ok, latency_ms, err = check_tcp_server(h, p, timeout=0.7)
        
        with st.container():
            st.markdown(f"**{name}**")
            st.caption(f"`{h}:{p}` • {desc}")
            
            if ok:
                st.success(f"🟢 Online • {latency_ms:.1f}ms latency", icon="✅")
            else:
                st.error("🔴 Offline", icon="❌")
                if err:
                    with st.expander("🔍 Error details"):
                        st.code(err, language="text")

st.markdown("---")

# ---- Metrics Section (room + per-file analysis) ----
if HAS_PLOTTING:
    st.markdown('<div class="section-header"><h2>📈 File Transfer Metrics</h2></div>', unsafe_allow_html=True)
    
    metrics_dir = Path(PROJECT_ROOT) / "data" / "metrics"
    if not metrics_dir.exists() or not list(metrics_dir.glob("*.csv")):
        st.info("📊 No metrics available yet. Upload files to generate performance data.")
    else:
        files = sorted(metrics_dir.glob("room_*_file_metrics.csv"))
        
        if files:
            # Metrics for current room
            current_room = st.session_state.current_room
            current_room_files = [f for f in files if f"room_{current_room}_" in f.name]
            
            if current_room_files:
                fp = current_room_files[0]
                
                try:
                    df = pd.read_csv(fp)
                    
                    # Header with file info
                    col_info1, col_info2 = st.columns([3, 1])
                    with col_info1:
                        st.markdown(f"**📁 Metrics File:** `{fp.name}`")
                    with col_info2:
                        st.metric("Total Events", f"{len(df):,}")
                    
                    # ---------- NEW: per-file filter ----------
                    if "file" in df.columns:
                        file_names = sorted(df["file"].dropna().unique())
                        st.markdown("**🔍 Filter Options**")
                        file_choice = st.selectbox(
                            "Select file to analyze",
                            ["All files"] + file_names,
                            help="Filter metrics by specific file"
                        )
                        if file_choice != "All files":
                            df = df[df["file"] == file_choice].copy()
                            st.info(f"📌 Filtered to: **{file_choice}** ({len(df):,} events)")
                        else:
                            file_choice = "All files"
                    else:
                        file_choice = "All files"
                    
                    st.markdown("---")
                    
                    # Show recent events (filtered)
                    with st.expander("📋 View Recent Events Table", expanded=False):
                        st.dataframe(df.tail(30), use_container_width=True, height=400)
                    
                    # Plot RTT if available
                    ack_df = df[df["event"] == "ACK"].copy()
                    if not ack_df.empty and "rtt_ms" in ack_df.columns:
                        ack_df["rel_seq"] = ack_df["seq"] - ack_df["seq"].min() + 1
                        
                        col_chart1, col_chart2 = st.columns(2)
                        
                        with col_chart1:
                            st.markdown("**⏱️ Round-Trip Time Performance**")
                            
                            fig1, ax1 = plt.subplots(figsize=(7, 5))
                            ax1.plot(
                                ack_df["rel_seq"],
                                ack_df["rtt_ms"],
                                marker="o",
                                markersize=3,
                                label="RTT sample",
                                alpha=0.8,
                                color="#60a5fa",
                                linewidth=1.5
                            )
                            if "srtt_ms" in ack_df.columns:
                                ax1.plot(
                                    ack_df["rel_seq"],
                                    ack_df["srtt_ms"],
                                    marker=".",
                                    markersize=2,
                                    label="EWMA RTT",
                                    linewidth=2.5,
                                    color="#03C084",
                                )
                            ax1.set_xlabel("Chunk Sequence", fontweight='bold')
                            ax1.set_ylabel("RTT (ms)", fontweight='bold')
                            title_suffix = f" – {file_choice}" if file_choice != "All files" else ""
                            ax1.set_title("Round-Trip Time Analysis" + title_suffix, fontweight='bold', pad=15)
                            ax1.legend(loc='best', framealpha=0.9)
                            ax1.grid(True, alpha=0.2, linestyle='--', linewidth=0.5)
                            ax1.spines['top'].set_visible(False)
                            ax1.spines['right'].set_visible(False)
                            plt.tight_layout()
                            st.pyplot(fig1)
                            plt.close(fig1)
                        
                        with col_chart2:
                            st.markdown("**📊 Congestion Window Evolution**")
                            
                            fig2, ax2 = plt.subplots(figsize=(7, 5))
                            ax2.plot(
                                df["seq"], 
                                df["cwnd"], 
                                marker="o", 
                                markersize=3,
                                color="#10b981", 
                                alpha=0.8, 
                                label="CWND",
                                linewidth=2
                            )
                            ax2.set_xlabel("Event Sequence", fontweight='bold')
                            ax2.set_ylabel("CWND (segments)", fontweight='bold')
                            algo = df["algo"].iloc[0] if "algo" in df.columns else "unknown"
                            ax2.set_title(f"Congestion Control ({algo.upper()}){title_suffix}", fontweight='bold', pad=15)
                            ax2.grid(True, alpha=0.2, linestyle='--', linewidth=0.5)
                            ax2.legend(loc='best', framealpha=0.9)
                            ax2.spines['top'].set_visible(False)
                            ax2.spines['right'].set_visible(False)
                            plt.tight_layout()
                            st.pyplot(fig2)
                            plt.close(fig2)
                    
                    # Detailed Congestion Window vs Transmission Round plot
                    st.markdown("---")
                    st.markdown("**📈 Detailed Congestion Window Dynamics**")
                    
                    if not df.empty and "cwnd" in df.columns and "ssthresh" in df.columns:
                        df_plot = df.copy()
                        df_plot["round"] = range(1, len(df_plot) + 1)
                        
                        fig3, ax3 = plt.subplots(figsize=(14, 7))
                        
                        # Plot CWND with gradient effect
                        ax3.plot(
                            df_plot["round"],
                            df_plot["cwnd"],
                            marker="o",
                            color="#60a5fa",
                            linewidth=3,
                            label="Congestion Window (CWND)",
                            markersize=4,
                            markeredgecolor='white',
                            markeredgewidth=0.5,
                        )
                        
                        # Plot ssthresh
                        ax3.plot(
                            df_plot["round"],
                            df_plot["ssthresh"],
                            color="#ef4444",
                            linestyle="--",
                            linewidth=2.5,
                            label="Slow Start Threshold (ssthresh)",
                            alpha=0.9,
                        )
                        
                        # Shade regions with better colors
                        ax3.fill_between(
                            df_plot["round"],
                            0,
                            df_plot["ssthresh"],
                            alpha=0.15,
                            color="#10b981",
                            label="Slow Start Region",
                        )
                        ax3.fill_between(
                            df_plot["round"],
                            df_plot["ssthresh"],
                            df_plot["cwnd"].max() * 1.15,
                            alpha=0.15,
                            color="#f59e0b",
                            label="Congestion Avoidance Region",
                        )
                        
                        algo = df_plot["algo"].iloc[0] if "algo" in df_plot.columns else "unknown"
                        title_suffix = f" – {file_choice}" if file_choice != "All files" else ""
                        ax3.set_xlabel("Transmission Round", fontsize=13, fontweight='bold')
                        ax3.set_ylabel("Window Size (segments)", fontsize=13, fontweight='bold')
                        ax3.set_title(
                            f"TCP {algo.upper()} Congestion Control Dynamics{title_suffix}", 
                            fontsize=15, 
                            fontweight='bold',
                            pad=20
                        )
                        ax3.legend(loc="best", fontsize=10, framealpha=0.95, edgecolor='#374151')
                        ax3.grid(True, alpha=0.2, linestyle=':', linewidth=0.5)
                        ax3.set_xlim(0, len(df_plot) + 1)
                        ax3.set_ylim(0, max(df_plot["cwnd"].max(), df_plot["ssthresh"].max()) * 1.15)
                        ax3.spines['top'].set_visible(False)
                        ax3.spines['right'].set_visible(False)
                        
                        plt.tight_layout()
                        st.pyplot(fig3)
                        plt.close(fig3)
                        
                        # Stats with better layout
                        st.markdown("**📊 Performance Statistics**")
                        col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
                        with col_stat1:
                            st.metric("Max CWND", f"{df_plot['cwnd'].max():.2f}", help="Peak congestion window size")
                        with col_stat2:
                            st.metric("Final CWND", f"{df_plot['cwnd'].iloc[-1]:.2f}", help="Ending congestion window")
                        with col_stat3:
                            st.metric("Final ssthresh", f"{df_plot['ssthresh'].iloc[-1]:.2f}", help="Ending slow start threshold")
                        with col_stat4:
                            avg_cwnd = df_plot['cwnd'].mean()
                            st.metric("Avg CWND", f"{avg_cwnd:.2f}", help="Average congestion window throughout transfer")
                    
                except Exception as e:
                    st.error(f"Error loading metrics: {e}")
            else:
                st.info(f"📊 No metrics for room `{st.session_state.current_room}` yet. Upload a file to generate data.")
                
                if files:
                    st.write("**Other rooms with metrics:**")
                    for f in files[:5]:
                        room_num = f.stem.split('_')[1]
                        st.caption(f"• Room {room_num}")
else:
    st.warning("⚠️ Install pandas and matplotlib to view metrics: `pip install pandas matplotlib`")

st.markdown("---")

# ---- Networking Concepts Section ----
st.markdown('<div class="section-header"><h2>🎓 Networking Concepts Demonstrated</h2></div>', unsafe_allow_html=True)
st.caption("Explore the networking principles and protocols implemented in SyncroX")

with st.expander("📡 Custom TCP Protocols", expanded=False):
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
    
    #### RTT Estimation
    - **Sample RTT**: Measure time between chunk send and ACK receipt
    - **EWMA Smoothing**: `SRTT = (1-α)×SRTT + α×RTT` where α=0.125
    - **Adaptive timeout**: RTO calculated from SRTT + 4×RTTVAR
    
    #### Chunking Strategy
    - **Fixed chunk size**: 4096 bytes (4KB) per segment for predictable behavior
    - **Sequential numbering**: Each chunk gets sequence number for ordering
    
    #### Metrics Logging
    - **Per-transfer CSV**: Records seq, event, cwnd, ssthresh, rtt_ms, srtt_ms
    - **Room isolation**: Metrics tagged with room code and filename
    - **Real-time plotting**: Dashboard visualizes CWND evolution and threshold crossings
    """)

with st.expander("🔒 Reliability & Security", expanded=True):
    st.markdown("""
    #### Protocol Reliability
    - **Request-Response Pattern**: Every client command receives OK/ERROR acknowledgment
    - **Error propagation**: Detailed error messages
    - **Timeout handling**: Client and server enforce timeouts
    
    #### Room-Based Isolation
    - **Namespace separation**: 4-digit room codes partition all resources
    - **No cross-room leakage**: Files, messages, and documents scoped to room
    
    #### Docker Sandbox Security
    - **Process isolation**: Each execution in separate container, no shared state
    - **Resource limits**: CPU, memory, and time constraints prevent DoS
    
    #### Rate Limiting & DoS Prevention
    - **Chat rate limit**: Max messages per time window per client
    """)

st.markdown("---")
st.markdown("""
<div style="text-align: center; padding: 2rem 0 1rem 0;">
    <p style="color: #9ca3af; font-size: 0.875rem;">
        💡 This dashboard provides real-time monitoring of all TCP services and detailed performance analytics
    </p>
    <p style="color: #6b7280; font-size: 0.75rem; margin-top: 0.5rem;">
        SyncroX • Advanced Networking Laboratory Platform
    </p>
</div>
""", unsafe_allow_html=True)
