"""
tray/tray.py — System Tray Icon and Context Menu

Manages the Windows system tray icon, which is the primary
user-facing component of NetPath Sentinel.

Changes from Milestone 1:
    - Now accepts a NetworkMonitor instance and passes it to DashboardWindow.
    - The tray icon color will eventually reflect network state (Milestone 4+).
      For now it always shows green (the monitor has started).
"""

from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QBrush
from PySide6.QtCore import Qt

from netpath_sentinel.ui.dashboard import DashboardWindow
from netpath_sentinel.monitoring.network_monitor import NetworkMonitor


def _create_tray_icon(connected: bool = True) -> QIcon:
    """
    Draw a WiFi-style tray icon programmatically using Qt's painter API.

    Drawing in code (rather than loading an image file) lets us update the
    icon color dynamically to reflect network state changes:
        Green  (#22c55e) = connected / healthy
        Orange (#f59e0b) = degraded
        Red    (#ef4444) = disconnected

    The icon is drawn at 64×64 and Windows scales it to the tray size (~16-20px).
    """
    size = 64
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)

    painter = QPainter(px)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    color = QColor("#22c55e") if connected else QColor("#ef4444")

    # Dark circle background
    painter.setBrush(QBrush(QColor("#1a1d24")))
    painter.setPen(QPen(color, 3))
    painter.drawEllipse(4, 4, size - 8, size - 8)

    # WiFi arcs (outer, middle) + center dot
    cx, cy = size // 2, size // 2 + 8
    painter.setPen(QPen(color, 4, Qt.PenStyle.SolidLine,
                        Qt.PenCapStyle.RoundCap))

    from PySide6.QtCore import QRect
    painter.drawArc(QRect(cx - 22, cy - 22, 44, 44), 30 * 16, 120 * 16)
    painter.drawArc(QRect(cx - 14, cy - 14, 28, 28), 30 * 16, 120 * 16)

    painter.setBrush(QBrush(color))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(cx - 4, cy - 2, 8, 8)

    painter.end()
    return QIcon(px)


class TrayIcon(QSystemTrayIcon):
    """
    The NetPath Sentinel system tray icon.

    Holds references to both the NetworkMonitor (for future status-based
    icon updates) and the DashboardWindow (to show/hide on click).
    """

    def __init__(self, app: QApplication, monitor: NetworkMonitor) -> None:
        super().__init__()

        self._app     = app
        self._monitor = monitor

        # Create the dashboard window once; reuse it across show/hide cycles
        self._dashboard = DashboardWindow(monitor)

        self.setIcon(_create_tray_icon(connected=True))
        self.setToolTip("NetPath Sentinel — Monitoring")

        self._build_menu()

        # Single left-click toggles the dashboard
        self.activated.connect(self._on_activated)

    def _build_menu(self) -> None:
        menu = QMenu()
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
            QMenu::item { padding: 6px 20px 6px 12px; border-radius: 4px; }
            QMenu::item:selected { background-color: #2d3748; color: #63b3ed; }
            QMenu::separator { height: 1px; background: #2d3748; margin: 4px 8px; }
        """)

        open_act = menu.addAction("📊  Open Dashboard")
        open_act.triggered.connect(self._show_dashboard)

        menu.addSeparator()

        exit_act = menu.addAction("✕  Exit NetPath Sentinel")
        exit_act.triggered.connect(self._quit)

        self.setContextMenu(menu)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Single left-click toggles the dashboard open/closed."""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self._dashboard.isVisible():
                self._dashboard.hide()
            else:
                self._show_dashboard()

    def _show_dashboard(self) -> None:
        """Position the dashboard near the system tray and bring it to front."""
        dash = self._dashboard
        screen_rect = self._app.primaryScreen().availableGeometry()

        # Place bottom-right, just above the taskbar
        x = screen_rect.right()  - dash.width()  - 12
        y = screen_rect.bottom() - dash.height() - 12

        dash.move(x, y)
        dash.show()
        dash.raise_()
        dash.activateWindow()

    def _quit(self) -> None:
        print("[NetPath Sentinel] Exiting.")
        self._app.quit()
