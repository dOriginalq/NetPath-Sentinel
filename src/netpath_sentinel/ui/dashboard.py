"""
ui/dashboard.py — Full Popup Dashboard Window

Milestone 2: Complete UI based on assets/ui-reference.png.

Layout:
    DashboardWindow (frameless QWidget, 420 × 650 px)
    ├── _TitleBar        — draggable header with window controls
    ├── QStackedWidget
    │   ├── _DashboardView  — status, speed, metrics, charts
    │   ├── _HistoryView    — recent events, test target, network details
    │   └── _SettingsView   — placeholder for Milestone TBD
    └── _NavBar          — three-tab bottom navigation bar

All metric values display "—" (placeholder) at Milestone 2.
Chart data is clearly labeled MOCK DATA at Milestone 2.
Real values will be wired in at Milestone 3+.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QStackedWidget, QGridLayout,
)
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPixmap

from netpath_sentinel.ui.styles import APP_STYLESHEET
from netpath_sentinel.ui.charts import LatencyChart, ActivityChart


# ── Shared style snippets ─────────────────────────────────────────────────────
_CARD = """
    QFrame {
        background-color: #1a1d24;
        border: 1px solid #252b38;
        border-radius: 8px;
    }
"""
_LBL = "background: transparent; font-family: 'Segoe UI';"

_GREEN  = "#22c55e"
_ORANGE = "#f59e0b"
_RED    = "#ef4444"
_BLUE   = "#3b82f6"
_PURPLE = "#a855f7"
_MUTED  = "#94a3b8"
_DIM    = "#4a5568"


# ── Small reusable helpers ────────────────────────────────────────────────────

def _lbl(text: str, color: str = "#e2e8f0", size: int = 12,
         bold: bool = False, align=Qt.AlignmentFlag.AlignLeft) -> QLabel:
    """Create a styled QLabel."""
    l = QLabel(text)
    weight = "bold" if bold else "normal"
    l.setStyleSheet(
        f"{_LBL} color:{color}; font-size:{size}px; font-weight:{weight};"
    )
    l.setAlignment(align)
    return l


def _sep() -> QFrame:
    """Thin horizontal divider line."""
    line = QFrame()
    line.setFixedHeight(1)
    line.setStyleSheet("background-color: #252b38; border: none;")
    return line


def _metric_cell(label: str, value: str, unit: str = "",
                 color: str = _GREEN) -> QFrame:
    """
    A single compact metric cell used in the 3-column grids.

    Example:
        Ping
        24 ms        ← value in green
    """
    cell = QFrame()
    cell.setStyleSheet(_CARD)
    v = QVBoxLayout(cell)
    v.setContentsMargins(8, 8, 8, 8)
    v.setSpacing(2)

    lbl_label = _lbl(label, _MUTED, 11, align=Qt.AlignmentFlag.AlignCenter)
    v.addWidget(lbl_label)

    # Value + optional unit on the same row
    val_row = QWidget()
    val_row.setStyleSheet("background: transparent;")
    row = QHBoxLayout(val_row)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(2)
    row.setAlignment(Qt.AlignmentFlag.AlignCenter)

    lbl_val  = _lbl(value, color, 15, bold=True, align=Qt.AlignmentFlag.AlignRight)
    lbl_unit = _lbl(unit,  _MUTED, 10, align=Qt.AlignmentFlag.AlignLeft)
    row.addWidget(lbl_val)
    if unit:
        row.addWidget(lbl_unit)

    v.addWidget(val_row)
    return cell


def _section_title(text: str) -> QWidget:
    """Bold white section title with a muted 'View All' / 'Edit' link on the right."""
    w = QWidget()
    w.setStyleSheet("background: transparent;")
    row = QHBoxLayout(w)
    row.setContentsMargins(0, 0, 0, 0)
    row.addWidget(_lbl(text, "#e2e8f0", 13, bold=True))
    row.addStretch()
    return w


# ══════════════════════════════════════════════════════════════════════════════
# Title Bar
# ══════════════════════════════════════════════════════════════════════════════

class _TitleBar(QFrame):
    """
    Custom frameless window title bar.

    Provides:
    - App icon + name (left)
    - Settings / minimize / close buttons (right)
    - Mouse drag support (the title bar is the drag handle)
    """

    def __init__(self, on_close, parent=None):
        super().__init__(parent)
        self.setFixedHeight(44)
        self.setStyleSheet("""
            QFrame {
                background-color: #13161e;
                border-bottom: 1px solid #252b38;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
        """)

        row = QHBoxLayout(self)
        row.setContentsMargins(14, 0, 10, 0)
        row.setSpacing(6)

        icon = _lbl("📡", size=16)
        title = _lbl("NetPath Sentinel", "#e2e8f0", 14, bold=True)
        row.addWidget(icon)
        row.addWidget(title)
        row.addStretch()

        for symbol, tip, cb in [
            ("⚙", "Settings (coming soon)", None),
            ("−", "Hide dashboard", on_close),
            ("✕", "Close (monitoring continues)", on_close),
        ]:
            btn = QPushButton(symbol)
            btn.setFixedSize(26, 26)
            btn.setToolTip(tip)
            hover_extra = (
                "QPushButton:hover { background-color:#c53030; color:white; }"
                if symbol == "✕" else ""
            )
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; border: none;
                    color: #64748b; font-size: 13px; border-radius: 4px;
                }}
                QPushButton:hover {{ background-color: #2d3748; color: #e2e8f0; }}
                {hover_extra}
            """)
            if cb:
                btn.clicked.connect(cb)
            row.addWidget(btn)


