"""
Network Discovery Utility for Ziref.
Provides helpers for detecting the host machine's local Wi-Fi / LAN IP address
so physical Android devices on the same local network can connect seamlessly.
"""

import socket
import logging

logger = logging.getLogger("ziref.network")


def get_local_lan_ip() -> str:
    """
    Determines the local LAN IP address of this machine that routes outbound traffic.
    Works by creating a UDP connection to a public IP (without sending packets)
    to query the OS kernel for the preferred local routing interface.
    """
    # Strategy 1: Outbound UDP route probe
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.2)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith("127."):
            return ip
    except Exception as e:
        logger.debug(f"UDP route probe failed: {e}")

    # Strategy 2: Hostname resolution fallback
    try:
        hostname = socket.gethostname()
        candidates = socket.gethostbyname_ex(hostname)[2]
        for ip in candidates:
            if not ip.startswith("127.") and not ip.startswith("169.254."):
                return ip
    except Exception as e:
        logger.debug(f"Hostname resolution failed: {e}")

    # Fallback to localhost if no network interface is found
    return "127.0.0.1"
