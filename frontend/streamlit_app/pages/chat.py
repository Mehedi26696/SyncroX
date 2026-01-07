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

st.set_page_config(
    page_title="Chat - SyncroX",
    page_icon=page_icon,
    layout="wide",
   
)

# Apply custom CSS for Raleway font and new color scheme + SyncroX theme
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
        max-width: 1200px;
        margin: 0 auto;
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
    
    h1, h2, h3, h4, h5, h6, p, div, span, label, button {
        font-family: 'Raleway', sans-serif !important;
        color: #087f5b;
    }
    
    h1 { font-size: 3rem !important; }
    h2 { font-size: 2.5rem !important; }
    h3 { font-size: 2rem !important; }
    h4 { font-size: 1.5rem !important; }

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

    /* Global buttons (SyncroX green) */
    div.stButton > button {
        background-color: #087f5b !important;
        color: #ebfbee !important;
        border-radius: 8px !important;
        border: none !important;
        font-weight: 800 !important;
        padding: 0.6rem 1rem !important;
        font-size: 1.1rem !important;
    }
    div.stButton > button:hover {
        background-color: #006E6D !important;
        color: #ebfbee !important;
    }

    /* Sidebar-specific buttons */
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

    /* Disabled nav button (current page) */
    [data-testid="stSidebar"] button[disabled] {
        background-color: #b2f2bb !important;
        color: #087f5b !important;
        opacity: 0.9 !important;
    }

    /* Logout secondary button */
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

    /* Text input styling (chat box) */
    .stTextInput>div>div>input {
        background-color: white !important;
        color: #087f5b !important;
        border-radius: 999px !important;
        border: 2px solid #087f5b !important;
        padding: 0.6rem 1.1rem !important;
        font-size: 1.1rem !important;
    }
    .stTextInput>div>div>input:focus {
        border-color: #006E6D !important;
        box-shadow: 0 0 0 2px #006E6D !important;
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

# Sidebar - shared component
from components.sidebar import render_sidebar
render_sidebar(current_page="chat")

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
    key = f"chat_image_upload_{st.session_state.get('chat_uploader_key', 0)}"
    uploaded_file = st.session_state.get(key)
    client = st.session_state.get("chat_client")
    
    if uploaded_file is not None and client:
        # Prevent duplicate sends of the same file in a row
        file_id = f"{uploaded_file.name}_{uploaded_file.size}"
        if st.session_state.get("last_uploaded_file_id") == file_id:
            return
        st.session_state.last_uploaded_file_id = file_id
        
        try:
            bytes_data = uploaded_file.getvalue()
            b64_str = base64.b64encode(bytes_data).decode("utf-8")
            client.send_image(b64_str)
            st.session_state["chat_status"] = "Image sent!"
            # Increment key to clear uploader
            st.session_state.chat_uploader_key = st.session_state.get('chat_uploader_key', 0) + 1
        except Exception as e:
            st.session_state["chat_status"] = f"Error sending image: {e}"


# Initialize session state
if "chat_client" not in st.session_state:
    st.session_state.chat_client = None
if "chat_log" not in st.session_state:
    st.session_state.chat_log = []  # List of {"type": "message"|"system", "sender": str, "text": str, "msg_id": int}
if "chat_status" not in st.session_state:
    st.session_state.chat_status = ""
if "chat_message" not in st.session_state:
    st.session_state.chat_message = ""
if "chat_uploader_key" not in st.session_state:
    st.session_state.chat_uploader_key = 0
if "last_uploaded_file_id" not in st.session_state:
    st.session_state.last_uploaded_file_id = None
if "chat_image_cache" not in st.session_state:
    st.session_state.chat_image_cache = {}  # filename -> base64
if "chat_history_buffer" not in st.session_state:
    st.session_state.chat_history_buffer = []
if "chat_history_loaded" not in st.session_state:
    st.session_state.chat_history_loaded = False
    if "chat_history_room" not in st.session_state:
        st.session_state.chat_history_room = None
    if "chat_history_loading" not in st.session_state:
        st.session_state.chat_history_loading = False
if "chat_seen_ids" not in st.session_state:
    st.session_state.chat_seen_ids = set()  # Track room:msg_id to allow valid repeats
if "chat_current_user" not in st.session_state:
    st.session_state.chat_current_user = ""

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
    st.session_state.chat_seen_ids = set()
    st.session_state.chat_history_buffer = []
    st.session_state.chat_history_loaded = False
    st.session_state.chat_image_cache = {}
    st.session_state.chat_current_user = st.session_state.username
    st.session_state.chat_room = ""

st.markdown("<h2 style='color: #087f5b; margin-bottom: 0.5rem;'>💬 Real-time Chat</h2>", unsafe_allow_html=True)
st.markdown(
    f"<p style='color: #6b7280; font-size: 0.9rem; margin-bottom: 1.5rem;'>Room: <strong>{st.session_state.current_room}</strong> • User: <strong>{st.session_state.username}</strong></p>",
    unsafe_allow_html=True,
)

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
        
        # We don't set st.session_state.chat_room = st.session_state.current_room here anymore.
        # We wait for the server confirmation (OK Joined) in the message loop.
        st.session_state.chat_status = f"Connecting to {st.session_state.current_room}..."
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
rerun_at_end = False

for line in new_lines:
    if line.startswith("MSG "):
        # Format: "MSG <room> <msg_id> <timestamp> <username>: <message>"
        parts = line.split(maxsplit=4)
        if len(parts) >= 5:
            msg_id = int(parts[2])
            timestamp = parts[3].replace("_", " ")
            msg_content = parts[4]  # "username: message"
            if ": " in msg_content:
                sender, text = msg_content.split(": ", 1)
                sender = sender.strip()
                text = text.strip()  # Normalize text
                is_me = (sender.lower() == current_user)
                
                # Deduplicate using unique msg_id
                room_from_msg = parts[1]
                msg_key = f"{room_from_msg}:{msg_id}"
                if msg_key not in st.session_state.chat_seen_ids:
                    st.session_state.chat_seen_ids.add(msg_key)
                    st.session_state.chat_log.append({
                        "type": "message",
                        "sender": sender,
                        "text": text,
                        "is_me": is_me,
                        "msg_id": msg_id,
                        "timestamp": timestamp
                    })
                        
    elif line.startswith("IMG "):
        # Format: "IMG <room> <msg_id> <timestamp> <username> <base64>"
        parts = line.split(maxsplit=5)
        if len(parts) >= 6:
            msg_id = int(parts[2])
            timestamp = parts[3].replace("_", " ")
            sender = parts[4].strip()
            img_data = parts[5].strip()
            is_me = (sender.lower() == current_user)
            
            # Deduplicate using unique msg_id
            room_from_img = parts[1]
            img_key = f"{room_from_img}:{msg_id}"
            if img_key not in st.session_state.chat_seen_ids:
                st.session_state.chat_seen_ids.add(img_key)
                st.session_state.chat_log.append({
                    "type": "image",
                    "sender": sender,
                    "filename": img_data, # This is now just a filename
                    "is_me": is_me,
                    "msg_id": msg_id,
                    "timestamp": timestamp
                })
    
    
    elif line.startswith("IMG_DATA "):
        # Format: "IMG_DATA <filename> <base64>"
        parts = line.split(maxsplit=2)
        if len(parts) >= 3:
            filename = parts[1]
            b64_data = parts[2]
            st.session_state.chat_image_cache[filename] = b64_data
            rerun_at_end = True

    elif line.startswith("HISTORY "):
        # Format: "HISTORY <room> <count>" - marks start of history
        parts = line.split()
        if len(parts) >= 2:
            st.session_state.chat_history_room = parts[1]
        st.session_state.chat_history_loading = True
        st.session_state.chat_history_buffer = []
    
    elif line.startswith("HIST "):
        # Format: "HIST <msg_id> <type> <timestamp> <sender> <content>"
        parts = line.split(maxsplit=5)
        if len(parts) >= 6:
            orig_msg_id = parts[1]
            msg_type = parts[2]  # text, image, system
            timestamp = parts[3].replace("_", " ")  # Restore space in timestamp
            sender = parts[4].strip()
            content = parts[5].strip()
            
            # Case-insensitive comparison for is_me check
            is_me = (sender.lower() == current_user)
            
            # Deduplicate using unique server-provided ID
            # Use room:msg_id format to prevent cross-room collisions
            hist_room = st.session_state.chat_history_room or st.session_state.current_room
            msg_key = f"{hist_room}:{orig_msg_id}"
            if msg_key in st.session_state.chat_seen_ids:
                continue # Skip if already seen (e.g. real-time echo)
            st.session_state.chat_seen_ids.add(msg_key)
            
            if msg_type == "system":
                st.session_state.chat_history_buffer.append({
                    "type": "system",
                    "text": f"[{timestamp}] {content}",
                    "is_history": True,
                    "msg_id": orig_msg_id
                })
            elif msg_type == "image":
                st.session_state.chat_history_buffer.append({
                    "type": "image",
                    "sender": sender,
                    "filename": content,
                    "is_me": is_me,
                    "is_history": True,
                    "timestamp": timestamp,
                    "msg_id": orig_msg_id
                })
            else:  # text
                st.session_state.chat_history_buffer.append({
                    "type": "message",
                    "sender": sender,
                    "text": content,
                    "is_me": is_me,
                    "is_history": True,
                    "timestamp": timestamp,
                    "msg_id": orig_msg_id
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
        error_msg = line[6:]
        st.session_state.chat_log.append({"type": "system", "text": f"❌ {error_msg}"})
        
        # If joining failed, reset the chat_room state so user stays/returns to selection
        if "RoomNotFound" in error_msg or "not in a room" in error_msg:
            st.session_state.chat_room = None
            client.current_room = None
            st.session_state.chat_history_loaded = False
            rerun_at_end = True
    else:
        st.session_state.chat_log.append({"type": "system", "text": line})

if rerun_at_end:
    st.rerun()



# Custom CSS for chat bubbles (WhatsApp/Modern messaging style)
st.markdown("""
<style>
/* Modern chat container with shadow */
.stContainer {
    background: white;
    border-radius: 16px;
    padding: 1rem;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
}

.chat-message {
    padding: 12px 16px;
    border-radius: 16px;
    margin: 6px 0;
    max-width: 65%;
    word-wrap: break-word;
    font-family: 'Raleway', system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    font-size: 1rem;
    line-height: 1.5;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
    position: relative;
}

/* Me (right side – Primary green bubble) */
.message-me {
    margin-left: auto;
    text-align: left;
    background: #087f5b;
    color: white;
    border-bottom-right-radius: 4px;
}

/* Others (left side – Light gray bubble like WhatsApp) */
.message-other {
    margin-right: auto;
    text-align: left;
    background: #ffffff;
    color: #1f2937;
    border: 1px solid #e5e7eb;
    border-bottom-left-radius: 4px;
}

/* Sender label */
.message-sender {
    font-size: 0.75rem;
    font-weight: 700;
    margin-bottom: 4px;
    letter-spacing: 0.3px;
}

.message-me .message-sender {
    color: #d3f9d8;
}

.message-other .message-sender {
    color: #087f5b;
}

/* Message text */
.message-text {
    font-size: 1rem;
    line-height: 1.5;
    color: inherit;
}

/* Timestamp styling */
.message-timestamp {
    font-size: 0.65rem;
    margin-top: 2px;
    opacity: 0.8;
    text-align: right;
}

.message-me .message-timestamp {
    color: #ffffff !important;
}

.message-other .message-timestamp {
    color: #000000 !important;
    opacity: 0.6;
}

.timestamp-container {
    padding-top: 2px;
    display: flex;
    justify-content: flex-end;
}

/* System messages (centered, subtle) */
.system-message {
    text-align: center;
    color: #6b7280;
    font-size: 0.8rem;
    margin: 16px auto;
    font-weight: 500;
    padding: 8px 16px;
    background: #f3f4f6;
    border-radius: 12px;
    display: inline-block;
    max-width: 80%;
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

/* Custom styling for Expanders to look like modern action buttons */
div[data-testid="stExpander"] details summary {
    background-color: #f3f4f6 !important;
    border: 2px solid #d1d5db !important;
    border-radius: 12px !important;
    padding: 1rem !important;
    font-size: 1rem !important;
    font-weight: 600 !important;
    color: #087f5b !important;
    transition: all 0.2s ease;
}

div[data-testid="stExpander"] details summary:hover {
    border-color: #087f5b !important;
    background-color: #d3f9d8 !important;
    color: #006E6D !important;
}

div[data-testid="stExpander"] {
    background-color: transparent !important;
    border: none !important;
}

/* Chat Row Flex Layout for Avatars */
.chat-row {
    display: flex;
    align-items: flex-end;
    margin: 10px 0;
    gap: 10px;
}

.row-me {
    justify-content: flex-end;
}

.row-other {
    justify-content: flex-start;
}

.chat-avatar {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    background-color: #087f5b;
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.95rem;
    font-weight: 700;
    flex-shrink: 0;
    box-shadow: 0 2px 4px rgba(8, 127, 91, 0.2);
}

.avatar-me {
    background-color: #087f5b;
    color: white;
    order: 2; /* Avatar after message for Me */
}

.avatar-other {
    background-color: #f3f4f6;
    border: 2px solid #087f5b;
    color: #087f5b;
    /* order: 1; REMOVED to let it default to 0 (before message) */
}

/* Adjust bubble margins since we have flex gap */
.chat-message {
    margin: 0 !important;
}

/* Remove background for image avatars */
img.chat-avatar {
    background-color: transparent !important;
    box-shadow: 0 2px 4px rgba(8, 127, 91, 0.15) !important;
    border: 2px solid #087f5b !important;
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

# Message container with scrollable area
chat_container = st.container(height=450)

messages_to_show = st.session_state.chat_log[-100:]

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
                
                # Avatar Selection
                if is_me:
                    avatar_html = f'<img src="{avatar_me_src}" class="chat-avatar avatar-me">' if avatar_me_src else f'<div class="chat-avatar avatar-me">You</div>'
                else:
                    avatar_html = f'<img src="{avatar_other_src}" class="chat-avatar avatar-other">' if avatar_other_src else f'<div class="chat-avatar avatar-other">{sender_name[0].upper()}</div>'

                # Format timestamp for display (just the time part or full if history)
                raw_ts = msg.get("timestamp", "")
                display_ts = raw_ts.split()[-1] if raw_ts else ""
                
                st.markdown(f'''
                <div class="chat-row {row_class}">
                    {avatar_html}
                    <div class="chat-message {bubble_class}">
                        <div class="message-sender">{sender_name}</div>
                        <div class="message-text">{msg["text"]}</div>
                        <div class="timestamp-container">
                            <div class="message-timestamp">{display_ts}</div>
                        </div>
                    </div>
                </div>
                ''', unsafe_allow_html=True)

            elif msg["type"] == "image":
                is_me = msg.get("is_me", False)
                row_class = "row-me" if is_me else "row-other"
                bubble_class = "message-me" if is_me else "message-other"
                sender_name = "You" if is_me else msg["sender"]

                # Avatar Selection
                if is_me:
                    avatar_html = f'<img src="{avatar_me_src}" class="chat-avatar avatar-me">' if avatar_me_src else f'<div class="chat-avatar avatar-me">You</div>'
                else:
                    avatar_html = f'<img src="{avatar_other_src}" class="chat-avatar avatar-other">' if avatar_other_src else f'<div class="chat-avatar avatar-other">{sender_name[0].upper()}</div>'

                # Format timestamp for display
                raw_ts = msg.get("timestamp", "")
                display_ts = raw_ts.split()[-1] if raw_ts else ""

                # Fetch from cache or request from server
                filename = msg.get("filename")
                img_src = None
                
                if filename in st.session_state.chat_image_cache:
                    b64_data = st.session_state.chat_image_cache[filename]
                    if not b64_data.startswith("data:image"):
                        img_src = f"data:image/png;base64,{b64_data}"
                    else:
                        img_src = b64_data
                else:
                    # Not in cache, request it
                    if client:
                        client.request_image(filename)
                    # Show loader
                    img_src = None

                st.markdown(f'''
                <div class="chat-row {row_class}">
                    {avatar_html}
                    <div class="chat-message {bubble_class}">
                        <div class="message-sender">{sender_name}</div>
                        {f'<img src="{img_src}" class="zoomable-image" tabindex="0">' if img_src else '<div style="padding: 20px; color: #6b7280; font-size: 0.8rem;">📥 Loading image...</div>'}
                        <div class="timestamp-container">
                            <div class="message-timestamp">{display_ts}</div>
                        </div>
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
            key=f"chat_image_upload_{st.session_state.chat_uploader_key}", 
            on_change=handle_image_upload
        )

if st.session_state.get("chat_status"):
    st.caption(st.session_state["chat_status"])


