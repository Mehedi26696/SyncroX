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
# SERVER_HOST = "10.22.39.83"
SERVER_HOST = "127.0.0.1"

# Server ports (usually don't need to change these)
CHAT_PORT = 9009
FILE_PORT = 9010
COLLAB_PORT = 9011
EXEC_PORT = 9012
ROOM_MGMT_PORT = 9013


# Streamlit frontend port
FRONTEND_PORT = 8501

# =============================
# FILE TRANSFER SIMULATION
# =============================
# Set the probability of simulated packet loss (0.0 = no loss, 0.1 = 10% loss, 0.5 = 50% loss)
# Used by file_transfer client and server for testing Tahoe/Reno
# WARNING: Non-zero values will cause upload failures until retransmission logic is added
SYNCROX_LOSS_PROB = 0.1  # Set to 0.0 for reliable transfers

# =============================
# NETWORKING CONSTANTS
# =============================
CHUNK_SIZE = 4096
ALPHA = 0.125
BETA = 0.25
MIN_RTO = 200.0
INITIAL_CWND = 1.0
INITIAL_SSTHRESH = 16.0
DEFAULT_RWND = 32

# =============================
# TIMEOUTS & RETRIES
# =============================
HANDSHAKE_TIMEOUT = 5.0
TERMINATION_TIMEOUT = 3.0
MAX_RETRIES = 5
UDP_RECV_TIMEOUT = 1.0
TOTAL_DOWNLOAD_TIMEOUT = 30.0
