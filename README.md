# NetPath Sentinel

**NetPath Sentinel: An ISP-Aware Network Monitoring, Anomaly Detection, and Root-Cause Analysis System**

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Status: Active Development](https://img.shields.io/badge/status-active%20development-green.svg)]()

---

## What is NetPath Sentinel?

NetPath Sentinel is a lightweight Windows background application that continuously monitors your network connection and records network health information.

It lives quietly in the **Windows system tray**, collecting measurements in the background and presenting them through a compact popup dashboard — no full-screen window, no constant interruptions.

### Why does this project exist?

This project was motivated by intermittent connectivity problems on a JioFiber connection, where certain websites and services occasionally fail, while connecting through Cloudflare WARP appears to resolve the problem.

Rather than making assumptions, NetPath Sentinel exists to **measure and record actual network behavior** so that connectivity problems can be analyzed based on evidence.

The application collects data to help answer questions like:

- Is the problem related to **DNS**?
- Is it an **IPv4** or **IPv6** issue?
- Is there **packet loss** or excessive **latency**?
- Does the problem occur at the **TCP** or **TLS** layer?
- Does the network **path change** during failures?
- Is the problem on the **ISP side** or the **destination side**?
- Does using **Cloudflare WARP** change the observed behavior?

The application measures these things rather than making unsupported claims.

---

## Project Objective

1. **Functional tool**: A real-time, always-on network health monitor for personal use on Windows.
2. **Learning project**: A hands-on way to understand DNS, TCP, IPv4/IPv6, routing, latency, jitter, packet loss, and network anomaly detection through working code.
3. **Research tool**: A data collection platform for comparing network behavior with and without Cloudflare WARP to study ISP-level connectivity patterns.

---

## Technology Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.12+ |
| UI Framework | PySide6 (Qt for Python) |
| Local Storage | SQLite |
| Networking | Python standard library (socket, subprocess, etc.) |
| Charting | pyqtgraph |
| Tray | PySide6 SystemTrayIcon |

---

## Current Development Status

> **Milestone 0 — Repository & Project Foundation** ✅

The project structure has been initialized. No monitoring functionality has been implemented yet.

See the [Roadmap](#roadmap) below for what is planned.

---

## Project Structure

```
NetPath-Sentinel/
│
├── README.md
├── requirements.txt
├── .gitignore
├── LICENSE
│
├── src/
│   └── netpath_sentinel/
│       ├── main.py               # Application entry point
│       │
│       ├── tray/
│       │   └── tray.py           # System tray icon and menu
│       │
│       ├── ui/
│       │   ├── dashboard.py      # Popup dashboard window
│       │   ├── charts.py         # Latency and activity charts
│       │   └── styles.py         # Visual styles / QSS
│       │
│       ├── monitoring/
│       │   ├── network_monitor.py  # Main monitoring coordinator
│       │   ├── connectivity.py     # Ping, TCP, TLS checks
│       │   ├── dns_monitor.py      # DNS resolution monitoring
│       │   └── latency_monitor.py  # RTT / jitter / packet loss
│       │
│       ├── storage/
│       │   └── database.py       # SQLite read/write
│       │
│       └── models/
│           └── network_event.py  # NetworkEvent data model
│
├── tests/
│
├── docs/
│   ├── architecture.md
│   ├── methodology.md
│   └── development-log.md
│
└── assets/
    └── ui-reference.png          # UI design reference
```

---

## Roadmap

| Milestone | Description | Status |
|-----------|-------------|--------|
| **M0** | Repository & Project Foundation | ✅ Complete |
| **M1** | Basic Tray Application | ✅ Complete |
| **M2** | Popup Dashboard UI | 🔲 Pending |
| **M3** | Basic Network Monitoring | 🔲 Pending |
| **M4** | Connectivity Health Monitoring | 🔲 Pending |
| **M5** | DNS / IPv4 / IPv6 Monitoring | 🔲 Pending |
| **M6** | SQLite Event Storage | 🔲 Pending |
| **M7** | Historical Dashboard | 🔲 Pending |
| **M8** | Network Diagnostics | 🔲 Pending |
| **M9** | Connection Incident Analysis | 🔲 Pending |
| **M10** | Jio/WARP Path Comparison | 🔲 Pending |
| **M11** | Research Dashboard | 🔲 Pending |
| **M12** | Documentation & Research Preparation | 🔲 Pending |

---

## Installation

> Installation instructions will be added once the core application is implemented (Milestone 1+).

### Prerequisites

- Windows 10 or 11
- Python 3.12+

### Quick Start (Development)

```bash
# Clone the repository
git clone https://github.com/dOriginalq/NetPath-Sentinel.git
cd NetPath-Sentinel

# Create a virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python src/netpath_sentinel/main.py
```

---

## Research Objective

This project specifically investigates intermittent connectivity failures observed on a JioFiber broadband connection.

The hypothesis being tested is that certain failures may be route- or protocol-specific, which would explain why Cloudflare WARP (which uses a different network path and tunneling protocol) may resolve the problem.

**The application does not assume JioFiber is responsible.**

It collects measurements to determine whether the problem is:

- DNS-related
- IPv4/IPv6-related
- Latency/packet-loss-related
- Path-related
- Destination-side infrastructure
- Something else entirely

The collected dataset will be compared across two environments:
- Native JioFiber connection
- JioFiber + Cloudflare WARP

---

## Security Principles

NetPath Sentinel is a **defensive, personal network monitoring tool**.

It:
- Monitors your own machine and network only
- Stores all data locally (SQLite, no cloud)
- Does NOT capture packet payloads
- Does NOT collect passwords or authentication tokens
- Does NOT perform any unauthorized network access
- Does NOT attempt to bypass ISP controls

---

## License

MIT License. See [LICENSE](LICENSE) for details.

---

## Development Notes

This project follows a strict milestone-based development process. Each milestone is committed and pushed to GitHub before the next one begins.

Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) style.
