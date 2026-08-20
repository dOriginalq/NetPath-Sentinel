"""
ui/dashboard.py — Full Popup Dashboard Window

Milestone 5: Integrated DNS / IPv4 / IPv6 Protocol Monitoring UI.

What changed from Milestone 4:
    - Wired DNS resolution latency and failure detection in Metric Grid 2.
    - Wired IPv4 connectivity verification ("Active" / "Failed").
    - Wired IPv6 dual-stack connectivity verification ("Active" / "Failed" / "Unavailable").
    - Updated Status Card with DNS anomaly integration.
"""

from __future__ import annotations

from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QStackedWidget, QGridLayout,
)
from PySide6.QtCore import Qt, QPoint, QTimer
from PySide6.QtGui import QPainter, QColor, QPen, QBrush

from netpath_sentinel.ui.styles import APP_STYLESHEET
from netpath_sentinel.ui.charts import LatencyChart, ActivityChart
from netpath_sentinel.monitoring.network_monitor import NetworkMonitor, NetworkState


# ── Shared style constants ────────────────────────────────────────────────────
_CARD   = """
    QFrame {
        background-color: #1a1d24;
        border: 1px solid #252b38;
        border-radius: 8px;
    }
"""
_LBL    = "background: transparent; font-family: 'Segoe UI';"
_GREEN  = "#22c55e"
_ORANGE = "#f59e0b"
_RED    = "#ef4444"
_BLUE   = "#3b82f6"
_PURPLE = "#a855f7"
_MUTED  = "#94a3b8"
_DIM    = "#4a5568"


# ── Reusable helper functions ─────────────────────────────────────────────────

def _lbl(text: str, color: str = "#e2e8f0", size: int = 12,
         bold: bool = False, align=Qt.AlignmentFlag.AlignLeft) -> QLabel:
    l = QLabel(text)
    l.setStyleSheet(
        f"{_LBL} color:{color}; font-size:{size}px; font-weight:{'bold' if bold else 'normal'};"
    )
    l.setAlignment(align)
    return l


def _sep() -> QFrame:
    line = QFrame()
    line.setFixedHeight(1)
    line.setStyleSheet("background-color: #252b38; border: none;")
    return line


def _metric_cell(label: str, value: str, unit: str = "",
                 color: str = _GREEN) -> tuple[QFrame, QLabel]:
    """
    Create a single metric cell (label + live value).

    Returns:
        (cell_frame, value_label) — caller stores the label ref for updates.
    """
    cell = QFrame()
    cell.setStyleSheet(_CARD)
    v = QVBoxLayout(cell)
    v.setContentsMargins(8, 8, 8, 8)
    v.setSpacing(2)

    lbl_label = _lbl(label, _MUTED, 11, align=Qt.AlignmentFlag.AlignCenter)
    v.addWidget(lbl_label)

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
    return cell, lbl_val


# ══════════════════════════════════════════════════════════════════════════════
# Status Indicator — painted green/orange/red circle with symbol
# ══════════════════════════════════════════════════════════════════════════════

class _StatusIndicator(QWidget):
    """
    Dynamic status indicator drawn via QPainter.

    Supports 3 health states:
        - "healthy": Green glow + circle + checkmark
        - "degraded": Orange glow + circle + exclamation mark
        - "disconnected": Red glow + circle + cross mark
    """

    def __init__(self, status: str = "disconnected", parent=None):
        super().__init__(parent)
        self.setFixedSize(36, 36)
        self._status = status

    def set_status(self, status: str) -> None:
        """Update status and repaint."""
        if self._status != status:
            self._status = status
            self.update()

    def set_connected(self, connected: bool) -> None:
        """Legacy helper for binary connection state."""
        self.set_status("healthy" if connected else "disconnected")

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self._status == "healthy":
            color = QColor(_GREEN)
        elif self._status == "degraded":
            color = QColor(_ORANGE)
        else:
            color = QColor(_RED)

        # Outer glow ring
        glow = QColor(color)
        glow.setAlpha(40)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(glow))
        p.drawEllipse(2, 2, 32, 32)

        # Filled central circle
        p.setBrush(QBrush(color))
        p.drawEllipse(6, 6, 24, 24)

        # Foreground symbol
        p.setPen(QPen(QColor("white"), 2.5,
                      Qt.PenStyle.SolidLine,
                      Qt.PenCapStyle.RoundCap,
                      Qt.PenJoinStyle.RoundJoin))

        if self._status == "healthy":
            # Checkmark
            p.drawLine(11, 18, 16, 23)
            p.drawLine(16, 23, 25, 13)
        elif self._status == "degraded":
            # Exclamation point
            p.drawLine(18, 12, 18, 20)
            p.drawPoint(18, 24)
        else:
            # Cross mark
            p.drawLine(13, 13, 23, 23)
            p.drawLine(23, 13, 13, 23)

        p.end()


