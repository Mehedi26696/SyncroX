import os
import sys
from pathlib import Path

# --- Make project root importable ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import streamlit as st

# ============================================================================
# SYNCRO-X MAIN APP - WELCOME & ROOM MANAGEMENT
# ============================================================================

st.set_page_config(
    page_title="SyncroX", 
    page_icon="🔄", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if "username" not in st.session_state:
    st.session_state.username = ""
if "current_room" not in st.session_state:
    st.session_state.current_room = ""
if "is_logged_in" not in st.session_state:
    st.session_state.is_logged_in = False


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
        st.markdown("<h1 style='text-align: center;'>🔄 Welcome to SyncroX</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; font-size: 1.2em; color: #888;'>Collaborative Platform for Real-time Chat, Code Editing & File Sharing</p>", unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Username input
        st.markdown("### 👤 Enter Your Name")
        username = st.text_input(
            "Username",
            placeholder="Enter your name...",
            key="username_input",
            label_visibility="collapsed"
        )
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Room selection
        st.markdown("### 🚪 Room Management")
        
        tab1, tab2 = st.tabs(["📝 Create New Room", "🔑 Join Existing Room"])
        
        with tab1:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🎲 Generate 4-Digit Room Code", use_container_width=True, type="primary"):
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
        
        # Features section
        with st.expander("✨ What can you do with SyncroX?"):
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**💬 Real-time Chat**")
                st.caption("Instant messaging with room-based conversations")
                st.markdown("**📁 File Transfer**")
                st.caption("Secure file sharing within your room")
            with col_b:
                st.markdown("**🤝 Collaborative Code Editor**")
                st.caption("Live code editing with execution support")
                st.markdown("**📊 Dashboard**")
                st.caption("Monitor connections and system status")


def render_main_app():
    """Main app interface after login"""
    
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
        st.markdown("#### 💬 Chat")
        st.markdown("Real-time messaging with all room members")
        if st.button("Open Chat →", use_container_width=True, key="nav_chat"):
            st.switch_page("pages/chat.py")
    
    with col2:
        st.markdown("#### 🤝 Code Editor")
        st.markdown("Collaborate on code in real-time")
        if st.button("Open Editor →", use_container_width=True, key="nav_editor"):
            st.switch_page("pages/code_editor.py")
    
    with col3:
        st.markdown("#### 📁 File Manager")
        st.markdown("Share files securely with your team")
        if st.button("Open Files →", use_container_width=True, key="nav_files"):
            st.switch_page("pages/file_manager.py")
    
    with col4:
        st.markdown("#### 📊 Dashboard")
        st.markdown("Monitor server status and metrics")
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


if __name__ == "__main__":
    main()
