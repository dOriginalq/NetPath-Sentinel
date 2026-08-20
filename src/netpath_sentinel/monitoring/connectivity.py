"""
monitoring/connectivity.py — Basic Network Connectivity Checks

Detects whether the network interface is up and whether the Internet
is reachable, using low-level socket and psutil APIs.

Key concepts:
    TCP Connect:
        Rather than sending a full HTTP request, we attempt to open a
        TCP socket to a well-known server. If the three-way handshake
        succeeds (SYN → SYN-ACK → ACK), the path is clear. This tests:
        - DNS resolution (if we use a hostname)
        - Routing to the target
        - The remote server accepting connections
        Using a raw IP (e.g., "8.8.8.8") skips DNS, isolating network
        reachability from DNS health.

    Network Interface:
        The OS assigns each physical or virtual NIC (Network Interface Card)
        a name (e.g., "Wi-Fi", "Ethernet"). psutil lets us query which
        interfaces exist, whether they are "up", and how many bytes they
        have transferred. An interface with zero bytes sent/received is
        physically connected but not in use.
"""

import socket
from typing import Optional

import psutil


# Interface names to ignore — these are not real network paths
_LOOPBACK_PREFIXES = ("Loopback", "lo")


def check_tcp_connect(host: str, port: int, timeout: float = 2.0) -> bool:
    """
    Attempt a TCP connection and return True if it succeeds.

    This is our primary "is the Internet reachable?" probe.
    We use port 443 (HTTPS) to a stable public IP, which is almost
    never blocked by ISPs (unlike ICMP which can be rate-limited).

    Args:
        host: IP address or hostname to connect to.
        port: TCP port number.
        timeout: Seconds to wait before declaring failure.

    Returns:
        True if the TCP handshake completed, False on any failure.
    """
    try:
        # socket.create_connection() does DNS resolution + TCP connect
        # in one step. Using a context manager ensures the socket is
        # properly closed even if an exception occurs.
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def get_active_interface() -> Optional[str]:
    """
    Find the name of the currently active network interface.

    Algorithm:
        1. Get all interface statistics (is it up? what speed?)
        2. Get all interface byte counters (how much traffic has it seen?)
        3. Skip loopback interfaces — they don't represent Internet access
        4. Return the first interface that is both "up" and has transferred data

    Why check byte counters?
        An interface can be "up" (enabled) but carry no traffic if it has
        no IP address assigned or is not the default route. Checking for
        non-zero bytes is a simple heuristic to find the *active* interface.

    Returns:
        Interface name (e.g., "Wi-Fi" or "Ethernet"), or None if not found.
    """
    try:
        stats    = psutil.net_if_stats()
        counters = psutil.net_io_counters(pernic=True)
    except Exception:
        return None

    for name, stat in stats.items():
        # Skip loopback
        if any(name.startswith(prefix) for prefix in _LOOPBACK_PREFIXES):
            continue

        # Skip interfaces that are down
        if not stat.isup:
            continue

        # Skip interfaces with zero traffic (likely inactive)
        if name in counters:
            c = counters[name]
            if c.bytes_sent > 0 or c.bytes_recv > 0:
                return name

    return None
