"""
ui/dashboard.py — Popup Dashboard Window

This is the Milestone 1 version of the dashboard.
Its only job is to demonstrate:
  - A frameless dark popup window
  - A draggable title bar (since Qt frameless windows have no OS chrome)
  - A close button that HIDES the window (not exits the app)

The full dashboard UI will be implemented in Milestone 2.

Why frameless?
    A standard OS window (with title bar, min/max/close buttons) looks
    out of place for a small tray popup. A frameless QWidget lets us
    draw our own title bar matching the dark theme design reference.

How dragging works:
    Since there is no OS title bar to drag, we track mouse press/move
    events manually and update the window position accordingly.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
)
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QColor

from netpath_sentinel.ui.styles import APP_STYLESHEET


class DashboardWindow(QWidget):
    """
    The NetPath Sentinel popup dashboard window.

    Milestone 1: Minimal placeholder with title bar and close button.
    Milestone 2: Full UI based on assets/ui-reference.png.
    """

    # Fixed popup dimensions (matches the reference UI proportions)
    WINDOW_WIDTH = 400
    WINDOW_HEIGHT = 520

    def __init__(self) -> None:
        super().__init__()

        # ── Window flags ──────────────────────────────────────────────────
        # Qt.FramelessWindowHint: Remove the OS title bar/border
        # Qt.WindowStaysOnTopHint: Keep above other windows when shown
        # Qt.Tool: Don't show in the taskbar (we're a tray app)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )

        # Make the window background use our dark theme
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

        self.setFixedSize(self.WINDOW_WIDTH, self.WINDOW_HEIGHT)
        self.setStyleSheet(APP_STYLESHEET)

        # Track mouse position for window dragging
        self._drag_start_pos: QPoint | None = None

        self._build_ui()

    def _build_ui(self) -> None:
        """Build the Milestone 1 placeholder UI."""
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── Title bar ─────────────────────────────────────────────────────
        title_bar = self._make_title_bar()
        root_layout.addWidget(title_bar)

        # ── Body ──────────────────────────────────────────────────────────
        body = self._make_body()
        root_layout.addWidget(body, 1)

        # ── Footer ────────────────────────────────────────────────────────
        footer = self._make_footer()
        root_layout.addWidget(footer)

    def _make_title_bar(self) -> QWidget:
        """
        Custom title bar widget.

        Since the window is frameless, we draw our own title bar.
        This bar also serves as the drag handle to move the window.
        """
        bar = QFrame()
        bar.setFixedHeight(44)
        bar.setStyleSheet("""
            QFrame {
                background-color: #13161e;
                border-bottom: 1px solid #2d3748;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
        """)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(14, 0, 10, 0)
        layout.setSpacing(8)

        # WiFi icon + app name
        icon_label = QLabel("📡")
        icon_label.setStyleSheet("background: transparent; font-size: 16px;")

        title_label = QLabel("NetPath Sentinel")
        title_label.setStyleSheet("""
            background: transparent;
            color: #e2e8f0;
            font-size: 14px;
            font-weight: bold;
            font-family: "Segoe UI", sans-serif;
        """)

        layout.addWidget(icon_label)
        layout.addWidget(title_label)
        layout.addStretch()

        # Settings placeholder button
        settings_btn = self._make_icon_button("⚙")
        settings_btn.setToolTip("Settings (coming soon)")
        layout.addWidget(settings_btn)

        # Minimize — just hides the dashboard, app keeps running
        min_btn = self._make_icon_button("−")
        min_btn.setToolTip("Hide dashboard")
        min_btn.clicked.connect(self.hide)
        layout.addWidget(min_btn)

        # Close — same as minimize for a tray app: hide, don't quit
        close_btn = self._make_icon_button("✕")
        close_btn.setToolTip("Close dashboard (monitoring continues)")
        close_btn.setStyleSheet(close_btn.styleSheet() + """
            QPushButton:hover { background-color: #c53030; color: white; }
        """)
        close_btn.clicked.connect(self.hide)
        layout.addWidget(close_btn)

        return bar

    def _make_icon_button(self, symbol: str) -> QPushButton:
        """Create a small square icon button for the title bar."""
        btn = QPushButton(symbol)
        btn.setFixedSize(28, 28)
        btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #94a3b8;
                font-size: 14px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2d3748;
                color: #e2e8f0;
            }
        """)
        return btn

    def _make_body(self) -> QWidget:
        """
        Placeholder body for Milestone 1.

        This will be replaced by the full dashboard UI in Milestone 2.
        """
        body = QFrame()
        body.setStyleSheet("QFrame { background-color: #0f1117; }")

        layout = QVBoxLayout(body)
        layout.setContentsMargins(20, 30, 20, 20)
        layout.setSpacing(16)

        # Status badge
        status_card = QFrame()
        status_card.setProperty("class", "card")
        status_card.setStyleSheet("""
            QFrame {
                background-color: #1a1d24;
                border: 1px solid #2d3748;
                border-radius: 8px;
                padding: 4px;
            }
        """)
        status_layout = QHBoxLayout(status_card)
        status_layout.setContentsMargins(16, 12, 16, 12)

        status_dot = QLabel("●")
        status_dot.setStyleSheet("color: #22c55e; font-size: 18px; background: transparent;")

        status_info = QVBoxLayout()
        status_title = QLabel("Connected")
        status_title.setStyleSheet("color: #22c55e; font-weight: bold; font-size: 16px; background: transparent;")
        status_sub = QLabel("Monitoring active")
        status_sub.setStyleSheet("color: #94a3b8; font-size: 11px; background: transparent;")
        status_info.addWidget(status_title)
        status_info.addWidget(status_sub)

        status_layout.addWidget(status_dot)
        status_layout.addSpacing(8)
        status_layout.addLayout(status_info)
        status_layout.addStretch()

        layout.addWidget(status_card)

        # Milestone note
        note_frame = QFrame()
        note_frame.setStyleSheet("""
            QFrame {
                background-color: #1a2035;
                border: 1px solid #2d4a7a;
                border-radius: 8px;
            }
        """)
        note_layout = QVBoxLayout(note_frame)
        note_layout.setContentsMargins(16, 14, 16, 14)
        note_layout.setSpacing(8)

        note_title = QLabel("🚧  Milestone 1 — Tray Application")
        note_title.setStyleSheet("color: #63b3ed; font-weight: bold; font-size: 13px; background: transparent;")

        note_body = QLabel(
            "The system tray is working.\n\n"
            "• Left-click the tray icon to show/hide this window\n"
            "• Right-click the tray icon for the context menu\n"
            "• Closing this window does NOT exit the app\n"
            "• Use 'Exit NetPath Sentinel' from the tray menu to quit\n\n"
            "Full dashboard UI will be implemented in Milestone 2."
        )
        note_body.setStyleSheet("color: #94a3b8; font-size: 12px; background: transparent; line-height: 1.5;")
        note_body.setWordWrap(True)

        note_layout.addWidget(note_title)
        note_layout.addWidget(note_body)

        layout.addWidget(note_frame)
        layout.addStretch()

        return body

    def _make_footer(self) -> QWidget:
        """Footer bar with version and status."""
        footer = QFrame()
        footer.setFixedHeight(36)
        footer.setStyleSheet("""
            QFrame {
                background-color: #13161e;
                border-top: 1px solid #2d3748;
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
            }
        """)

        layout = QHBoxLayout(footer)
        layout.setContentsMargins(14, 0, 14, 0)

        version_label = QLabel("v0.1.0  ·  Milestone 1")
        version_label.setStyleSheet("color: #4a5568; font-size: 11px; background: transparent;")

        status_label = QLabel("● Running")
        status_label.setStyleSheet("color: #22c55e; font-size: 11px; background: transparent;")

        layout.addWidget(version_label)
        layout.addStretch()
        layout.addWidget(status_label)

        return footer

    # ── Drag to move the frameless window ─────────────────────────────────

    def mousePressEvent(self, event) -> None:
        """Record the position where the user started dragging the window."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        """Move the window by the amount the mouse has moved since press."""
        if self._drag_start_pos is not None and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_start_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        """Clear the drag start position when the mouse button is released."""
        self._drag_start_pos = None
        super().mouseReleaseEvent(event)
