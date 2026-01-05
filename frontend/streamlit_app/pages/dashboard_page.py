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

st.set_page_config(
    page_title="Dashboard - SyncroX", 
    page_icon=page_icon, 
    layout="wide",
    
)

# Apply custom CSS for Raleway font, new color scheme & SyncroX theme
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Raleway:wght@300;400;500;600;700&display=swap');
    
    * {
        font-family: 'Raleway', sans-serif !important;
        font-size: 18px;
    }
    
    .stApp {
        background-color: #ebfbee;
    }
    
    .main {
        background-color: #ebfbee;
        padding-top: 2rem;
    }
    
    [data-testid="stSidebar"] {
        background-color: #d3f9d8;
        border-right: 2px solid #087f5b;
    }
    
    /* Sidebar text colors */
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] div,
    [data-testid="stSidebar"] label {
        color: #000000 !important;
    }
    
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Raleway', sans-serif !important;
        color: #087f5b !important;
    }
    
    h1 { font-size: 3rem !important; }
    h2 { font-size: 2.5rem !important; }
    h3 { font-size: 2rem !important; }
    h4 { font-size: 1.5rem !important; }

    p, div, span, label {
        font-family: 'Raleway', sans-serif !important;
        color: #2b8a3e;
    }

    /* Sidebar headings */
    [data-testid="stSidebar"] h3 {
        color: #087f5b !important;
        font-weight: 700 !important;
        font-size: 1.5rem !important;
    }

    /* Sidebar info box */
    .stAlert {
        background-color: #d3f9d8 !important;
        border-left: 4px solid #087f5b !important;
        color: #087f5b !important;
        font-size: 1.1rem !important;
    }

    /* Sidebar navigation buttons */
    [data-testid="stSidebar"] button {
        background-color: #087f5b !important;
        color: #000000 !important;
        border-radius: 8px !important;
        border: none !important;
        font-weight: 700 !important;
        margin-bottom: 8px !important;
        padding: 0.6rem 1rem !important;
        font-size: 1.3rem !important;
    }
    [data-testid="stSidebar"] button p,
    [data-testid="stSidebar"] button span,
    [data-testid="stSidebar"] button div,
    [data-testid="stSidebar"] button * {
        color: #000000 !important;
        font-size: 1.2rem !important;
    }
    [data-testid="stSidebar"] button:hover {
        background-color: #006E6D !important;
        color: #000000 !important;
    }
    [data-testid="stSidebar"] button:hover p,
    [data-testid="stSidebar"] button:hover span,
    [data-testid="stSidebar"] button:hover div,
    [data-testid="stSidebar"] button:hover * {
        color: #000000 !important;
    }

    /* Disabled nav (current page) */
    [data-testid="stSidebar"] button[disabled] {
        background-color: #b2f2bb !important;
        color: #087f5b !important;
        opacity: 0.9 !important;
    }
    [data-testid="stSidebar"] button[disabled] * {
        color: #087f5b !important;
    }

    /* Logout secondary button */
    button[kind="secondary"] {
        background-color: #b2f2bb !important;
        color: #087f5b !important;
        border: 2px solid #087f5b !important;
        font-size: 1.1rem !important;
    }
    button[kind="secondary"] * {
        color: #087f5b !important;
    }
    button[kind="secondary"]:hover {
        border-color: #006E6D !important;
        background-color: #d3f9d8 !important;
    }
    button[kind="secondary"]:hover * {
        color: #087f5b !important;
    }

    /* Global primary buttons (if any) */
    div.stButton > button {
        background-color: #087f5b !important;
        color: #ebfbee !important;
        border-radius: 8px !important;
        border: none !important;
        font-weight: 800 !important;
        font-size: 1.1rem !important;
        padding: 0.6rem 1rem !important;
    }
    div.stButton > button:hover {
        background-color: #006E6D !important;
        color: #ebfbee !important;
    }

    /* Expander styling (for error details, metrics, concepts) */
    details {
        border-radius: 10px;
        border: 2px solid #087f5b;
        background-color: #d3f9d8;
        margin-bottom: 12px;
        transition: all 0.3s ease;
    }
    summary {
        color: #087f5b !important;
        font-weight: 600;
        padding: 0.75rem;
        cursor: pointer;
        font-size: 1.6rem !important;
        border: 1px solid black;
    }
    summary:hover {
        color: #006E6D !important;
    }
    details[open] {
        border-color: #006E6D;
        box-shadow: 0 0 20px rgba(8, 127, 91, 0.25);
    }

    /* Captions / subtle text */
    .stCaption, .stMarkdown small {
        color: #2b8a3e !important;
        font-size: 1rem !important;
    }
    
    /* Metric cards enhancement */
    [data-testid="stMetricValue"] {
        font-size: 2.8rem !important;
        font-weight: 700 !important;
        color: #087f5b !important;
    }
    
    [data-testid="stMetricLabel"] {
        font-size: 1.3rem !important;
        font-weight: 500 !important;
        color: #2b8a3e !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* Server status card */
    .server-card {
        background: linear-gradient(135deg, #d3f9d8 0%, #b2f2bb 100%);
        border: 2px solid #087f5b;
        border-radius: 12px;
        padding: 1.5rem;
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

# Sidebar - shared component
from components.sidebar import render_sidebar
render_sidebar(current_page="dashboard")


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
                    filter_col1, filter_col2 = st.columns(2)
                    
                    with filter_col1:
                        if "file" in df.columns:
                            file_names = sorted(df["file"].dropna().unique())
                            st.markdown("**🔍 Filter by File**")
                            file_choice = st.selectbox(
                                "Select file to analyze",
                                ["All files"] + file_names,
                                help="Filter metrics by specific file"
                            )
                            if file_choice != "All files":
                                df = df[df["file"] == file_choice].copy()
                        else:
                            file_choice = "All files"
                    
                    with filter_col2:
                        if "algo" in df.columns:
                            algos = sorted(df["algo"].dropna().unique())
                            st.markdown("**🔧 Filter by Algorithm**")
                            algo_choice = st.selectbox(
                                "Select algorithm",
                                ["All algorithms"] + algos,
                                help="Filter metrics by congestion control algorithm"
                            )
                            if algo_choice != "All algorithms":
                                df = df[df["algo"] == algo_choice].copy()
                        else:
                            algo_choice = "All algorithms"
                    
                    if file_choice != "All files" or algo_choice != "All algorithms":
                        filter_info = []
                        if file_choice != "All files":
                            filter_info.append(f"File: **{file_choice}**")
                        if algo_choice != "All algorithms":
                            filter_info.append(f"Algorithm: **{algo_choice.upper()}**")
                        st.info(f"📌 Filtered: {', '.join(filter_info)} ({len(df):,} events)")
                    
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
                            
                            # Build title with filters
                            current_algo = df["algo"].iloc[0].upper() if "algo" in df.columns else "TCP"
                            title_parts = [f"RTT Analysis ({current_algo})"]
                            if file_choice != "All files":
                                title_parts.append(file_choice[:30])
                            ax1.set_title(" – ".join(title_parts), fontweight='bold', pad=15)
                            ax1.legend(loc='best', framealpha=0.9, title="Metrics")
                            ax1.grid(True, alpha=0.2, linestyle='--', linewidth=0.5)
                            ax1.spines['top'].set_visible(False)
                            ax1.spines['right'].set_visible(False)
                            plt.tight_layout()
                            st.pyplot(fig1)
                            plt.close(fig1)
                        
                        with col_chart2:
                            st.markdown("**📊 Congestion Window Evolution**")
                            
                            fig2, ax2 = plt.subplots(figsize=(7, 5))
                            current_algo = df["algo"].iloc[0] if "algo" in df.columns else "unknown"
                            algo_label = current_algo.upper()
                            
                            ax2.plot(
                                df["seq"], 
                                df["cwnd"], 
                                marker="o", 
                                markersize=3,
                                color="#10b981" if current_algo == "reno" else "#f59e0b", 
                                alpha=0.8, 
                                label=f"CWND ({algo_label})",
                                linewidth=2
                            )
                            ax2.set_xlabel("Event Sequence", fontweight='bold')
                            ax2.set_ylabel("CWND (segments)", fontweight='bold')
                            
                            # Build title with filters
                            title_parts = [f"{algo_label} Congestion Control"]
                            if file_choice != "All files":
                                title_parts.append(file_choice[:30])
                            ax2.set_title(" – ".join(title_parts), fontweight='bold', pad=15)
                            ax2.grid(True, alpha=0.2, linestyle='--', linewidth=0.5)
                            
                            # Add algorithm behavior note in legend
                            if current_algo == "tahoe":
                                ax2.legend(loc='best', framealpha=0.9, title="Tahoe: cwnd→1 on loss")
                            else:
                                ax2.legend(loc='best', framealpha=0.9, title="Reno: cwnd→ssthresh on loss")
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
                        
                        current_algo = df_plot["algo"].iloc[0] if "algo" in df_plot.columns else "unknown"
                        algo_label = current_algo.upper()
                        
                        # Build comprehensive title
                        title_parts = [f"TCP {algo_label} Congestion Control Dynamics"]
                        if file_choice != "All files":
                            title_parts.append(file_choice[:40])
                        
                        ax3.set_xlabel("Transmission Round", fontsize=13, fontweight='bold')
                        ax3.set_ylabel("Window Size (segments)", fontsize=13, fontweight='bold')
                        ax3.set_title(
                            " – ".join(title_parts), 
                            fontsize=15, 
                            fontweight='bold',
                            pad=20
                        )
                        
                        # Algorithm-specific legend title
                        if current_algo == "tahoe":
                            legend_title = "TAHOE: On loss → cwnd = 1 (restart slow start)"
                        else:
                            legend_title = "RENO: On loss → cwnd = ssthresh (fast recovery)"
                        ax3.legend(loc="best", fontsize=10, framealpha=0.95, edgecolor='#374151', title=legend_title)
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
