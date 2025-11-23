import os
import sys
import time
from pathlib import Path

import streamlit as st
import pandas as pd
from PIL import Image

# --- Make project root importable (same style as other pages) ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

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
st.title("📜 Execution Output & History")

history = st.session_state.get("exec_history", [])

# Latest output (what the collab page shows)
st.subheader("Latest execution (this session)")
last_output = st.session_state.get("collab_output", "")
if last_output:
    st.text_area("Most recent output", value=last_output, height=180, disabled=True)
else:
    st.info("No execution output yet in this session. Go to the Code Editor and run some code.")

st.markdown("---")

if not history:
    st.info("No execution history recorded yet. Once you run code in the Collab editor, runs will appear here.")
    st.stop()

# Convert to DataFrame for easier filtering
df = pd.DataFrame(history)

# Make timestamp human readable
df["time"] = pd.to_datetime(df["timestamp"], unit="s")

# ---- Filters ----
st.subheader("Filters")

rooms = sorted(df["room"].dropna().unique().tolist())
current_room = st.session_state.current_room
if current_room in rooms:
    default_room_idx = rooms.index(current_room)
else:
    default_room_idx = 0

col_f1, col_f2, col_f3 = st.columns(3)

with col_f1:
    selected_room = st.selectbox("Room", rooms, index=default_room_idx)

with col_f2:
    langs = ["(all)"] + sorted(df["language"].dropna().unique().tolist())
    selected_lang = st.selectbox("Language", langs, index=0)

with col_f3:
    users = ["(all)"] + sorted(df["user"].dropna().unique().tolist())
    selected_user = st.selectbox("User", users, index=0)

# Apply filters
mask = df["room"] == selected_room
if selected_lang != "(all)":
    mask &= df["language"] == selected_lang
if selected_user != "(all)":
    mask &= df["user"] == selected_user

df_filtered = df[mask].sort_values("time", ascending=False)

if df_filtered.empty:
    st.warning("No executions match the current filters.")
    st.stop()

# ---- Summary metrics for the filtered data ----
st.subheader("Summary (filtered)")

latest = df_filtered.iloc[0]

m1, m2, m3 = st.columns(3)
with m1:
    st.metric("Latest language", latest["language"])
with m2:
    st.metric("Return code", latest["return_code"])
with m3:
    st.metric("Execution time (ms)", f"{latest['time_ms']:.0f}")

st.caption(
    "These metrics correspond to the most recent run that matches your filters."
)

# ---- Detailed view of the latest run ----
st.subheader("Latest run details")

with st.expander("🔍 Code used in latest run", expanded=False):
    st.code(latest["code"], language=latest["language"] if latest["language"] != "cpp" else "c++")

cols_out = st.columns(2)
with cols_out[0]:
    st.markdown("**Stdout**")
    st.text_area("stdout", latest["stdout"] or "[no stdout]", height=200, disabled=True, label_visibility="collapsed")
with cols_out[1]:
    st.markdown("**Stderr**")
    st.text_area("stderr", latest["stderr"] or "[no stderr]", height=200, disabled=True, label_visibility="collapsed")

st.markdown("---")

# ---- Table of all matching runs ----
st.subheader("Execution history table")

show_cols = ["time", "user", "room", "language", "success", "return_code", "time_ms"]
st.dataframe(
    df_filtered[show_cols].rename(
        columns={
            "time": "Time",
            "user": "User",
            "room": "Room",
            "language": "Language",
            "success": "OK?",
            "return_code": "RC",
            "time_ms": "Time (ms)",
        }
    ),
    use_container_width=True,
    hide_index=True,
)

st.caption(
    "This table shows all runs for the selected room / language / user in the current Streamlit session. "
    "You can take screenshots of this table for your report to show how different languages and rooms behaved."
)
