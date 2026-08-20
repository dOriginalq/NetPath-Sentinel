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

from netpath_sentinel.monitoring.latency_monitor import ping_once, calculate_jitter
from netpath_sentinel.monitoring.connectivity import check_tcp_connect, get_active_interface


# ── Monitoring targets ────────────────────────────────────────────────────────
#
# We use Google's public DNS server (8.8.8.8) as our primary probe target.
# Reasons:
#   - Globally reachable, extremely reliable
#   - Low latency from most locations
#   - Both ICMP ping (latency) and TCP/443 (connectivity) are supported
#   - Not a single-point-of-failure for our measurements
#
PROBE_HOST     = "8.8.8.8"   # Google DNS — primary latency + connectivity probe
PROBE_PORT     = 443          # HTTPS port — rarely blocked by ISPs

LOOP_INTERVAL  = 3            # Seconds between full measurement cycles
MAX_HISTORY    = 60           # Maximum rolling-window samples to keep


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

    All fields have safe default values so the UI can render immediately
    before the first monitoring cycle completes.
    """

    # ── Connectivity ──────────────────────────────────────────────────────
    is_connected: bool = False
    """True if we successfully reached PROBE_HOST via TCP."""

    interface_name: str = "—"
    """Name of the active network interface (e.g., 'Wi-Fi', 'Ethernet')."""

    # ── Latency ───────────────────────────────────────────────────────────
    latency_ms: float = 0.0
    """Most recent RTT to PROBE_HOST in milliseconds."""

    latency_history: list = field(default_factory=list)
    """Rolling history of RTT values, oldest → newest (max MAX_HISTORY entries)."""

    jitter_ms: float = 0.0
    """Mean absolute difference between consecutive RTT values (ms)."""

    # ── Bandwidth ─────────────────────────────────────────────────────────
    download_kbps: float = 0.0
    """Current download throughput in KB/s (sampled from interface counters)."""

    upload_kbps: float = 0.0
    """Current upload throughput in KB/s."""

    download_history: list = field(default_factory=list)
    """Rolling history of download KB/s samples."""

    upload_history: list = field(default_factory=list)
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

    Usage (from main.py):
        monitor = NetworkMonitor()
        monitor.start()
        # pass monitor to TrayIcon / DashboardWindow
        # ...
        monitor.stop()   # called on app exit

    Reading state (from the UI thread, via QTimer callback):
        state = monitor.state   # returns a safe copy
        latency = state.latency_ms
    """

    def __init__(self) -> None:
        self._state      = NetworkState()
        self._lock       = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

        # Bandwidth sampling requires two consecutive readings.
        # These store the previous reading so we can compute the diff.
        self._prev_recv: int   = 0
        self._prev_sent: int   = 0
        self._prev_time: float = 0.0

    @property
    def state(self) -> NetworkState:
        """
        Return a thread-safe copy of the current NetworkState.

        The UI thread calls this every 2 seconds via QTimer.
        We hold the lock only for the brief moment needed to copy fields.
        """
        with self._lock:
            s = self._state
            return NetworkState(
                is_connected      = s.is_connected,
                interface_name    = s.interface_name,
                latency_ms        = s.latency_ms,
                latency_history   = list(s.latency_history),   # shallow copy of list of floats
                jitter_ms         = s.jitter_ms,
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
            return  # already running

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="NetPathMonitor",
            daemon=True,   # exits automatically when the main process exits
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

        Each cycle (every LOOP_INTERVAL seconds):
            1. Sample bandwidth  — reads OS byte counters (fast, ~1ms)
            2. Find active interface — queries psutil (fast, ~5ms)
            3. Check TCP connectivity — opens a socket (up to 2s)
            4. Ping for RTT — runs ping.exe (up to 1.5s)
            5. Update shared state under lock
            6. Sleep for the remaining cycle time
        """
        print("[Monitor] Monitoring loop started.")

        while not self._stop_event.is_set():
            cycle_start = time.monotonic()

            # ── 1. Sample bandwidth ───────────────────────────────────────
            # Read system-wide byte counters and compute KB/s.
            dl_kbps, ul_kbps = self._sample_bandwidth()

            # ── 2. Detect active interface ────────────────────────────────
            # Find which NIC is carrying traffic.
            interface = get_active_interface()

            # ── 3. Check connectivity ─────────────────────────────────────
            # TCP connect to 8.8.8.8:443. This tells us whether the Internet
            # path is clear at the transport layer, independent of DNS.
            connected = False
            if interface:
                connected = check_tcp_connect(PROBE_HOST, PROBE_PORT, timeout=2.0)

            # ── 4. Measure RTT via ping ───────────────────────────────────
            # Only ping if we believe we're online — avoids waiting 1.5s
            # for a timeout when we already know we're offline.
            rtt: Optional[float] = None
            if connected:
                rtt = ping_once(PROBE_HOST, timeout_ms=1500)

            # ── 5. Update shared state ────────────────────────────────────
            with self._lock:
                s = self._state

                s.is_connected    = connected
                s.interface_name  = interface or "—"

                # Bandwidth
                s.download_kbps = dl_kbps
                s.upload_kbps   = ul_kbps
                _append(s.download_history, dl_kbps, MAX_HISTORY)
                _append(s.upload_history,   ul_kbps, MAX_HISTORY)

                # Latency + jitter
                if rtt is not None:
                    s.latency_ms = rtt
                    _append(s.latency_history, rtt, MAX_HISTORY)
                    # Compute jitter from the last 10 RTT samples for responsiveness
                    s.jitter_ms = calculate_jitter(s.latency_history[-10:])

                s.last_updated = datetime.now()

            # ── 6. Sleep for the remainder of the cycle ───────────────────
            # self._stop_event.wait() is an interruptible sleep:
            # if stop() is called, the wait returns immediately.
            elapsed    = time.monotonic() - cycle_start
            sleep_for  = max(0.0, LOOP_INTERVAL - elapsed)
            self._stop_event.wait(sleep_for)

        print("[Monitor] Monitoring loop exited.")

    def _sample_bandwidth(self) -> tuple[float, float]:
        """
        Compute current download and upload speed in KB/s.

        Strategy: psutil.net_io_counters() returns *cumulative* bytes
        transferred since the process started. By reading it twice and
        dividing the difference by elapsed time, we get bytes/second.

        On the first call we only record the baseline — returns (0, 0).
        On subsequent calls we compute the actual throughput.
        """
        now = time.monotonic()

        try:
            c = psutil.net_io_counters()   # system-wide totals across all interfaces
            recv = c.bytes_recv
            sent = c.bytes_sent
        except Exception:
            return 0.0, 0.0

        if self._prev_time == 0.0:
            # First call — record baseline, return zeroes
            self._prev_recv = recv
            self._prev_sent = sent
            self._prev_time = now
            return 0.0, 0.0

        dt = now - self._prev_time
        if dt <= 0:
            return 0.0, 0.0

        # bytes/sec → KB/s (divide by 1024)
        dl_kbps = (recv - self._prev_recv) / dt / 1024
        ul_kbps = (sent - self._prev_sent) / dt / 1024

        self._prev_recv = recv
        self._prev_sent = sent
        self._prev_time = now

        # Clamp to >= 0 in case of counter wrap or system anomaly
        return max(0.0, dl_kbps), max(0.0, ul_kbps)


# ── Utility ───────────────────────────────────────────────────────────────────

def _append(history: list, value: float, max_len: int) -> None:
    """Append a value to a rolling history list, evicting the oldest if full."""
    history.append(value)
    if len(history) > max_len:
        history.pop(0)
