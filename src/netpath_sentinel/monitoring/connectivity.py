"""
monitoring/connectivity.py — Network Connectivity & Health Classification

Detects whether the network interface is up, whether target endpoints are
reachable via TCP, and evaluates composite network health status.

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

    Health Status Classification:
        - "healthy" (Green): Connected, packet loss < 2%, latency < 120ms, jitter < 25ms.
        - "degraded" (Orange): Connected, but packet loss >= 2%, high latency (>= 120ms),
          or high jitter (>= 25ms).
        - "disconnected" (Red): No network interface active or TCP probes fail.
"""

import socket
from typing import Optional

import psutil


# Interface names to ignore — these are not real network paths
_LOOPBACK_PREFIXES = ("Loopback", "lo")

# Default high availability probe targets
DEFAULT_PROBE_TARGETS = [
    ("8.8.8.8", 443),   # Google DNS over HTTPS port
    ("1.1.1.1", 443),   # Cloudflare DNS over HTTPS port
]


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
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def check_multi_tcp(targets: list[tuple[str, int]], timeout: float = 2.0) -> dict[tuple[str, int], bool]:
    """
    Attempt TCP connections to multiple targets.

    Returns a dict mapping (host, port) -> bool success status.
    """
    results = {}
    for host, port in targets:
        results[(host, port)] = check_tcp_connect(host, port, timeout=timeout)
    return results


def get_active_interface() -> Optional[str]:
    """
    Find the name of the currently active network interface.

    Algorithm:
        1. Get all interface statistics (is it up? what speed?)
        2. Get all interface byte counters (how much traffic has it seen?)
        3. Skip loopback interfaces — they don't represent Internet access
        4. Return the first interface that is both "up" and has transferred data

    Returns:
        Interface name (e.g., "Wi-Fi" or "Ethernet"), or None if not found.
    """
    try:
        stats    = psutil.net_if_stats()
        counters = psutil.net_io_counters(pernic=True)
    except Exception:
        return None

    for name, stat in stats.items():
        if any(name.startswith(prefix) for prefix in _LOOPBACK_PREFIXES):
            continue

        if not stat.isup:
            continue

        if name in counters:
            c = counters[name]
            if c.bytes_sent > 0 or c.bytes_recv > 0:
                return name

    return None


def evaluate_health_status(
    is_connected: bool,
    packet_loss_pct: float,
    latency_ms: float,
    jitter_ms: float,
) -> tuple[str, str]:
    """
    Classify the current network connection health.

    Thresholds:
        - Latency: Normal < 120ms, Degraded >= 120ms
        - Jitter: Normal < 25ms, Degraded >= 25ms
        - Packet Loss: Normal < 2.0%, Degraded >= 2.0%

    Returns:
        tuple of (status_string, reason_description)
        where status_string is one of "healthy", "degraded", "disconnected".
    """
    if not is_connected or packet_loss_pct >= 100.0:
        return "disconnected", "No active Internet connection"

    reasons = []
    if packet_loss_pct >= 2.0:
        reasons.append(f"Packet loss: {packet_loss_pct:.0f}%")
    if latency_ms >= 120.0:
        reasons.append(f"High latency: {latency_ms:.0f}ms")
    if jitter_ms >= 25.0:
        reasons.append(f"High jitter: {jitter_ms:.0f}ms")

    if reasons:
        return "degraded", " · ".join(reasons)

    return "healthy", "All probes responsive"
