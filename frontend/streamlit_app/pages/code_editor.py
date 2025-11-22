import os
import sys
import time
from pathlib import Path

# --- Make project root importable ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import streamlit as st
from streamlit_autorefresh import st_autorefresh
from backend.collab.client import TcpCollabClient
from backend.code_exec.client import TcpExecClient

# ============================================================================
# COLLABORATIVE CODE EDITOR PAGE
# ============================================================================

st.set_page_config(page_title="Code Editor - SyncroX", page_icon="🤝", layout="wide")

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
    
    if st.button("🤝 Code Editor", use_container_width=True, disabled=True):
        st.switch_page("pages/code_editor.py")
    
    if st.button("📁 File Manager", use_container_width=True):
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

# Auto-refresh every 0.5 seconds for remote updates
st_autorefresh(interval=500, key="collab_refresh")

# Initialize session state
if "collab_client" not in st.session_state:
    st.session_state.collab_client = None
if "collab_editor" not in st.session_state:
    st.session_state.collab_editor = ""
if "collab_status" not in st.session_state:
    st.session_state.collab_status = ""
if "collab_language" not in st.session_state:
    st.session_state.collab_language = "python"
if "collab_output" not in st.session_state:
    st.session_state.collab_output = ""
if "collab_last_sent" not in st.session_state:
    st.session_state.collab_last_sent = ""
if "collab_last_sent_time" not in st.session_state:
    st.session_state.collab_last_sent_time = 0.0
if "collab_users" not in st.session_state:
    st.session_state.collab_users = []
if "collab_users_last_request" not in st.session_state:
    st.session_state.collab_users_last_request = 0.0
if "collab_stdin" not in st.session_state:
    st.session_state.collab_stdin = ""
if "exec_client" not in st.session_state:
    st.session_state.exec_client = None

st.header("🤝 Collaborative Code Editor")
st.caption(f"Room: `{st.session_state.current_room}` • User: `{st.session_state.username}`")

client = st.session_state.collab_client

# ---------- Connect to collab and exec servers ----------
if client is None:
    st.info("Connecting to collaboration server...")
    
    try:
        client = TcpCollabClient(
            host="127.0.0.1", port=9011, username=st.session_state.username
        )
        client.join_room(st.session_state.current_room)
        
        st.session_state.collab_client = client
        st.session_state.collab_status = f"Connected to room {st.session_state.current_room}"
        st.session_state.collab_last_sent = ""
        st.session_state.collab_last_sent_time = 0.0
        
        # Connect exec client
        st.session_state.exec_client = TcpExecClient(host="127.0.0.1", port=9012)
        st.rerun()
    except Exception as e:
        st.error(f"Could not connect to collab/exec server: {e}")
        st.stop()

# ---------- ALREADY CONNECTED ----------
client = st.session_state.collab_client

# Pull document updates from server
new_doc = client.get_latest_doc()
if new_doc is not None and new_doc != st.session_state.collab_editor:
    st.session_state.collab_editor = new_doc
    st.session_state.collab_last_sent = new_doc

# Request / read active users list
now = time.time()
if now - st.session_state.collab_users_last_request > 2.0:
    client.request_users(st.session_state.current_room)
    st.session_state.collab_users_last_request = now

users_update = client.get_latest_users()
if users_update is not None:
    st.session_state.collab_users = users_update

# Show last editor + active users
if getattr(client, "last_editor", None):
    st.caption(f"Last update from **{client.last_editor}**")

if st.session_state.collab_users:
    labels = [f"{name} ({status})" for name, status in st.session_state.collab_users]
    st.caption("Active users: " + ", ".join(labels))

st.markdown("### Shared Code")

# Language selector
st.session_state.collab_language = st.selectbox(
    "Language",
    ["python", "c", "cpp", "java"],
    key="collab_language_select",
)

# Editor
code = st.text_area(
    "Code",
    height=350,
    key="collab_editor",
    help="Code is automatically synced across all users in this room"
)

# Optional stdin
stdin_text = st.text_area(
    "Program input (stdin)",
    height=80,
    key="collab_stdin",
    help="This text will be sent to the program's standard input",
)

# ---------- AUTO-SYNC: push local edits every ~1s ----------
now = time.time()
if (
    code != st.session_state.collab_last_sent
    and now - st.session_state.collab_last_sent_time > 1.0
):
    try:
        client.set_code(st.session_state.current_room, code)
        st.session_state.collab_last_sent = code
        st.session_state.collab_last_sent_time = now
        st.session_state.collab_status = "✅ Synced changes to room"
    except Exception as e:
        st.session_state.collab_status = f"❌ Error syncing: {e}"

# ---------- Manual Save + Run ----------
col_save1, col_save2 = st.columns([1, 1])
with col_save1:
    if st.button("💾 Save to Room", use_container_width=True):
        try:
            client.set_code(st.session_state.current_room, code)
            st.session_state.collab_last_sent = code
            st.session_state.collab_last_sent_time = time.time()
            st.success("✅ Code saved and broadcast to all users")
        except Exception as e:
            st.error(f"❌ Error saving: {e}")

with col_save2:
    run_clicked = st.button("▶ Run Code", use_container_width=True, type="primary")

if run_clicked:
    lang = st.session_state.collab_language
    code_to_run = st.session_state.collab_editor
    
    exec_client = st.session_state.exec_client
    if exec_client is None:
        st.error("❌ Exec server not connected")
    else:
        with st.spinner(f"🔄 Running {lang} code..."):
            try:
                success, out_text, err_text, rc, time_ms = exec_client.execute(
                    room=st.session_state.current_room,
                    language=lang,
                    code=code_to_run,
                    stdin_text=stdin_text,
                )

                output = f"[language={lang}, return_code={rc}, time={time_ms} ms, success={success}]\n\n"
                if out_text:
                    output += out_text
                if err_text:
                    if output and not output.endswith("\n"):
                        output += "\n"
                    output += err_text

                st.session_state.collab_output = output
                
                # Display immediately
                st.success(f"✅ Execution completed in {time_ms}ms")
                if out_text:
                    st.code(out_text, language=None)
                if err_text:
                    st.error(err_text)
                    
            except Exception as e:
                st.session_state.collab_output = f"[exception] {repr(e)}"
                st.error(f"❌ Exception: {repr(e)}")

if st.session_state.collab_status:
    st.info(st.session_state.collab_status)

st.markdown("### Output")

st.text_area(
    "Execution output",
    value=st.session_state.collab_output,
    height=180,
    disabled=True,
)

st.markdown("---")
st.caption(
    "💡 Code is synced in real-time. Supports Python, C, C++, and Java execution in Docker sandbox."
)
