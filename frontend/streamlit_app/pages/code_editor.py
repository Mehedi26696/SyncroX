import os
import sys
import time
import json
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
from PIL import Image

# ========================================================================
# COLLABORATIVE CODE EDITOR PAGE
# ========================================================================

# Load custom icon
icon_path = os.path.join(PROJECT_ROOT, "assets", "image.png")
page_icon = Image.open(icon_path) if os.path.exists(icon_path) else "🤝"

st.set_page_config(
    page_title="Collab - SyncroX",
    page_icon=page_icon,
    layout="wide",
)

# ------------------ THEME / CSS ------------------
st.markdown(
    """
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
        color: #f9fafb !important;
    }

    p, div, span, label {
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
    [data-testid="stSidebar"] button[disabled] {
        background-color: #064e3b !important;
        color: #9ca3af !important;
        opacity: 0.9 !important;
    }

    /* Generic buttons in main area */
    div.stButton > button {
        background-color: #03C084 !important;
        color: #020617 !important;
        border-radius: 8px !important;
        border: none !important;
        font-weight: 800 !important;
        padding: 0.4rem 0.8rem !important;
    }
    div.stButton > button:hover {
        background-color: #02a673 !important;
        color: #f9fafb !important;
    }

    /* Textareas (editor, stdin, output) */
    .stTextArea textarea {
        background-color: #020617 !important;
        color: #e5e7eb !important;
        border-radius: 12px !important;
        border: 1px solid #1f2933 !important;
        font-family: "JetBrains Mono", "Fira Code", "Source Code Pro", monospace !important;
        font-size: 0.9rem !important;
    }
    .stTextArea textarea:focus {
        border-color: #03C084 !important;
        box-shadow: 0 0 0 1px #03C084 !important;
        outline: none !important;
    }

    .stCaption, .stMarkdown small {
        color: #9ca3af !important;
    }
</style>
""",
    unsafe_allow_html=True,
)

# ------------------ AUTH / NAV ------------------

# Check if user is logged in
if not st.session_state.get("is_logged_in", False):
    st.error("⚠️ Please login first!")
    if st.button("Go to Home"):
        st.switch_page("app.py")
    st.stop()

room = st.session_state.current_room
username = st.session_state.username

# Sidebar - User info and navigation
with st.sidebar:
    st.markdown("### 👤 User Information")
    st.info(f"**Name:** {username}\n\n**Room:** `{room}`")

    st.markdown("---")
    st.markdown("### 🧭 Navigation")
    st.caption("Select a feature below:")

    if st.button("💬 Chat", use_container_width=True):
        st.switch_page("pages/chat.py")

    if st.button("🤝 Code Editor", use_container_width=True, disabled=True):
        st.switch_page("pages/code_editor.py")

    if st.button("📁 File Manager", use_container_width=True):
        st.switch_page("pages/file_manager.py")

    if st.button("📊 Dashboard", use_container_width=True):
        st.switch_page("pages/dashboard_page.py")

    if st.button("📜 Execution Output", use_container_width=True):
        st.switch_page("pages/exec_output.py")

    st.markdown("---")
    if st.button("🚪 Leave Room & Logout", use_container_width=True, type="secondary"):
        st.session_state.is_logged_in = False
        st.session_state.username = ""
        st.session_state.current_room = ""
        # Clear all TCP clients from state
        for key in list(st.session_state.keys()):
            if key.endswith("_client"):
                st.session_state.pop(key)
        st.switch_page("app.py")

# ------------------ SESSION STATE ------------------

# Auto-refresh every 1 second for live editing (but not during/after execution)
time_since_exec = time.time() - st.session_state.get("last_execution_time", 0)
is_executing = st.session_state.get("is_executing", False)

# Only auto-refresh if not executing and at least 3 seconds since last execution
if not is_executing and time_since_exec > 3.0:
    st_autorefresh(interval=1000, key="collab_refresh")

if "collab_client" not in st.session_state:
    st.session_state.collab_client = None
if "collab_username" not in st.session_state:
    st.session_state.collab_username = username
if "collab_editor" not in st.session_state:
    st.session_state.collab_editor = "# Welcome to collaborative coding!\n# Start writing your code here..."
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
if "last_exec_lang" not in st.session_state:
    st.session_state.last_exec_lang = None
