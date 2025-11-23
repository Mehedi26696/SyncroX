import os
import sys
from pathlib import Path

# --- Make project root importable ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import streamlit as st
from PIL import Image

# ============================================================================
# SYNCRO-X MAIN APP - WELCOME & ROOM MANAGEMENT
# ============================================================================

st.set_page_config(
    page_title="SyncroX", 
    page_icon="/assets/logo.png", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Apply custom CSS for Raleway font and black background
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
    }
    
    h1, h2, h3, h4, h5, h6, p, div, span, label, button {
        font-family: 'Raleway', sans-serif !important;
    }
    div.stButton > button {
        background-color: #03C084 !important;
        color: black !important;
        border-radius: 8px;
        border: none;
        font-weight: 800 !important;
    }
    div.stButton > button:hover {
        background-color: #218838 !important;
        color: white !important;
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
        <div style="text-align: center; font-size: 1rem; color: #9ca3af;">
            Built  by
            <a href="https://github.com/Abs-Futy7" target="_blank" style="color:#03C084; text-decoration:none;">
                MD. Abu Bakar Siddique (@Abs-Futy7)
            </a>
            &nbsp;and&nbsp;
            <a href="https://github.com/Mehedi26696" target="_blank" style="color:#03C084; text-decoration:none;">
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
        
        st.markdown("<h2 style='text-align: center; font-family: Raleway ; font-weight: 400; font-color: white;'>Collaborative Platform for Real-time Chat, Code Editing & File Sharing</h2>", unsafe_allow_html=True)

        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Username input
        st.markdown("### Enter Your Name")
        username = st.text_input(
            "Username",
            placeholder="Enter your name...",
            key="username_input",
            label_visibility="collapsed"
        )
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Room selection
        st.markdown("### Room Management")
        
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
        st.markdown("<h3 style='text-align:center; color:white;'>What can you do with SyncroX?</h3>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        # Custom CSS for feature boxes
        st.markdown("""
        <style>
        .feature-box {
            border: 1.5px solid #03C084;
            border-radius: 12px;
            padding: 18px;
            margin-bottom: 20px;
            background: #0a0a0a;
            box-shadow: 0 0 10px rgba(3, 192, 132, 0.15);
            transition: 0.2s ease-in-out;
        }
        .feature-box:hover {
            box-shadow: 0 0 20px rgba(3, 192, 132, 0.35);
            transform: translateY(-3px);
        }
        .feature-title {
            color: gray;
            font-size: 28px;
            font-weight: 600;
        }
        </style>
        """, unsafe_allow_html=True)

        feat_col1, feat_col2 = st.columns(2)

        with feat_col1:
            st.markdown("""
            <div class="feature-box">
                <div class="feature-title">Real-time Chat</div>
                <span style="color:#d0d0d0;">Instant messaging with room-based conversations</span>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("""
            <div class="feature-box">
                <div class="feature-title">File Transfer</div>
                <span style="color:#d0d0d0;">Secure file sharing within your room</span>
            </div>
            """, unsafe_allow_html=True)

        with feat_col2:
            st.markdown("""
            <div class="feature-box">
                <div class="feature-title">Collaborative Code Editor</div>
                <span style="color:#d0d0d0;">Live code editing with execution support</span>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("""
            <div class="feature-box">
                <div class="feature-title">Dashboard</div>
                <span style="color:#d0d0d0;">Monitor connections and system status</span>
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
        color: #03C084 !important;
        font-weight: 700 !important;
    }

    /* Sidebar info box */
    .stAlert {
        background-color: #0d0d0d !important;
        border-left: 4px solid #03C084 !important;
        color: white !important;
    }

    /* Sidebar nav buttons override (stronger than global) */
    [data-testid="stSidebar"] button {
        background-color: #03C084 !important;
        color: black !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
        margin-bottom: 8px !important;
        border: none !important;
    }
    [data-testid="stSidebar"] button:hover {
        background-color: #02a673 !important;
        color: white !important;
    }

    /* Logout secondary button */
    button[kind="secondary"] {
        background-color: #111 !important;
        color: white !important;
        border: 1px solid #444 !important;
    }
    button[kind="secondary"]:hover {
        border-color: #03C084 !important;
        background-color: #1a1a1a !important;
    }

    /* Feature card styling */
    .feature-card {
        border: 1.5px solid #03C08433;
        border-radius: 14px;
        padding: 20px;
        background-color: #0b0b0b;
        box-shadow: 0 0 10px rgba(3, 192, 132, 0.15);
        transition: 0.25s;
        height: 180px;
    }
    .feature-card:hover {
        border-color: #03C084;
        box-shadow: 0 0 22px rgba(3, 192, 132, 0.45);
        transform: translateY(-4px);
    }
    .feature-card h4 {
        color: #03C084 !important;
        font-weight: 700 !important;
        margin-bottom: 8px !important;
    }
    .feature-card p {
        color: #cfcfcf !important;
        font-size: 14px !important;
    }

    /* Metric cards (Room Activity) */
    .stMetric {
        background-color: #0b0b0b !important;
        padding: 18px !important;
        border-radius: 14px !important;
        border: 1.5px solid #03C08433 !important;
        box-shadow: 0px 0px 12px rgba(3, 192, 132, 0.2);
    }
    .stMetric:hover {
        border-color: #03C084 !important;
        box-shadow: 0px 0px 20px rgba(3, 192, 132, 0.35);
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Sidebar - User info and navigation
    with st.sidebar:
        st.markdown("### 👤 User Information")
        st.info(f"**Name:** {st.session_state.username}\n\n**Room:** `{st.session_state.current_room}`")
        
        st.markdown("---")
        
        st.markdown("### 🧭 Navigation")
        st.caption("Select a feature below:")
        
        # Navigation buttons
        if st.button("💬 Chat", use_container_width=True):
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
            st.rerun()
    
    # Main content area
    st.markdown(f"# 🔄 SyncroX - Room `{st.session_state.current_room}`")
    
    st.markdown("---")
    
    # Feature cards
    st.markdown("### Choose a feature to get started:")
    
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
    st.markdown("### 📈 Room Activity")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric("Room Code", st.session_state.current_room)
    with col_b:
        st.metric("Your Username", st.session_state.username)
    with col_c:
        st.metric("Status", "🟢 Connected")
    
    st.markdown("---")
    
    # Info section
    st.info(
        "💡 **Tip:** Use the sidebar on the left to navigate between features. "
        "All features in this room are synchronized in real-time!"
    )

    # Footer on main app page
    render_footer()


if __name__ == "__main__":
    main()
