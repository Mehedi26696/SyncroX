"""
Shared sidebar component for SyncroX pages.
Import and call render_sidebar(current_page) in each page.
"""
import streamlit as st
import uuid


def render_sidebar(current_page: str = "home"):
    """
    Render the common sidebar with user info and navigation.
    
    Args:
        current_page: One of "home", "chat", "code_editor", "file_manager", "dashboard"
                     The current page button will be disabled.
    """
    # Generate unique key prefix for this render to avoid duplicate widget IDs
    if "sidebar_key_prefix" not in st.session_state:
        st.session_state.sidebar_key_prefix = str(uuid.uuid4())[:8]
    key_prefix = st.session_state.sidebar_key_prefix
    
    with st.sidebar:
        # User info section
        st.markdown("### 👤 Session Info")
        username = st.session_state.get("username", "Guest")
        room = st.session_state.get("current_room", "None")
        
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #087f5b 0%, #0ca678 100%); 
                    padding: 1rem; border-radius: 10px; margin-bottom: 1rem;">
            <p style="color: white; margin: 0; font-size: 0.9rem;">👤 <strong>{username}</strong></p>
            <p style="color: rgba(255,255,255,0.9); margin: 0.5rem 0 0 0; font-size: 0.85rem;">
                🔑 Room: <code style="background: #fff; color: #111; padding: 2px 6px; border-radius: 4px;">{room}</code>
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Navigation section
        st.markdown("### 🧭 Navigate")
        
        # Navigation buttons with icons
        nav_items = [
            ("🏠 Home", "home", "app.py"),
            ("💬 Chat", "chat", "pages/chat.py"),
            ("🤝 Code Editor", "code_editor", "pages/code_editor.py"),
            ("📁 File Manager", "file_manager", "pages/file_manager.py"),
            ("📜 Exec History", "exec_output", "pages/exec_output.py"),
            ("📊 Dashboard", "dashboard", "pages/dashboard_page.py"),
        ]
        
        for label, page_id, page_path in nav_items:
            is_current = (page_id == current_page)
            if st.button(
                label, 
                use_container_width=True, 
                disabled=is_current,
                key=f"{key_prefix}_nav_{page_id}"
            ):
                st.switch_page(page_path)
        
        st.markdown("---")
        
        # Logout section
        st.markdown("### ⚙️ Actions")
        if st.button("🚪 Leave Room", use_container_width=True, type="secondary", key=f"{key_prefix}_logout_btn"):
            # Clear session state
            st.session_state.is_logged_in = False
            st.session_state.username = ""
            st.session_state.current_room = ""
            
            # Clear all client connections
            keys_to_remove = [key for key in st.session_state.keys() 
                            if key.endswith('_client') or key.startswith(('chat_', 'collab_', 'exec_', 'ft_'))]
            for key in keys_to_remove:
                try:
                    del st.session_state[key]
                except:
                    pass
            st.switch_page("app.py")
        
        # Footer info
        st.markdown("---")
        st.caption("SyncroX v1.0")
        st.caption("🌐 Collaborative Platform")
