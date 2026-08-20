"""
tray/tray.py — System Tray Icon and Context Menu

Manages the Windows system tray icon, which is the primary
user-facing component of NetPath Sentinel.

Milestone 4 updates:
    - Tray icon dynamically updates color based on health status:
        * Healthy    -> Green  (#22c55e)
        * Degraded   -> Orange (#f59e0b)
        * Disconnected -> Red  (#ef4444)
    - Tooltip dynamically shows live network state (latency, loss, status)
    - Periodic QTimer on UI thread syncs tray icon with monitor state
"""

from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QBrush
from PySide6.QtCore import Qt, QTimer

from netpath_sentinel.ui.dashboard import DashboardWindow
from netpath_sentinel.monitoring.network_monitor import NetworkMonitor


_COLOR_MAP = {
    "healthy":      "#22c55e",
    "degraded":     "#f59e0b",
    "disconnected": "#ef4444",
}


def _create_tray_icon(status: str = "healthy") -> QIcon:
    """
    Draw a WiFi-style tray icon programmatically using Qt's painter API.

    Drawing in code (rather than loading an image file) lets us update the
    icon color dynamically to reflect network state changes:
        Green  (#22c55e) = healthy
        Orange (#f59e0b) = degraded
        Red    (#ef4444) = disconnected

    The icon is drawn at 64×64 and Windows scales it to the tray size (~16-20px).
    """
    size = 64
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)

    painter = QPainter(px)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    hex_color = _COLOR_MAP.get(status, "#22c55e")
    color = QColor(hex_color)

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

    Holds references to both the NetworkMonitor (for dynamic status-based
    icon and tooltip updates) and the DashboardWindow (to show/hide on click).
    """

    def __init__(self, app: QApplication, monitor: NetworkMonitor) -> None:
        super().__init__()

        self._app     = app
        self._monitor = monitor
        self._current_status = "healthy"

        # Create the dashboard window once; reuse it across show/hide cycles
        self._dashboard = DashboardWindow(monitor)

        self.setIcon(_create_tray_icon("healthy"))
        self.setToolTip("NetPath Sentinel — Initializing")

        self._build_menu()

        # Single left-click toggles the dashboard
        self.activated.connect(self._on_activated)

        # Periodic timer to update tray icon and tooltip based on monitor state
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._sync_tray_state)
        self._timer.start(2500)

    def _sync_tray_state(self) -> None:
        """Update the tray icon and tooltip to reflect monitor health status."""
        state = self._monitor.state
        status = state.health_status

        if status != self._current_status:
            self._current_status = status
            self.setIcon(_create_tray_icon(status))

        # Format tooltip
        if status == "healthy":
            tip = f"NetPath Sentinel — Healthy ({state.latency_ms:.0f}ms · {state.packet_loss_pct:.0f}% loss)"
        elif status == "degraded":
            tip = f"NetPath Sentinel — Degraded ({state.health_reason})"
        else:
            tip = f"NetPath Sentinel — Disconnected ({state.interface_name})"

        self.setToolTip(tip)

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
