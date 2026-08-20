"""
ui/charts.py — Real-Time Latency and Activity Charts

Uses pyqtgraph for fast Qt-native chart rendering.

Why pyqtgraph instead of matplotlib?
    pyqtgraph is designed specifically for Qt applications and live data.
    It renders directly inside Qt's widget tree, so it integrates without
    flickering or event-loop conflicts, and it supports real-time updates
    efficiently (important for Milestone 3+).

At Milestone 2: both charts display clearly labeled MOCK DATA.
At Milestone 3+: update_data() will be called by the monitoring system.
"""

from __future__ import annotations
import math
import random

import pyqtgraph as pg
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCore import Qt

# ── Global pyqtgraph appearance ───────────────────────────────────────────────
# These must be set BEFORE creating any PlotWidget instances.
pg.setConfigOption("background", "#0f1117")  # matches our window background
pg.setConfigOption("foreground", "#64748b")  # default axis/tick color
pg.setConfigOption("antialias", True)        # smooth line rendering


# ── Shared helpers ────────────────────────────────────────────────────────────

_AXIS_PEN   = pg.mkPen(color="#2d3748", width=1)
_TICK_PEN   = pg.mkPen(color="#64748b")
_LBL        = "background: transparent; font-family: 'Segoe UI';"


def _style_axis(axis) -> None:
    """Apply the shared dark-theme style to a pyqtgraph AxisItem."""
    axis.setStyle(tickLength=3)
    axis.setPen(_AXIS_PEN)
    axis.setTextPen(_TICK_PEN)


def _chart_header(title: str, note: str) -> QWidget:
    """Create a two-label row: bold title on the left, dimmed note on the right."""
    w = QWidget()
    row = QHBoxLayout(w)
    row.setContentsMargins(0, 0, 0, 2)
    lbl_t = QLabel(title)
    lbl_t.setStyleSheet(_LBL + "color:#e2e8f0; font-size:12px; font-weight:600;")
    lbl_n = QLabel(note)
    lbl_n.setStyleSheet(_LBL + "color:#4a5568; font-size:10px;")
    row.addWidget(lbl_t)
    row.addStretch()
    row.addWidget(lbl_n)
    return w


# ── Mock data generators ──────────────────────────────────────────────────────

def _mock_latency(n: int) -> list[float]:
    """
    Generate plausible latency data for the placeholder chart.

    Produces a smooth 25-45ms baseline with occasional spikes.
    The wave pattern mimics real latency variation under moderate load.
    """
    result = []
    for i in range(n):
        base  = 30 + 12 * math.sin(i / 9)
        noise = random.uniform(-4, 4)
        spike = 58 if i in (19, 20, 44) else 0   # simulate brief congestion spikes
        result.append(max(5.0, base + noise + spike))
    return result


def _mock_activity(n: int, peak: float) -> list[float]:
    """Generate random-looking throughput values for the activity chart."""
    return [max(1.0, random.gauss(peak * 0.55, peak * 0.3)) for _ in range(n)]


# ── Chart widgets ─────────────────────────────────────────────────────────────

