import os
import sys
import time
import subprocess

from typing import Optional, List

# --- Make project root importable ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import streamlit as st
from streamlit_autorefresh import st_autorefresh

from backend.tcp_chat.streamlit_client import TcpChatClient
from backend.file_transfer.client import TcpFileClient
from backend.collab.client import TcpCollabClient



# ---------------- GLOBAL CONFIG ----------------

st.set_page_config(page_title="SyncroX", page_icon="💬", layout="wide")

if "page" not in st.session_state:
    st.session_state.page = "home"


def go_to(page_name: str):
    st.session_state.page = page_name


# ---------------- CHAT SEND CALLBACK ----------------

def send_chat_message():
    """Callback for the Send button in the chat page."""
    client: Optional[TcpChatClient] = st.session_state.get("chat_client")
    msg: str = st.session_state.get("chat_message", "")

    if client is None:
        st.session_state["chat_status"] = "Not connected to server."
        return

    if not getattr(client, "current_room", None):
        st.session_state["chat_status"] = "You must create or join a room first."
        return

    if not msg.strip():
        st.session_state["chat_status"] = "Cannot send empty message."
        return

    try:
        # Actually send via TCP
        client.send_message(msg.strip())
        # Show your own msg instantly
        st.session_state.chat_log.append(f"YOU: {msg.strip()}")
        # Clear the input safely (inside callback)
        st.session_state.chat_message = ""
        st.session_state["chat_status"] = ""
    except Exception as e:
        st.session_state["chat_status"] = f"Error sending message: {e}"


# ---------------- PAGE COMPONENTS ----------------

def home_page():
    st.title("SyncroX")
    st.subheader("Choose a module")

    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.markdown("### 💬 Chat")
        st.write("Real-time text chat with your lab partners (TCP rooms with 4-digit codes).")
        st.button("Open Chat", use_container_width=True,
                  on_click=go_to, args=("chat",))

        st.markdown("### 🤝 Collab")
        st.write("Live code collaboration & shared editor (coming soon).")
        st.button("Open Collab", use_container_width=True,
                  on_click=go_to, args=("collab",))

    with col2:
        st.markdown("### 📁 File Transfer")
        st.write("Upload, download & share lab files securely (HTTP API, coming soon).")
        st.button("Open File Transfer", use_container_width=True,
                  on_click=go_to, args=("file_transfer",))

        st.markdown("### 📊 Dashboard")
        st.write("View connection status, logs & usage stats (coming soon).")
        st.button("Open Dashboard", use_container_width=True,
                  on_click=go_to, args=("dashboard",))


