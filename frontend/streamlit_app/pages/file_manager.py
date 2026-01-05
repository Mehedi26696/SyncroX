import os
import sys
from pathlib import Path

# --- Make project root importable ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import streamlit as st
from backend.file_transfer.client import TcpFileClient
from PIL import Image
from config import SERVER_HOST, FILE_PORT

# ============================================================================
# FILE MANAGER PAGE
# ============================================================================

# Load custom icon
icon_path = os.path.join(PROJECT_ROOT, "assets", "image.png")
page_icon = Image.open(icon_path) if os.path.exists(icon_path) else "📁"

st.set_page_config(
    page_title="File Transfer - SyncroX",
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
    }
    
    [data-testid="stSidebar"] {
        background-color: #d3f9d8;
        border-right: 2px solid #087f5b;
    }

    /* Sidebar text colors (match main page) */
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] div,
    [data-testid="stSidebar"] label {
        color: #000000 !important;
    }
    [data-testid="stSidebar"] .stMarkdown {
        color: #000000 !important;
    }
    [data-testid="stSidebar"] [data-testid="stNotificationContentInfo"] {
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

    /* Global buttons */
    div.stButton > button {
        background-color: #087f5b !important;
        color: #ebfbee !important;
        border-radius: 8px !important;
        border: none !important;
        font-weight: 800 !important;
        padding: 0.6rem 1rem !important;
        font-size: 1.3rem !important;
    }
    div.stButton > button * {
        color: #ebfbee !important;
    }
    div.stButton > button:hover {
        background-color: #006E6D !important;
        color: #ebfbee !important;
    }
    div.stButton > button:hover * {
        color: #ebfbee !important;
    }
    
    /* Download button specific */
    div.stDownloadButton > button {
        background-color: #b2f2bb !important;
        color: #087f5b !important;
        border-radius: 8px !important;
        border: 2px solid #087f5b !important;
        font-weight: 800 !important;
        padding: 0.6rem 1rem !important;
        font-size: 1.3rem !important;
    }
    div.stDownloadButton > button * {
        color: #087f5b !important;
    }
    div.stDownloadButton > button:hover {
        background-color: #d3f9d8 !important;
        color: #087f5b !important;
    }
    div.stDownloadButton > button:hover * {
        color: #087f5b !important;
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
        color: #ebfbee !important;
        border-radius: 8px !important;
        border: none !important;
        font-weight: 700 !important;
        margin-bottom: 8px !important;
        font-size: 1.1rem !important;
        padding: 0.6rem 1rem !important;
    }
    [data-testid="stSidebar"] button:hover {
        background-color: #006E6D !important;
        color: #ebfbee !important;
    }

    /* Disabled nav (current page) */
    [data-testid="stSidebar"] button[disabled] {
        background-color: #b2f2bb !important;
        color: #087f5b !important;
        opacity: 0.9 !important;
    }

    /* Logout secondary button (match main page) */
    button[kind="secondary"] {
        background-color: #b2f2bb !important;
        color: #087f5b !important;
        border: 2px solid #087f5b !important;
        font-size: 1.1rem !important;
    }
    button[kind="secondary"]:hover {
        border-color: #006E6D !important;
        background-color: #d3f9d8 !important;
    }

    /* File uploader styling */
    .stFileUploader > div > div {
        background-color: #020617 !important;
        border-radius: 12px !important;
        border: 1px solid #1f2933 !important;
    }
    .stFileUploader label {
        color: #9ca3af !important;
    }

    /* Radio (algorithm selector) */
    .stRadio > label {
        color: #087f5b !important;
        font-weight: 600 !important;
        font-size: 1.4rem !important;
    }

    /* Metrics (Algorithm / etc.) */
    .stMetric {
        background-color: #d3f9d8 !important;
        padding: 18px !important;
        border-radius: 12px !important;
        border: 3px solid #087f5b !important;
        box-shadow: 0 2px 10px rgba(8, 127, 91, 0.25) !important;
    }
    [data-testid="stMetric"] {
        background-color: #d3f9d8 !important;
        padding: 12px !important;
        border-radius: 12px !important;
        border: 2px solid #087f5b !important;
        box-shadow: 0 2px 10px rgba(8, 127, 91, 0.25) !important;
    }
    [data-testid="stMetric"] > div {
        background-color: transparent !important;
    }
    [data-testid="stMetricLabel"] {
        color: #087f5b !important;
        font-weight: 600 !important;
        font-size: 1.2rem !important;
    }
    [data-testid="stMetricValue"] {
        color: #006E6D !important;
        font-weight: 700 !important;
        font-size: 1.8rem !important;
    }

    /* Upload & list sections subtle card feel via headings spacing */
    h2, h3 {
        margin-top: 0.5rem !important;
        margin-bottom: 0.2rem !important;
    }

    /* Expanders for files */
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
render_sidebar(current_page="file_manager")

st.header("File Transfer")
st.caption(f"Room: `{st.session_state.current_room}` • User: `{st.session_state.username}`")

# Initialize session state
if "ft_algo" not in st.session_state:
    st.session_state.ft_algo = "reno"

# Congestion control algorithm selector
col_info, col_algo = st.columns([2, 1])
with col_info:
    st.info("💡 Upload and download files shared within your room")
with col_algo:
    st.session_state.ft_algo = st.radio(
        "Congestion Control",
        ["reno", "tahoe"],
        index=0 if st.session_state.ft_algo == "reno" else 1,
        horizontal=True,
        help="Simulates TCP congestion control algorithms",
        key="algo_radio"
    )

# Use session state value consistently
algo = st.session_state.ft_algo

st.markdown("---")

# ---- Upload section ----
st.subheader("⬆️ Upload File")

upload_col1, upload_col2 = st.columns([3, 1])
with upload_col1:
    up_file = st.file_uploader(
        "Choose a file to upload",
        type=None,
        help="Any file type is supported"
    )
with upload_col2:
    st.metric("Algorithm", algo.upper())

if up_file is not None:
    filename = up_file.name
    file_size = len(up_file.getvalue())
    st.write(f"**File:** {filename}")
    st.write(f"**Size:** {file_size:,} bytes ({file_size/1024:.2f} KB)")
    
    if st.button("⬆️ Upload File", type="primary", use_container_width=True):
        data = up_file.getvalue()
        try:
            client = TcpFileClient(host=SERVER_HOST, port=FILE_PORT, algo=algo)
            with st.spinner(f"Uploading {filename}..."):
                resp = client.upload_bytes(st.session_state.current_room, filename, data)
            client.close()
            
            if resp.startswith("OK"):
                st.success(f"✅ Upload successful: {filename}")
                st.info(
                    f"📊 Metrics logged to `data/metrics/room_{st.session_state.current_room}_file_metrics.csv`"
                )
            else:
                st.error(f"❌ Upload failed: {resp}")
        except Exception as e:
            st.error(f"❌ Upload failed: {e}")

st.markdown("---")

# ---- List & Download section ----
st.subheader("📂 Files in This Room")

try:
    client = TcpFileClient(host=SERVER_HOST, port=FILE_PORT, algo=algo)
    files = client.list_files(st.session_state.current_room)
except Exception as e:
    files = []
    st.error(f"❌ Could not list files: {e}")
    client = None

if files:
    st.write(f"Found **{len(files)}** file(s) in room `{st.session_state.current_room}`")
    
    for name, size, created in files:
        with st.expander(f"📄 {name} ({size:,} bytes)"):
            col_info, col_action = st.columns([3, 1])
            
            with col_info:
                st.write(f"**Size:** {size:,} bytes ({size/1024:.2f} KB)")
                st.write(f"**Created:** {created}")
            
            with col_action:
                if client and st.button(f"⬇️ Download", key=f"dl_{name}", use_container_width=True):
                    try:
                        with st.spinner(f"Downloading {name}..."):
                            data = client.download_bytes(st.session_state.current_room, name)
                        
                        if data is None:
                            st.error("❌ Download failed")
                        else:
                            st.download_button(
                                "💾 Save to Disk",
                                data=data,
                                file_name=name,
                                mime="application/octet-stream",
                                use_container_width=True
                            )
                    except Exception as e:
                        st.error(f"❌ Download failed: {e}")
else:
    st.info("📭 No files in this room yet. Upload a file to get started!")

if client:
    try:
        client.close()
    except Exception:
        pass

st.markdown("---")

