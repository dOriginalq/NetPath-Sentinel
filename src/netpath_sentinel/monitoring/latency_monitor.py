"""
monitoring/latency_monitor.py — RTT, Jitter, and Packet Loss Measurement

Placeholder for Milestone 4.

This module will implement:
  - Round-trip time (RTT) measurement via ping
  - Jitter calculation (variation in RTT between consecutive measurements)
  - Packet loss percentage estimation

Understanding these metrics:
  RTT (latency): The time it takes for a packet to travel from your machine
    to a destination and back. High RTT = slow responses.

  Jitter: The inconsistency in RTT over time. Stable connections have low jitter.
    High jitter causes problems with video calls and real-time applications.

  Packet loss: The percentage of sent packets that never receive a reply.
    Even 1-2% packet loss can significantly degrade TCP performance because
    TCP treats lost packets as a congestion signal and slows down transmission.
"""
