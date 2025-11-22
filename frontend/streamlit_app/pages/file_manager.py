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

# ============================================================================
# FILE MANAGER PAGE
# ============================================================================

st.set_page_config(page_title="File Manager - SyncroX", page_icon="📁", layout="wide")

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
    
    if st.button("📁 File Manager", use_container_width=True, disabled=True):
        st.switch_page("pages/file_manager.py")
    
    if st.button("📊 Dashboard", use_container_width=True):
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

st.header("📁 File Manager")
st.caption(f"Room: `{st.session_state.current_room}` • User: `{st.session_state.username}`")

# Initialize session state
if "ft_algo" not in st.session_state:
    st.session_state.ft_algo = "reno"

# Congestion control algorithm selector
col_info, col_algo = st.columns([2, 1])
with col_info:
    st.info("💡 Upload and download files shared within your room")
with col_algo:
    algo = st.radio(
        "Congestion Control",
        ["reno", "tahoe"],
        index=0 if st.session_state.ft_algo == "reno" else 1,
        horizontal=True,
        help="Simulates TCP congestion control algorithms"
    )
    st.session_state.ft_algo = algo

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
            client = TcpFileClient(host="127.0.0.1", port=9010, algo=algo)
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
    client = TcpFileClient(host="127.0.0.1", port=9010, algo=algo)
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
st.caption(
    "💡 Files are scoped to your room. Uses TCP with Tahoe/Reno congestion control simulation."
)