if "last_exec_time" not in st.session_state:
    st.session_state.last_exec_time = None
if "exec_history" not in st.session_state:
    # list of dicts, each is one execution record
    st.session_state.exec_history = []
if "last_execution_time" not in st.session_state:
    st.session_state.last_execution_time = 0
if "is_executing" not in st.session_state:
    st.session_state.is_executing = False
if "last_run_click_time" not in st.session_state:
    st.session_state.last_run_click_time = 0

# ------------------ CONNECT CLIENTS ------------------

# Collab client
if st.session_state.collab_client is not None and not st.session_state.collab_client.alive:
    st.session_state.collab_client = None

if st.session_state.collab_client is None:
    try:
        collab_client = TcpCollabClient(host="127.0.0.1", port=9011, username=username)
        collab_client.join_room(room)
        collab_client.request_doc(room) # Explicitly request doc to ensure sync
        st.session_state.collab_client = collab_client
        st.session_state.collab_status = f"Connected to room {room} as {username}."
    except Exception as e:
        st.error(f"Could not connect to collab server: {e}")
        st.stop()

# Exec client
if st.session_state.exec_client is None:
    try:
        st.session_state.exec_client = TcpExecClient(host="127.0.0.1", port=9012)
    except Exception as e:
        st.error(f"Could not connect to exec server: {e}")
        st.stop()

client: TcpCollabClient = st.session_state.collab_client
exec_client: TcpExecClient = st.session_state.exec_client

# ------------------ LIVE SYNC: AUTO-SAVE & PULL UPDATES ------------------

# Auto-save: if user changed code and 2 seconds passed, broadcast it
now = time.time()
if (st.session_state.collab_editor != st.session_state.collab_last_sent and 
    now - st.session_state.collab_last_sent_time > 2.0):
    try:
        # Save language metadata in first line as comment
        lang_meta = f"//LANG:{st.session_state.collab_language}\n"
        code_with_meta = lang_meta + st.session_state.collab_editor
        
        if client.alive:
            client.set_code(room, code_with_meta)
            st.session_state.collab_last_sent = st.session_state.collab_editor
            st.session_state.collab_last_sent_time = now
            st.session_state.collab_status = "✓ Auto-saved (live sync active)"
        else:
             st.session_state.collab_status = "⚠️ Connection lost. Please refresh."
    except Exception as e:
        st.session_state.collab_status = f"Auto-save error: {e}"

# Pull updates from server (other users' changes)
new_doc = client.get_latest_doc()
if new_doc is not None:
    # Extract language metadata if present
    if new_doc.startswith("//LANG:"):
        lines = new_doc.split("\n", 1)
        lang_line = lines[0]
        actual_code = lines[1] if len(lines) > 1 else ""
        
        # Extract language from metadata
        lang = lang_line.replace("//LANG:", "").strip()
        if lang in ["python", "c", "cpp", "java"]:
            st.session_state.collab_language = lang
        
        new_doc = actual_code
    
    if new_doc != st.session_state.collab_editor:
        st.toast(f"Updated from {client.last_editor}")
        st.session_state.collab_editor = new_doc
        st.session_state.collab_last_sent = new_doc
        st.session_state.collab_status = f"✓ Live update received from {client.last_editor or 'collaborator'}"

# Active users (if supported by your client)
if hasattr(client, "request_users") and hasattr(client, "get_latest_users"):
    now = time.time()
    if now - st.session_state.collab_users_last_request > 2.0:
        client.request_users(room)
        st.session_state.collab_users_last_request = now

    users_update = client.get_latest_users()
    if users_update is not None:
        st.session_state.collab_users = users_update

# ------------------ PAGE HEADER ------------------

st.header("🤝 Collab – Live Code Editor")

