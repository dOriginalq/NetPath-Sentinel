"""
monitoring/dns_monitor.py — DNS Resolution Monitoring

Measures DNS resolution latency and failure rates using the system resolver.

Why DNS monitoring is critical for ISP diagnostics:
    DNS (Domain Name System) translates human-readable domain names (e.g., google.com)
    into IP addresses (e.g., 142.250.190.46).
    If DNS fails or responds very slowly:
      - Websites fail to load ("Server Not Found" / ERR_NAME_NOT_RESOLVED).
      - Applications stall for 5-10 seconds waiting for DNS timeouts.
      - The user experiences this as "the Internet is broken", even if raw IP
        routing and ICMP ping are functioning normally.

    On ISP connections like JioFiber, issues can stem from:
      1. ISP DNS cache poisoning or aggressive filtering
      2. High latency or packet drop specifically to ISP recursive resolvers
      3. Broken IPv6 AAAA record handling (causing dual-stack timeout delays)
"""

import time
import socket
from typing import Optional


# Default stable domains used for resolution health benchmarks
BENCHMARK_DOMAINS = ["google.com", "cloudflare.com"]


def measure_dns_resolution(
    host: str = "google.com",
    timeout: float = 2.0,
) -> tuple[Optional[float], str, list[str]]:
    """
    Measure the time taken to resolve a domain name using the OS resolver.

    Args:
        host: Domain name to resolve (e.g., 'google.com').
        timeout: Maximum duration in seconds to wait for resolution.

    Returns:
        tuple of (resolution_time_ms, status_code, ip_list)
        - resolution_time_ms: float latency in milliseconds, or None on failure.
        - status_code: 'ok', 'timeout', or 'failed'.
        - ip_list: list of resolved IP strings (IPv4 and/or IPv6).
    """
    start_time = time.monotonic()
    original_timeout = socket.getdefaulttimeout()

    try:
        socket.setdefaulttimeout(timeout)
        # socket.getaddrinfo queries the system-configured resolver (ISP, 1.1.1.1, WARP, etc.)
        addr_info = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
        elapsed_ms = (time.monotonic() - start_time) * 1000.0

        # Extract unique IP addresses resolved
        resolved_ips: list[str] = []
        for item in addr_info:
            ip = item[4][0]
            if ip not in resolved_ips:
                resolved_ips.append(ip)

        return round(elapsed_ms, 1), "ok", resolved_ips

    except socket.timeout:
        return None, "timeout", []
    except (socket.gaierror, OSError):
        return None, "failed", []
    finally:
        socket.setdefaulttimeout(original_timeout)


def measure_multi_dns(
    domains: list[str] = BENCHMARK_DOMAINS,
    timeout: float = 2.0,
) -> dict[str, tuple[Optional[float], str]]:
    """
    Measure resolution time for multiple benchmark domains.

    Returns a dictionary mapping domain -> (resolution_time_ms, status).
    """
    results: dict[str, tuple[Optional[float], str]] = {}
    for domain in domains:
        latency_ms, status, _ = measure_dns_resolution(domain, timeout=timeout)
        results[domain] = (latency_ms, status)
    return results