# ══════════════════════════════════════════════════════════════════════════════
# Dashboard View  (left panel of UI reference)
# ══════════════════════════════════════════════════════════════════════════════

class _DashboardView(QWidget):
    """
    Main metrics panel — mirrors the left side of assets/ui-reference.png.

    Sections (top → bottom):
        1. Connection status card
        2. Download / Upload speed row
        3. Ping / Jitter / Packet Loss metric grid
        4. DNS / IPv4 / IPv6 status grid
        5. Latency line chart
        6. Activity bar chart
        7. Footer (uptime · test server)

    All values show "—" placeholder at Milestone 2.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #0f1117;")

        # Outer layout holds a scroll area so content is never clipped
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical { background:#0f1117; width:5px; border-radius:3px; }
            QScrollBar::handle:vertical { background:#2d3748; border-radius:3px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
        """)

        content = QWidget()
        content.setStyleSheet("background: #0f1117;")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(12, 10, 12, 8)
        cl.setSpacing(7)

        cl.addWidget(self._make_status_card())
        cl.addWidget(self._make_speed_row())
        cl.addWidget(self._make_metric_grid())
        cl.addWidget(self._make_protocol_grid())
        cl.addWidget(LatencyChart())
        cl.addWidget(ActivityChart())
        cl.addWidget(self._make_footer())

        scroll.setWidget(content)
        outer.addWidget(scroll)

    # ── Section builders ──────────────────────────────────────────────────

    def _make_status_card(self) -> QFrame:
        """Green 'Connected' card with signal bars indicator."""
        card = QFrame()
        card.setFixedHeight(68)
        card.setStyleSheet(_CARD)

        row = QHBoxLayout(card)
        row.setContentsMargins(14, 0, 14, 0)
        row.setSpacing(10)

        # Status circle indicator — drawn programmatically
        indicator = _StatusIndicator(connected=True)
        row.addWidget(indicator)

        # Status text
        col = QVBoxLayout()
        col.setSpacing(1)
        col.addWidget(_lbl("Connected", _GREEN, 15, bold=True))
        col.addWidget(_lbl("Network interface active  ·  placeholder", _MUTED, 10))
        row.addLayout(col)
        row.addStretch()

        # Signal bars (unicode block characters)
        bars = _lbl("▁▃▅▇", _GREEN, 16)
        bars.setStyleSheet(bars.styleSheet() + " letter-spacing: 2px;")
        row.addWidget(bars)

        return card

    def _make_speed_row(self) -> QFrame:
        """Download / upload speed display."""
        card = QFrame()
        card.setFixedHeight(62)
        card.setStyleSheet(_CARD)

        row = QHBoxLayout(card)
        row.setContentsMargins(16, 0, 16, 0)
        row.setSpacing(0)

        # Download side
        dl = QHBoxLayout()
        dl.setSpacing(8)
        dl_arrow = _lbl("↓", _BLUE, 22, bold=True)
        dl_col = QVBoxLayout()
        dl_col.setSpacing(0)
        dl_col.addWidget(_lbl("—", "#e2e8f0", 20, bold=True))
        dl_col.addWidget(_lbl("Download", _MUTED, 10))
        dl.addWidget(dl_arrow)
        dl.addLayout(dl_col)
        dl.addWidget(_lbl("Mbps", _MUTED, 11))

        # Upload side
        ul = QHBoxLayout()
        ul.setSpacing(8)
        ul_arrow = _lbl("↑", _PURPLE, 22, bold=True)
        ul_col = QVBoxLayout()
        ul_col.setSpacing(0)
        ul_col.addWidget(_lbl("—", "#e2e8f0", 20, bold=True))
        ul_col.addWidget(_lbl("Upload", _MUTED, 10))
        ul.addWidget(ul_arrow)
        ul.addLayout(ul_col)
        ul.addWidget(_lbl("Mbps", _MUTED, 11))

        row.addLayout(dl)
        row.addStretch()

        # Divider
        div = QFrame()
        div.setFixedSize(1, 32)
        div.setStyleSheet("background:#252b38; border:none;")
        row.addWidget(div)

        row.addStretch()
        row.addLayout(ul)

        return card

    def _make_metric_grid(self) -> QWidget:
        """3-column grid: Ping | Jitter | Packet Loss"""
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        g = QGridLayout(w)
        g.setContentsMargins(0, 0, 0, 0)
        g.setSpacing(6)
        g.addWidget(_metric_cell("Ping",         "—",    "ms",  _GREEN),  0, 0)
        g.addWidget(_metric_cell("Jitter",        "—",    "ms",  _GREEN),  0, 1)
        g.addWidget(_metric_cell("Packet Loss",   "—",    "%",   _GREEN),  0, 2)
        return w

    def _make_protocol_grid(self) -> QWidget:
        """3-column grid: DNS | IPv4 | IPv6"""
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        g = QGridLayout(w)
        g.setContentsMargins(0, 0, 0, 0)
        g.setSpacing(6)
        g.addWidget(_metric_cell("DNS",  "—",       "ms",     _GREEN), 0, 0)
        g.addWidget(_metric_cell("IPv4", "Active",  "",        _GREEN), 0, 1)
        g.addWidget(_metric_cell("IPv6", "Active",  "",        _GREEN), 0, 2)
        return w

    def _make_footer(self) -> QFrame:
        """Slim footer: uptime · test server indicator."""
        bar = QFrame()
        bar.setFixedHeight(34)
        bar.setStyleSheet("QFrame { background: transparent; border-top: 1px solid #252b38; }")

        row = QHBoxLayout(bar)
        row.setContentsMargins(4, 0, 4, 0)

        row.addWidget(_lbl("⏱  Uptime: —:——:——", _DIM, 10))
        row.addStretch()

        dot = _lbl("●", _GREEN, 10)
        row.addWidget(_lbl("Test Server: Cloudflare", _DIM, 10))
        row.addSpacing(4)
        row.addWidget(dot)

        return bar


