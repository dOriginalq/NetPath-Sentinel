"""
tests/test_milestone2.py — Milestone 2: Dashboard UI Tests

Smoke tests that verify the UI modules are correctly structured
without needing a running Qt display.

Run with:
    pytest tests/test_milestone2.py -v
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def test_charts_module_importable():
    """charts.py must be importable."""
    import netpath_sentinel.ui.charts as charts_mod
    assert hasattr(charts_mod, "LatencyChart")
    assert hasattr(charts_mod, "ActivityChart")


def test_latency_chart_has_update_method():
    """LatencyChart must expose update_data() for Milestone 3 wiring."""
    from netpath_sentinel.ui.charts import LatencyChart
    assert callable(getattr(LatencyChart, "update_data", None))


def test_activity_chart_has_update_method():
    """ActivityChart must expose update_data() for Milestone 3 wiring."""
    from netpath_sentinel.ui.charts import ActivityChart
    assert callable(getattr(ActivityChart, "update_data", None))


def test_dashboard_window_class_present():
    """DashboardWindow must be importable and have the right dimensions."""
    from netpath_sentinel.ui.dashboard import DashboardWindow
    assert DashboardWindow.WINDOW_WIDTH  == 420
    assert DashboardWindow.WINDOW_HEIGHT == 650


def test_dashboard_module_has_required_views():
    """The dashboard module must contain all view classes."""
    import netpath_sentinel.ui.dashboard as dash
    assert hasattr(dash, "_DashboardView")
    assert hasattr(dash, "_HistoryView")
    assert hasattr(dash, "_SettingsView")
    assert hasattr(dash, "_NavBar")
    assert hasattr(dash, "_TitleBar")
    assert hasattr(dash, "_StatusIndicator")


def test_mock_latency_generator():
    """Mock latency data must return correct length and sane values."""
    from netpath_sentinel.ui.charts import _mock_latency
    data = _mock_latency(60)
    assert len(data) == 60
    assert all(isinstance(v, float) for v in data)
    assert all(v >= 5.0 for v in data)   # no negative or zero latency
    assert any(v > 50 for v in data)     # must have at least one spike


def test_mock_activity_generator():
    """Mock activity data must return correct length and positive values."""
    from netpath_sentinel.ui.charts import _mock_activity
    data = _mock_activity(30, peak=80)
    assert len(data) == 30
    assert all(v >= 1.0 for v in data)


def test_stylesheet_has_color_palette():
    """APP_STYLESHEET must include all palette colors from the design spec."""
    from netpath_sentinel.ui.styles import APP_STYLESHEET
    required_colors = ["#0f1117", "#1a1d24", "#22c55e", "#3b82f6", "#ef4444"]
    for color in required_colors:
        assert color in APP_STYLESHEET, f"Missing color {color} in APP_STYLESHEET"