top_left, top_right = st.columns([3, 1])
with top_left:
    st.markdown(f"**User:** `{username}` • **Room:** `{room}` • 🟢 **LIVE EDITING**")
    if hasattr(client, "last_editor") and getattr(client, "last_editor"):
        st.caption(f"Last update from **{client.last_editor}** at {time.strftime('%H:%M:%S')}")

    if st.session_state.collab_users:
        labels = [f"{name} ({status})" for name, status in st.session_state.collab_users]
        st.caption("👥 Active users: " + ", ".join(labels))
    
    # Show typing indicator
    time_since_last_edit = now - st.session_state.collab_last_sent_time
    if time_since_last_edit < 2.0 and st.session_state.collab_editor != st.session_state.collab_last_sent:
        st.caption("⌨️ You are typing... (will auto-save in 2s)")

with top_right:
    if st.button("Disconnect", use_container_width=True):
        try:
            client.close()
        except Exception:
            pass
        st.session_state.collab_client = None
        st.session_state.exec_client = None
        st.session_state.collab_status = "Disconnected from collab server."
        st.stop()

if st.session_state.collab_status:
    st.info(st.session_state.collab_status)

st.markdown("### Shared code")

# ------------------ LANGUAGE SELECTOR ------------------

selected_lang = st.selectbox(
    "Language",
    ["python", "c", "cpp", "java"],
    index=["python", "c", "cpp", "java"].index(st.session_state.collab_language)
    if st.session_state.collab_language in ["python", "c", "cpp", "java"]
    else 0,
    key="collab_language_select",
)
st.session_state.collab_language = selected_lang

# ------------------ EDITOR & STDIN ------------------

code_text = st.text_area(
    "Code",
    height=350,
    key="collab_editor",
)

stdin_text = st.text_area(
    "Program input (stdin)",
    height=100,
    key="collab_stdin",
)

# ------------------ RUN / HISTORY BUTTONS (auto-save is automatic) ------------------

col_btn1, col_btn2 = st.columns([1, 1])

with col_btn1:
    run_clicked = st.button("▶ Run Code", use_container_width=True, key="run_code_btn")

with col_btn2:
    if st.button("📜 View Exec History", use_container_width=True):
        st.switch_page("pages/exec_output.py")

# ------------------ HANDLE EXECUTION ------------------

