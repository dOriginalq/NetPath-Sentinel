"""
monitoring/network_monitor.py — Main Monitoring Coordinator

This module runs in a background thread, completely independent of the UI.
The dashboard UI reads from NetworkMonitor.state (via a thread-safe lock).

Thread model:
    Main thread  — Qt event loop (tray icon, dashboard window)
    Monitor thread — NetworkMonitor._run() loop (this file)

Communication between threads:
    The two threads share a single NetworkState object, protected by a
    threading.Lock. The monitor thread holds the lock only long enough
    to update fields. The UI thread holds it only long enough to copy
    the state. Neither thread should hold the lock for extended periods.

Why daemon=True on the thread?
    A daemon thread is automatically killed when the main process exits.
    This means the user doesn't need to explicitly stop the monitor —
    clicking Exit on the tray terminates everything cleanly.
"""

import time
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import psutil

from netpath_sentinel.monitoring.latency_monitor import (
    ping_once,
    calculate_jitter,
    calculate_packet_loss,
)
from netpath_sentinel.monitoring.connectivity import (
    check_tcp_connect,
    check_ipv4_connectivity,
    check_ipv6_connectivity,
    get_active_interface,
    evaluate_health_status,
    DEFAULT_PROBE_TARGETS,
)
from netpath_sentinel.monitoring.dns_monitor import measure_dns_resolution


# ── Monitoring targets ────────────────────────────────────────────────────────
PRIMARY_HOST   = "8.8.8.8"
SECONDARY_HOST = "1.1.1.1"
DNS_BENCHMARK  = "google.com"

LOOP_INTERVAL  = 3            # Seconds between full measurement cycles
MAX_HISTORY    = 60           # Maximum rolling-window samples to keep for charts
PROBE_WINDOW   = 20           # Window size for packet loss calculation


# ══════════════════════════════════════════════════════════════════════════════
# NetworkState — shared data object
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class NetworkState:
    """
    A snapshot of all current network measurements.

    This is the data contract between the monitoring thread and the UI thread.
    The UI reads a *copy* of this state every 2 seconds (via QTimer).
    The monitor updates this object every LOOP_INTERVAL seconds.
    """

    # ── Connectivity & Health ─────────────────────────────────────────────
    is_connected: bool = False
    """True if we successfully reached at least one probe host via TCP."""

    interface_name: str = "—"
    """Name of the active network interface (e.g., 'Wi-Fi', 'Ethernet')."""

    health_status: str = "disconnected"
    """One of: 'healthy', 'degraded', 'disconnected'."""

    health_reason: str = "Initializing monitor…"
    """Human-readable explanation of the current health state."""

    # ── DNS & Protocols (Milestone 5) ─────────────────────────────────────
    dns_latency_ms: float = 0.0
    """Time in ms to resolve benchmark domain (e.g. google.com)."""

    dns_status: str = "—"
    """DNS resolution status: 'ok', 'timeout', or 'failed'."""

    ipv4_status: str = "—"
    """IPv4 connectivity status: 'Active' or 'Failed'."""

    ipv6_status: str = "—"
    """IPv6 connectivity status: 'Active', 'Failed', or 'Unavailable'."""

    # ── Latency & Reliability ─────────────────────────────────────────────
    latency_ms: float = 0.0
    """Most recent RTT to probe target in milliseconds."""

    latency_history: list[float] = field(default_factory=list)
    """Rolling history of RTT values, oldest → newest (max MAX_HISTORY entries)."""

    jitter_ms: float = 0.0
    """Mean absolute difference between consecutive RTT values (ms)."""

    packet_loss_pct: float = 0.0
    """Percentage of probe pings lost in the recent rolling window (0.0 - 100.0)."""

    probe_history: list[bool] = field(default_factory=list)
    """Rolling history of ping outcomes (True=success, False=lost)."""

    # ── Bandwidth ─────────────────────────────────────────────────────────
    download_kbps: float = 0.0
    """Current download throughput in KB/s (sampled from interface counters)."""

    upload_kbps: float = 0.0
    """Current upload throughput in KB/s."""

    download_history: list[float] = field(default_factory=list)
    """Rolling history of download KB/s samples."""

    upload_history: list[float] = field(default_factory=list)
    """Rolling history of upload KB/s samples."""

    # ── Timing ────────────────────────────────────────────────────────────
    start_time: datetime = field(default_factory=datetime.now)
    """When monitoring started (used to compute uptime display)."""

    last_updated: Optional[datetime] = None
    """Timestamp of the most recent measurement cycle completion."""


# ══════════════════════════════════════════════════════════════════════════════
# NetworkMonitor — background monitoring coordinator
# ══════════════════════════════════════════════════════════════════════════════

