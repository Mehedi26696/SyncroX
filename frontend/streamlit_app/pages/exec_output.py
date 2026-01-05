import os
import sys
import time
from pathlib import Path
from datetime import datetime

import streamlit as st
import pandas as pd
from PIL import Image

# --- Make project root importable (same style as other pages) ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.exec_history import get_history_manager

# ============================================================================
# EXECUTION OUTPUT / HISTORY PAGE
# ============================================================================

# Load custom icon
icon_path = os.path.join(PROJECT_ROOT, "assets", "image.png")
page_icon = Image.open(icon_path) if os.path.exists(icon_path) else "📜"

st.set_page_config(page_title="Execution Output - SyncroX", page_icon=page_icon, layout="wide")

# Basic styling (SyncroX theme)
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

    body {
        background-color: #020617;
        color: #e5e7eb;
    }

    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }

    h1, h2, h3, h4, h5, h6 {
        color: #f9fafb !important;
    }

    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #0a0a0a;
        border-right: 1px solid rgba(3, 192, 132, 0.25);
    }

    [data-testid="stSidebar"] h3 {
        color: #03C084 !important;
        font-weight: 700 !important;
    }

    .stAlert {
        background-color: #0d0d0d !important;
        border-left: 4px solid #03C084 !important;
        color: #e5e7eb !important;
    }

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

    /* Metric-style boxes (if you want custom containers) */
    .metric-box {
        border-radius: 12px;
        padding: 0.75rem 1rem;
        background: linear-gradient(135deg, #020617, #0f172a);
        border: 1px solid rgba(3, 192, 132, 0.4);
    }

    /* Default st.metric card tweak */
    .stMetric {
        background-color: #0b0b0b !important;
        padding: 16px !important;
        border-radius: 12px !important;
        border: 1px solid rgba(3, 192, 132, 0.35) !important;
        box-shadow: 0 0 12px rgba(3, 192, 132, 0.25);
    }

    /* Dataframe and text areas minor tweaks */
    .stDataFrame {
        border-radius: 12px !important;
        overflow: hidden !important;
    }

    textarea {
        background-color: #020617 !important;
        color: #e5e7eb !important;
        border-radius: 10px !important;
        border: 1px solid #1f2933 !important;
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        background-color: #0a0a0a !important;
        border-radius: 8px !important;
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #111827;
        border-radius: 8px;
        padding: 8px 16px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #03C084 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- Login check ---
if not st.session_state.get("is_logged_in", False):
    st.error("⚠️ Please login first!")
    if st.button("Go to Home"):
        st.switch_page("app.py")
    st.stop()

# ============================================================================
# Sidebar - navigation
# ============================================================================
with st.sidebar:
    st.markdown("### 👤 User Information")
    st.info(f"**Name:** {st.session_state.username}\n\n**Room:** `{st.session_state.current_room}`")

    st.markdown("---")
    st.markdown("### 🧭 Navigation")
    st.caption("Select a feature below:")

    if st.button("💬 Chat", use_container_width=True):
        st.switch_page("pages/chat.py")

    if st.button("🤝 Code Editor", use_container_width=True):
        st.switch_page("pages/code_editor.py")

    if st.button("📁 File Manager", use_container_width=True):
        st.switch_page("pages/file_manager.py")

    if st.button("📊 Dashboard", use_container_width=True):
        st.switch_page("pages/dashboard_page.py")

    # Current page (disabled)
    if st.button("📜 Execution Output", use_container_width=True, disabled=True):
        st.switch_page("pages/exec_output.py")

    st.markdown("---")
    if st.button("🚪 Leave Room & Logout", use_container_width=True, type="secondary"):
        st.session_state.is_logged_in = False
        st.session_state.username = ""
        st.session_state.current_room = ""
        # Clear all client connections
        for key in list(st.session_state.keys()):
            if key.endswith("_client"):
                try:
                    st.session_state[key].close()
                except Exception:
                    pass
                del st.session_state[key]
        st.switch_page("app.py")

# ============================================================================
# Main content
# ============================================================================
st.title("📜 Execution History")
st.caption("View all code executions across rooms, users, and languages. Data is persisted to disk.")

# Get history manager
history_manager = get_history_manager()

# Get current room from session
current_room = st.session_state.get("current_room", "")

# ============================================================================
# Filters Section
# ============================================================================
st.markdown("---")
st.subheader("🔍 Filters")

# Get available filter options
all_rooms = history_manager.get_all_rooms()
if current_room and current_room not in all_rooms:
    all_rooms = [current_room] + all_rooms

# Filter columns
col_f1, col_f2, col_f3, col_f4 = st.columns([1, 1, 1, 1])

with col_f1:
    room_options = ["All Rooms"] + all_rooms
    default_room_idx = room_options.index(current_room) if current_room in room_options else 0
    selected_room = st.selectbox("📂 Room", room_options, index=default_room_idx)

# Get users/languages based on room selection
filter_room = None if selected_room == "All Rooms" else selected_room
available_users = history_manager.get_unique_users(filter_room)
available_langs = history_manager.get_unique_languages(filter_room)

with col_f2:
    lang_options = ["All Languages"] + available_langs
    selected_lang = st.selectbox("💻 Language", lang_options, index=0)

with col_f3:
    user_options = ["All Users"] + available_users
    # Default to current user if available
    current_user = st.session_state.get("username", "")
    default_user_idx = user_options.index(current_user) if current_user in user_options else 0
    selected_user = st.selectbox("👤 User", user_options, index=default_user_idx)

with col_f4:
    limit_options = [25, 50, 100, 200, 500]
    selected_limit = st.selectbox("📊 Max Records", limit_options, index=1)

# Apply filters
filter_lang = None if selected_lang == "All Languages" else selected_lang
filter_user = None if selected_user == "All Users" else selected_user

# Load history based on filters
if selected_room == "All Rooms":
    history = history_manager.get_all_history(
        language=filter_lang,
        user=filter_user,
        limit=selected_limit
    )
else:
    history = history_manager.get_room_history(
        room=selected_room,
        language=filter_lang,
        user=filter_user,
        limit=selected_limit
    )

# ============================================================================
# Statistics Section
# ============================================================================
st.markdown("---")
st.subheader("📊 Statistics")

if history:
    stats = history_manager.get_stats(filter_room)
    
    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.metric("Total Executions", stats["total_executions"])
    with m2:
        st.metric("Successful", stats["successful"])
    with m3:
        st.metric("Failed", stats["failed"])
    with m4:
        st.metric("Success Rate", f"{stats['success_rate']:.1f}%")
    with m5:
        st.metric("Avg Time (ms)", f"{stats['avg_time_ms']:.0f}")
    
    # Language breakdown
    if stats["by_language"]:
        with st.expander("📈 Breakdown by Language", expanded=False):
            lang_df = pd.DataFrame([
                {"Language": lang, "Executions": count}
                for lang, count in stats["by_language"].items()
            ])
            st.dataframe(lang_df, use_container_width=True, hide_index=True)
    
    # User breakdown
    if stats["by_user"]:
        with st.expander("👥 Breakdown by User", expanded=False):
            user_df = pd.DataFrame([
                {"User": user, "Executions": count}
                for user, count in stats["by_user"].items()
            ])
            st.dataframe(user_df, use_container_width=True, hide_index=True)
else:
    st.info("No execution history found. Run some code in the Code Editor to see history here.")

# ============================================================================
# History Table
# ============================================================================
st.markdown("---")
st.subheader("📋 Execution History")

if not history:
    st.warning("No executions match the current filters.")
    st.stop()

# Convert to DataFrame
df = pd.DataFrame(history)

# Format timestamp
df["time"] = pd.to_datetime(df["timestamp"], unit="s").dt.strftime("%Y-%m-%d %H:%M:%S")

# Create status column
df["status"] = df["success"].apply(lambda x: "✅ Success" if x else "❌ Failed")

# Display table with key columns
display_cols = ["time", "user", "room", "language", "status", "return_code", "time_ms"]
display_df = df[display_cols].copy()
display_df.columns = ["Time", "User", "Room", "Language", "Status", "Return Code", "Time (ms)"]

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
    height=400,
)

# ============================================================================
# Detailed View - Select and View Individual Executions
# ============================================================================
st.markdown("---")
st.subheader("🔎 Detailed View")

# Create selection options
if len(history) > 0:
    # Create labels for each execution
    exec_options = []
    for i, record in enumerate(history):
        ts = datetime.fromtimestamp(record["timestamp"]).strftime("%H:%M:%S")
        user = record.get("user", "unknown")
        lang = record.get("language", "unknown")
        status = "✅" if record.get("success") else "❌"
        label = f"{i+1}. [{ts}] {user} - {lang} {status}"
        exec_options.append(label)
    
    selected_exec_idx = st.selectbox(
        "Select an execution to view details:",
        range(len(exec_options)),
        format_func=lambda x: exec_options[x],
        index=0
    )
    
    selected_record = history[selected_exec_idx]
    
    # Display details in tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📝 Code", "📤 Output", "📥 Input", "ℹ️ Info"])
    
    with tab1:
        st.markdown("**Code Executed:**")
        lang_for_display = selected_record.get("language", "python")
        if lang_for_display == "cpp":
            lang_for_display = "cpp"
        st.code(selected_record.get("code", "[No code]"), language=lang_for_display)
    
    with tab2:
        col_out1, col_out2 = st.columns(2)
        with col_out1:
            st.markdown("**stdout:**")
            stdout = selected_record.get("stdout", "") or "[No stdout]"
            st.text_area("stdout", value=stdout, height=200, disabled=True, label_visibility="collapsed")
        with col_out2:
            st.markdown("**stderr:**")
            stderr = selected_record.get("stderr", "") or "[No stderr]"
            st.text_area("stderr", value=stderr, height=200, disabled=True, label_visibility="collapsed")
    
    with tab3:
        st.markdown("**stdin (Program Input):**")
        stdin = selected_record.get("stdin", "") or "[No stdin provided]"
        st.text_area("stdin", value=stdin, height=150, disabled=True, label_visibility="collapsed")
    
    with tab4:
        info_col1, info_col2 = st.columns(2)
        with info_col1:
            st.markdown("**Execution Details:**")
            st.write(f"- **Timestamp:** {datetime.fromtimestamp(selected_record['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}")
            st.write(f"- **User:** {selected_record.get('user', 'unknown')}")
            st.write(f"- **Room:** {selected_record.get('room', 'unknown')}")
            st.write(f"- **Language:** {selected_record.get('language', 'unknown')}")
        with info_col2:
            st.markdown("**Results:**")
            st.write(f"- **Success:** {'Yes ✅' if selected_record.get('success') else 'No ❌'}")
            st.write(f"- **Return Code:** {selected_record.get('return_code', 'N/A')}")
            st.write(f"- **Execution Time:** {selected_record.get('time_ms', 0)} ms")
            if selected_record.get("id"):
                st.write(f"- **ID:** `{selected_record.get('id')}`")

# ============================================================================
# Session History (Current Session Only)
# ============================================================================
st.markdown("---")
with st.expander("📦 Current Session History (in-memory)", expanded=False):
    session_history = st.session_state.get("exec_history", [])
    if session_history:
        st.caption(f"Showing {len(session_history)} executions from this browser session only.")
        session_df = pd.DataFrame(session_history)
        session_df["time"] = pd.to_datetime(session_df["timestamp"], unit="s").dt.strftime("%H:%M:%S")
        session_df["status"] = session_df["success"].apply(lambda x: "✅" if x else "❌")
        display_session = session_df[["time", "user", "language", "status", "time_ms"]].copy()
        display_session.columns = ["Time", "User", "Language", "Status", "Time (ms)"]
        st.dataframe(display_session, use_container_width=True, hide_index=True)
    else:
        st.info("No executions in current session yet.")

# ============================================================================
# Footer
# ============================================================================
st.markdown("---")
st.caption(
    "💡 **Note:** Execution history is stored persistently in `data/exec_history/` directory. "
    "Each room has its own history file. History is preserved across server restarts."
)
