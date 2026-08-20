"""
tests/test_milestone5.py — Milestone 5: DNS & Protocol Monitoring Tests

Tests for:
  - DNS resolution latency measurement and IP extraction
  - DNS failure handling (non-existent domain / timeout)
  - Multi-domain DNS benchmarking
  - IPv4 direct transport check
  - IPv6 transport & unreachability classification
  - Composite health evaluation with DNS anomalies
  - NetworkState M5 fields and thread-safe copying

Run with:
    pytest tests/test_milestone5.py -v
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


# ── DNS Resolution Tests ──────────────────────────────────────────────────────

def test_dns_resolution_valid_domain():
    """Resolving a known domain should return positive latency and valid IP list."""
    from netpath_sentinel.monitoring.dns_monitor import measure_dns_resolution
    latency, status, ips = measure_dns_resolution("localhost", timeout=2.0)
    assert status == "ok"
    assert latency is not None
    assert latency >= 0.0
    assert len(ips) > 0


def test_dns_resolution_invalid_domain():
    """Resolving a non-existent domain should gracefully return 'failed' status without crashing."""
    from netpath_sentinel.monitoring.dns_monitor import measure_dns_resolution
    latency, status, ips = measure_dns_resolution("nonexistent-domain-xyz-123456789.invalid", timeout=1.5)
    assert status == "failed"
    assert latency is None
    assert ips == []


def test_multi_dns_benchmark():
    """Multi-domain benchmark should return results for each requested domain."""
    from netpath_sentinel.monitoring.dns_monitor import measure_multi_dns
    domains = ["localhost"]
    results = measure_multi_dns(domains, timeout=2.0)
    assert "localhost" in results
    lat, status = results["localhost"]
    assert status == "ok"


# ── IPv4 & IPv6 Dual-Stack Tests ──────────────────────────────────────────────

def test_ipv4_connectivity_check():
    """IPv4 check must return either 'Active' or 'Failed'."""
    from netpath_sentinel.monitoring.connectivity import check_ipv4_connectivity
    status = check_ipv4_connectivity("8.8.8.8", 443, timeout=1.0)
    assert status in ("Active", "Failed")


def test_ipv6_connectivity_check():
    """IPv6 check must return 'Active', 'Failed', or 'Unavailable'."""
    from netpath_sentinel.monitoring.connectivity import check_ipv6_connectivity
    status = check_ipv6_connectivity("2001:4860:4860::8888", 443, timeout=1.0)
    assert status in ("Active", "Failed", "Unavailable")


# ── Health Evaluation with DNS Tests ──────────────────────────────────────────

def test_health_evaluation_degraded_on_dns_failure():
    from netpath_sentinel.monitoring.connectivity import evaluate_health_status
    status, reason = evaluate_health_status(
        is_connected=True,
        packet_loss_pct=0.0,
        latency_ms=25.0,
        jitter_ms=3.0,
        dns_status="failed",
        dns_latency_ms=0.0,
    )
    assert status == "degraded"
    assert "dns failed" in reason.lower()


def test_health_evaluation_degraded_on_dns_timeout():
    from netpath_sentinel.monitoring.connectivity import evaluate_health_status
    status, reason = evaluate_health_status(
        is_connected=True,
        packet_loss_pct=0.0,
        latency_ms=25.0,
        jitter_ms=3.0,
        dns_status="timeout",
        dns_latency_ms=0.0,
    )
    assert status == "degraded"
    assert "dns timeout" in reason.lower()


def test_health_evaluation_degraded_on_slow_dns():
    from netpath_sentinel.monitoring.connectivity import evaluate_health_status
    status, reason = evaluate_health_status(
        is_connected=True,
        packet_loss_pct=0.0,
        latency_ms=25.0,
        jitter_ms=3.0,
        dns_status="ok",
        dns_latency_ms=180.0,
    )
    assert status == "degraded"
    assert "slow dns" in reason.lower()


# ── NetworkState M5 Field Tests ───────────────────────────────────────────────

def test_network_state_m5_fields():
    from netpath_sentinel.monitoring.network_monitor import NetworkState
    state = NetworkState()
    assert hasattr(state, "dns_latency_ms")
    assert hasattr(state, "dns_status")
    assert hasattr(state, "ipv4_status")
    assert hasattr(state, "ipv6_status")
    assert state.dns_latency_ms == 0.0
    assert state.dns_status == "—"


def test_network_state_copy_includes_m5_fields():
    from netpath_sentinel.monitoring.network_monitor import NetworkMonitor
    monitor = NetworkMonitor()
    state = monitor.state
    assert hasattr(state, "dns_latency_ms")
    assert hasattr(state, "dns_status")
    assert hasattr(state, "ipv4_status")
    assert hasattr(state, "ipv6_status")
