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
from PIL import Image
from config import SERVER_HOST, CHAT_PORT
import base64
import io

# ============================================================================
# CHAT PAGE
# ============================================================================

# Load custom icon
icon_path = os.path.join(PROJECT_ROOT, "assets", "image.png")
page_icon = Image.open(icon_path) if os.path.exists(icon_path) else "💬"

st.set_page_config(page_title="Chat - SyncroX", page_icon=page_icon, layout="wide")

# Apply custom CSS for Raleway font and black background + SyncroX theme
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
        border-right: 1px solid rgba(3, 192, 132, 0.25);
    }
    
    h1, h2, h3, h4, h5, h6, p, div, span, label, button {
        font-family: 'Raleway', sans-serif !important;
        color: #f9fafb;
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

    /* Global buttons (SyncroX green) */
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

    /* Sidebar-specific buttons */
    [data-testid="stSidebar"] button {
        background-color: #03C084 !important;
        color: #020617 !important;
        border-radius: 8px !important;
        border: none !important;
        font-weight: 700 !important;
        margin-bottom: 8px !important;
    }
    [data-testid="stSidebar"] button:hover {
        background-color: #02a673 !important;
        color: #f9fafb !important;
    }

    /* Disabled nav button (current page) */
    [data-testid="stSidebar"] button[disabled] {
        background-color: #064e3b !important;
        color: #9ca3af !important;
        opacity: 0.9 !important;
    }

    /* Logout secondary button */
    button[kind="secondary"] {
        background-color: #111827 !important;
        color: #e5e7eb !important;
        border: 1px solid #374151 !important;
    }
    button[kind="secondary"]:hover {
        border-color: #03C084 !important;
        background-color: #1f2933 !important;
    }

    /* Text input styling (chat box) */
    .stTextInput>div>div>input {
        background-color: #020617 !important;
        color: #e5e7eb !important;
        border-radius: 999px !important;
        border: 1px solid #1f2933 !important;
        padding: 0.4rem 0.9rem !important;
    }
    .stTextInput>div>div>input:focus {
        border-color: #03C084 !important;
        box-shadow: 0 0 0 1px #03C084 !important;
        outline: none !important;
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


def add_emoji(emoji: str):
    """Helper to append emoji to the text input."""
    current = st.session_state.get("chat_message", "")
    st.session_state.chat_message = current + emoji


def handle_image_upload():
    """Callback for image uploader."""
    uploaded_file = st.session_state.get("chat_image_upload")
    client = st.session_state.get("chat_client")
    
    if uploaded_file is not None and client:
        try:
            bytes_data = uploaded_file.getvalue()
            b64_str = base64.b64encode(bytes_data).decode("utf-8")
            client.send_image(b64_str)
            st.session_state["chat_status"] = "Image sent!"
            # Clear uploader (trick: usage of key with unique ID or just notify user)
        except Exception as e:
            st.session_state["chat_status"] = f"Error sending image: {e}"


# Initialize session state
if "chat_client" not in st.session_state:
    st.session_state.chat_client = None
if "chat_log" not in st.session_state:
    st.session_state.chat_log = []  # List of {"type": "message"|"system", "sender": str, "text": str, "msg_id": int}
if "chat_status" not in st.session_state:
    st.session_state.chat_status = ""
if "chat_room" not in st.session_state:
    st.session_state.chat_room = ""
if "chat_message" not in st.session_state:
    st.session_state.chat_message = ""
if "chat_history_buffer" not in st.session_state:
    st.session_state.chat_history_buffer = []
if "chat_history_loaded" not in st.session_state:
    st.session_state.chat_history_loaded = False
if "chat_history_loading" not in st.session_state:
    st.session_state.chat_history_loading = False
if "chat_seen_messages" not in st.session_state:
    st.session_state.chat_seen_messages = set()  # Track seen message hashes to prevent duplicates
if "chat_current_user" not in st.session_state:
    st.session_state.chat_current_user = ""
if "chat_seen_by" not in st.session_state:
    st.session_state.chat_seen_by = {}  # msg_id -> list of usernames who have seen it
if "chat_pending_seen" not in st.session_state:
    st.session_state.chat_pending_seen = set()  # msg_ids to mark as seen

# Reset chat state if user or room changed (e.g., after logout/login)
if st.session_state.chat_current_user != st.session_state.username or st.session_state.chat_room != st.session_state.current_room:
    # User or room changed - reset all chat state
    if st.session_state.chat_client:
        try:
            st.session_state.chat_client.close()
        except:
            pass
    st.session_state.chat_client = None
    st.session_state.chat_log = []
    st.session_state.chat_seen_messages = set()
    st.session_state.chat_history_buffer = []
    st.session_state.chat_history_loaded = False
    st.session_state.chat_current_user = st.session_state.username
    st.session_state.chat_room = ""
    st.session_state.chat_seen_by = {}
    st.session_state.chat_pending_seen = set()

st.header("Real-time Chat")
st.caption(f"Room: `{st.session_state.current_room}` • User: `{st.session_state.username}`")

client = st.session_state.chat_client

# ---------- if NOT connected: show connect UI ----------
if client is None:
    st.info("Connecting to chat server...")
    
    try:
        st.session_state.chat_client = TcpChatClient(
            host=SERVER_HOST,
            port=CHAT_PORT,
            username=st.session_state.username,
        )
        # Give server time to respond to HELLO
        time.sleep(0.1)
        
        # Join the room (server will auto-create if doesn't exist)
        st.session_state.chat_client.join_room(st.session_state.current_room)
        
        # Set current_room immediately (don't wait for server response)
        st.session_state.chat_client.current_room = st.session_state.current_room
        
        # Wait for server response
        time.sleep(0.2)
        
        # Request chat history for this room (only if not already loaded)
        if not st.session_state.chat_history_loaded:
            st.session_state.chat_client.request_history(50)
        
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
current_user = st.session_state.username.strip().lower()
import hashlib

for line in new_lines:
    if line.startswith("MSG "):
        # Format: "MSG <room> <msg_id> <username>: <message>"
        parts = line.split(maxsplit=3)
        if len(parts) >= 4:
            msg_id = int(parts[2])
            msg_content = parts[3]  # "username: message"
            if ": " in msg_content:
                sender, text = msg_content.split(": ", 1)
                sender = sender.strip()
                text = text.strip()  # Normalize text
                is_me = (sender.lower() == current_user)
                
                # Create a unique hash to prevent duplicates (use normalized content)
                msg_hash = hashlib.md5(f"{sender.lower()}:{text}".encode()).hexdigest()[:16]
                if msg_hash not in st.session_state.chat_seen_messages:
                    st.session_state.chat_seen_messages.add(msg_hash)
                    st.session_state.chat_log.append({
                        "type": "message",
                        "sender": sender,
                        "text": text,
                        "is_me": is_me,
                        "msg_id": msg_id
                    })
                    # Mark for seen (if not our own message)
                    if not is_me:
                        st.session_state.chat_pending_seen.add(msg_id)
                    # Initialize seen_by for this message
                    if msg_id not in st.session_state.chat_seen_by:
                        st.session_state.chat_seen_by[msg_id] = [sender] if is_me else []
                        
    elif line.startswith("IMG "):
        # Format: "IMG <room> <msg_id> <username> <base64>"
        parts = line.split(maxsplit=4)
        if len(parts) >= 5:
            msg_id = int(parts[2])
            sender = parts[3].strip()
            img_data = parts[4].strip()
            is_me = (sender.lower() == current_user)
            
            # Create a unique hash to prevent duplicates (use normalized content)
            img_hash = hashlib.md5(f"img:{sender.lower()}:{img_data[:100]}".encode()).hexdigest()[:16]
            if img_hash not in st.session_state.chat_seen_messages:
                st.session_state.chat_seen_messages.add(img_hash)
                st.session_state.chat_log.append({
                    "type": "image",
                    "sender": sender,
                    "data": img_data,
                    "is_me": is_me,
                    "msg_id": msg_id
                })
                # Mark for seen (if not our own message)
                if not is_me:
                    st.session_state.chat_pending_seen.add(msg_id)
                # Initialize seen_by for this message
                if msg_id not in st.session_state.chat_seen_by:
                    st.session_state.chat_seen_by[msg_id] = [sender] if is_me else []
    
    elif line.startswith("SEEN_BY "):
        # Format: "SEEN_BY <room> <msg_id> <user1,user2,...>"
        parts = line.split(maxsplit=3)
        if len(parts) >= 4:
            msg_id = int(parts[2])
            seen_users = parts[3].split(",")
            st.session_state.chat_seen_by[msg_id] = seen_users
    
    elif line.startswith("HISTORY "):
        # Format: "HISTORY <room> <count>" - marks start of history
        st.session_state.chat_history_loading = True
        st.session_state.chat_history_buffer = []
    
    elif line.startswith("HIST "):
        # Format: "HIST <type> <timestamp> <sender> <content>"
        # Note: timestamp has _ instead of space (e.g., 2026-01-05_12:30:45)
        parts = line.split(maxsplit=4)
        if len(parts) >= 5:
            msg_type = parts[1]  # text, image, system
            timestamp = parts[2].replace("_", " ")  # Restore space in timestamp
            sender = parts[3].strip()
            content = parts[4].strip()  # Normalize content
            
            # Case-insensitive comparison for is_me check
            is_me = (sender.lower() == current_user)
            
            # Add to seen messages to prevent duplicates with real-time messages (use normalized content)
            if msg_type == "image":
                hist_hash = hashlib.md5(f"img:{sender.lower()}:{content[:100]}".encode()).hexdigest()[:16]
            else:
                hist_hash = hashlib.md5(f"{sender.lower()}:{content}".encode()).hexdigest()[:16]
            st.session_state.chat_seen_messages.add(hist_hash)
            
            if msg_type == "system":
                st.session_state.chat_history_buffer.append({
                    "type": "system",
                    "text": f"[{timestamp}] {content}",
                    "is_history": True
                })
            elif msg_type == "image":
                st.session_state.chat_history_buffer.append({
                    "type": "image",
                    "sender": sender,
                    "data": content,
                    "is_me": is_me,
                    "is_history": True
                })
            else:  # text
                st.session_state.chat_history_buffer.append({
                    "type": "message",
                    "sender": sender,
                    "text": content,
                    "is_me": is_me,
                    "is_history": True
                })
    
    elif line == "HISTORY_END":
        # End of history - prepend history buffer to chat log
        if hasattr(st.session_state, 'chat_history_buffer') and st.session_state.chat_history_buffer:
            # Add separator
            st.session_state.chat_history_buffer.append({
                "type": "system",
                "text": "─── Previous messages ───"
            })
            # Prepend history to chat log
            st.session_state.chat_log = st.session_state.chat_history_buffer + st.session_state.chat_log
            st.session_state.chat_history_buffer = []
        st.session_state.chat_history_loading = False
        st.session_state.chat_history_loaded = True

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

# Custom CSS for chat bubbles (Messenger/SyncroX hybrid)
st.markdown("""
<style>
.chat-message {
    padding: 10px 14px;
    border-radius: 18px;
    margin: 4px 0;
    max-width: 70%;
    word-wrap: break-word;
    font-family: 'Raleway', system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    font-size: 0.92rem;
    line-height: 1.4;
    background-color: #111827;
    box-shadow: 0 1px 2px rgba(0,0,0,0.15);
}

/* Me (right side – SyncroX green bubble) */
.message-me {
    margin-left: auto;
    text-align: left;
    background: linear-gradient(135deg, #03C084 0%, #02a673 100%);
    color: #020617;
    border-bottom-right-radius: 6px;
}

/* Others (left side – dark bubble) */
.message-other {
    margin-right: auto;
    text-align: left;
    background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
    color: #e5e7eb;
    border: 1px solid rgba(55, 65, 81, 0.5);
    border-bottom-left-radius: 6px;
}

/* Sender label */
.message-sender {
    font-size: 0.75rem;
    font-weight: 700;
    opacity: 0.75;
    margin-bottom: 3px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.message-me .message-sender {
    color: #064e3b;
}

.message-other .message-sender {
    color: #9ca3af;
}

/* Message text */
.message-text {
    font-size: 0.92rem;
    line-height: 1.5;
    color: inherit;
}

/* Seen by indicator */
.seen-by {
    font-size: 0.65rem;
    color: #6b7280;
    margin-top: 4px;
    opacity: 0.8;
}

.message-me .seen-by {
    color: #064e3b;
    text-align: right;
}

.message-other .seen-by {
    color: #9ca3af;
}

/* System messages (centered, subtle) */
.system-message {
    text-align: center;
    color: #6b7280;
    font-size: 0.75rem;
    margin: 12px 0;
    font-style: italic;
    padding: 6px 12px;
    background: rgba(31, 41, 55, 0.5);
    border-radius: 12px;
    display: inline-block;
    width: 100%;
}

/* Image styling with CSS-only Lightbox (Focus to zoom) */
.zoomable-image {
    border-radius: 12px;
    max-width: 100%;
    margin-top: 8px;
    cursor: zoom-in;
    transition: transform 0.2s ease;
}

.zoomable-image:focus {
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    max-width: 90vw;
    max-height: 90vh;
    width: auto;
    height: auto;
    z-index: 999999;
    box-shadow: 0 0 0 100vmax rgba(0,0,0,0.85);
    outline: none;
    cursor: zoom-out;
    border-radius: 4px;
}

/* Custom styling for Expanders to look like big buttons */
div[data-testid="stExpander"] details summary {
    background-color: #111827 !important;
    border: 1px solid #374151 !important;
    border-radius: 8px !important;
    padding: 1rem !important;
    font-size: 1.1rem !important;
    font-weight: 600 !important;
    color: #e5e7eb !important;
    transition: all 0.2s ease;
}

div[data-testid="stExpander"] details summary:hover {
    border-color: #03C084 !important;
    background-color: #1f2933 !important;
    color: #03C084 !important;
}

div[data-testid="stExpander"] {
    background-color: transparent !important;
    border: none !important;
}

/* Chat Row Flex Layout for Avatars */
.chat-row {
    display: flex;
    align-items: flex-end;
    margin: 8px 0;
    gap: 8px;
}

.row-me {
    justify-content: flex-end;
}

.row-other {
    justify-content: flex-start;
}

.chat-avatar {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background-color: #374151;
    color: #e5e7eb;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.9rem;
    font-weight: 700;
    flex-shrink: 0;
    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
}

.avatar-me {
    background-color: #03C084;
    color: #020617;
    order: 2; /* Avatar after message for Me */
}

.avatar-other {
    background-color: #1f2933;
    border: 1px solid #374151;
    /* order: 1; REMOVED to let it default to 0 (before message) */
}

/* Adjust bubble margins since we have flex gap */
.chat-message {
    margin: 0 !important;
}

/* Remove background for image avatars */
img.chat-avatar {
    background-color: transparent !important;
    box-shadow: none !important;
    border: none !important;
}
</style>
""", unsafe_allow_html=True)

# Helper to load images as Base64
def get_image_base64(path):
    if os.path.exists(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return None

# Load avatars
icon_me_path = os.path.join(PROJECT_ROOT, "assets", "Icon.png")
icon_other_path = os.path.join(PROJECT_ROOT, "assets", "Icon2.png")

img_me_b64 = get_image_base64(icon_me_path)
img_other_b64 = get_image_base64(icon_other_path)

# Default fallback if images missing
avatar_me_src = f"data:image/png;base64,{img_me_b64}" if img_me_b64 else ""
avatar_other_src = f"data:image/png;base64,{img_other_b64}" if img_other_b64 else ""

# Helper to format seen by list
def format_seen_by(msg_id, sender, current_username):
    """Format the 'Seen by' text for a message."""
    seen_list = st.session_state.chat_seen_by.get(msg_id, [])
    if not seen_list:
        return ""
    
    # Filter out the sender (they sent it, don't show as "seen")
    others = [u for u in seen_list if u.lower() != sender.lower()]
    if not others:
        return ""
    
    # Format names nicely
    if len(others) == 1:
        return f"👁 Seen by {others[0]}"
    elif len(others) == 2:
        return f"👁 Seen by {others[0]} and {others[1]}"
    elif len(others) <= 4:
        return f"👁 Seen by {', '.join(others[:-1])} and {others[-1]}"
    else:
        return f"👁 Seen by {', '.join(others[:3])} and {len(others) - 3} others"

# Send seen receipts for pending messages
if st.session_state.chat_pending_seen and client:
    for msg_id in list(st.session_state.chat_pending_seen):
        try:
            client.mark_seen(msg_id)
        except:
            pass
    st.session_state.chat_pending_seen.clear()

# Message container with scrollable area
chat_container = st.container(height=450)

# Find the last message from current user to show "Seen by" only on that one
messages_to_show = st.session_state.chat_log[-100:]
last_own_msg_index = -1
for i in range(len(messages_to_show) - 1, -1, -1):
    msg = messages_to_show[i]
    if isinstance(msg, dict) and msg.get("is_me") and msg.get("type") in ("message", "image"):
        last_own_msg_index = i
        break

with chat_container:
    for idx, msg in enumerate(messages_to_show):
        if isinstance(msg, dict):
            if msg["type"] == "system":
                st.markdown(f'<div class="system-message">{msg["text"]}</div>', unsafe_allow_html=True)
            elif msg["type"] == "message":
                is_me = msg.get("is_me", False)
                row_class = "row-me" if is_me else "row-other"
                bubble_class = "message-me" if is_me else "message-other"
                sender_name = "You" if is_me else msg["sender"]
                msg_id = msg.get("msg_id")
                
                # Get seen by info (only show for last own message)
                seen_html = ""
                if is_me and msg_id and idx == last_own_msg_index:
                    seen_text = format_seen_by(msg_id, msg["sender"], st.session_state.username)
                    if seen_text:
                        seen_html = f'<div class="seen-by">{seen_text}</div>'
                
                # Avatar Selection
                if is_me:
                    avatar_html = f'<img src="{avatar_me_src}" class="chat-avatar avatar-me">' if avatar_me_src else f'<div class="chat-avatar avatar-me">You</div>'
                else:
                    avatar_html = f'<img src="{avatar_other_src}" class="chat-avatar avatar-other">' if avatar_other_src else f'<div class="chat-avatar avatar-other">{sender_name[0].upper()}</div>'

                # Only show seen_html if it has content
                seen_div = seen_html if seen_html else ""
                st.markdown(f'''
                <div class="chat-row {row_class}">
                    {avatar_html}
                    <div class="chat-message {bubble_class}">
                        <div class="message-sender">{sender_name}</div>
                        <div class="message-text">{msg["text"]}</div>{seen_div}
                    </div>
                </div>
                ''', unsafe_allow_html=True)

            elif msg["type"] == "image":
                is_me = msg.get("is_me", False)
                row_class = "row-me" if is_me else "row-other"
                bubble_class = "message-me" if is_me else "message-other"
                sender_name = "You" if is_me else msg["sender"]
                msg_id = msg.get("msg_id")
                
                # Get seen by info (only show for last own message)
                seen_html = ""
                if is_me and msg_id and idx == last_own_msg_index:
                    seen_text = format_seen_by(msg_id, msg["sender"], st.session_state.username)
                    if seen_text:
                        seen_html = f'<div class="seen-by">{seen_text}</div>'
                
                # Avatar Selection
                if is_me:
                    avatar_html = f'<img src="{avatar_me_src}" class="chat-avatar avatar-me">' if avatar_me_src else f'<div class="chat-avatar avatar-me">You</div>'
                else:
                    avatar_html = f'<img src="{avatar_other_src}" class="chat-avatar avatar-other">' if avatar_other_src else f'<div class="chat-avatar avatar-other">{sender_name[0].upper()}</div>'

                # Check if data handles the prefix or needs it
                img_src = msg["data"]
                if not img_src.startswith("data:image"):
                    img_src = f"data:image/png;base64,{img_src}"
                
                # Only show seen_html if it has content
                seen_div = seen_html if seen_html else ""
                st.markdown(f'''
                <div class="chat-row {row_class}">
                    {avatar_html}
                    <div class="chat-message {bubble_class}">
                        <div class="message-sender">{sender_name}</div>
                        <img src="{img_src}" class="zoomable-image" tabindex="0">{seen_div}
                    </div>
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

# Helper tools
col_tools1, col_tools2 = st.columns([1, 1])
with col_tools1:
    with st.expander("😀 Add Emoji"):
        emojis = ["😀", "😂", "🥰", "😎", "🤔", "👍", "👎", "🎉", "🔥", "❤️"]
        cols = st.columns(5)
        for i, emo in enumerate(emojis):
            with cols[i % 5]:
                # FIX: Use on_click to modify state before the next render to avoid StreamlitAPIException
                st.button(emo, key=f"emo_{i}", on_click=add_emoji, args=(emo,))

with col_tools2:
    with st.expander("🖼️ Send Image"):
        st.file_uploader(
            "Upload Image", 
            type=["png", "jpg", "jpeg"], 
            key="chat_image_upload", 
            on_change=handle_image_upload
        )

if st.session_state.get("chat_status"):
    st.caption(st.session_state["chat_status"])


