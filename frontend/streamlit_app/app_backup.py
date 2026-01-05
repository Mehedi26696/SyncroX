import os
import sys
import time
import subprocess
import socket
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path


from typing import Optional, List

# --- Make project root importable ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


from backend.tcp_chat.streamlit_client import TcpChatClient
from backend.file_transfer.client import TcpFileClient
from backend.collab.client import TcpCollabClient
from backend.code_exec.client import TcpExecClient

# --- Import config for host/port ---
try:
    from config import SERVER_HOST, CHAT_PORT, FILE_PORT, COLLAB_PORT, EXEC_PORT
except ImportError:
    SERVER_HOST = "127.0.0.1"
    CHAT_PORT = 9009
    FILE_PORT = 9010
    COLLAB_PORT = 9011
    EXEC_PORT = 9012



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
    # auto-refresh so new messages appear
    st_autorefresh(interval=1000, key="chat_refresh")

    st.header("💬 Chat – TCP Rooms")

    # Back to home button
    if st.button("⬅ Back to Home", key="chat_back"):
        go_to("home")
        return

    # --- init session state ---
    if "chat_client" not in st.session_state:
        st.session_state.chat_client = None
    if "chat_log" not in st.session_state:
        st.session_state.chat_log = []
    if "chat_status" not in st.session_state:
        st.session_state.chat_status = ""
    if "chat_room" not in st.session_state:
        st.session_state.chat_room = ""
    if "chat_username" not in st.session_state:
        st.session_state.chat_username = ""
    if "chat_message" not in st.session_state:
        st.session_state.chat_message = ""

    client: TcpChatClient | None = st.session_state.chat_client

    # ---------- if NOT connected: show connect UI ----------
    if client is None:
        st.subheader("Connect to chat server")

        username = st.text_input("Username", key="chat_username")

        col1, col2 = st.columns([1, 1])
        with col1:
            connect_clicked = st.button(
                "Connect",
                type="primary",
                use_container_width=True,
            )

        with col2:
            st.caption(f"Server: {SERVER_HOST}:{CHAT_PORT} (TCP chat server)")

        if connect_clicked:
            if not username.strip():
                st.warning("Please enter a username.")
            else:
                try:
                    st.session_state.chat_client = TcpChatClient(
                        host=SERVER_HOST,
                        port=CHAT_PORT,
                        username=username.strip(),
                    )
                    st.session_state.chat_status = (
                        "Connected. Create or join a 4-digit room."
                    )
                    st.session_state.chat_log.append(
                        "SYSTEM Connected to chat server."
                    )
                except Exception as e:
                    st.error(f"Could not connect to server: {e}")
        if st.session_state.chat_status:
            st.info(st.session_state.chat_status)
        return

    # ---------- already connected ----------
    client = st.session_state.chat_client

    # keep track of current room from client object
    current_room = getattr(client, "current_room", None)
    if current_room and current_room != st.session_state.chat_room:
        st.session_state.chat_room = current_room

    # drain messages from TCP client into chat_log
    new_lines = client.get_new_messages()
    for line in new_lines:
        # MSG 1858 username: text
        if line.startswith("MSG "):
            parts = line.split(maxsplit=2)
            if len(parts) >= 3:
                st.session_state.chat_log.append(parts[2])
        elif line.startswith("SYSTEM "):
            st.session_state.chat_log.append(line[7:])
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
            st.session_state.chat_log.append(line)

    # ---------- layout: chat on left, room controls on right ----------
    col_chat, col_rooms = st.columns([3, 1])

    # LEFT: messages + send box
    with col_chat:
        st.subheader("Messages")

        chat_box = st.container()
        for msg in st.session_state.chat_log[-200:]:
            chat_box.write(msg)

        st.text_input(
            "Type your message",
            key="chat_message",
            on_change=send_chat_message,  # uses the callback defined at top
        )

        if st.session_state.get("chat_status"):
            st.caption(st.session_state["chat_status"])

    # RIGHT: room management
    with col_rooms:
        st.subheader("Room control")
        st.write(f"Current room: `{st.session_state.chat_room or 'None'}`")

        if st.button("Create random room", use_container_width=True):
            client.create_room()

        join_code = st.text_input(
            "Join room by code (4 digits)",
            key="join_room_code",
            max_chars=4,
        )
        if st.button("Join room", use_container_width=True):
            if not join_code or len(join_code) != 4 or not join_code.isdigit():
                st.warning("Enter a valid 4-digit room code.")
            else:
                client.join_room(join_code.strip())

        if st.button("List rooms", use_container_width=True):
            client.list_rooms()

        st.markdown("---")
        if st.button("Disconnect", use_container_width=True):
            try:
                client.close()
            except Exception:
                pass
            st.session_state.chat_client = None
            st.session_state.chat_room = ""
            st.session_state.chat_log.append("SYSTEM Disconnected from server.")
 


