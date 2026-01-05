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

st.set_page_config(
    page_title="Execution Output - SyncroX",
    page_icon=page_icon,
    layout="wide",
   
)

# Basic styling (SyncroX theme)
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
        color: #000000 !important;
        border-radius: 8px !important;
        border: none !important;
        font-weight: 700 !important;
        margin-bottom: 8px !important;
        padding: 0.6rem 1rem !important;
        font-size: 1.1rem !important;
    }
    [data-testid="stSidebar"] button p,
    [data-testid="stSidebar"] button span,
    [data-testid="stSidebar"] button div,
    [data-testid="stSidebar"] button * {
        color: #000000 !important;
    }
    [data-testid="stSidebar"] button:hover {
        background-color: #006E6D !important;
        color: #000000 !important;
    }
    [data-testid="stSidebar"] button:hover * {
        color: #000000 !important;
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
""", unsafe_allow_html=True)

# --- Login check ---
if not st.session_state.get("is_logged_in", False):
    st.error("⚠️ Please login first!")
    if st.button("Go to Home"):
        st.switch_page("app.py")
    st.stop()

# Sidebar - shared component
from components.sidebar import render_sidebar
render_sidebar(current_page="exec_output")

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
