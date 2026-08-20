"""
monitoring/latency_monitor.py — RTT, Jitter Measurement

Implements latency measurement via the Windows ping command and
derives jitter from consecutive RTT samples.

Why subprocess ping instead of raw ICMP sockets?
    Raw ICMP sockets require Administrator privileges on Windows.
    Calling the system ping.exe works without elevation and gives
    us the same RTT information. The small overhead of spawning a
    subprocess is irrelevant at our polling interval (every few seconds).

Key concepts:
    RTT (Round-Trip Time / latency):
        The time a packet takes to travel from this machine to a target
        and back. Measured in milliseconds. High RTT = slow responses.

    Jitter:
        The variation in RTT between consecutive measurements.
        A stable connection has low jitter (e.g., ±2ms).
        High jitter degrades real-time applications even when average
        latency is acceptable — video calls and gaming are most sensitive.
"""

import re
import subprocess
from typing import Optional


def ping_once(host: str, timeout_ms: int = 1500) -> Optional[float]:
    """
    Send a single ICMP echo request and return the round-trip time.

    Args:
        host: IP address or hostname (e.g., "8.8.8.8" or "google.com")
        timeout_ms: Max time to wait for a reply, in milliseconds.

    Returns:
        RTT in milliseconds (float), or None if the ping failed or timed out.

    Windows ping output example:
        Reply from 8.8.8.8: bytes=32 time=24ms TTL=57
        We extract the "24" from "time=24ms".
    """
    try:
        result = subprocess.run(
            [
                "ping",
                "-n", "1",              # send exactly 1 packet
                "-w", str(timeout_ms),  # wait timeout_ms ms for a reply
                host,
            ],
            capture_output=True,
            text=True,
            # subprocess timeout is slightly longer than ping's own timeout
            # to avoid killing ping before it can print its output
            timeout=(timeout_ms / 1000) + 2.0,
        )

        if result.returncode != 0:
            # ping.exe returns non-zero when the host is unreachable
            return None

        # Extract RTT from lines like "time=24ms" or "time<1ms"
        # The "<" variant appears when RTT rounds down to less than 1ms
        match = re.search(r"time[=<](\d+)ms", result.stdout)
        if match:
            return float(match.group(1))

        # Reply received but couldn't parse — treat as failure
        return None

    except subprocess.TimeoutExpired:
        # The subprocess itself timed out (shouldn't normally happen)
        return None
    except (OSError, ValueError):
        return None


def calculate_jitter(rtt_history: list[float]) -> float:
    """
    Calculate jitter from a list of recent RTT measurements.

    Method: mean absolute difference between consecutive RTT samples.

        jitter = mean(|RTT[i] - RTT[i-1]|)

    This is the same method used by many network monitoring tools.
    It captures how much the latency *changes* step-by-step, which
    directly correlates with how "bumpy" the connection feels.

    Args:
        rtt_history: RTT values in ms, ordered oldest → newest.
                     At least 2 values are needed for a meaningful result.

    Returns:
        Jitter in ms, or 0.0 if fewer than 2 samples are available.
    """
    if len(rtt_history) < 2:
        return 0.0

    diffs = [
        abs(rtt_history[i] - rtt_history[i - 1])
        for i in range(1, len(rtt_history))
    ]
    return round(sum(diffs) / len(diffs), 1)