def collab_page():
    # Auto-refresh every 1 second so remote updates and auto-sync happen
    st_autorefresh(interval=1000, key="collab_refresh")

    st.header("🤝 Collab – TCP Shared Code Editor")

    # --- session state ---
    if "collab_client" not in st.session_state:
        st.session_state.collab_client = None
    if "collab_username" not in st.session_state:
        st.session_state.collab_username = ""
    if "collab_room" not in st.session_state:
        st.session_state.collab_room = ""
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

    client: TcpCollabClient | None = st.session_state.collab_client

    # ---------- FIRST: connect UI ----------
    if client is None:
        st.subheader("Connect to collab server")

        username = st.text_input("Username", key="collab_username")
        room_input = st.text_input(
            "Room code (4 digits, same as chat/file)",
            key="collab_room_input",
            max_chars=4,
        )

        connect_clicked = st.button(
            "Connect to room", type="primary", use_container_width=True
        )

        if connect_clicked:
            if not username.strip():
                st.warning("Enter a username.")
                return
            if not (room_input and len(room_input) == 4 and room_input.isdigit()):
                st.warning("Enter a valid 4-digit room code.")
                return
            try:
                client = TcpCollabClient(
                    host="127.0.0.1", port=9011, username=username.strip()
                )
                client.join_room(room_input.strip())

                # remember room + initialise last_sent
                st.session_state.collab_room = room_input.strip()
                st.session_state.collab_client = client
                st.session_state.collab_status = (
                    f"Connected as {username.strip()} to room {room_input.strip()}."
                )
                st.session_state.collab_last_sent = ""
                st.session_state.collab_last_sent_time = 0.0
            except Exception as e:
                st.error(f"Could not connect to collab server: {e}")
                return

        if st.session_state.collab_status:
            st.info(st.session_state.collab_status)
        return

    # ---------- ALREADY CONNECTED ----------
    client = st.session_state.collab_client
    room = st.session_state.collab_room
    username = st.session_state.collab_username

    top_left, top_right = st.columns([3, 1])
    with top_left:
        st.markdown(f"**User:** `{username}`  •  **Room:** `{room}`")
    with top_right:
        if st.button("Disconnect", use_container_width=True):
            try:
                client.close()
            except Exception:
                pass
            st.session_state.collab_client = None
            st.session_state.collab_editor = ""
            st.session_state.collab_status = "Disconnected from collab server."
            return

    # --- PULL remote updates from server (other users' saves/auto-sync) ---
    new_doc = client.get_latest_doc()
    if new_doc is not None and new_doc != st.session_state.collab_editor:
        st.session_state.collab_editor = new_doc
        # update last_sent so we don't immediately echo back
        st.session_state.collab_last_sent = new_doc

    st.markdown("### Shared code")

    # Language selector (UI only for now)
    st.session_state.collab_language = st.selectbox(
        "Language",
        ["python"],
        index=0,
        key="collab_language_select",
    )

    # Editor – widget state is the source of truth
    code = st.text_area(
        "Code",
        height=350,
        key="collab_editor",
    )

    # ---------- AUTO-SYNC: push local edits every ~1s ----------
    now = time.time()
    if (
        code != st.session_state.collab_last_sent
        and now - st.session_state.collab_last_sent_time > 1.0  # throttle
    ):
        try:
            client.set_code(room, code)
            st.session_state.collab_last_sent = code
            st.session_state.collab_last_sent_time = now
            st.session_state.collab_status = "Synced changes to room."
        except Exception as e:
            st.session_state.collab_status = f"Error syncing: {e}"

    # ---------- Manual Save (still there, for demo) ----------
    col_save1, col_save2, col_save3 = st.columns([1, 1, 3])
    with col_save1:
        if st.button("💾 Save to room", use_container_width=True):
            try:
                client.set_code(room, code)
                st.session_state.collab_last_sent = code
                st.session_state.collab_last_sent_time = time.time()
                st.session_state.collab_status = "Saved code to room (broadcast to others)."
            except Exception as e:
                st.session_state.collab_status = f"Error saving: {e}"

    # ---------- Run button (local exec, same as before) ----------
    with col_save2:
        run_clicked = st.button("▶ Run", use_container_width=True)

    if run_clicked:
        lang = st.session_state.collab_language
        code_to_run = st.session_state.collab_editor

        if lang == "python":
            try:
                import tempfile
                with tempfile.NamedTemporaryFile(
                    "w", suffix=".py", delete=False, encoding="utf-8"
                ) as tf:
                    tf.write(code_to_run)
                    tmp_path = tf.name

                result = subprocess.run(
                    ["python", tmp_path],
                    capture_output=True,
                    text=True,
                    timeout=3,
                )
                output = ""
                if result.stdout:
                    output += result.stdout
                if result.stderr:
                    output += ("\n" if output else "") + result.stderr
                st.session_state.collab_output = output or "[no output]"
            except subprocess.TimeoutExpired:
                st.session_state.collab_output = "[execution timed out]"
            except Exception as e:
                st.session_state.collab_output = f"[error running code] {e}"
        else:
            st.session_state.collab_output = (
                f"Execution for language '{lang}' not implemented yet."
            )

    if st.session_state.collab_status:
        st.info(st.session_state.collab_status)

    st.markdown("### Output")
    st.text_area(
        "Execution output",
        value=st.session_state.collab_output,
        height=160,
        disabled=True,
    )

    st.caption(
        "We use a custom TCP protocol (JOIN / SET / DOC). "
        "Each client auto-sends edits about once per second and pulls updates "
        "from the server every 1.5 seconds, so users in the same room see each "
        "other's code almost live (last writer wins)."
    )








