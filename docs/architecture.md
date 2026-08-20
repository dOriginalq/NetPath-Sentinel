# NetPath Sentinel — Architecture

> **Status**: Milestone 0 — placeholder. This document will be completed at Milestone 12.

## Overview

NetPath Sentinel is a Windows background application with three primary components:

1. **Tray** — Windows system tray icon and context menu
2. **Background Monitor** — Independent thread that continuously measures network health
3. **Dashboard** — Compact popup UI displaying current and historical data

```
NetPath Sentinel
       │
       ├── Tray (PySide6 QSystemTrayIcon)
       │
       ├── Background Monitor (Python threading.Thread)
       │   ├── Latency Monitor
       │   ├── DNS Monitor
       │   ├── Connectivity Checker (IPv4 / IPv6)
       │   └── Network Interface Sampler
       │
       └── Dashboard (PySide6 QWidget popup)
           ├── Status Panel
           ├── Metrics Panel
           ├── Charts (pyqtgraph)
           └── Events Panel
```

## Data Flow

```
Background Monitor
       │
       ▼
In-memory state (latest measurements)
       │
       ├──► SQLite database (persistent history)
       │
       └──► Dashboard reads state on open / refresh
```

## Technology Choices

| Choice | Reason |
|--------|--------|
| Python | Readable, standard library covers most networking needs |
| PySide6 | Native Qt tray and window support on Windows |
| SQLite | Simple, file-based, no server required |
| pyqtgraph | Real-time charting within Qt, fast |
| threading | Simple concurrency model, sufficient for this scale |

*This document will be expanded at Milestone 12.*
