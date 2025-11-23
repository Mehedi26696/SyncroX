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

# Apply custom CSS for Raleway font and black background
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
    }
    
    h1, h2, h3, h4, h5, h6, p, div, span, label, button {
        font-family: 'Raleway', sans-serif !important;
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

with st.expander("📡 Custom TCP Protocols"):
    st.markdown("""
    - **Chat:** `HELLO / JOIN / MSG / LIST` for room-based messaging
    - **File Transfer:** Size-prefixed framing with per-chunk ACKs
    - **Collab:** `SET / DOC / USERS` for real-time document sync
    - **Exec:** `EXECUTE / RESULT` for remote code execution
    """)

with st.expander("🔄 Flow & Congestion Control"):
    st.markdown("""
    - **Chunked transfers:** 4KB segments with explicit sizes
    - **EWMA RTT:** Smoothed round-trip time calculation
    - **Tahoe/Reno simulation:** Slow start, congestion avoidance, loss recovery
    - **Per-chunk ACKs:** Measure latency and adjust window size
    """)

with st.expander("🔒 Reliability & Security"):
    st.markdown("""
    - **Request-response pattern:** Every command gets OK/ERROR response
    - **Room isolation:** 4-digit codes scope all data transfers
    - **Docker sandbox:** Untrusted code runs in isolated containers
    - **Rate limiting:** Prevents message flooding in chat
    """)

st.markdown("---")
st.caption("💡 This dashboard shows real-time status of all TCP services and performance metrics")