# ══════════════════════════════════════════════════════════════════════════════
# Title Bar
# ══════════════════════════════════════════════════════════════════════════════

class _TitleBar(QFrame):
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

        row.addWidget(_lbl("📡", size=16))
        row.addWidget(_lbl("NetPath Sentinel", "#e2e8f0", 14, bold=True))
        row.addStretch()

        for symbol, tip, cb in [
            ("⚙", "Settings (coming soon)", None),
            ("−", "Hide dashboard",          on_close),
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
                QPushButton {{ background:transparent; border:none;
                    color:#64748b; font-size:13px; border-radius:4px; }}
                QPushButton:hover {{ background-color:#2d3748; color:#e2e8f0; }}
                {hover_extra}
            """)
            if cb:
                btn.clicked.connect(cb)
            row.addWidget(btn)


# ══════════════════════════════════════════════════════════════════════════════
# Dashboard View — live metrics panel
# ══════════════════════════════════════════════════════════════════════════════

class _DashboardView(QWidget):
    """
    Main metrics panel. Refreshes every 2 seconds from the NetworkMonitor.
    """

    def __init__(self, monitor: NetworkMonitor, parent=None):
        super().__init__(parent)
        self._monitor = monitor
        self.setStyleSheet("background-color: #0f1117;")

        # Widget references updated by _refresh()
        self._ind:            _StatusIndicator | None = None
        self._lbl_status:     QLabel | None = None
        self._lbl_reason:     QLabel | None = None
        self._lbl_bars:       QLabel | None = None
        self._lbl_dl:         QLabel | None = None
        self._lbl_ul:         QLabel | None = None
        self._lbl_ping:       QLabel | None = None
        self._lbl_jitter:     QLabel | None = None
        self._lbl_pkt_loss:   QLabel | None = None
        self._lbl_dns:        QLabel | None = None
        self._lbl_ipv4:       QLabel | None = None
        self._lbl_ipv6:       QLabel | None = None
        self._lbl_uptime:     QLabel | None = None
        self._latency_chart:  LatencyChart | None = None
        self._activity_chart: ActivityChart | None = None

        self._build()

        timer = QTimer(self)
        timer.timeout.connect(self._refresh)
        timer.start(2000)

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea { border:none; background:transparent; }
            QScrollBar:vertical { background:#0f1117; width:5px; border-radius:3px; }
            QScrollBar::handle:vertical { background:#2d3748; border-radius:3px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
        """)

        content = QWidget()
        content.setStyleSheet("background:#0f1117;")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(12, 10, 12, 8)
        cl.setSpacing(7)

        cl.addWidget(self._make_status_card())
        cl.addWidget(self._make_speed_row())
        cl.addWidget(self._make_metric_row1())
        cl.addWidget(self._make_metric_row2())

        self._latency_chart  = LatencyChart()
        self._activity_chart = ActivityChart()
        cl.addWidget(self._latency_chart)
        cl.addWidget(self._activity_chart)
        cl.addWidget(self._make_footer())

        scroll.setWidget(content)
        outer.addWidget(scroll)

    # ── Section builders ──────────────────────────────────────────────────

    def _make_status_card(self) -> QFrame:
        card = QFrame()
        card.setFixedHeight(68)
        card.setStyleSheet(_CARD)
        row = QHBoxLayout(card)
        row.setContentsMargins(14, 0, 14, 0)
        row.setSpacing(10)

        self._ind = _StatusIndicator(status="disconnected")
        row.addWidget(self._ind)

        col = QVBoxLayout()
        col.setSpacing(1)
        self._lbl_status = _lbl("Connecting…", _MUTED, 15, bold=True)
        self._lbl_reason = _lbl("Waiting for monitor…", _MUTED, 10)
        col.addWidget(self._lbl_status)
        col.addWidget(self._lbl_reason)
        row.addLayout(col)
        row.addStretch()

        self._lbl_bars = _lbl("▁▃▅▇", _GREEN, 16)
        self._lbl_bars.setStyleSheet(self._lbl_bars.styleSheet() + " letter-spacing:2px;")
        row.addWidget(self._lbl_bars)
        return card

    def _make_speed_row(self) -> QFrame:
        card = QFrame()
        card.setFixedHeight(62)
        card.setStyleSheet(_CARD)
        row = QHBoxLayout(card)
        row.setContentsMargins(16, 0, 16, 0)
        row.setSpacing(0)

        dl = QHBoxLayout()
        dl.setSpacing(8)
        dl.addWidget(_lbl("↓", _BLUE, 22, bold=True))
        dl_col = QVBoxLayout()
        dl_col.setSpacing(0)
        self._lbl_dl = _lbl("—", "#e2e8f0", 20, bold=True)
        dl_col.addWidget(self._lbl_dl)
        dl_col.addWidget(_lbl("Download", _MUTED, 10))
        dl.addLayout(dl_col)
        dl.addWidget(_lbl("Mbps", _MUTED, 11))

        ul = QHBoxLayout()
        ul.setSpacing(8)
        ul.addWidget(_lbl("↑", _PURPLE, 22, bold=True))
        ul_col = QVBoxLayout()
        ul_col.setSpacing(0)
        self._lbl_ul = _lbl("—", "#e2e8f0", 20, bold=True)
        ul_col.addWidget(self._lbl_ul)
        ul_col.addWidget(_lbl("Upload", _MUTED, 10))
        ul.addLayout(ul_col)
        ul.addWidget(_lbl("Mbps", _MUTED, 11))

        div = QFrame()
        div.setFixedSize(1, 32)
        div.setStyleSheet("background:#252b38; border:none;")

        row.addLayout(dl)
        row.addStretch()
        row.addWidget(div)
        row.addStretch()
        row.addLayout(ul)
        return card

    def _make_metric_row1(self) -> QWidget:
        """Ping | Jitter | Packet Loss — all live metrics."""
        w = QWidget()
        w.setStyleSheet("background:transparent;")
        g = QGridLayout(w)
        g.setContentsMargins(0, 0, 0, 0)
        g.setSpacing(6)

        ping_cell, self._lbl_ping     = _metric_cell("Ping",        "—", "ms", _GREEN)
        jit_cell,  self._lbl_jitter   = _metric_cell("Jitter",      "—", "ms", _GREEN)
        pkt_cell,  self._lbl_pkt_loss = _metric_cell("Packet Loss", "0", "%",  _GREEN)

        g.addWidget(ping_cell, 0, 0)
        g.addWidget(jit_cell,  0, 1)
        g.addWidget(pkt_cell,  0, 2)
        return w

    def _make_metric_row2(self) -> QWidget:
        """DNS | IPv4 | IPv6 — all live metrics in Milestone 5."""
        w = QWidget()
        w.setStyleSheet("background:transparent;")
        g = QGridLayout(w)
        g.setContentsMargins(0, 0, 0, 0)
        g.setSpacing(6)

        dns_cell,  self._lbl_dns  = _metric_cell("DNS",  "—", "ms", _GREEN)
        ip4_cell,  self._lbl_ipv4 = _metric_cell("IPv4", "—", "",   _GREEN)
        ip6_cell,  self._lbl_ipv6 = _metric_cell("IPv6", "—", "",   _GREEN)

        g.addWidget(dns_cell, 0, 0)
        g.addWidget(ip4_cell, 0, 1)
        g.addWidget(ip6_cell, 0, 2)
        return w

    def _make_footer(self) -> QFrame:
        bar = QFrame()
        bar.setFixedHeight(34)
        bar.setStyleSheet(
            "QFrame { background:transparent; border-top:1px solid #252b38; }"
        )
        row = QHBoxLayout(bar)
        row.setContentsMargins(4, 0, 4, 0)

        self._lbl_uptime = _lbl("⏱  Uptime: —:——:——", _DIM, 10)
        row.addWidget(self._lbl_uptime)
        row.addStretch()
        row.addWidget(_lbl("Test Server: Multi-Probe", _DIM, 10))
        row.addSpacing(4)
        row.addWidget(_lbl("●", _GREEN, 10))
        return bar

    # ── Live data refresh ─────────────────────────────────────────────────

    def _refresh(self) -> None:
        """
        Called every 2 seconds by QTimer on the main Qt thread.
        """
        state: NetworkState = self._monitor.state
        status = state.health_status

        # ── Status indicator & card ───────────────────────────────────────
        if self._ind:
            self._ind.set_status(status)

        if status == "healthy":
            title_text = "Connected"
            title_color = _GREEN
        elif status == "degraded":
            title_text = "Degraded"
            title_color = _ORANGE
        else:
            title_text = "Disconnected"
            title_color = _RED

        if self._lbl_status:
            self._lbl_status.setText(title_text)
            self._lbl_status.setStyleSheet(
                f"{_LBL} color:{title_color}; font-size:15px; font-weight:bold;"
            )

        if self._lbl_reason:
            if state.is_connected:
                sub = f"{state.interface_name} · {state.health_reason}"
            else:
                sub = state.health_reason
            self._lbl_reason.setText(sub)

        if self._lbl_bars:
            self._lbl_bars.setStyleSheet(
                f"{_LBL} color:{title_color}; font-size:16px; letter-spacing:2px;"
            )

        # ── Speed row ─────────────────────────────────────────────────────
        if self._lbl_dl:
            dl_mbps = state.download_kbps * 8 / 1000
            self._lbl_dl.setText(f"{dl_mbps:.1f}")
        if self._lbl_ul:
            ul_mbps = state.upload_kbps * 8 / 1000
            self._lbl_ul.setText(f"{ul_mbps:.1f}")

        # ── Latency, Jitter, Packet Loss ──────────────────────────────────
        if self._lbl_ping:
            if state.latency_ms > 0:
                self._lbl_ping.setText(f"{state.latency_ms:.0f}")
                color = _GREEN if state.latency_ms < 100 else (_ORANGE if state.latency_ms < 150 else _RED)
                self._lbl_ping.setStyleSheet(
                    f"{_LBL} color:{color}; font-size:15px; font-weight:bold;"
                )
            else:
                self._lbl_ping.setText("—")

        if self._lbl_jitter:
            if state.jitter_ms > 0:
                self._lbl_jitter.setText(f"{state.jitter_ms:.0f}")
                color = _GREEN if state.jitter_ms < 15 else (_ORANGE if state.jitter_ms < 35 else _RED)
                self._lbl_jitter.setStyleSheet(
                    f"{_LBL} color:{color}; font-size:15px; font-weight:bold;"
                )
            else:
                self._lbl_jitter.setText("—")

        if self._lbl_pkt_loss:
            loss = state.packet_loss_pct
            self._lbl_pkt_loss.setText(f"{loss:.0f}")
            color = _GREEN if loss <= 1.0 else (_ORANGE if loss <= 10.0 else _RED)
            self._lbl_pkt_loss.setStyleSheet(
                f"{_LBL} color:{color}; font-size:15px; font-weight:bold;"
            )

        # ── DNS, IPv4, IPv6 (Milestone 5) ─────────────────────────────────
        if self._lbl_dns:
            if state.dns_status == "ok":
                self._lbl_dns.setText(f"{state.dns_latency_ms:.0f}")
                color = _GREEN if state.dns_latency_ms < 50 else (_ORANGE if state.dns_latency_ms < 120 else _RED)
                self._lbl_dns.setStyleSheet(f"{_LBL} color:{color}; font-size:15px; font-weight:bold;")
            elif state.dns_status in ("timeout", "failed"):
                self._lbl_dns.setText(state.dns_status.capitalize())
                self._lbl_dns.setStyleSheet(f"{_LBL} color:{_RED}; font-size:12px; font-weight:bold;")
            else:
                self._lbl_dns.setText("—")

        if self._lbl_ipv4:
            self._lbl_ipv4.setText(state.ipv4_status)
            color = _GREEN if state.ipv4_status == "Active" else (_RED if state.ipv4_status == "Failed" else _MUTED)
            self._lbl_ipv4.setStyleSheet(f"{_LBL} color:{color}; font-size:13px; font-weight:bold;")

        if self._lbl_ipv6:
            self._lbl_ipv6.setText(state.ipv6_status)
            if state.ipv6_status == "Active":
                color = _GREEN
            elif state.ipv6_status == "Failed":
                color = _RED
            else:
                color = _MUTED
            self._lbl_ipv6.setStyleSheet(f"{_LBL} color:{color}; font-size:13px; font-weight:bold;")

        # ── Charts ────────────────────────────────────────────────────────
        if self._latency_chart and state.latency_history:
            self._latency_chart.update_data(state.latency_history)

        if self._activity_chart and state.download_history:
            self._activity_chart.update_data(
                state.download_history, state.upload_history
            )

        # ── Uptime ────────────────────────────────────────────────────────
        if self._lbl_uptime:
            elapsed = datetime.now() - state.start_time
            h, rem = divmod(int(elapsed.total_seconds()), 3600)
            m, s   = divmod(rem, 60)
            self._lbl_uptime.setText(f"⏱  Uptime: {h:02d}:{m:02d}:{s:02d}")


# ══════════════════════════════════════════════════════════════════════════════
# History View — events, diagnostics, network details
# ══════════════════════════════════════════════════════════════════════════════

class _HistoryView(QWidget):
    """Placeholder — will be populated with real events at Milestone 6."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #0f1117;")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea { border:none; background:transparent; }
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

    def _make_events_section(self) -> QFrame:
        card = QFrame()
        card.setStyleSheet(_CARD)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(14, 12, 14, 12)
        cl.setSpacing(6)

        hdr = QWidget()
        hdr.setStyleSheet("background:transparent;")
        hrow = QHBoxLayout(hdr)
        hrow.setContentsMargins(0, 0, 0, 0)
        hrow.addWidget(_lbl("Recent Events", "#e2e8f0", 13, bold=True))
        hrow.addStretch()
        va = QPushButton("View All")
        va.setStyleSheet("QPushButton { background:transparent; border:none; color:#3b82f6; font-size:11px; padding:0; } QPushButton:hover { color:#60a5fa; }")
        hrow.addWidget(va)
        cl.addWidget(hdr)
        cl.addWidget(_sep())

        for icon, ts, name, dur, color in [
            ("🔴", "—:——:——", "Connection Lost",     "—",    _RED),
            ("🟠", "—:——:——", "High Latency",         "— ms", _ORANGE),
            ("🟠", "—:——:——", "DNS Timeout",          "—",    _ORANGE),
            ("🟢", "—:——:——", "Connection Restored",  "—",    _GREEN),
        ]:
            r = QWidget()
            r.setStyleSheet("background:transparent;")
            rl = QHBoxLayout(r)
            rl.setContentsMargins(0, 2, 0, 2)
            rl.setSpacing(8)
            rl.addWidget(_lbl(icon, size=12))
            rl.addWidget(_lbl(ts, _DIM, 11))
            rl.addWidget(_lbl(name, color, 12))
            rl.addStretch()
            rl.addWidget(_lbl(dur, _MUTED, 11))
            cl.addWidget(r)

        cl.addWidget(_lbl("[ Events populated at Milestone 6 ]", _DIM, 10,
                          align=Qt.AlignmentFlag.AlignCenter))
        return card

    def _make_current_test(self) -> QFrame:
        card = QFrame()
        card.setStyleSheet(_CARD)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(14, 12, 14, 12)
        cl.setSpacing(6)

        hdr = QWidget()
        hdr.setStyleSheet("background:transparent;")
        hrow = QHBoxLayout(hdr)
        hrow.setContentsMargins(0, 0, 0, 0)
        hrow.addWidget(_lbl("Current Test", "#e2e8f0", 13, bold=True))
        hrow.addStretch()
        edit = QPushButton("Edit")
        edit.setStyleSheet("QPushButton { background:transparent; border:none; color:#3b82f6; font-size:11px; padding:0; }")
        hrow.addWidget(edit)
        cl.addWidget(hdr)
        cl.addWidget(_sep())

        body = QWidget()
        body.setStyleSheet("background:transparent;")
        brow = QHBoxLayout(body)
        brow.setContentsMargins(0, 4, 0, 4)
        brow.setSpacing(12)
        brow.addWidget(_lbl("🌐", size=22))
        info = QVBoxLayout()
        info.setSpacing(1)
        info.addWidget(_lbl("8.8.8.8  (Google DNS)", "#e2e8f0", 13, bold=True))
        info.addWidget(_lbl("Primary probe target", _MUTED, 11))
        brow.addLayout(info)
        brow.addStretch()
        brow.addWidget(_lbl("— ms", _GREEN, 15, bold=True))
        cl.addWidget(body)
        return card

    def _make_network_details(self) -> QFrame:
        card = QFrame()
        card.setStyleSheet(_CARD)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(14, 12, 14, 12)
        cl.setSpacing(6)

        cl.addWidget(_lbl("Network Details", "#e2e8f0", 13, bold=True))
        cl.addWidget(_sep())

        for icon, label, value in [
            ("📶", "IP Address", "—.—.—.—"),
            ("🌐", "Public IP",  "—.—.—.—"),
            ("🔗", "ASN",        "—"),
            ("→",  "Route",      "— Hops"),
        ]:
            r = QWidget()
            r.setStyleSheet("background:transparent;")
            rl = QHBoxLayout(r)
            rl.setContentsMargins(0, 3, 0, 3)
            rl.setSpacing(8)
            rl.addWidget(_lbl(icon, _MUTED, 13))
            rl.addWidget(_lbl(label, _MUTED, 12))
            rl.addStretch()
            rl.addWidget(_lbl(value, "#e2e8f0", 12))
            cl.addWidget(r)

        cl.addWidget(_lbl("[ Populated at Milestone 8 — Diagnostics ]", _DIM, 10,
                          align=Qt.AlignmentFlag.AlignCenter))
        return card

    def _make_diagnostics_row(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background:transparent;")
        row = QHBoxLayout(w)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        diag = QPushButton("⚡  Run Diagnostics")
        diag.setFixedHeight(38)
        diag.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #2563eb, stop:1 #3b82f6);
                color:#fff; border:none; border-radius:7px;
                font-size:13px; font-weight:bold; font-family:'Segoe UI';
            }
            QPushButton:hover { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 #1d4ed8, stop:1 #2563eb); }
        """)
        diag.setToolTip("Implemented at Milestone 8")

        more = QPushButton("···")
        more.setFixedSize(38, 38)
        more.setStyleSheet("""
            QPushButton { background:#1a1d24; color:#64748b;
                border:1px solid #252b38; border-radius:7px; font-size:16px; }
            QPushButton:hover { background:#252b38; color:#94a3b8; }
        """)
        row.addWidget(diag)
        row.addWidget(more)
        return w


# ══════════════════════════════════════════════════════════════════════════════
# Settings View (placeholder)
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
    _BTN = """
        QPushButton {{
            background:transparent; border:none;
            border-top:2px solid {border};
            color:{color};
            font-size:12px; font-family:'Segoe UI';
            padding:8px 0 6px 0;
        }}
    """

    def __init__(self, on_tab_change, parent=None):
        super().__init__(parent)
        self.setFixedHeight(46)
        self.setStyleSheet("""
            QFrame { background-color:#13161e; border-top:1px solid #252b38;
                border-bottom-left-radius:10px; border-bottom-right-radius:10px; }
        """)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)

        self._buttons: list[QPushButton] = []
        for label, idx in [("📊  Dashboard", 0), ("🕐  History", 1), ("⚙  Settings", 2)]:
            btn = QPushButton(label)
            btn.clicked.connect(lambda _, i=idx: self._select(i, on_tab_change))
            self._buttons.append(btn)
            row.addWidget(btn)

        self._select(0, on_tab_change)

    def _select(self, active: int, on_tab_change) -> None:
        for i, btn in enumerate(self._buttons):
            if i == active:
                btn.setStyleSheet(self._BTN.format(border="#3b82f6", color="#3b82f6"))
            else:
                btn.setStyleSheet(self._BTN.format(border="transparent", color="#64748b"))
        on_tab_change(active)


# ══════════════════════════════════════════════════════════════════════════════
# Main Dashboard Window
# ══════════════════════════════════════════════════════════════════════════════

class DashboardWindow(QWidget):
    """
    420 × 650 px frameless popup dashboard.
    Receives the NetworkMonitor and passes it to _DashboardView.
    Closing hides the window — monitoring continues in the background.
    """

    WINDOW_WIDTH  = 420
    WINDOW_HEIGHT = 650

    def __init__(self, monitor: NetworkMonitor) -> None:
        super().__init__()

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setFixedSize(self.WINDOW_WIDTH, self.WINDOW_HEIGHT)
        self.setStyleSheet(APP_STYLESHEET)

        self._drag_start_pos: QPoint | None = None
        self._monitor = monitor

        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(_TitleBar(on_close=self.hide))

        stack = QStackedWidget()
        stack.addWidget(_DashboardView(self._monitor))
        stack.addWidget(_HistoryView())
        stack.addWidget(_SettingsView())
        root.addWidget(stack, 1)

        root.addWidget(_NavBar(on_tab_change=stack.setCurrentIndex))

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
