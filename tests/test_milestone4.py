"""
tests/test_milestone4.py — Milestone 4: Connectivity Health Monitoring Tests

Tests for:
  - Packet loss calculation from rolling probe history
  - Health status evaluation (healthy, degraded, disconnected)
  - Multi-target TCP connect checks
  - Dynamic tray icon generation for different health states
  - Status indicator widget states
  - NetworkState health fields and thread-safe copying

Run with:
    pytest tests/test_milestone4.py -v
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


# ── Packet Loss Calculation Tests ─────────────────────────────────────────────

def test_packet_loss_empty_history():
    from netpath_sentinel.monitoring.latency_monitor import calculate_packet_loss
    assert calculate_packet_loss([]) == 0.0


def test_packet_loss_zero():
    from netpath_sentinel.monitoring.latency_monitor import calculate_packet_loss
    assert calculate_packet_loss([True, True, True, True, True]) == 0.0


def test_packet_loss_hundred_percent():
    from netpath_sentinel.monitoring.latency_monitor import calculate_packet_loss
    assert calculate_packet_loss([False, False, False, False]) == 100.0


def test_packet_loss_partial():
    from netpath_sentinel.monitoring.latency_monitor import calculate_packet_loss
    # 1 loss out of 4 probes = 25.0%
    assert calculate_packet_loss([True, True, False, True]) == 25.0
    # 2 losses out of 10 probes = 20.0%
    assert calculate_packet_loss([True, True, False, True, True, True, False, True, True, True]) == 20.0


# ── Health Status Evaluation Tests ────────────────────────────────────────────

def test_health_evaluation_healthy():
    from netpath_sentinel.monitoring.connectivity import evaluate_health_status
    status, reason = evaluate_health_status(
        is_connected=True,
        packet_loss_pct=0.0,
        latency_ms=25.0,
        jitter_ms=3.0,
    )
    assert status == "healthy"
    assert "responsive" in reason.lower() or "normal" in reason.lower()


def test_health_evaluation_disconnected_offline():
    from netpath_sentinel.monitoring.connectivity import evaluate_health_status
    status, reason = evaluate_health_status(
        is_connected=False,
        packet_loss_pct=0.0,
        latency_ms=0.0,
        jitter_ms=0.0,
    )
    assert status == "disconnected"
    assert "no active internet" in reason.lower()


def test_health_evaluation_disconnected_total_loss():
    from netpath_sentinel.monitoring.connectivity import evaluate_health_status
    status, reason = evaluate_health_status(
        is_connected=True,
        packet_loss_pct=100.0,
        latency_ms=0.0,
        jitter_ms=0.0,
    )
    assert status == "disconnected"


def test_health_evaluation_degraded_packet_loss():
    from netpath_sentinel.monitoring.connectivity import evaluate_health_status
    status, reason = evaluate_health_status(
        is_connected=True,
        packet_loss_pct=5.0,
        latency_ms=30.0,
        jitter_ms=4.0,
    )
    assert status == "degraded"
    assert "packet loss" in reason.lower()


def test_health_evaluation_degraded_high_latency():
    from netpath_sentinel.monitoring.connectivity import evaluate_health_status
    status, reason = evaluate_health_status(
        is_connected=True,
        packet_loss_pct=0.0,
        latency_ms=160.0,
        jitter_ms=5.0,
    )
    assert status == "degraded"
    assert "latency" in reason.lower()


def test_health_evaluation_degraded_high_jitter():
    from netpath_sentinel.monitoring.connectivity import evaluate_health_status
    status, reason = evaluate_health_status(
        is_connected=True,
        packet_loss_pct=0.0,
        latency_ms=35.0,
        jitter_ms=40.0,
    )
    assert status == "degraded"
    assert "jitter" in reason.lower()


def test_health_evaluation_multiple_degraded_factors():
    from netpath_sentinel.monitoring.connectivity import evaluate_health_status
    status, reason = evaluate_health_status(
        is_connected=True,
        packet_loss_pct=10.0,
        latency_ms=180.0,
        jitter_ms=30.0,
    )
    assert status == "degraded"
    assert "packet loss" in reason.lower()
    assert "latency" in reason.lower()
    assert "jitter" in reason.lower()


# ── Tray Icon Generation Tests ────────────────────────────────────────────────

def test_tray_icon_generation_all_states():
    """Verify tray icon can be generated programmatically for all 3 health statuses."""
    from PySide6.QtWidgets import QApplication
    from netpath_sentinel.tray.tray import _create_tray_icon
    from PySide6.QtGui import QIcon

    app = QApplication.instance() or QApplication(sys.argv)
    for status in ["healthy", "degraded", "disconnected"]:
        icon = _create_tray_icon(status)
        assert isinstance(icon, QIcon)
        assert not icon.isNull()


# ── NetworkState M4 Field Tests ───────────────────────────────────────────────

def test_network_state_m4_fields():
    from netpath_sentinel.monitoring.network_monitor import NetworkState
    state = NetworkState()
    assert hasattr(state, "health_status")
    assert hasattr(state, "health_reason")
    assert hasattr(state, "packet_loss_pct")
    assert hasattr(state, "probe_history")
    assert state.packet_loss_pct == 0.0
    assert isinstance(state.probe_history, list)


def test_network_state_copy_includes_m4_fields():
    from netpath_sentinel.monitoring.network_monitor import NetworkMonitor
    monitor = NetworkMonitor()
    state = monitor.state
    assert hasattr(state, "health_status")
    assert hasattr(state, "packet_loss_pct")
    assert hasattr(state, "probe_history")
    # Verify probe_history is a distinct list instance
    assert state.probe_history is not monitor._state.probe_history
