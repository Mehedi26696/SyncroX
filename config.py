"""
SyncroX Configuration

Change SERVER_HOST to the IP address of the machine running the servers.
- For local development: "127.0.0.1"
- For LAN access: Use server's IP, e.g., "192.168.1.100"
- To find your IP on Windows: Run 'ipconfig' in terminal
- To find your IP on Linux/Mac: Run 'ifconfig' or 'ip addr'
"""

# ============================================================================
# SERVER CONFIGURATION
# ============================================================================

# Change this to your server's IP address for multi-device access
SERVER_HOST = "10.22.39.83"
# SERVER_HOST = "127.0.0.1"

# Server ports (usually don't need to change these)
CHAT_PORT = 9009
FILE_PORT = 9010
COLLAB_PORT = 9011
EXEC_PORT = 9012

# Streamlit frontend port
FRONTEND_PORT = 8501
