"""
NetPath Sentinel — Application Entry Point

Run this file to start the application:
    python src/netpath_sentinel/main.py

What happens on startup:
    1. A Qt application is created (Qt is the GUI framework under PySide6)
    2. Qt is told NOT to quit when the dashboard window closes
       (the app lives in the system tray, not in a window)
    3. A system tray icon is created and shown
    4. The Qt event loop starts — this blocks until the user exits
"""

import sys
import os

# When running directly with `python src/netpath_sentinel/main.py`,
# Python needs to know where to find the `netpath_sentinel` package.
# This adds the `src/` directory to the module search path.
_src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from PySide6.QtWidgets import QApplication
from netpath_sentinel.tray.tray import TrayIcon


def main() -> None:
    """Create the application, show the tray icon, and start the event loop."""

    # QApplication is the foundation of every PySide6 app.
    # sys.argv passes command-line arguments to Qt (e.g., --platform).
    app = QApplication(sys.argv)

    # IMPORTANT: By default Qt quits when the last visible window closes.
    # We are a tray application — the dashboard popup is not the application.
    # Setting this to False means closing the dashboard keeps us running.
    app.setQuitOnLastWindowClosed(False)

    # Give the application a name (shown in some OS dialogs).
    app.setApplicationName("NetPath Sentinel")
    app.setApplicationVersion("0.1.0")

    # Create and show the system tray icon.
    tray = TrayIcon(app)
    tray.show()

    print("[NetPath Sentinel] Running in system tray. Right-click the tray icon to exit.")

    # app.exec() starts the Qt event loop.
    # This blocks here until the application exits (e.g., user clicks Exit).
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