def file_transfer_page():
    
    st.header("📁 File Transfer (TCP, Room-based)")

    # --- session state ---
    if "ft_client" not in st.session_state:
        st.session_state.ft_client = None
    if "ft_status" not in st.session_state:
        st.session_state.ft_status = ""
    if "ft_room" not in st.session_state:
        st.session_state.ft_room = ""

    # --- room selection ---
    st.subheader("Room code")

    room = st.text_input(
        "Enter 4-digit room code (same as your chat room)",
        key="ft_room",
        max_chars=4,
    )

    if not room or len(room) != 4 or not room.isdigit():
        st.warning("Enter a valid 4-digit room code to use file transfer.")
        return

    # --- connect client (once) ---
    if st.session_state.ft_client is None:
        try:
            st.session_state.ft_client = TcpFileClient(host="127.0.0.1", port=9010)
            st.success("Connected to TCP file server.")
        except Exception as e:
            st.error(f"Could not connect to file server: {e}")
            return

    client: TcpFileClient = st.session_state.ft_client

    # ---------- Upload section ----------
    st.subheader(f"Upload files (room {room})")

    uploaded_files = st.file_uploader(
        "Choose file(s) to upload",
        accept_multiple_files=True,
    )

    if st.button("⬆️ Upload selected file(s)", use_container_width=True):
        if not uploaded_files:
            st.warning("Please choose at least one file.")
        else:
            success = 0
            fail = 0
            for uf in uploaded_files:
                data = uf.getvalue()
                resp = client.upload_bytes(room, uf.name, data)
                if resp.startswith("OK"):
                    success += 1
                else:
                    fail += 1
                    st.error(f"Upload failed for {uf.name}: {resp}")
            st.session_state.ft_status = f"Uploaded {success} file(s), {fail} failed."

    if st.session_state.ft_status:
        st.info(st.session_state.ft_status)

    st.divider()

    # ---------- List & download section ----------
    st.subheader(f"Files in room {room}")

    files = client.list_files(room)
    if not files:
        st.info("No files uploaded yet for this room.")
        return

    # Display table-like list
    for name, size, created in files:
        col1, col2, col3, col4 = st.columns([3, 2, 3, 2])
        with col1:
            st.write(name)
        with col2:
            st.write(f"{size/1024:.1f} KB")
        with col3:
            st.write(created)
        with col4:
            if st.button(f"⬇️ Get {name}", key=f"dlbtn_{room}_{name}"):
                data = client.download_bytes(room, name)
                if data is None:
                    st.error(f"Failed to download {name}")
                else:
                    st.session_state["last_download_name"] = name
                    st.session_state["last_download_data"] = data
                    st.experimental_rerun()

    # Show download button if we have a last downloaded file in state
    if "last_download_data" in st.session_state:
        st.success(f"Ready to download: {st.session_state['last_download_name']}")
        st.download_button(
            "Click to save file",
            data=st.session_state["last_download_data"],
            file_name=st.session_state["last_download_name"],
            mime="application/octet-stream",
        )



def dashboard_page():
    st.header("📊 Dashboard")
    st.info("Dashboard coming soon…")


# ---------------- ROUTER ----------------

page = st.session_state.page

if page == "home":
    home_page()
elif page == "chat":
    chat_page()
elif page == "collab":
    collab_page()
elif page == "file_transfer":
    file_transfer_page()
elif page == "dashboard":
    dashboard_page()
