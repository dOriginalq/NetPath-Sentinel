"""
models/network_event.py — NetworkEvent Data Model

Placeholder for Milestone 6.

This module will define the NetworkEvent dataclass/model used to
represent a single recorded network observation or anomaly.

Fields will include:
  timestamp     — When the event was recorded
  event_type    — e.g., "connection_lost", "high_latency", "dns_timeout"
  severity      — e.g., "info", "warning", "critical"
  latency_ms    — Round-trip time in milliseconds
  packet_loss   — Packet loss percentage (0.0 - 100.0)
  dns_status    — "ok", "timeout", "failed"
  ipv4_status   — "active", "failed"
  ipv6_status   — "active", "failed"
  duration_s    — Duration of the event in seconds (for outages)
"""