class LatencyChart(QWidget):
    """
    Line chart: RTT (ping latency) over the last 60 seconds.

    Why we plot latency over time rather than showing a single number:
        A single ping value tells you almost nothing. Plotting over time
        reveals: spikes (congestion / routing change), a rising baseline
        (growing load), sudden jumps (path switch), or flat lines (ICMP
        being dropped — a different kind of problem).

    Data source: MOCK at Milestone 2. Real data wired in at Milestone 3.
    """

    SAMPLES = 60  # one sample per second, 60 s of history

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._data = _mock_latency(self.SAMPLES)
        self._setup()

    def _setup(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(_chart_header("Latency (ms)", "Last 60 sec  ·  mock data"))

        pw = pg.PlotWidget()
        pw.setFixedHeight(96)
        pw.setMouseEnabled(x=False, y=False)
        pw.setMenuEnabled(False)
        pw.hideButtons()
        pw.setBackground("#0f1117")
        pw.showGrid(x=True, y=True, alpha=0.12)

        _style_axis(pw.getAxis("bottom"))
        _style_axis(pw.getAxis("left"))

        pw.getAxis("bottom").setTicks([[
            (-60, "-60s"), (-45, "-45s"), (-30, "-30s"), (-15, "-15s"), (0, "Now")
        ]])
        pw.getAxis("left").setTicks([[(0, "0"), (50, "50"), (100, "100")]])
        pw.setXRange(-60, 0, padding=0)
        pw.setYRange(0, 110, padding=0)

        x = list(range(-self.SAMPLES + 1, 1))
        pen   = pg.mkPen(color="#22c55e", width=1.8)
        brush = pg.mkBrush(34, 197, 94, 38)   # translucent green fill under line

        self._curve = pw.plot(x, self._data, pen=pen, fillLevel=0, brush=brush)
        self._pw = pw
        layout.addWidget(pw)

    def update_data(self, values: list[float]) -> None:
        """
        Replace chart data with real measurements.

        Called by the monitoring system at Milestone 3+.

        Args:
            values: Up to 60 RTT values in milliseconds, oldest → newest.
        """
        n = min(len(values), self.SAMPLES)
        x = list(range(-n + 1, 1))
        self._pw.clear()
        pen   = pg.mkPen(color="#22c55e", width=1.8)
        brush = pg.mkBrush(34, 197, 94, 38)
        self._curve = self._pw.plot(x, values[-n:], pen=pen, fillLevel=0, brush=brush)


class ActivityChart(QWidget):
    """
    Bar chart: download / upload throughput over the last 30 time slots.

    Each bar represents approximately 2 seconds of network activity.
    Download bars are blue (#3b82f6), upload bars are purple (#a855f7).

    Throughput is measured by sampling the OS network interface byte
    counters (psutil) at regular intervals — implemented at Milestone 3.

    Data source: MOCK at Milestone 2. Real data wired in at Milestone 3.
    """

    SAMPLES = 30

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._dl = _mock_activity(self.SAMPLES, peak=75)
        self._ul = _mock_activity(self.SAMPLES, peak=28)
        self._setup()

    def _setup(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(2)

        # Header with colour-coded legend
        hdr = QWidget()
        row = QHBoxLayout(hdr)
        row.setContentsMargins(0, 0, 0, 2)

        def _leg(text, color):
            l = QLabel(text)
            l.setStyleSheet(_LBL + f"color:{color}; font-size:11px;")
            return l

        title = QLabel("Activity")
        title.setStyleSheet(_LBL + "color:#e2e8f0; font-size:12px; font-weight:600;")
        row.addWidget(title)
        row.addStretch()
        row.addWidget(_leg("↓ Download", "#3b82f6"))
        row.addSpacing(8)
        row.addWidget(_leg("↑ Upload", "#a855f7"))
        row.addSpacing(8)
        row.addWidget(_leg("Last 60 sec  ·  mock data", "#4a5568"))
        layout.addWidget(hdr)

        # Plot
        pw = pg.PlotWidget()
        pw.setFixedHeight(88)
        pw.setMouseEnabled(x=False, y=False)
        pw.setMenuEnabled(False)
        pw.hideButtons()
        pw.setBackground("#0f1117")
        pw.showGrid(x=False, y=True, alpha=0.12)

        _style_axis(pw.getAxis("bottom"))
        _style_axis(pw.getAxis("left"))
        pw.getAxis("bottom").setTicks([[]])          # no x-axis labels on bar chart
        pw.getAxis("left").setTicks([[(0, "0"), (50, "50")]])
        pw.setYRange(0, 105, padding=0)

        # Side-by-side bars: download left, upload right of each tick position
        bw = 0.38
        xs_dl = [i - 0.22 for i in range(self.SAMPLES)]
        xs_ul = [i + 0.22 for i in range(self.SAMPLES)]

        pw.addItem(pg.BarGraphItem(x=xs_dl, height=self._dl, width=bw,
                                    brush="#3b82f6", pen=pg.mkPen(None)))
        pw.addItem(pg.BarGraphItem(x=xs_ul, height=self._ul, width=bw,
                                    brush="#a855f7", pen=pg.mkPen(None)))
        self._pw = pw
        layout.addWidget(pw)

    def update_data(self, dl_values: list[float], ul_values: list[float]) -> None:
        """
        Replace bar chart data with real throughput measurements.

        Args:
            dl_values: Download KB/s samples, oldest → newest (up to SAMPLES).
            ul_values: Upload KB/s samples, oldest → newest (up to SAMPLES).
        """
        n   = min(len(dl_values), len(ul_values), self.SAMPLES)
        bw  = 0.38
        xs_dl = [i - 0.22 for i in range(n)]
        xs_ul = [i + 0.22 for i in range(n)]
        self._pw.clear()
        self._pw.addItem(pg.BarGraphItem(x=xs_dl, height=dl_values[-n:], width=bw,
                                          brush="#3b82f6", pen=pg.mkPen(None)))
        self._pw.addItem(pg.BarGraphItem(x=xs_ul, height=ul_values[-n:], width=bw,
                                          brush="#a855f7", pen=pg.mkPen(None)))
