# NetPath Sentinel — Development Log

## 2026-08-20 — Milestone 0: Repository & Project Foundation

**Status**: ✅ Complete

### What was done

- Initialized Git repository
- Created full project directory structure
- Created `.gitignore` (Python standard)
- Created `README.md` explaining the project objective, stack, and roadmap
- Created `requirements.txt` with justified dependencies
- Created `LICENSE` (MIT)
- Created placeholder source files for all planned modules
- Created placeholder documentation files
- Saved UI reference image to `assets/ui-reference.png`
- Committed and pushed to GitHub

### Notes

The UI reference image provided by the developer shows a two-panel compact popup:
- Left panel: real-time network metrics (status, speed, ping, jitter, packet loss, DNS, IPv4, IPv6, latency chart, activity chart)
- Right panel: recent events, current test, network details, diagnostics button, navigation

This will be the primary design reference for Milestone 2.

---

## 2026-08-20 — Milestone 1: Basic Tray Application

**Status**: ✅ Complete

### What was done

- Implemented `main.py` — Qt application entry, `setQuitOnLastWindowClosed(False)`, starts tray
- Implemented `tray/tray.py` — `QSystemTrayIcon` with:
  - Programmatic WiFi-style tray icon drawn with `QPainter` (no external image files needed)
  - Context menu: **Open Dashboard** / **Exit NetPath Sentinel**
  - Left-click toggles dashboard show/hide
  - Dashboard positioned near bottom-right corner (system tray area)
- Implemented `ui/styles.py` — full QSS stylesheet with documented color palette
- Implemented `ui/dashboard.py` — frameless dark popup with:
  - Custom drag-to-move title bar (no OS chrome)
  - Close/minimize buttons that **hide** (not quit) the app
  - M1 placeholder body explaining tray behaviour
- Created `tests/test_milestone1.py` — 9 smoke tests (all passed)
- Verified: app starts, Qt event loop holds, no errors after 5s, clean termination

### Key learnings

- `QApplication.setQuitOnLastWindowClosed(False)` is the critical setting that makes a tray app possible — without it, Qt exits when the popup is closed
- `Qt.WindowType.Tool` prevents the app from appearing in the taskbar
- Frameless windows need manual mouse event tracking for drag-to-move
- A `QSystemTrayIcon` requires a running `QApplication` to display

### Testing results

```
9 passed in 0.13s
App process state after 5s: Running
No errors or tracebacks
```

---

*Future milestones will be logged here as they are completed.*
