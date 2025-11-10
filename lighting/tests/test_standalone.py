#!/usr/bin/env python3
"""Test bridge with OSC sender (no Pure Data required)."""

from pythonosc import udp_client
import time


def test_standalone():
    """
    Send test pulses to lighting bridge.

    Prerequisites:
    - Bridge running (python src/main.py)
    - Backend configured and authenticated
    """
    client = udp_client.SimpleUDPClient('127.0.0.1', 8001)

    test_data = [
        (0, 1000),  # Zone 0: 60 BPM
        (1, 833),   # Zone 1: 72 BPM
        (2, 1034),  # Zone 2: 58 BPM
        (3, 750),   # Zone 3: 80 BPM
    ]

    print("Sending test pulses for 30 seconds...")
    print("Watch bulbs for color-coded pulses:")
    print("  Zone 0 (60 BPM): Green")
    print("  Zone 1 (72 BPM): Yellow-Green")
    print("  Zone 2 (58 BPM): Blue-Green")
    print("  Zone 3 (80 BPM): Green")
    print()

    start = time.time()
    while time.time() - start < 30:
        for zone, ibi in test_data:
            client.send_message(f'/light/{zone}/pulse', ibi)
            time.sleep(ibi / 1000)


if __name__ == '__main__':
    test_standalone()