def collab_page():
    # Auto-refresh every 0.5 seconds so remote updates and user list refresh
    st_autorefresh(interval=500, key="collab_refresh")

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
    if "collab_users" not in st.session_state:
        st.session_state.collab_users = []
    if "collab_users_last_request" not in st.session_state:
        st.session_state.collab_users_last_request = 0.0
    if "collab_stdin" not in st.session_state:
        st.session_state.collab_stdin = ""
    if "exec_client" not in st.session_state:
        st.session_state.exec_client = None
    if "exec_running" not in st.session_state:
        st.session_state.exec_running = False

    client: TcpCollabClient | None = st.session_state.collab_client

    # ---------- FIRST: connect UI ----------
    if client is None:
        st.subheader("Connect to collab server")

        username = st.text_input(
            "Username",
            key="collab_username_input",
            value=st.session_state.collab_username,
        )
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
                # Collab TCP client
                client = TcpCollabClient(
                    host=SERVER_HOST, port=COLLAB_PORT, username=username.strip()
                )
                client.join_room(room_input.strip())

                st.session_state.collab_client = client
                st.session_state.collab_username = username.strip()
                st.session_state.collab_room = room_input.strip()
                st.session_state.collab_status = (
                    f"Connected as {username.strip()} to room {room_input.strip()}."
                )
                st.session_state.collab_last_sent = ""
                st.session_state.collab_last_sent_time = 0.0

                # Exec TCP client (for Run button)
                st.session_state.exec_client = TcpExecClient(
                    host=SERVER_HOST, port=EXEC_PORT
                )
            except Exception as e:
                st.error(f"Could not connect to collab/exec server: {e}")
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
            try:
                if st.session_state.exec_client:
                    st.session_state.exec_client.close()
            except Exception:
                pass
            st.session_state.collab_client = None
            st.session_state.exec_client = None
            st.session_state.collab_editor = ""
            st.session_state.collab_status = "Disconnected from collab and exec servers."
            return

    # --- pull document updates from server ---
    new_doc = client.get_latest_doc()
    if new_doc is not None and new_doc != st.session_state.collab_editor:
        st.session_state.collab_editor = new_doc
        st.session_state.collab_last_sent = new_doc

    # --- request / read active users list ---
    now = time.time()
    if now - st.session_state.collab_users_last_request > 2.0:
        client.request_users(room)
        st.session_state.collab_users_last_request = now

    users_update = client.get_latest_users()
    if users_update is not None:
        st.session_state.collab_users = users_update

    # --- show last editor + active users ---
    if getattr(client, "last_editor", None):
        st.caption(f"Last update from **{client.last_editor}**")

    if st.session_state.collab_users:
        labels = [f"{name} ({status})" for name, status in st.session_state.collab_users]
        st.caption("Active users: " + ", ".join(labels))

    st.markdown("### Shared code")

    # Language selector – now supports multiple languages
    st.session_state.collab_language = st.selectbox(
        "Language",
        ["python", "c", "cpp", "java"],
        index=0,
        key="collab_language_select",
    )

    # Editor – shared across the room
    code = st.text_area(
        "Code",
        height=350,
        key="collab_editor",
    )

    # Optional stdin
    stdin_text = st.text_area(
        "Program input (stdin)",
        height=80,
        key="collab_stdin",
        help="This text will be sent to the program's standard input.",
    )

    # ---------- AUTO-SYNC: push local edits every ~1s ----------
    now = time.time()
    if (
        code != st.session_state.collab_last_sent
        and now - st.session_state.collab_last_sent_time > 1.0
    ):
        try:
            client.set_code(room, code)
            st.session_state.collab_last_sent = code
            st.session_state.collab_last_sent_time = now
            st.session_state.collab_status = "Synced changes to room."
        except Exception as e:
            st.session_state.collab_status = f"Error syncing: {e}"

    # ---------- manual Save + Run ----------
    col_save1, col_save2, col_save3 = st.columns([1, 1, 3])
    with col_save1:
        if st.button("💾 Save to room", use_container_width=True):
            try:
                client.set_code(room, code)
                st.session_state.collab_last_sent = code
                st.session_state.collab_last_sent_time = time.time()
                st.session_state.collab_status = (
                    "Saved code to room (broadcast to others)."
                )
            except Exception as e:
                st.session_state.collab_status = f"Error saving: {e}"

    with col_save2:
        run_clicked = st.button("▶ Run", use_container_width=True)

    if run_clicked:
        lang = st.session_state.collab_language
        code_to_run = st.session_state.collab_editor
        room_code = st.session_state.collab_room or "0000"

        exec_client: TcpExecClient = st.session_state.exec_client
        if exec_client is None:
            st.session_state.collab_output = "[exec server not connected]"
            st.error("Exec server not connected")
        else:
            with st.spinner(f"Running {lang} code..."):
                try:
                    success, out_text, err_text, rc, time_ms = exec_client.execute(
                        room=room_code,
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
                    st.success(f"Execution completed in {time_ms}ms")
                    if out_text:
                        st.code(out_text, language=None)
                    if err_text:
                        st.error(err_text)
                        
                except Exception as e:
                    st.session_state.collab_output = f"[exception in exec_client.execute] {repr(e)}"
                    st.error(f"Exception: {repr(e)}")


    if st.session_state.collab_status:
        st.info(st.session_state.collab_status)

    st.markdown("### Output")
    
    st.text_area(
        "Execution output",
        value=st.session_state.collab_output,
        height=180,
        disabled=True,
    )

    st.caption(
        "We use a custom TCP protocol (HELLO / JOIN / SET / DOC / USERS / EXECUTE / RESULT). "
        "Each client auto-sends edits about once per second and pulls updates every 1.5 seconds, "
        "so users in the same 4-digit room share one code document and can execute Python, C, C++ "
        "and Java code in a Docker sandbox via our TCP execution service."
    )








def file_transfer_page():
    st.header("📁 File Transfer – TCP with Tahoe/Reno Simulation")

    if "ft_room" not in st.session_state:
        st.session_state.ft_room = ""
    if "ft_algo" not in st.session_state:
        st.session_state.ft_algo = "reno"

    col1, col2 = st.columns(2)
    with col1:
        room = st.text_input(
            "Room code (4 digits)",
            max_chars=4,
            value=st.session_state.ft_room,
        )
    with col2:
        algo = st.radio(
            "Congestion control (simulation)",
            ["reno", "tahoe"],
            index=0 if st.session_state.ft_algo == "reno" else 1,
            horizontal=True,
        )

    st.session_state.ft_room = room
    st.session_state.ft_algo = algo

    if not (room and len(room) == 4 and room.isdigit()):
        st.warning("Enter a valid 4-digit room to enable transfer.")
        if st.button("⬅ Back to Home"):
            go_to("home")
        return

    st.markdown("---")

    # ---- Upload section ----
    st.subheader("Upload file (instrumented)")
    upload_col1, upload_col2 = st.columns([3, 1])
    with upload_col1:
        up_file = st.file_uploader("Choose a file to upload", type=None)
    with upload_col2:
        st.markdown("**Algorithm:**")
        st.markdown(f"`{algo}` (simulation)")

    if up_file is not None:
        filename = up_file.name
        data = up_file.read()
        if st.button("⬆ Upload with metrics", type="primary", use_container_width=True):
            try:
                client = TcpFileClient(host=SERVER_HOST, port=FILE_PORT, algo=algo)
                resp = client.upload_bytes(room, filename, data)
                client.close()
                st.success(f"Upload finished. Server responded: `{resp}`")
                st.info(
                    f"Metrics logged to `data/metrics/room_{room}_file_metrics.csv` "
                    f"for file `{filename}` using `{algo}`."
                )
            except Exception as e:
                st.error(f"Upload failed: {e}")

    st.markdown("---")

    # ---- List / download section ----
    st.subheader("Files in this room")
    try:
        client = TcpFileClient(host=SERVER_HOST, port=FILE_PORT, algo=algo)
        files = client.list_files(room)
    except Exception as e:
        files = []
        st.error(f"Could not list files: {e}")
        client = None

    if files:
        for name, size, created in files:
            with st.expander(f"{name}  ({size} bytes)"):
                st.write(f"Created at: `{created}`")
                if client and st.button(f"⬇ Download `{name}`", key=f"dl_{name}"):
                    try:
                        data = client.download_bytes(room, name)
                        if data is None:
                            st.error("Download failed or file not found.")
                        else:
                            st.download_button(
                                "Save to disk",
                                data=data,
                                file_name=name,
                                mime="application/octet-stream",
                            )
                    except Exception as e:
                        st.error(f"Download failed: {e}")
    else:
        st.info("No files in this room yet.")

    if client:
        try:
            client.close()
        except Exception:
            pass

    st.markdown("---")
    if st.button("⬅ Back to Home"):
        go_to("home")


def check_tcp_server(host: str, port: int, timeout: float = 0.5):
    """
    Try to open a TCP connection to (host, port).
    Returns (ok, latency_ms, error_message).
    """
    start = time.time()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            latency_ms = (time.time() - start) * 1000.0
            return True, latency_ms, ""
    except OSError as e:
        return False, None, str(e)


def dashboard_page():
    st.header("📊 SyncroX – Networking Dashboard")

    st.write(
        "Overview of all TCP services used by SyncroX. "
        "This shows whether each backend server is reachable and how long "
        "it takes to open a TCP connection (rough latency)."
    )

    host = SERVER_HOST

    services = [
        ("Chat server", "Real-time text chat over TCP rooms.", host, CHAT_PORT),
        ("File server", "Reliable TCP file transfer scoped by 4-digit room.", host, FILE_PORT),
        ("Collab server", "Shared code editor & live document sync.", host, COLLAB_PORT),
        ("Exec server", "Docker-sandboxed code execution (Python/C/C++/Java).", host, EXEC_PORT),
    ]

    cols = st.columns(2)
    for i, (name, desc, h, p) in enumerate(services):
        with cols[i % 2]:
            ok, latency_ms, err = check_tcp_server(h, p, timeout=0.7)

            st.subheader(name)
            st.caption(f"Host: `{h}` • Port: `{p}`")
            st.write(desc)

            if ok:
                st.success(f"Online · ~{latency_ms:.1f} ms to connect")
            else:
                st.error("Offline / unreachable")
                with st.expander("Error details", expanded=False):
                    st.code(err or "No additional error info.")

        st.markdown("---")
    st.subheader("📉 File transfer congestion behaviour (per room & file)")

    metrics_dir = Path("data") / "metrics"
    if not metrics_dir.exists():
        st.info("No metrics yet – run some file transfers first.")
        return

    files = sorted(metrics_dir.glob("room_*_file_metrics.csv"))
    if not files:
        st.info("No metrics files found. Upload a file to any room to generate logs.")
        return

    room_options = {f"Room {fp.stem.split('_')[1]}": fp for fp in files}
    room_label = st.selectbox("Choose a room log", list(room_options.keys()))
    fp = room_options[room_label]

    df = pd.read_csv(fp)
    st.write(f"Loaded {len(df)} events from `{fp.name}`")

    # ---- choose file within this room ----
    if "file" in df.columns:
        file_names = sorted(df["file"].dropna().unique())
        file_label = st.selectbox(
            "Choose a specific file (or All files)",
            ["All files"] + file_names,
        )
        if file_label != "All files":
            df = df[df["file"] == file_label].copy()
            st.write(f"Filtered to file `{file_label}`, {len(df)} events.")
    else:
        file_label = "All files"

    st.dataframe(df.tail(10), use_container_width=True)

    # Only ACK rows have RTT / srtt values
    ack_df = df[df["event"] == "ACK"].copy()
    if ack_df.empty:
        st.warning("No ACK events to plot yet for this selection.")
        return

    # Normalize seq to start at 1 for nicer x-axis
    ack_df["rel_seq"] = ack_df["seq"] - ack_df["seq"].min() + 1

    # --- Plot RTT vs EWMA ---
    fig1, ax1 = plt.subplots()
    ax1.plot(ack_df["rel_seq"], ack_df["rtt_ms"], marker="o", label="RTT sample")
    ax1.plot(ack_df["rel_seq"], ack_df["srtt_ms"], marker=".", label="EWMA RTT")
    ax1.set_xlabel("Chunk (seq)")
    ax1.set_ylabel("RTT (ms)")
    title_suffix = f" – {file_label}" if file_label != "All files" else ""
    ax1.set_title("RTT vs EWMA RTT" + title_suffix)
    ax1.legend()
    st.pyplot(fig1)

    # --- Plot cwnd evolution ---
    fig2, ax2 = plt.subplots()
    ax2.plot(df["seq"], df["cwnd"], marker="o")
    ax2.set_xlabel("Event seq")
    ax2.set_ylabel("cwnd (segments)")
    algo = df["algo"].iloc[0] if "algo" in df.columns else "unknown"
    ax2.set_title(f"Congestion window evolution ({algo}){title_suffix}")
    st.pyplot(fig2)

    # --- Highlight loss events ---
    loss_df = df[df["event"] == "LOSS"]
    if not loss_df.empty:
        fig3, ax3 = plt.subplots()
        ax3.plot(df["seq"], df["cwnd"], marker="o", label="cwnd")
        ax3.scatter(loss_df["seq"], loss_df["cwnd"], marker="x", s=80, label="loss")
        ax3.set_xlabel("Event seq")
        ax3.set_ylabel("cwnd (segments)")
        ax3.set_title("Loss events and cwnd changes" + title_suffix)
        ax3.legend()
        st.pyplot(fig3)


    st.markdown("---")
    st.markdown("### How this demonstrates networking concepts")

    st.markdown(
        """
- **Custom TCP-on-TCP instrumentation**  
  - File uploads are split into fixed-size segments. For each `DATA` segment the server
    sends an `ACK room seq`, so the client can measure per-segment RTT.
- **Exponential Weighted Moving Average (EWMA)**  
  - We compute a smoothed RTT `SRTT` and variance `RTTVAR`, then `RTO = SRTT + 4×RTTVAR`
    exactly like real TCP, and plot both **RTT samples** and **EWMA RTT**.
- **Tahoe / Reno congestion control simulation**  
  - `cwnd` starts at 1 segment and grows exponentially in **slow start** until
    `ssthresh`, then linearly in **congestion avoidance**.  
  - On timeouts we simulate **Tahoe** or **Reno** behaviour and log each change,
    which you can see in the congestion window plots.
- **Room-based analysis**  
  - Metrics are logged per 4-digit room (e.g. `room_4509_file_metrics.csv`), so each
    lab group can see their own cwnd/RTT graphs independently.
        """
    )




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
