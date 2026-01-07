# SyncroX Chat System Documentation

This document describes the architecture, protocol, and data handling of the SyncroX Real-time Chat System.

## 🏗️ Architecture Overview

The system follows a classic **Multi-Client Server** architecture over **TCP**.

- **Backend**: A Python-based TCP server (`server.py`) using non-blocking threads to handle multiple concurrent users.
- **Protocol**: A custom text-based command protocol (Newline-delimited).
- **Frontend**: A Streamlit-based web interface (`chat.py`) that communicates with the server via a persistent TCP client (`streamlit_client.py`).

---

## 🛰️ Protocol Specification

Clients communicate with the server using uppercase commands.

### Connection & Rooms
- `HELLO <username>`: Initial handshake. Server identifies the user.
- `JOIN_ROOM <room_code>`: Joins a specific chat room. Auto-creates the room if it doesn't exist.
- `LIST_ROOMS`: Requests a list of all active room codes.
- `BYE`: Graceful disconnection.

### Messaging
- `MSG <text>`: Client sends a text message.
- `MSG <room> <id> <timestamp> <user>: <text>`: Server broadcasts a message to all users in the room.

### Image Handling (Pro CDN Architecture)
- `IMG_SEND <base64>`: Client uploads an image as a Base64 string.
- `IMG <room> <id> <timestamp> <user> <filename>`: Server notifies clients of a new image (sends filename, not data).
- `GET_IMG <filename>`: Client requests the raw binary data for a specific image file.
- `IMG_DATA <filename> <base64>`: Server delivers the image data to the requesting client.

### History
- `HISTORY [limit]`: Client requests the last X messages.
- `HIST <type> <timestamp> <user> <content>`: Server streams historical records one by one.

---

## 🖼️ Advanced Image Handling (CDN Style)

SyncroX uses a **Private CDN** approach to handle images efficiently:

1. **Storage**: Images are moved from the network stream directly to the server's disk at `data/cdn/`.
2. **Protocol Optimization**: Real-time broadcasts only contain filenames. This prevents the chat from lagging during high-activity periods.
3. **Lazy Loading**: Clients only download image data (`GET_IMG`) when they need to render the message on screen.
4. **Caching**: Once an image is downloaded, it is stored in `st.session_state.chat_image_cache` for the remainder of the session.

---

## 💾 Persistence & Data Safety

- **JSON Logs**: Every message and image reference is stored in `data/chat_history/room_<room_id>_chat.json`.
- **Atomic Writes**: The `ChatHistoryManager` uses thread locks to prevent data corruption during simultaneous writes.
- **Duplicate Guards**:
    - **Frontend**: Uses MD5 hashing and a dynamic uploader key to prevent double-sending images.
    - **Sync**: Uses unique message IDs and timestamps to ensure history is perfectly ordered.

---

## ⚡ UI & Performance

- **Autorefresh**: The UI polls the TCP client every 1 second to pull new messages.
- **Conditional Styling**:
    - **Me**: Green bubbles, white text, white timestamps.
    - **Others**: White bubbles, dark text, black timestamps.
- **Micro-Animations**: Uses CSS transitions for smooth message entry and image zooming (focus-to-zoom).
