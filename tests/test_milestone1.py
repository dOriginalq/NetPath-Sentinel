"""
tests/test_milestone1.py — Milestone 1: Tray Application Tests

These are minimal smoke tests that verify the application modules
can be imported and the key classes are present.

We avoid starting an actual Qt application in tests (that requires a
display / event loop). GUI behaviour is verified manually per the
testing checklist in the development log.

Run with:
    pytest tests/test_milestone1.py -v
"""

import sys
import os

# Ensure the src/ directory is on the path so we can import netpath_sentinel
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def test_main_module_importable():
    """The main entry point module must be importable without side effects."""
    import netpath_sentinel.main as main_mod
    assert hasattr(main_mod, "main"), "main() function must exist in main.py"


def test_package_version():
    """The package must expose a version string."""
    import netpath_sentinel
    assert hasattr(netpath_sentinel, "__version__")
    assert isinstance(netpath_sentinel.__version__, str)
    assert len(netpath_sentinel.__version__) > 0


def test_styles_module_importable():
    """styles.py must be importable and expose APP_STYLESHEET."""
    from netpath_sentinel.ui.styles import APP_STYLESHEET
    assert isinstance(APP_STYLESHEET, str)
    assert len(APP_STYLESHEET) > 0


def test_styles_contains_dark_background():
    """The stylesheet must use the dark background color from the design spec."""
    from netpath_sentinel.ui.styles import APP_STYLESHEET
    assert "#0f1117" in APP_STYLESHEET, "Dark background color must be defined in APP_STYLESHEET"


def test_tray_module_importable():
    """tray.py must be importable (no Qt display needed for import)."""
    # We only import — we don't instantiate QSystemTrayIcon since that
    # requires a running QApplication.
    import netpath_sentinel.tray.tray as tray_mod
    assert hasattr(tray_mod, "TrayIcon")
    assert hasattr(tray_mod, "_create_tray_icon")


def test_dashboard_module_importable():
    """dashboard.py must be importable."""
    import netpath_sentinel.ui.dashboard as dash_mod
    assert hasattr(dash_mod, "DashboardWindow")


def test_monitoring_placeholders_importable():
    """All monitoring placeholder modules must be importable."""
    import netpath_sentinel.monitoring.network_monitor
    import netpath_sentinel.monitoring.connectivity
    import netpath_sentinel.monitoring.dns_monitor
    import netpath_sentinel.monitoring.latency_monitor


def test_storage_placeholder_importable():
    """Storage placeholder must be importable."""
    import netpath_sentinel.storage.database


def test_models_placeholder_importable():
    """Models placeholder must be importable."""
    import netpath_sentinel.models.network_event
