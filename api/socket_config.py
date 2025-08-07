"""
Socket configuration for proper port reuse
Top 0.1% approach: Prevent port locks before they happen
"""

import socket
import sys

def configure_socket_reuse():
    """
    Configure socket to allow immediate port reuse.
    This prevents "Address already in use" errors.
    """
    # Monkey-patch socket creation to add SO_REUSEADDR
    original_socket = socket.socket
    
    def socket_with_reuse(*args, **kwargs):
        sock = original_socket(*args, **kwargs)
        # Enable address reuse
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # On some systems, also need SO_REUSEPORT
        if hasattr(socket, 'SO_REUSEPORT'):
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        return sock
    
    socket.socket = socket_with_reuse
    
def setup_graceful_shutdown(cleanup_func=None):
    """
    Setup signal handlers for graceful shutdown
    """
    import signal
    import atexit
    
    def signal_handler(signum, frame):
        print(f"\n🛑 Received signal {signum}, shutting down gracefully...")
        if cleanup_func:
            cleanup_func()
        sys.exit(0)
    
    # Register handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Also register cleanup on normal exit
    if cleanup_func:
        atexit.register(cleanup_func)