if run_clicked:
    # Debounce: prevent execution if clicked within last 2 seconds
    time_since_last_click = time.time() - st.session_state.last_run_click_time
    if time_since_last_click < 2.0:
        st.warning("⏱️ Please wait, execution is in progress...")
    else:
        st.session_state.last_run_click_time = time.time()
        st.session_state.is_executing = True
        st.session_state.last_execution_time = time.time()
        
        lang = st.session_state.collab_language
        code_to_run = st.session_state.collab_editor

        if exec_client is None:
            st.error("❌ Exec server not connected")
            st.session_state.is_executing = False
        else:
            with st.spinner(f"🔄 Running {lang} code..."):
                try:
                    success, out_text, err_text, rc, time_ms = exec_client.execute(
                        room=room,
                        language=lang,
                        code=code_to_run,
                        stdin_text=stdin_text,
                    )
                    print(f"[STREAMLIT DEBUG] exec returned: success={success}, rc={rc}, time={time_ms}ms")
                    
                    st.session_state.last_exec_lang = lang
                    st.session_state.last_exec_time = time.strftime("%H:%M:%S")

                    meta = f"[language={lang}, return_code={rc}, time={time_ms} ms, success={success}]"
                    parts = [meta]
                    if out_text:
                        parts.append(out_text.rstrip("\n"))
                    if err_text:
                        parts.append("[stderr]")
                        parts.append(err_text.rstrip("\n"))

                    st.session_state.collab_output = "\n".join(parts) or "[no output]"

                    # Save output to file for reliable display
                    output_dir = os.path.join(PROJECT_ROOT, "data", "exec_output")
                    os.makedirs(output_dir, exist_ok=True)
                    output_file = os.path.join(output_dir, f"room_{room}_latest.json")
                    output_data = {
                        "timestamp": time.time(),
                        "language": lang,
                        "success": bool(success),
                        "return_code": rc,
                        "time_ms": time_ms,
                        "stdout": out_text,
                        "stderr": err_text,
                        "formatted_output": st.session_state.collab_output
                    }
                    with open(output_file, "w", encoding="utf-8") as f:
                        json.dump(output_data, f, indent=2)
                    print(f"[STREAMLIT DEBUG] Output saved to {output_file}")

                    # ---- store execution in per-session history ----
                    record = {
                        "timestamp": time.time(),
                        "room": room,
                        "user": username,
                        "language": lang,
                        "code": code_to_run,
                        "stdin": stdin_text,
                        "stdout": out_text,
                        "stderr": err_text,
                        "return_code": rc,
                        "success": bool(success),
                        "time_ms": time_ms,
                    }
                    if "exec_history" not in st.session_state:
                        st.session_state.exec_history = []
                    st.session_state.exec_history.append(record)

                    # keep only last 50 runs
                    if len(st.session_state.exec_history) > 50:
                        st.session_state.exec_history = st.session_state.exec_history[-50:]

                    print(f"[STREAMLIT DEBUG] Added to exec_history. Total records: {len(st.session_state.exec_history)}")
                    
                    # Clear execution flag
                    st.session_state.is_executing = False
                    
                    # Show success/failure status based on actual result
                    if success and rc == 0:
                        st.success(f"✅ Execution completed successfully in {time_ms} ms")
                    elif not success or rc != 0:
                        st.error(f"❌ Execution failed (RC={rc}) in {time_ms} ms")
                    else:
                        st.warning(f"⚠️ Execution completed with return code {rc} in {time_ms} ms")

                except Exception as e:
                    msg = f"[error executing {lang}] {e}"
                    st.session_state.collab_output = msg

                    # Save error to file
                    output_dir = os.path.join(PROJECT_ROOT, "data", "exec_output")
                    os.makedirs(output_dir, exist_ok=True)
                    output_file = os.path.join(output_dir, f"room_{room}_latest.json")
                    output_data = {
                        "timestamp": time.time(),
                        "language": lang,
                        "success": False,
                        "return_code": -1,
                        "time_ms": 0,
                        "stdout": "",
                        "stderr": str(e),
                        "formatted_output": msg
                    }
                    with open(output_file, "w", encoding="utf-8") as f:
                        json.dump(output_data, f, indent=2)

                    if "exec_history" not in st.session_state:
                        st.session_state.exec_history = []
                    st.session_state.exec_history.append({
                        "timestamp": time.time(),
                        "room": room,
                        "user": username,
                        "language": lang,
                        "code": code_to_run,
                        "stdin": stdin_text,
                        "stdout": "",
                        "stderr": str(e),
                        "return_code": -1,
                        "success": False,
                        "time_ms": 0,
                    })
                    print(f"[STREAMLIT DEBUG] Exception logged to exec_history. Total: {len(st.session_state.exec_history)}")
                    st.session_state.is_executing = False
                    st.error(f"❌ Exception: {e}")

# ------------------ OUTPUT (placed after execution to show fresh results) ------------------

st.markdown("### Output")

# Read output from file for reliable display
output_dir = os.path.join(PROJECT_ROOT, "data", "exec_output")
output_file = os.path.join(output_dir, f"room_{room}_latest.json")

display_output = st.session_state.collab_output
if os.path.exists(output_file):
    try:
        with open(output_file, "r", encoding="utf-8") as f:
            output_data = json.load(f)
            display_output = output_data.get("formatted_output", st.session_state.collab_output)
            
            # Show metadata
            if output_data.get("timestamp", 0) > 0:
                time_str = time.strftime("%H:%M:%S", time.localtime(output_data["timestamp"]))
                st.caption(f"Last execution: {time_str} | Language: {output_data.get('language', 'unknown')} | Time: {output_data.get('time_ms', 0)}ms")
    except Exception as e:
        print(f"[STREAMLIT DEBUG] Error reading output file: {e}")
        display_output = st.session_state.collab_output

# Use unique key based on file modification time
output_key = f"exec_output_{os.path.getmtime(output_file) if os.path.exists(output_file) else 0}"
st.text_area(
    "Execution output",
    value=display_output,
    height=180,
    disabled=True,
    key=output_key,
)

st.markdown("---")
st.caption(
    "💡 **Live editing enabled**: Your changes auto-save every 2 seconds. Others' edits appear automatically every second. "
    "Code execution uses a separate TCP exec server with Docker sandboxing (Python, C, C++, Java)."
)
