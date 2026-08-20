# NetPath Sentinel — Monitoring Methodology

> **Status**: Milestone 0 — placeholder. This document will be completed at Milestone 12.

## What We Measure

| Metric | Method | Why |
|--------|--------|-----|
| Latency (RTT) | ICMP ping via `ping` command | Measures round-trip delay to a target |
| Jitter | Standard deviation of consecutive RTTs | Measures RTT consistency |
| Packet Loss | Ratio of lost pings to sent pings | Detects unstable links |
| DNS Resolution Time | Timed `socket.getaddrinfo()` call | Measures DNS health |
| IPv4 Connectivity | TCP connect to known IPv4-only endpoint | Verifies IPv4 path |
| IPv6 Connectivity | TCP connect to known IPv6 endpoint | Verifies IPv6 path |
| Network Interface Bandwidth | `psutil` byte counters, sampled per second | Estimates throughput |

## Targets Used for Measurement

Measurements use well-known, stable public endpoints:
- `1.1.1.1` (Cloudflare DNS) — low latency, highly available
- `8.8.8.8` (Google DNS) — secondary reference
- `google.com` — DNS + IPv4 connectivity reference

*This document will be expanded with actual measurement details as each milestone is implemented.*

## Limitations

- ICMP ping may be blocked by some firewalls (uncommon on consumer ISP connections)
- Packet loss is estimated, not directly measured at the IP layer
- Bandwidth measurement is per-interface, not per-connection

## Assumptions

- The test machine is running Windows 10 or 11
- The user has a standard consumer broadband connection
- The user is not actively modifying network routes during measurement
