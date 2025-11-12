#!/usr/bin/env python3
"""
Test script for intensity-based volume scaling.

Sends beat messages with varying intensity values to the audio engine.
"""

import time
from pythonosc import udp_client

def main():
    """Send test beat messages with different intensity values."""
    client = udp_client.SimpleUDPClient("127.0.0.1", 8001)

    print("Intensity Scaling Test")
    print("======================")
    print("Sending beats with varying intensity values...")
    print("Listen for volume changes in the audio playback\n")

    # Test various intensities including edge cases
    test_cases = [
        (0.0, "silence (intensity=0.0)"),
        (0.2, "quiet"),
        (0.5, "medium"),
        (0.8, "loud"),
        (1.0, "full volume"),
        (1.5, "clamped to 1.0"),
        (-0.5, "clamped to 0.0"),
        (0.1, "very quiet"),
    ]

    for i, (intensity, description) in enumerate(test_cases, 1):
        timestamp_ms = int(time.time() * 1000)
        bpm = 70.0

        print(f"Beat {i}: Intensity {intensity:.2f} - {description}")
        client.send_message("/beat/0", [timestamp_ms, bpm, intensity])

        time.sleep(1.5)  # Wait between beats

    print("\nTest complete!")
    print("Expected behavior:")
    print("- With --enable-intensity-scaling:")
    print("  * Intensity 0.0 should be silent")
    print("  * Intensity 1.0 should be full volume")
    print("  * Values <0 or >1 should be clamped to [0.0, 1.0]")
    print("- Without flag: All beats should play at original amplitude")

if __name__ == "__main__":
    main()
