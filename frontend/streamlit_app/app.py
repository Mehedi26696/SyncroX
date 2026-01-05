import os
import sys
from pathlib import Path

# --- Make project root importable ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Add components folder to path
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

import streamlit as st
from PIL import Image
from components.sidebar import render_sidebar

# ============================================================================
# SYNCRO-X MAIN APP - WELCOME & ROOM MANAGEMENT
# ============================================================================

st.set_page_config(
    page_title="SyncroX", 
    page_icon="/assets/logo.png", 
    layout="wide",
    
)

# Apply custom CSS for Raleway font and new color scheme
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
    }
    
    /* Sidebar text colors */
    [data-testid="stSidebar"] h3 {
        color: #000000 !important;
    }
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] div,
    [data-testid="stSidebar"] label {
        color: #000000 !important;
    }
    [data-testid="stSidebar"] .stMarkdown {
        color: #000000 !important;
    }
    
    /* Sidebar info/alert box text */
    [data-testid="stSidebar"] [data-testid="stNotificationContentInfo"] {
        color: #000000 !important;
    }
    
    h1, h2, h3, h4, h5, h6, p, div, span, label, button {
        font-family: 'Raleway', sans-serif !important;
    }
    
    h1 { font-size: 3rem !important; }
    h2 { font-size: 2.5rem !important; }
    h3 { font-size: 2rem !important; }
    h4 { font-size: 1.5rem !important; }
    
    /* Tab labels styling */
    .stTabs [data-baseweb="tab-list"] button {
        color: #6b7280 !important;
        font-size: 2rem !important;
        font-weight: 600 !important;
        border: 2px solid #6b7280 !important;
        border-radius: 8px !important;
        margin-right: 8px !important;
        padding: 0.5rem 1rem !important;
    }
    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
        color: #087f5b !important;
        border-color: #087f5b !important;
        background-color: rgba(8, 127, 91, 0.1) !important;
    }
    
    /* Remove tab underline indicator */
    .stTabs [data-baseweb="tab-highlight"] {
        display: none !important;
    }
    .stTabs [data-baseweb="tab-border"] {
        display: none !important;
    }
    
    div.stButton > button {
        background-color: #087f5b !important;
        color: #ebfbee !important;
        border-radius: 8px;
        border: none;
        font-weight: 800 !important;
        font-size: 1.3rem !important;
        padding: 0.6rem 1rem !important;
    }
    div.stButton > button:hover {
        background-color: #006E6D !important;
        color: #ebfbee !important;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "username" not in st.session_state:
    st.session_state.username = ""
if "current_room" not in st.session_state:
    st.session_state.current_room = ""
if "is_logged_in" not in st.session_state:
    st.session_state.is_logged_in = False


def render_footer():
    """Shared footer for all views"""
    st.markdown(
        """
        <hr style="border: 0; border-top: 1px solid #1f2933; margin-top: 3rem; margin-bottom: 0.75rem;" />
        <div style="text-align: center; font-size: 1.2rem; color: #2b8a3e;">
            Built  by
            <a href="https://github.com/Abs-Futy7" target="_blank" style="color:#087f5b; text-decoration:none; font-weight: 600;">
                MD. Abu Bakar Siddique (@Abs-Futy7)
            </a>
            &nbsp;and&nbsp;
            <a href="https://github.com/Mehedi26696" target="_blank" style="color:#087f5b; text-decoration:none; font-weight: 600;">
                H. M. Mehedi Hasan (@Mehedi26696)
            </a>
        </div>
        """,
        unsafe_allow_html=True,
    )


def main():
    # ========================================================================
    # WELCOME PAGE - User not logged in
    # ========================================================================
    if not st.session_state.is_logged_in:
        render_welcome_page()
        return
    
    # ========================================================================
    # MAIN APP - User logged in with room
    # ========================================================================
    render_main_app()


def render_welcome_page():
    """Welcome page with room creation/joining"""
    
    # Center the welcome content
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Display logo
        logo_path = os.path.join(PROJECT_ROOT, "assets", "logo.png")
        if os.path.exists(logo_path):
            logo = Image.open(logo_path)
            st.image(logo, use_column_width=True)
        
        st.markdown("<h2 style='text-align: center; font-family: Raleway ; font-weight: 400; color: #087f5b;'>Collaborative Platform for Real-time Chat, Code Editing & File Sharing</h2>", unsafe_allow_html=True)

        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Username input
        st.markdown("<h3 style='color: #6b7280;'>Enter Your Name</h3>", unsafe_allow_html=True)
        username = st.text_input(
            "Username",
            placeholder="Enter your name...",
            key="username_input",
            label_visibility="collapsed"
        )
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Room selection
        st.markdown("<h3 style='color: #6b7280;'>Room Management</h3>", unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["📝 Create New Room", "🔑 Join Existing Room"])
        
        with tab1:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Generate 4-Digit Room Code", use_container_width=True, type="primary"):
                if not username.strip():
                    st.error("⚠️ Please enter your name first!")
                else:
                    import random
                    room_code = f"{random.randint(1000, 9999)}"
                    st.session_state.username = username.strip()
                    st.session_state.current_room = room_code
                    st.session_state.is_logged_in = True
                    st.success(f"✅ Room **{room_code}** created! Redirecting...")
                    st.rerun()
        
        with tab2:
            st.markdown("<br>", unsafe_allow_html=True)
            room_code = st.text_input(
                "Enter 4-digit room code",
                max_chars=4,
                placeholder="1234",
                key="join_room_input",
                label_visibility="collapsed"
            )
            
            if st.button("🚀 Join Room", use_container_width=True, type="primary"):
                if not username.strip():
                    st.error("⚠️ Please enter your name first!")
                elif not room_code or len(room_code) != 4 or not room_code.isdigit():
                    st.error("⚠️ Please enter a valid 4-digit room code!")
                else:
                    st.session_state.username = username.strip()
                    st.session_state.current_room = room_code
                    st.session_state.is_logged_in = True
                    st.success(f"✅ Joined room **{room_code}**! Redirecting...")
                    st.rerun()
        
        st.markdown("<br><br>", unsafe_allow_html=True)
        
        # --- Features section (boxed layout) ---
        st.markdown("<h3 style='text-align:center; color:#087f5b; font-size: 2.2rem;'>What can you do with SyncroX?</h3>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        # Custom CSS for feature boxes
        st.markdown("""
        <style>
        .feature-box {
            border: 2px solid #087f5b;
            border-radius: 12px;
            padding: 22px;
            margin-bottom: 20px;
            background: #d3f9d8;
            box-shadow: 0 0 10px rgba(8, 127, 91, 0.15);
            transition: 0.2s ease-in-out;
        }
        .feature-box:hover {
            box-shadow: 0 0 20px rgba(8, 127, 91, 0.35);
            transform: translateY(-3px);
        }
        .feature-title {
            color: #087f5b;
            font-size: 32px;
            font-weight: 600;
        }
        </style>
        """, unsafe_allow_html=True)

        feat_col1, feat_col2 = st.columns(2)

        with feat_col1:
            st.markdown("""
            <div class="feature-box">
                <div class="feature-title">Real-time Chat</div>
                <span style="color:#2b8a3e; font-size: 1.1rem;">Instant messaging with room-based conversations</span>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("""
            <div class="feature-box">
                <div class="feature-title">File Transfer</div>
                <span style="color:#2b8a3e; font-size: 1.1rem;">Secure file sharing within your room</span>
            </div>
            """, unsafe_allow_html=True)

        with feat_col2:
            st.markdown("""
            <div class="feature-box">
                <div class="feature-title">Collaborative Code Editor</div>
                <span style="color:#2b8a3e; font-size: 1.1rem;">Live code editing with execution support</span>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("""
            <div class="feature-box">
                <div class="feature-title">Dashboard</div>
                <span style="color:#2b8a3e; font-size: 1.1rem;">Monitor connections and system status</span>
            </div>
            """, unsafe_allow_html=True)

        # Footer on welcome page
        render_footer()


def render_main_app():
    """Main app interface after login"""

    # Extra CSS just for the after-login UI
    st.markdown("""
    <style>
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

    /* Sidebar nav buttons override (stronger than global) */
    [data-testid="stSidebar"] button {
        background-color: #087f5b !important;
        color: #ebfbee !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
        margin-bottom: 8px !important;
        border: none !important;
        font-size: 1.1rem !important;
        padding: 0.6rem 1rem !important;
    }
    [data-testid="stSidebar"] button:hover {
        background-color: #006E6D !important;
        color: #ebfbee !important;
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

    /* Feature card styling */
    .feature-card {
        border: 2px solid #087f5b;
        border-radius: 14px;
        padding: 24px;
        background-color: #d3f9d8;
        box-shadow: 0 0 10px rgba(8, 127, 91, 0.15);
        transition: 0.25s;
        height: 200px;
    }
    .feature-card:hover {
        border-color: #006E6D;
        box-shadow: 0 0 22px rgba(8, 127, 91, 0.45);
        transform: translateY(-4px);
    }
    .feature-card h4 {
        color: #087f5b !important;
        font-weight: 700 !important;
        margin-bottom: 10px !important;
        font-size: 1.5rem !important;
    }
    .feature-card p {
        color: #2b8a3e !important;
        font-size: 1.1rem !important;
    }

    /* Metric cards (Room Activity) */
    .stMetric {
        background-color: #d3f9d8 !important;
        padding: 20px !important;
        border-radius: 14px !important;
        border: 2px solid #087f5b !important;
        box-shadow: 0px 0px 12px rgba(8, 127, 91, 0.2);
    }
    .stMetric:hover {
        border-color: #006E6D !important;
        box-shadow: 0px 0px 20px rgba(8, 127, 91, 0.35);
    }
    .stMetric label {
        color: #374151 !important;
        font-size: 1.2rem !important;
        font-weight: 600 !important;
    }
    .stMetric [data-testid="stMetricValue"] {
        color: #1f2937 !important;
        font-size: 2.2rem !important;
        font-weight: 700 !important;
    }
    .stMetric div {
        color: #1f2937 !important;
    }
    .stMetric [data-testid="stMetricValue"] > div {
        color: #1f2937 !important;
    }
    [data-testid="stMetricLabel"] {
        color: #374151 !important;
    }
    [data-testid="stMetricValue"] {
        color: #1f2937 !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Sidebar - Shared component
    render_sidebar(current_page="home")
    
    # Main content area
    st.markdown(f"<h1 style='color: #4b5563;'>🔄 SyncroX - Room <code>{st.session_state.current_room}</code></h1>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Feature cards
    st.markdown("<h3 style='color: #6b7280;'>Choose a feature to get started:</h3>", unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div class="feature-card">
            <h4>💬 Chat</h4>
            <p>Real-time messaging with all room members</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Open Chat →", use_container_width=True, key="nav_chat"):
            st.switch_page("pages/chat.py")
    
    with col2:
        st.markdown("""
        <div class="feature-card">
            <h4>🤝 Code Editor</h4>
            <p>Collaborate on code in real-time</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Open Editor →", use_container_width=True, key="nav_editor"):
            st.switch_page("pages/code_editor.py")
    
    with col3:
        st.markdown("""
        <div class="feature-card">
            <h4>📁 File Manager</h4>
            <p>Share files securely with your team</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Open Files →", use_container_width=True, key="nav_files"):
            st.switch_page("pages/file_manager.py")
    
    with col4:
        st.markdown("""
        <div class="feature-card">
            <h4>📊 Dashboard</h4>
            <p>Monitor server status and metrics</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Open Dashboard →", use_container_width=True, key="nav_dash"):
            st.switch_page("pages/dashboard_page.py")
    
    st.markdown("---")
    
    # Quick stats
    st.markdown("<h3 style='color: #6b7280;'>📈 Room Activity</h3>", unsafe_allow_html=True)
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric("Room Code", st.session_state.current_room)
    with col_b:
        st.metric("Your Username", st.session_state.username)
    with col_c:
        st.metric("Status", "🟢 Connected")
    
    st.markdown("---")
    
    
    # Footer on main app page
    render_footer()


if __name__ == "__main__":
    main()
