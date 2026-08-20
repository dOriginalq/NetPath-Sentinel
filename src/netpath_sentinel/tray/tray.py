"""
tray/tray.py — System Tray Icon and Context Menu

This module implements the Windows system tray icon for NetPath Sentinel.

How Qt tray icons work:
    QSystemTrayIcon is a Qt class that places a small icon in the Windows
    notification area (system tray). It supports:
      - A context menu (right-click menu)
      - Left-click activation signals
      - Tooltip text
      - Balloon notifications (future use for alerts)

The tray icon is the primary way the user interacts with NetPath Sentinel.
The application runs invisibly in the background; the tray icon is its handle.
"""

from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QBrush
from PySide6.QtCore import Qt, QPoint, QRect

from netpath_sentinel.ui.dashboard import DashboardWindow


def _create_tray_icon(connected: bool = True) -> QIcon:
    """
    Draw a simple tray icon programmatically using Qt's painter.

    We create a 64x64 pixmap and draw a styled network indicator on it.
    Windows scales this down to the system tray size (~16x16 or 20x20).

    Why draw it in code rather than loading a file?
    - No extra asset files to manage at this early stage
    - The icon can later be updated dynamically to reflect network state
      (e.g., green = OK, orange = degraded, red = disconnected)

    Args:
        connected: If True, draw a green "healthy" icon; otherwise red.
    """
    size = 64
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)  # Start with a transparent background

    painter = QPainter(px)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Choose color based on connection state
    color = QColor("#22c55e") if connected else QColor("#ef4444")  # green / red

    # Draw a filled circle as the icon background
    painter.setBrush(QBrush(QColor("#1a1d24")))  # dark background
    painter.setPen(QPen(color, 3))
    painter.drawEllipse(4, 4, size - 8, size - 8)

    # Draw three WiFi-style arcs to represent network connectivity
    # Arc: drawArc(x, y, w, h, startAngle*16, spanAngle*16)  — Qt uses 1/16 degree units
    center_x = size // 2
    center_y = size // 2 + 8

    painter.setPen(QPen(color, 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))

    # Outer arc
    arc_rect = QRect(center_x - 22, center_y - 22, 44, 44)
    painter.drawArc(arc_rect, 30 * 16, 120 * 16)

    # Middle arc
    arc_rect = QRect(center_x - 14, center_y - 14, 28, 28)
    painter.drawArc(arc_rect, 30 * 16, 120 * 16)

    # Small inner dot
    painter.setBrush(QBrush(color))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(center_x - 4, center_y - 2, 8, 8)

    painter.end()
    return QIcon(px)


class TrayIcon(QSystemTrayIcon):
    """
    The NetPath Sentinel system tray icon.

    Responsibilities:
      - Display a tray icon reflecting network state
      - Provide a right-click context menu
      - Show/hide the dashboard popup when clicked
    """

    def __init__(self, app: QApplication) -> None:
        super().__init__()

        self._app = app

        # Create the dashboard window. It starts hidden.
        # We create it once and reuse it (show/hide) rather than
        # creating a new window each time — this is faster and preserves state.
        self._dashboard = DashboardWindow()

        # Set the tray icon image
        self.setIcon(_create_tray_icon(connected=True))

        # Tooltip shown when the user hovers over the tray icon
        self.setToolTip("NetPath Sentinel — Monitoring")

        # Build the right-click context menu
        self._build_menu()

        # Connect left-click (or double-click on some systems) to toggle the dashboard.
        # QSystemTrayIcon.ActivationReason tells us *how* the icon was activated:
        #   Trigger      = single left click
        #   DoubleClick  = double left click
        #   Context      = right click (Qt handles this automatically for the menu)
        self.activated.connect(self._on_tray_activated)

    def _build_menu(self) -> None:
        """Create the right-click context menu for the tray icon."""
        menu = QMenu()

        # Apply a minimal dark style to the menu
        menu.setStyleSheet("""
            QMenu {
                background-color: #1a1d24;
                color: #e2e8f0;
                border: 1px solid #2d3748;
                border-radius: 6px;
                padding: 4px;
                font-family: "Segoe UI", sans-serif;
                font-size: 13px;
            }
            QMenu::item {
                padding: 6px 20px 6px 12px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #2d3748;
                color: #63b3ed;
            }
            QMenu::separator {
                height: 1px;
                background: #2d3748;
                margin: 4px 8px;
            }
        """)

        # --- Open Dashboard action ---
        open_action = menu.addAction("📊  Open Dashboard")
        open_action.triggered.connect(self._show_dashboard)

        menu.addSeparator()

        # --- Exit action ---
        # This is the ONLY way to fully terminate NetPath Sentinel.
        # Closing the dashboard does NOT exit the app.
        exit_action = menu.addAction("✕  Exit NetPath Sentinel")
        exit_action.triggered.connect(self._quit)

        self.setContextMenu(menu)

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """
        Handle tray icon clicks.

        Single left-click toggles the dashboard open/closed.
        Right-click is handled automatically by Qt (shows the context menu).
        """
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            # Toggle: if the dashboard is visible, hide it; otherwise show it
            if self._dashboard.isVisible():
                self._dashboard.hide()
            else:
                self._show_dashboard()

    def _show_dashboard(self) -> None:
        """
        Position the dashboard near the system tray and show it.

        We position the popup near the bottom-right corner of the screen
        (where the system tray typically lives on Windows).
        The popup appears just above the taskbar.
        """
        dashboard = self._dashboard

        # Get the screen geometry to position near the tray area
        screen = self._app.primaryScreen()
        screen_rect = screen.availableGeometry()  # excludes taskbar

        # Place the dashboard at the bottom-right corner, above the taskbar
        x = screen_rect.right() - dashboard.width() - 12
        y = screen_rect.bottom() - dashboard.height() - 12

        dashboard.move(x, y)
        dashboard.show()
        dashboard.raise_()       # Bring to front
        dashboard.activateWindow()  # Give it keyboard focus

    def _quit(self) -> None:
        """Fully exit NetPath Sentinel."""
        print("[NetPath Sentinel] Exiting.")
        self._app.quit()
