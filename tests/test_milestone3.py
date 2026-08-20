"""
tests/test_milestone3.py — Milestone 3: Basic Network Monitoring Tests

Tests that verify:
  - Monitoring modules import correctly
  - NetworkState dataclass has all expected fields
  - Helper functions (ping_once, jitter, TCP connect) work correctly
  - NetworkMonitor can be created and started/stopped

Note: We do NOT test actual network connectivity here — that depends on
the environment where tests are run. We test the logic and structure.

Run with:
    pytest tests/test_milestone3.py -v
"""

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


# ── Module structure tests ────────────────────────────────────────────────────

def test_network_monitor_importable():
    from netpath_sentinel.monitoring.network_monitor import NetworkMonitor, NetworkState
    assert NetworkMonitor is not None
    assert NetworkState is not None


def test_latency_monitor_importable():
    from netpath_sentinel.monitoring.latency_monitor import ping_once, calculate_jitter
    assert callable(ping_once)
    assert callable(calculate_jitter)


def test_connectivity_importable():
    from netpath_sentinel.monitoring.connectivity import check_tcp_connect, get_active_interface
    assert callable(check_tcp_connect)
    assert callable(get_active_interface)


# ── NetworkState field tests ──────────────────────────────────────────────────

def test_network_state_defaults():
    """NetworkState must have safe defaults so the UI renders before monitoring starts."""
    from netpath_sentinel.monitoring.network_monitor import NetworkState
    s = NetworkState()
    assert s.is_connected == False
    assert s.interface_name == "—"
    assert s.latency_ms == 0.0
    assert s.jitter_ms == 0.0
    assert s.download_kbps == 0.0
    assert s.upload_kbps == 0.0
    assert isinstance(s.latency_history, list)
    assert isinstance(s.download_history, list)
    assert s.last_updated is None


def test_network_state_has_start_time():
    """start_time must be set on creation (used for uptime display)."""
    from netpath_sentinel.monitoring.network_monitor import NetworkState
    from datetime import datetime
    s = NetworkState()
    assert isinstance(s.start_time, datetime)


# ── Jitter calculation tests ──────────────────────────────────────────────────

def test_jitter_returns_zero_for_single_sample():
    from netpath_sentinel.monitoring.latency_monitor import calculate_jitter
    assert calculate_jitter([30.0]) == 0.0


def test_jitter_returns_zero_for_empty():
    from netpath_sentinel.monitoring.latency_monitor import calculate_jitter
    assert calculate_jitter([]) == 0.0


def test_jitter_stable_connection():
    """All samples the same → jitter should be 0."""
    from netpath_sentinel.monitoring.latency_monitor import calculate_jitter
    assert calculate_jitter([30.0, 30.0, 30.0, 30.0]) == 0.0


def test_jitter_known_values():
    """
    RTTs: 30, 40, 30, 40
    Consecutive diffs: 10, 10, 10
    Mean = 10.0
    """
    from netpath_sentinel.monitoring.latency_monitor import calculate_jitter
    result = calculate_jitter([30.0, 40.0, 30.0, 40.0])
    assert result == 10.0


def test_jitter_high_variance():
    """High jitter should be detected (not zero)."""
    from netpath_sentinel.monitoring.latency_monitor import calculate_jitter
    result = calculate_jitter([10.0, 200.0, 15.0, 180.0])
    assert result > 50.0


# ── NetworkMonitor lifecycle tests ────────────────────────────────────────────

def test_network_monitor_creates_without_error():
    from netpath_sentinel.monitoring.network_monitor import NetworkMonitor
    monitor = NetworkMonitor()
    assert monitor is not None


def test_network_monitor_state_before_start():
    """state property must return valid NetworkState before monitor is started."""
    from netpath_sentinel.monitoring.network_monitor import NetworkMonitor, NetworkState
    monitor = NetworkMonitor()
    state = monitor.state
    assert isinstance(state, NetworkState)
    assert state.is_connected == False


def test_network_monitor_start_stop():
    """Monitor must start and stop cleanly without hanging."""
    from netpath_sentinel.monitoring.network_monitor import NetworkMonitor
    monitor = NetworkMonitor()
    monitor.start()
    time.sleep(0.2)  # let the thread start
    assert monitor._thread is not None
    assert monitor._thread.is_alive()
    monitor.stop()
    assert not monitor._thread.is_alive()


def test_network_monitor_state_is_copy():
    """state property must return a new object each time (not the shared reference)."""
    from netpath_sentinel.monitoring.network_monitor import NetworkMonitor
    monitor = NetworkMonitor()
    state1 = monitor.state
    state2 = monitor.state
    # They should be equal in value but distinct objects
    assert state1 is not state2
    assert state1.latency_history is not state2.latency_history


# ── Rolling history utility test ──────────────────────────────────────────────

def test_append_history_trims_to_max():
    from netpath_sentinel.monitoring.network_monitor import _append
    history = []
    for i in range(65):
        _append(history, float(i), max_len=60)
    assert len(history) == 60
    assert history[0] == 5.0   # first 5 were evicted


# ── Connectivity function tests ───────────────────────────────────────────────

def test_check_tcp_connect_returns_bool():
    from netpath_sentinel.monitoring.connectivity import check_tcp_connect
    # We use a very short timeout so the test is fast even if offline
    result = check_tcp_connect("8.8.8.8", 443, timeout=1.0)
    assert isinstance(result, bool)


def test_get_active_interface_returns_string_or_none():
    from netpath_sentinel.monitoring.connectivity import get_active_interface
    result = get_active_interface()
    assert result is None or isinstance(result, str)
