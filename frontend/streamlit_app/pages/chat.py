import os
import sys
from pathlib import Path

# --- Make project root importable ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import streamlit as st
from streamlit_autorefresh import st_autorefresh
from backend.tcp_chat.streamlit_client import TcpChatClient
import time

# ============================================================================
# CHAT PAGE
# ============================================================================

st.set_page_config(page_title="Chat - SyncroX", page_icon="💬", layout="wide")

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
    if st.button("💬 Chat", use_container_width=True, disabled=True):
        st.switch_page("pages/chat.py")
    
    if st.button("🤝 Code Editor", use_container_width=True):
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

# Auto-refresh so new messages appear
st_autorefresh(interval=1000, key="chat_refresh")


def send_chat_message():
    """Callback for the Send button in the chat page."""
    client = st.session_state.get("chat_client")
    msg = st.session_state.get("chat_message", "")

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
        client.send_message(msg.strip())
        # Don't append here - server will echo it back to avoid duplicates
        st.session_state.chat_message = ""
        st.session_state["chat_status"] = ""
    except Exception as e:
        st.session_state["chat_status"] = f"Error sending message: {e}"


# Initialize session state
if "chat_client" not in st.session_state:
    st.session_state.chat_client = None
if "chat_log" not in st.session_state:
    st.session_state.chat_log = []  # List of {"type": "message"|"system", "sender": str, "text": str}
if "chat_status" not in st.session_state:
    st.session_state.chat_status = ""
if "chat_room" not in st.session_state:
    st.session_state.chat_room = ""
if "chat_message" not in st.session_state:
    st.session_state.chat_message = ""

st.header("💬 Real-time Chat")
st.caption(f"Room: `{st.session_state.current_room}` • User: `{st.session_state.username}`")

client = st.session_state.chat_client

# ---------- if NOT connected: show connect UI ----------
if client is None:
    st.info("Connecting to chat server...")
    
    try:
        st.session_state.chat_client = TcpChatClient(
            host="127.0.0.1",
            port=9009,
            username=st.session_state.username,
        )
        # Give server time to respond to HELLO
        time.sleep(0.1)
        
        # Join the room (server will auto-create if doesn't exist)
        st.session_state.chat_client.join_room(st.session_state.current_room)
        
        # Wait for server response
        time.sleep(0.2)
        
        st.session_state.chat_room = st.session_state.current_room
        st.session_state.chat_status = f"Connected to room {st.session_state.current_room}"
        st.rerun()
    except Exception as e:
        st.error(f"Could not connect to chat server: {e}")
        st.stop()

# ---------- already connected ----------
client = st.session_state.chat_client

# Keep track of current room
current_room = getattr(client, "current_room", None)
if current_room and current_room != st.session_state.chat_room:
    st.session_state.chat_room = current_room

# Drain messages from TCP client into chat_log
new_lines = client.get_new_messages()
for line in new_lines:
    if line.startswith("MSG "):
        # Format: "MSG <room> <username>: <message>"
        parts = line.split(maxsplit=2)
        if len(parts) >= 3:
            msg_content = parts[2]  # "username: message"
            if ": " in msg_content:
                sender, text = msg_content.split(": ", 1)
                is_me = (sender == st.session_state.username)
                st.session_state.chat_log.append({
                    "type": "message",
                    "sender": sender,
                    "text": text,
                    "is_me": is_me
                })
    elif line.startswith("SYSTEM "):
        st.session_state.chat_log.append({"type": "system", "text": line[7:]})
    elif line.startswith("ROOM "):
        parts = line.split()
        if len(parts) >= 2:
            st.session_state.chat_log.append({"type": "system", "text": f"✅ Room created: {parts[1]}"})
            client.current_room = parts[1]
    elif line.startswith("OK Joined"):
        parts = line.split()
        if len(parts) >= 3:
            st.session_state.chat_log.append({"type": "system", "text": f"✅ Joined room: {parts[2]}"})
            client.current_room = parts[2]
    elif line.startswith("ROOMS "):
        st.session_state.chat_log.append({"type": "system", "text": f"📋 Available rooms: {line[6:]}"})
    elif line.startswith("ERROR "):
        st.session_state.chat_log.append({"type": "system", "text": f"❌ {line[6:]}"})
    else:
        st.session_state.chat_log.append({"type": "system", "text": line})

# ---------- Chat interface ----------
st.markdown("### Messages")

# Custom CSS for chat bubbles
st.markdown("""
<style>
.chat-message {
    padding: 8px 12px;
    border-radius: 18px;
    margin: 6px 0;
    max-width: 22%;               /* 🔹 Narrower, like Messenger */
    word-wrap: break-word;
    font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    font-size: 0.9rem;
    line-height: 1.4;
}

/* Me (right side – green bubble) */
.message-me {
    margin-left: auto;
    text-align: left;
    background: #00a884;          /* WhatsApp/Messenger style green */
    color: #f9fafb;
    border-bottom-right-radius: 4px;
}

/* Others (left side – dark bubble) */
.message-other {
    margin-right: auto;
    text-align: left;
    background: rgba(32, 44, 51, 0.95);
    color: #e5e7eb;
    border-bottom-left-radius: 4px;
}

/* Sender label */
.message-sender {
    font-size: 0.72rem;
    font-weight: 600;
    opacity: 0.8;
    margin-bottom: 2px;
}

/* Message text */
.message-text {
    font-size: 0.9rem;
    line-height: 1.45;
}

/* System messages (centered, subtle) */
.system-message {
    text-align: center;
    color: #9ca3af;
    font-size: 0.8rem;
    margin: 10px 0;
    font-style: italic;
}
</style>
""", unsafe_allow_html=True)



# Message container with scrollable area
chat_container = st.container(height=450)
with chat_container:
    for msg in st.session_state.chat_log[-100:]:
        if isinstance(msg, dict):
            if msg["type"] == "system":
                st.markdown(f'<div class="system-message">{msg["text"]}</div>', unsafe_allow_html=True)
            elif msg["type"] == "message":
                is_me = msg.get("is_me", False)
                bubble_class = "message-me" if is_me else "message-other"
                sender_name = "You" if is_me else msg["sender"]
                
                st.markdown(f'''
                <div class="chat-message {bubble_class}">
                    <div class="message-sender">{sender_name}</div>
                    <div class="message-text">{msg["text"]}</div>
                </div>
                ''', unsafe_allow_html=True)
        else:
            # Fallback for old format
            st.write(msg)

# Message input
st.text_input(
    "Type your message",
    key="chat_message",
    on_change=send_chat_message,
    placeholder="Type a message and press Enter..."
)

if st.session_state.get("chat_status"):
    st.caption(st.session_state["chat_status"])

st.markdown("---")
st.caption("💡 Messages are synchronized in real-time across all users in this room")
