"""
ui/styles.py — Qt Style Sheet (QSS) Definitions

Qt Style Sheets (QSS) work similarly to CSS — they let us apply visual
styles to Qt widgets using a selector-based syntax.

Reference: https://doc.qt.io/qt-6/stylesheet-reference.html

Design reference: assets/ui-reference.png

Color palette used throughout the application:
    Background deep:  #0f1117   (main window background)
    Background card:  #1a1d24   (card / section backgrounds)
    Background hover: #2d3748   (hover states)
    Border:           #2d3748   (subtle card borders)
    Text primary:     #e2e8f0   (main labels)
    Text secondary:   #94a3b8   (sub-labels, units)
    Green (healthy):  #22c55e
    Orange (warning): #f59e0b
    Red (critical):   #ef4444
    Blue (accent):    #3b82f6
    Purple (upload):  #a855f7
"""

# The main application-level stylesheet.
# Applied to the root QWidget so all child widgets inherit it.
APP_STYLESHEET = """
/* ── Root window ─────────────────────────────────────────────────────── */
QWidget {
    background-color: #0f1117;
    color: #e2e8f0;
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 13px;
}

/* ── Labels ──────────────────────────────────────────────────────────── */
QLabel {
    background: transparent;
    color: #e2e8f0;
}

QLabel[class="secondary"] {
    color: #94a3b8;
    font-size: 11px;
}

QLabel[class="status-ok"] {
    color: #22c55e;
    font-weight: bold;
}

QLabel[class="status-warn"] {
    color: #f59e0b;
    font-weight: bold;
}

QLabel[class="status-error"] {
    color: #ef4444;
    font-weight: bold;
}

/* ── Cards (frames used as grouped sections) ─────────────────────────── */
QFrame[class="card"] {
    background-color: #1a1d24;
    border: 1px solid #2d3748;
    border-radius: 8px;
}

/* ── Push buttons ────────────────────────────────────────────────────── */
QPushButton {
    background-color: #2d3748;
    color: #e2e8f0;
    border: 1px solid #4a5568;
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 13px;
}

QPushButton:hover {
    background-color: #3d4a5c;
    border-color: #63b3ed;
    color: #63b3ed;
}

QPushButton:pressed {
    background-color: #1a1d24;
}

QPushButton[class="primary"] {
    background-color: #3b82f6;
    color: #ffffff;
    border: none;
    font-weight: bold;
}

QPushButton[class="primary"]:hover {
    background-color: #2563eb;
    color: #ffffff;
}

/* ── Scroll area ─────────────────────────────────────────────────────── */
QScrollArea {
    border: none;
    background: transparent;
}

QScrollBar:vertical {
    background: #1a1d24;
    width: 6px;
    margin: 0;
    border-radius: 3px;
}

QScrollBar::handle:vertical {
    background: #4a5568;
    border-radius: 3px;
    min-height: 20px;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0;
}
"""
