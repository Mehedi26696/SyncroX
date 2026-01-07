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
from backend.code_exec.exec_history import get_history_manager
from PIL import Image
from config import SERVER_HOST, COLLAB_PORT, EXEC_PORT

# ========================================================================
# COLLABORATIVE CODE EDITOR PAGE
# ========================================================================

# Load custom icon
icon_path = os.path.join(PROJECT_ROOT, "assets", "image.png")
page_icon = Image.open(icon_path) if os.path.exists(icon_path) else "🤝"

st.set_page_config(
    page_title="Collab - SyncroX",
    page_icon=page_icon,
    layout="wide"
)

# ------------------ THEME / CSS ------------------
st.markdown(
    """
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
        color: #087f5b !important;
    }
    
    h1 { font-size: 3rem !important; }
    h2 { font-size: 2.5rem !important; }
    h3 { font-size: 2rem !important; }
    h4 { font-size: 1.5rem !important; }

    p, div, span, label {
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
        color: #ebfbee !important;
        border-radius: 8px !important;
        border: none !important;
        font-weight: 700 !important;
        margin-bottom: 8px !important;
        padding: 0.6rem 1rem !important;
        font-size: 1.1rem !important;
    }
    [data-testid="stSidebar"] button:hover {
        background-color: #006E6D !important;
        color: #ebfbee !important;
    }
    [data-testid="stSidebar"] button[disabled] {
        background-color: #b2f2bb !important;
        color: #087f5b !important;
        opacity: 0.9 !important;
    }

    /* Generic buttons in main area */
    div.stButton > button {
        background-color: #087f5b !important;
        color: #ebfbee !important;
        border-radius: 8px !important;
        border: none !important;
        font-weight: 800 !important;
        padding: 0.6rem 1rem !important;
        font-size: 1.1rem !important;
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

    /* Textareas (editor, stdin, output) */
    .stTextArea textarea {
        background-color: white !important;
        color: #087f5b !important;
        border-radius: 12px !important;
        border: 2px solid #087f5b !important;
        font-family: "JetBrains Mono", "Fira Code", "Source Code Pro", monospace !important;
        font-size: 1rem !important;
    }
    .stTextArea textarea:focus {
        border-color: #006E6D !important;
        box-shadow: 0 0 0 2px #006E6D !important;
        outline: none !important;
    }

    .stCaption, .stMarkdown small {
        color: #2b8a3e !important;
        font-size: 1rem !important;
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

# Sidebar - shared component
from components.sidebar import render_sidebar
render_sidebar(current_page="code_editor")

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
    st.session_state.collab_editor = ""  # Start empty, wait for server doc
if "collab_status" not in st.session_state:
    st.session_state.collab_status = ""
if "collab_language" not in st.session_state:
    st.session_state.collab_language = "python"
if "collab_initialized" not in st.session_state:
    st.session_state.collab_initialized = False  # Track if we've received initial doc from server
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
        collab_client = TcpCollabClient(host=SERVER_HOST, port=COLLAB_PORT, username=username)
        # Join room with current language
        collab_client.join_room(room, st.session_state.collab_language)
        collab_client.request_doc(room, st.session_state.collab_language) # Explicitly request doc to ensure sync
        st.session_state.collab_client = collab_client
        st.session_state.collab_status = f"Connected to room {room} as {username}."
    except Exception as e:
        st.error(f"Could not connect to collab server: {e}")
        st.stop()

# Exec client
if st.session_state.exec_client is None:
    try:
        st.session_state.exec_client = TcpExecClient(host=SERVER_HOST, port=EXEC_PORT)
    except Exception as e:
        st.error(f"Could not connect to exec server: {e}")
        st.stop()

client: TcpCollabClient = st.session_state.collab_client
exec_client: TcpExecClient = st.session_state.exec_client

# ------------------ LIVE SYNC: AUTO-SAVE & PULL UPDATES ------------------

# Get current language
current_lang = st.session_state.collab_language

# Auto-save: ONLY if initialized (received doc from server) and user changed code and 2 seconds passed
now = time.time()
if (st.session_state.collab_initialized and  # Only save after we've received initial doc
    st.session_state.collab_editor != st.session_state.collab_last_sent and 
    st.session_state.collab_editor.strip() != "" and  # Don't save empty content
    now - st.session_state.collab_last_sent_time > 2.0):
    try:
        if client.alive:
            # Send code with language info (no need for metadata in content anymore)
            client.set_code(room, st.session_state.collab_editor, current_lang)
            st.session_state.collab_last_sent = st.session_state.collab_editor
            st.session_state.collab_last_sent_time = now
            st.session_state.collab_status = f"✓ Auto-saved ({current_lang})"
        else:
             st.session_state.collab_status = "⚠️ Connection lost. Please refresh."
    except Exception as e:
        st.session_state.collab_status = f"Auto-save error: {e}"

# Periodically request latest doc from server (every 1.5 seconds) to ensure sync
if "collab_last_poll_time" not in st.session_state:
    st.session_state.collab_last_poll_time = 0.0

if now - st.session_state.collab_last_poll_time > 1.5:
    try:
        if client.alive:
            client.request_doc(room, current_lang)
            st.session_state.collab_last_poll_time = now
    except Exception:
        pass

# Pull updates from server (other users' changes)
doc_update = client.get_latest_doc(for_lang=current_lang)
if doc_update is not None:
    new_doc, update_lang = doc_update
    
    # Only apply if same language as current
    if update_lang == current_lang and new_doc != st.session_state.collab_editor:
        st.session_state.collab_initialized = True  # Mark as initialized - we have real data from server
        st.toast(f"Updated from {client.last_editor}")
        st.session_state.collab_editor = new_doc
        st.session_state.collab_last_sent = new_doc
        st.session_state.collab_status = f"✓ Live update received from {client.last_editor or 'collaborator'}"
        # Force rerun to immediately show the updated code in the text area
        st.rerun()

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
    col_refresh, col_disconnect = st.columns(2)
    with col_refresh:
        if st.button("🔄 Refresh", use_container_width=True, key="refresh_btn"):
            # Request latest doc from server for current language
            try:
                if client.alive:
                    client.request_doc(room, current_lang)
                    st.session_state.collab_status = f"🔄 Refreshing {current_lang}..."
                    st.rerun()
            except Exception as e:
                st.session_state.collab_status = f"Refresh error: {e}"
    with col_disconnect:
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

# Track previous language to detect changes
if "collab_prev_language" not in st.session_state:
    st.session_state.collab_prev_language = st.session_state.collab_language

selected_lang = st.selectbox(
    "Language",
    ["python", "c", "cpp", "java"],
    index=["python", "c", "cpp", "java"].index(st.session_state.collab_language)
    if st.session_state.collab_language in ["python", "c", "cpp", "java"]
    else 0,
    key="collab_language_select",
)

# Check if language changed
if selected_lang != st.session_state.collab_prev_language:
    st.session_state.collab_language = selected_lang
    st.session_state.collab_prev_language = selected_lang
    st.session_state.collab_initialized = False  # Reset initialized flag on language change
    # Request doc for new language from server
    try:
        if client.alive:
            client.request_doc(room, selected_lang)
            st.session_state.collab_status = f"🔄 Loading {selected_lang} code..."
            # Reset editor state to avoid showing old language's code
            st.session_state.collab_last_sent = ""
            st.session_state.collab_last_sent_time = 0.0
            st.rerun()
    except Exception as e:
        st.session_state.collab_status = f"Error loading {selected_lang}: {e}"
else:
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

                    # keep only last 50 runs in session
                    if len(st.session_state.exec_history) > 50:
                        st.session_state.exec_history = st.session_state.exec_history[-50:]

                    # ---- Save to persistent history (room-wise JSON file) ----
                    try:
                        history_manager = get_history_manager()
                        history_manager.add_execution(
                            room=room,
                            user=username,
                            language=lang,
                            code=code_to_run,
                            stdin=stdin_text,
                            stdout=out_text,
                            stderr=err_text,
                            return_code=rc,
                            success=bool(success),
                            time_ms=time_ms,
                        )
                        print(f"[STREAMLIT DEBUG] Saved to persistent history for room {room}")
                    except Exception as hist_err:
                        print(f"[STREAMLIT DEBUG] Error saving to persistent history: {hist_err}")

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
                    
                    # ---- Save error to persistent history ----
                    try:
                        history_manager = get_history_manager()
                        history_manager.add_execution(
                            room=room,
                            user=username,
                            language=lang,
                            code=code_to_run,
                            stdin=stdin_text,
                            stdout="",
                            stderr=str(e),
                            return_code=-1,
                            success=False,
                            time_ms=0,
                        )
                    except Exception as hist_err:
                        print(f"[STREAMLIT DEBUG] Error saving error to persistent history: {hist_err}")
                    
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

