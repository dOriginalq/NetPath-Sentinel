"""
NetPath Sentinel — Application Entry Point

Run with:
    python src/netpath_sentinel/main.py

Startup sequence:
    1. Create Qt application
    2. Disable Qt's default "quit on last window close" behaviour
       (we are a tray app — closing the popup must not exit the process)
    3. Create and START the background network monitor
    4. Create the system tray icon (passes monitor to the dashboard)
    5. Enter the Qt event loop — blocks until Exit is chosen from the tray
"""

import sys
import os

# Add src/ to sys.path so `netpath_sentinel` is importable when running
# this file directly with: python src/netpath_sentinel/main.py
_src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from PySide6.QtWidgets import QApplication

from netpath_sentinel.tray.tray import TrayIcon
from netpath_sentinel.monitoring.network_monitor import NetworkMonitor


def main() -> None:
    """Entry point: create the Qt application, start monitoring, show tray."""

    app = QApplication(sys.argv)

    # Without this, Qt would exit when the dashboard popup is closed.
    # We want the app to keep running in the tray instead.
    app.setQuitOnLastWindowClosed(False)

    app.setApplicationName("NetPath Sentinel")
    app.setApplicationVersion("0.1.0")

    # Create and start the background monitor.
    # The monitor runs in its own daemon thread — it will continue
    # running as long as the application is alive.
    monitor = NetworkMonitor()
    monitor.start()

    # Create the tray icon. It receives the monitor so it can pass it
    # to the dashboard, which uses it to display live measurements.
    tray = TrayIcon(app, monitor)
    tray.show()

    print("[NetPath Sentinel] Running in system tray. Right-click the tray icon to exit.")

    # Enter the Qt event loop. This call blocks until app.quit() is called
    # (e.g., when the user clicks Exit from the tray menu).
    exit_code = app.exec()

    # Clean up: signal the monitor thread to stop before exiting.
    # (daemon=True means it would be killed anyway, but explicit is cleaner)
    monitor.stop()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
