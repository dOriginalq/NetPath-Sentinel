"""
monitoring/connectivity.py — Network Connectivity, Dual-Stack & Health Evaluation

Detects whether the network interface is up, whether target endpoints are
reachable via TCP (both IPv4 and IPv6), and evaluates composite network health status.

Key concepts:
    IPv4 vs IPv6:
        - IPv4 uses 32-bit addresses (e.g., 8.8.8.8).
        - IPv6 uses 128-bit addresses (e.g., 2001:4860:4860::8888).
        Many ISPs (including JioFiber) deploy native dual-stack IPv4/IPv6.
        However, if IPv6 routing fails while DNS returns IPv6 (AAAA) records,
        connections to websites can stall for seconds while falling back to IPv4
        (Happy Eyeballs algorithm). Explicitly checking IPv4 and IPv6 paths
        isolates whether connectivity problems are protocol-specific.

    Health Status Classification:
        - "healthy" (Green): Connected, DNS OK, packet loss < 2%, latency < 120ms, jitter < 25ms.
        - "degraded" (Orange): Connected, but high latency, high jitter, active packet loss,
          or slow/failing DNS.
        - "disconnected" (Red): Interface down, no TCP connectivity, or 100% packet loss.
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

IPV4_TEST_TARGET = ("8.8.8.8", 443)
IPV6_TEST_TARGET = ("2001:4860:4860::8888", 443)


def check_tcp_connect(host: str, port: int, timeout: float = 2.0) -> bool:
    """
    Attempt a TCP connection and return True if it succeeds.

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


def check_ipv4_connectivity(host: str = IPV4_TEST_TARGET[0], port: int = IPV4_TEST_TARGET[1], timeout: float = 1.5) -> str:
    """
    Test direct IPv4 connectivity using an AF_INET socket.

    Returns:
        'Active' if connected, 'Failed' if unreachable or timed out.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            s.connect((host, port))
            return "Active"
    except (socket.timeout, ConnectionRefusedError, OSError):
        return "Failed"


def check_ipv6_connectivity(host: str = IPV6_TEST_TARGET[0], port: int = IPV6_TEST_TARGET[1], timeout: float = 1.5) -> str:
    """
    Test direct IPv6 connectivity using an AF_INET6 socket.

    Returns:
        'Active' if IPv6 reachable,
        'Failed' if IPv6 configured but connection failed/timed out,
        'Unavailable' if IPv6 is not supported/configured on this network.
    """
    try:
        with socket.socket(socket.AF_INET6, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            s.connect((host, port))
            return "Active"
    except socket.timeout:
        return "Failed"
    except (ConnectionRefusedError, OSError) as e:
        # Check if IPv6 is simply disabled on the host/interface (error 10047 / 10051 / EAFNOSUPPORT)
        err_msg = str(e).lower()
        if "unsupported" in err_msg or "unreachable" in err_msg or getattr(e, 'errno', 0) in (10047, 10051, 10065):
            return "Unavailable"
        return "Failed"


def check_multi_tcp(targets: list[tuple[str, int]], timeout: float = 2.0) -> dict[tuple[str, int], bool]:
    """Attempt TCP connections to multiple targets."""
    results = {}
    for host, port in targets:
        results[(host, port)] = check_tcp_connect(host, port, timeout=timeout)
    return results


def get_active_interface() -> Optional[str]:
    """Find the name of the currently active network interface."""
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
    dns_status: str = "ok",
    dns_latency_ms: float = 0.0,
) -> tuple[str, str]:
    """
    Classify the current network connection health with DNS and transport awareness.

    Thresholds:
        - Latency: Normal < 120ms, Degraded >= 120ms
        - Jitter: Normal < 25ms, Degraded >= 25ms
        - Packet Loss: Normal < 2.0%, Degraded >= 2.0%
        - DNS Latency: Normal < 100ms, Degraded >= 100ms
        - DNS Status: 'ok' Normal, 'timeout'/'failed' Degraded

    Returns:
        tuple of (status_string, reason_description)
        where status_string is one of "healthy", "degraded", "disconnected".
    """
    if not is_connected or packet_loss_pct >= 100.0:
        return "disconnected", "No active Internet connection"

    reasons = []
    if dns_status in ("timeout", "failed"):
        reasons.append(f"DNS {dns_status}")
    elif dns_latency_ms >= 100.0:
        reasons.append(f"Slow DNS: {dns_latency_ms:.0f}ms")

    if packet_loss_pct >= 2.0:
        reasons.append(f"Packet loss: {packet_loss_pct:.0f}%")
    if latency_ms >= 120.0:
        reasons.append(f"High latency: {latency_ms:.0f}ms")
    if jitter_ms >= 25.0:
        reasons.append(f"High jitter: {jitter_ms:.0f}ms")

    if reasons:
        return "degraded", " · ".join(reasons)

    return "healthy", "All probes responsive"
