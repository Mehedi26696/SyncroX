import os
import sys
from typing import Optional, List

# --- Make project root importable ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import streamlit as st
from streamlit_autorefresh import st_autorefresh

from backend.tcp_chat.streamlit_client import TcpChatClient

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


def chat_page():
    # Auto-refresh this page every 1500 ms (1.5 seconds)
    st_autorefresh(interval=1500, key="chat_refresh")

    st.header("💬 Chat")

    # Back to home button
    if st.button("⬅ Back to Home", key="chat_back"):
        go_to("home")
        return

    # --- 1. initialize session state variables ---
    if "chat_client" not in st.session_state:
        st.session_state.chat_client = None
    if "chat_log" not in st.session_state:
        st.session_state.chat_log: List[str] = []
    if "chat_status" not in st.session_state:
        st.session_state["chat_status"] = ""

    client: Optional[TcpChatClient] = st.session_state.chat_client

    # --- 2. If not connected, show username + connect form ---
    if client is None:
        st.subheader("Connect to chat server")

        username = st.text_input("Username", key="chat_username")

        col1, col2 = st.columns([1, 1])
        with col1:
            connect_clicked = st.button("Connect", type="primary", use_container_width=True)
        with col2:
            st.caption("Server: 127.0.0.1:9009 (your TCP server)")

        if connect_clicked:
            if not username.strip():
                st.warning("Please enter a username.")
            else:
                try:
                    st.session_state.chat_client = TcpChatClient(
                        host="127.0.0.1",
                        port=9009,
                        username=username.strip(),
                    )
                    st.success("Connected to chat server 🎉")
                    st.session_state.chat_log.append("🛈 Connected to server.")
                    # No need for st.rerun; autorefresh will pick it up
                except Exception as e:
                    st.error(f"Could not connect to server: {e}")
        return

    # --- 3. If connected, drain messages from server into chat_log ---
    client = st.session_state.chat_client
    new_lines = client.get_new_messages()
    if new_lines:
        for line in new_lines:
            # Basic parsing of protocol
            if line.startswith("MSG "):
                # Format: "MSG 1858 username: message"
                parts = line.split(maxsplit=2)
                if len(parts) >= 3:
                    st.session_state.chat_log.append(parts[2])  # "username: message"
            elif line.startswith("SYSTEM "):
                st.session_state.chat_log.append(f"🛈 {line[7:]}")
            elif line.startswith("ROOM "):
                parts = line.split()
                if len(parts) >= 2:
                    st.session_state.chat_log.append(f"✅ Room created: {parts[1]}")
            elif line.startswith("OK Joined"):
                parts = line.split()
                if len(parts) >= 3:
                    st.session_state.chat_log.append(f"✅ Joined room: {parts[2]}")
            elif line.startswith("ROOMS "):
                st.session_state.chat_log.append(f"📋 Available rooms: {line[6:]}")
            elif line.startswith("ERROR "):
                st.session_state.chat_log.append(f"❌ {line[6:]}")
            else:
                # Any other line, just show raw
                st.session_state.chat_log.append(line)

    # --- 4. Show current room status + controls ---
    col_left, col_right = st.columns([2, 1])

    with col_left:
        room_label = client.current_room or "Not joined"
        st.markdown(f"**Current room:** `{room_label}`")

    with col_right:
        if st.button("Disconnect", use_container_width=True):
            try:
                client.close()
            except Exception:
                pass
            st.session_state.chat_client = None
            st.session_state.chat_log = []
            st.info("Disconnected from chat server.")
            return

    st.divider()

    # Room management
    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        if st.button("➕ Create room", use_container_width=True):
            client.create_room()
            st.info("Room creation requested (watch chat log for code).")

    with col2:
        join_code = st.text_input("Join room code", key="join_room_code", max_chars=4)
        if st.button("🔑 Join room", use_container_width=True):
            if not join_code.strip():
                st.warning("Enter a room code to join.")
            else:
                client.join_room(join_code.strip())
                st.info(f"Joining room {join_code.strip()}…")

    with col3:
        if st.button("📋 List rooms", use_container_width=True):
            client.list_rooms()
            st.info("Requested room list (watch chat log).")

    st.divider()

    # --- 5. Show chat log ---
    if st.session_state.chat_log:
        st.text_area(
            "Chat log",
            "\n".join(st.session_state.chat_log),
            height=300,
            disabled=True,
        )
    else:
        st.info("No messages yet. Create or join a room, then send something!")

    # --- 6. Send message UI (with callback) ---
    msg = st.text_input(
        "Type your message",
        key="chat_message",
        placeholder="Hello world"
    )

    send_col1, send_col2 = st.columns([1, 3])
    with send_col1:
        st.button(
            "Send",
            use_container_width=True,
            key="chat_send_btn",
            on_click=send_chat_message,
        )

    status = st.session_state.get("chat_status", "")
    if status:
        st.warning(status)


def collab_page():
    st.header("🤝 Collab")
    st.info("Collab editor coming soon…")


def file_transfer_page():
    st.header("📁 File Transfer")
    st.info("File transfer UI coming soon…")


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