class NetworkMonitor:
    """
    Coordinates all network measurements in a background thread.
    """

    def __init__(self) -> None:
        self._state      = NetworkState()
        self._lock       = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

        # Bandwidth sampling state
        self._prev_recv: int   = 0
        self._prev_sent: int   = 0
        self._prev_time: float = 0.0

    @property
    def state(self) -> NetworkState:
        """
        Return a thread-safe copy of the current NetworkState.
        """
        with self._lock:
            s = self._state
            return NetworkState(
                is_connected      = s.is_connected,
                interface_name    = s.interface_name,
                health_status     = s.health_status,
                health_reason     = s.health_reason,
                dns_latency_ms    = s.dns_latency_ms,
                dns_status        = s.dns_status,
                ipv4_status       = s.ipv4_status,
                ipv6_status       = s.ipv6_status,
                latency_ms        = s.latency_ms,
                latency_history   = list(s.latency_history),
                jitter_ms         = s.jitter_ms,
                packet_loss_pct   = s.packet_loss_pct,
                probe_history     = list(s.probe_history),
                download_kbps     = s.download_kbps,
                upload_kbps       = s.upload_kbps,
                download_history  = list(s.download_history),
                upload_history    = list(s.upload_history),
                start_time        = s.start_time,
                last_updated      = s.last_updated,
            )

    def start(self) -> None:
        """Start the background monitoring thread."""
        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="NetPathMonitor",
            daemon=True,
        )
        self._thread.start()
        print("[Monitor] Background monitoring started.")

    def stop(self) -> None:
        """Signal the monitoring loop to exit and wait for the thread to finish."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=10)
        print("[Monitor] Background monitoring stopped.")

    # ── Internal monitoring loop ──────────────────────────────────────────

    def _run(self) -> None:
        """
        Main monitoring loop — runs on the background thread.
        """
        print("[Monitor] Monitoring loop started.")

        while not self._stop_event.is_set():
            cycle_start = time.monotonic()

            # ── 1. Sample bandwidth ───────────────────────────────────────
            dl_kbps, ul_kbps = self._sample_bandwidth()

            # ── 2. Detect active interface ────────────────────────────────
            interface = get_active_interface()

            # ── 3. Check TCP connectivity to targets ──────────────────────
            connected = False
            ipv4_status = "—"
            ipv6_status = "—"

            if interface:
                for host, port in DEFAULT_PROBE_TARGETS:
                    if check_tcp_connect(host, port, timeout=1.5):
                        connected = True
                        break

                # Dual-stack protocol checks
                ipv4_status = check_ipv4_connectivity()
                ipv6_status = check_ipv6_connectivity()

            # ── 4. Measure DNS resolution ─────────────────────────────────
            dns_latency: Optional[float] = None
            dns_status = "failed" if not connected else "—"

            if connected:
                dns_latency, dns_status, _ = measure_dns_resolution(DNS_BENCHMARK, timeout=1.5)

            # ── 5. Measure RTT & Ping Probe ───────────────────────────────
            rtt: Optional[float] = None
            ping_success = False

            if connected:
                rtt = ping_once(PRIMARY_HOST, timeout_ms=1200)
                if rtt is not None:
                    ping_success = True
                else:
                    # Failover to secondary host
                    rtt_sec = ping_once(SECONDARY_HOST, timeout_ms=1200)
                    if rtt_sec is not None:
                        rtt = rtt_sec
                        ping_success = True

            # ── 6. Update shared state & health classification ────────────
            with self._lock:
                s = self._state

                s.is_connected   = connected
                s.interface_name = interface or "—"

                # DNS & Protocol fields
                s.dns_status      = dns_status
                s.dns_latency_ms  = dns_latency if dns_latency is not None else 0.0
                s.ipv4_status     = ipv4_status
                s.ipv6_status     = ipv6_status

                # Record ping success/loss outcome in rolling probe history
                if connected:
                    _append(s.probe_history, ping_success, PROBE_WINDOW)
                else:
                    _append(s.probe_history, False, PROBE_WINDOW)

                s.packet_loss_pct = calculate_packet_loss(s.probe_history)

                # Bandwidth
                s.download_kbps = dl_kbps
                s.upload_kbps   = ul_kbps
                _append(s.download_history, dl_kbps, MAX_HISTORY)
                _append(s.upload_history,   ul_kbps, MAX_HISTORY)

                # Latency & Jitter
                if rtt is not None:
                    s.latency_ms = rtt
                    _append(s.latency_history, rtt, MAX_HISTORY)
                    s.jitter_ms = calculate_jitter(s.latency_history[-10:])
                elif not connected:
                    s.latency_ms = 0.0
                    s.jitter_ms = 0.0

                # Health evaluation
                status, reason = evaluate_health_status(
                    is_connected=s.is_connected,
                    packet_loss_pct=s.packet_loss_pct,
                    latency_ms=s.latency_ms,
                    jitter_ms=s.jitter_ms,
                    dns_status=s.dns_status,
                    dns_latency_ms=s.dns_latency_ms,
                )
                s.health_status = status
                s.health_reason = reason
                s.last_updated  = datetime.now()

            # ── 7. Sleep for remainder of the cycle ───────────────────────
            elapsed   = time.monotonic() - cycle_start
            sleep_for = max(0.0, LOOP_INTERVAL - elapsed)
            self._stop_event.wait(sleep_for)

        print("[Monitor] Monitoring loop exited.")

    def _sample_bandwidth(self) -> tuple[float, float]:
        """Compute current download and upload speed in KB/s."""
        now = time.monotonic()

        try:
            c = psutil.net_io_counters()
            recv = c.bytes_recv
            sent = c.bytes_sent
        except Exception:
            return 0.0, 0.0

        if self._prev_time == 0.0:
            self._prev_recv = recv
            self._prev_sent = sent
            self._prev_time = now
            return 0.0, 0.0

        dt = now - self._prev_time
        if dt <= 0:
            return 0.0, 0.0

        dl_kbps = (recv - self._prev_recv) / dt / 1024
        ul_kbps = (sent - self._prev_sent) / dt / 1024

        self._prev_recv = recv
        self._prev_sent = sent
        self._prev_time = now

        return max(0.0, dl_kbps), max(0.0, ul_kbps)


# ── Utility ───────────────────────────────────────────────────────────────────

def _append(history: list, value, max_len: int) -> None:
    """Append a value to a rolling history list, evicting oldest if full."""
    history.append(value)
    if len(history) > max_len:
        history.pop(0)