# ══════════════════════════════════════════════════════════════════════════════
# History View  (right panel of UI reference)
# ══════════════════════════════════════════════════════════════════════════════

class _HistoryView(QWidget):
    """
    Events, diagnostics, and network details panel.
    Mirrors the right side of assets/ui-reference.png.

    Sections:
        1. Recent Events list
        2. Current Test target
        3. Network Details (IP / Public IP / ASN / Route)
        4. Run Diagnostics button
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #0f1117;")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical { background:#0f1117; width:5px; border-radius:3px; }
            QScrollBar::handle:vertical { background:#2d3748; border-radius:3px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
        """)

        content = QWidget()
        content.setStyleSheet("background:#0f1117;")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(12, 10, 12, 8)
        cl.setSpacing(10)

        cl.addWidget(self._make_events_section())
        cl.addWidget(self._make_current_test())
        cl.addWidget(self._make_network_details())
        cl.addWidget(self._make_diagnostics_row())
        cl.addStretch()

        scroll.setWidget(content)
        outer.addWidget(scroll)

    # ── Section builders ──────────────────────────────────────────────────

    def _make_events_section(self) -> QFrame:
        """
        Recent network events list.

        At Milestone 2 this shows four static placeholder events.
        At Milestone 6+ this will read from the SQLite event store.
        """
        card = QFrame()
        card.setStyleSheet(_CARD)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(14, 12, 14, 12)
        cl.setSpacing(6)

        # Header row
        hdr = QWidget()
        hdr.setStyleSheet("background: transparent;")
        hrow = QHBoxLayout(hdr)
        hrow.setContentsMargins(0, 0, 0, 0)
        hrow.addWidget(_lbl("Recent Events", "#e2e8f0", 13, bold=True))
        hrow.addStretch()
        view_all = QPushButton("View All")
        view_all.setStyleSheet("""
            QPushButton {
                background: transparent; border: none;
                color: #3b82f6; font-size: 11px; padding: 0;
            }
            QPushButton:hover { color: #60a5fa; }
        """)
        hrow.addWidget(view_all)
        cl.addWidget(hdr)
        cl.addWidget(_sep())

        # Placeholder events — clearly marked as mock data
        events = [
            ("🔴", "—:——:——", "Connection Lost",     "—",     _RED),
            ("🟠", "—:——:——", "High Latency",         "— ms",  _ORANGE),
            ("🟠", "—:——:——", "DNS Timeout",          "—",     _ORANGE),
            ("🟢", "—:——:——", "Connection Restored",  "—",     _GREEN),
        ]

        for icon, ts, name, dur, color in events:
            cl.addWidget(self._make_event_row(icon, ts, name, dur, color))

        note = _lbl("[ Placeholder — live events from Milestone 6 ]", _DIM, 10)
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cl.addWidget(note)

        return card

    def _make_event_row(self, icon, ts, name, dur, color) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        row = QHBoxLayout(w)
        row.setContentsMargins(0, 2, 0, 2)
        row.setSpacing(8)

        row.addWidget(_lbl(icon, size=12))
        row.addWidget(_lbl(ts, _DIM, 11))
        row.addWidget(_lbl(name, color, 12))
        row.addStretch()
        row.addWidget(_lbl(dur, _MUTED, 11))

        return w

    def _make_current_test(self) -> QFrame:
        """Shows the currently monitored target host and its latest latency."""
        card = QFrame()
        card.setStyleSheet(_CARD)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(14, 12, 14, 12)
        cl.setSpacing(6)

        hdr = QWidget()
        hdr.setStyleSheet("background: transparent;")
        hrow = QHBoxLayout(hdr)
        hrow.setContentsMargins(0, 0, 0, 0)
        hrow.addWidget(_lbl("Current Test", "#e2e8f0", 13, bold=True))
        hrow.addStretch()
        edit_btn = QPushButton("Edit")
        edit_btn.setStyleSheet("""
            QPushButton {
                background: transparent; border: none;
                color: #3b82f6; font-size: 11px; padding: 0;
            }
            QPushButton:hover { color: #60a5fa; }
        """)
        hrow.addWidget(edit_btn)
        cl.addWidget(hdr)
        cl.addWidget(_sep())

        body = QWidget()
        body.setStyleSheet("background: transparent;")
        brow = QHBoxLayout(body)
        brow.setContentsMargins(0, 4, 0, 4)
        brow.setSpacing(12)

        globe = _lbl("🌐", size=22)
        info_col = QVBoxLayout()
        info_col.setSpacing(1)
        info_col.addWidget(_lbl("google.com", "#e2e8f0", 13, bold=True))
        info_col.addWidget(_lbl("—.—.—.—", _MUTED, 11))
        brow.addWidget(globe)
        brow.addLayout(info_col)
        brow.addStretch()
        brow.addWidget(_lbl("— ms", _GREEN, 15, bold=True))

        cl.addWidget(body)
        return card

    def _make_network_details(self) -> QFrame:
        """
        Local IP, public IP, ASN, route hop count.

        At Milestone 2: all values are placeholder dashes.
        At Milestone 8 (Network Diagnostics): populated with real data.
        """
        card = QFrame()
        card.setStyleSheet(_CARD)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(14, 12, 14, 12)
        cl.setSpacing(6)

        cl.addWidget(_lbl("Network Details", "#e2e8f0", 13, bold=True))
        cl.addWidget(_sep())

        rows = [
            ("📶", "IP Address",  "—.—.—.—"),
            ("🌐", "Public IP",   "—.—.—.—"),
            ("🔗", "ASN",         "—"),
            ("→",  "Route",       "— Hops"),
        ]

        for icon, label, value in rows:
            r = QWidget()
            r.setStyleSheet("background: transparent;")
            rl = QHBoxLayout(r)
            rl.setContentsMargins(0, 3, 0, 3)
            rl.setSpacing(8)
            rl.addWidget(_lbl(icon, _MUTED, 13))
            rl.addWidget(_lbl(label, _MUTED, 12))
            rl.addStretch()
            rl.addWidget(_lbl(value, "#e2e8f0", 12))
            cl.addWidget(r)

        note = _lbl("[ Populated at Milestone 8 — Diagnostics ]", _DIM, 10)
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cl.addWidget(note)

        return card

    def _make_diagnostics_row(self) -> QWidget:
        """Run Diagnostics button + overflow menu."""
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        row = QHBoxLayout(w)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        diag_btn = QPushButton("⚡  Run Diagnostics")
        diag_btn.setFixedHeight(38)
        diag_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2563eb, stop:1 #3b82f6
                );
                color: #ffffff;
                border: none;
                border-radius: 7px;
                font-size: 13px;
                font-weight: bold;
                font-family: 'Segoe UI';
            }
            QPushButton:hover {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1d4ed8, stop:1 #2563eb
                );
            }
            QPushButton:pressed { background: #1e40af; }
        """)
        diag_btn.setToolTip("Network diagnostics will be implemented at Milestone 8")

        more_btn = QPushButton("···")
        more_btn.setFixedSize(38, 38)
        more_btn.setStyleSheet("""
            QPushButton {
                background: #1a1d24;
                color: #64748b;
                border: 1px solid #252b38;
                border-radius: 7px;
                font-size: 16px;
            }
            QPushButton:hover { background: #252b38; color: #94a3b8; }
        """)

        row.addWidget(diag_btn)
        row.addWidget(more_btn)
        return w


# ══════════════════════════════════════════════════════════════════════════════
# Settings View  (placeholder for a future milestone)
# ══════════════════════════════════════════════════════════════════════════════

class _SettingsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #0f1117;")
        v = QVBoxLayout(self)
        v.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(_lbl("⚙  Settings", _MUTED, 14, align=Qt.AlignmentFlag.AlignCenter))
        v.addWidget(_lbl("Coming in a future milestone.", _DIM, 11,
                         align=Qt.AlignmentFlag.AlignCenter))


# ══════════════════════════════════════════════════════════════════════════════
# Bottom Navigation Bar
# ══════════════════════════════════════════════════════════════════════════════

class _NavBar(QFrame):
    """
    Three-tab bottom navigation: Dashboard | History | Settings.

    The active tab shows blue text with a blue top-border underline.
    Switching tabs swaps the QStackedWidget page.
    """

    _BTN_STYLE = """
        QPushButton {{
            background: transparent;
            border: none;
            border-top: 2px solid {border};
            color: {color};
            font-size: 12px;
            font-family: 'Segoe UI';
            padding: 8px 0 6px 0;
        }}
        QPushButton:hover {{
            color: #94a3b8;
        }}
    """

    def __init__(self, on_tab_change, parent=None):
        super().__init__(parent)
        self.setFixedHeight(46)
        self.setStyleSheet("""
            QFrame {
                background-color: #13161e;
                border-top: 1px solid #252b38;
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
            }
        """)

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)

        tabs = [
            ("📊  Dashboard", 0),
            ("🕐  History",   1),
            ("⚙  Settings",  2),
        ]

        self._buttons: list[QPushButton] = []
        for label, idx in tabs:
            btn = QPushButton(label)
            btn.setCheckable(False)
            btn.clicked.connect(lambda _, i=idx: self._select(i, on_tab_change))
            self._buttons.append(btn)
            row.addWidget(btn)

        self._select(0, on_tab_change)   # Dashboard is active by default

    def _select(self, active_idx: int, on_tab_change) -> None:
        for i, btn in enumerate(self._buttons):
            if i == active_idx:
                btn.setStyleSheet(
                    self._BTN_STYLE.format(border="#3b82f6", color="#3b82f6")
                )
            else:
                btn.setStyleSheet(
                    self._BTN_STYLE.format(border="transparent", color="#64748b")
                )
        on_tab_change(active_idx)


# ══════════════════════════════════════════════════════════════════════════════
# Status Indicator Widget (the green circle on the status card)
# ══════════════════════════════════════════════════════════════════════════════

class _StatusIndicator(QWidget):
    """
    A small filled circle with a checkmark drawn using QPainter.

    Green = connected / healthy
    Orange = degraded
    Red = disconnected

    Drawing it in code means we can animate it or change its color
    at runtime to reflect real network state (Milestone 3+).
    """

    def __init__(self, connected: bool = True, parent=None):
        super().__init__(parent)
        self.setFixedSize(36, 36)
        self._color = QColor(_GREEN if connected else _RED)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Outer glow ring
        glow = QColor(self._color)
        glow.setAlpha(40)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(glow))
        p.drawEllipse(2, 2, 32, 32)

        # Filled circle
        p.setBrush(QBrush(self._color))
        p.drawEllipse(6, 6, 24, 24)

        # White checkmark
        p.setPen(QPen(QColor("white"), 2.5,
                       Qt.PenStyle.SolidLine,
                       Qt.PenCapStyle.RoundCap,
                       Qt.PenJoinStyle.RoundJoin))
        p.drawLine(11, 18, 16, 23)
        p.drawLine(16, 23, 25, 13)
        p.end()


# ══════════════════════════════════════════════════════════════════════════════
# Main Dashboard Window
# ══════════════════════════════════════════════════════════════════════════════

class DashboardWindow(QWidget):
    """
    The NetPath Sentinel popup dashboard window.

    420 × 650 px frameless window.
    Appears near the system tray when the tray icon is clicked.
    Closing or hiding does NOT exit the application.
    """

    WINDOW_WIDTH  = 420
    WINDOW_HEIGHT = 650

    def __init__(self) -> None:
        super().__init__()

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setFixedSize(self.WINDOW_WIDTH, self.WINDOW_HEIGHT)
        self.setStyleSheet(APP_STYLESHEET)

        # Drag support
        self._drag_start_pos: QPoint | None = None

        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Title bar
        root.addWidget(_TitleBar(on_close=self.hide))

        # Stacked content (three views)
        stack = QStackedWidget()
        stack.addWidget(_DashboardView())
        stack.addWidget(_HistoryView())
        stack.addWidget(_SettingsView())
        root.addWidget(stack, 1)

        # Bottom navigation
        root.addWidget(_NavBar(on_tab_change=stack.setCurrentIndex))

    # ── Drag to move ──────────────────────────────────────────────────────

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._drag_start_pos and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_start_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._drag_start_pos = None
        super().mouseReleaseEvent(event)
