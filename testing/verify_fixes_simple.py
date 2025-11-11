#!/usr/bin/env python3
"""
Simple verification of Karl's fixes by code inspection and basic testing.
"""

import time
import numpy as np
from pythonosc.udp_client import SimpleUDPClient


def generate_clean_ppg(num_samples, bpm=60):
    """Generate clean PPG signal."""
    heart_rate_hz = bpm / 60.0
    sample_rate = 50.0
    t = np.arange(num_samples) / sample_rate
    signal = 2048 + 300 * np.sin(2 * np.pi * heart_rate_hz * t)
    signal = np.clip(signal, 0, 4095).astype(int)
    return signal


def test_out_of_order():
    """Test out-of-order message detection."""
    print("\n" + "=" * 70)
    print("TEST: Out-of-Order Message Detection")
    print("=" * 70)

    client = SimpleUDPClient("127.0.0.1", 8000)

    print("Sending message 1: timestamp=1000ms")
    client.send_message("/ppg/2", [2048, 2048, 2048, 2048, 2048, 1000])
    time.sleep(0.2)

    print("Sending message 2: timestamp=2000ms (in order)")
    client.send_message("/ppg/2", [2048, 2048, 2048, 2048, 2048, 2000])
    time.sleep(0.2)

    print("Sending message 3: timestamp=1500ms (OUT OF ORDER)")
    client.send_message("/ppg/2", [2048, 2048, 2048, 2048, 2048, 1500])
    time.sleep(0.2)

    print("\nExpected in processor output:")
    print("  WARNING: Out-of-order sample dropped (PPG 2): 1.500s < 2.000s")


def test_gap_detection():
    """Test message gap detection."""
    print("\n" + "=" * 70)
    print("TEST: Message Gap Detection")
    print("=" * 70)

    client = SimpleUDPClient("127.0.0.1", 8000)

    # Send samples to get into active state
    print("Sending initial samples (timestamp 0-5000ms)...")
    for ts in range(0, 5000, 100):
        client.send_message("/ppg/3", [2048, 2048, 2048, 2048, 2048, ts])
        time.sleep(0.01)

    print("\nSending sample with 2-second gap (timestamp 7000ms)...")
    client.send_message("/ppg/3", [2048, 2048, 2048, 2048, 2048, 7000])
    time.sleep(0.2)

    print("\nExpected in processor output:")
    print("  WARNING: Message gap detected (PPG 3): 2.000s, resetting to warmup")


def test_beat_generation():
    """Test that beats are generated and observe timestamps."""
    print("\n" + "=" * 70)
    print("TEST: Beat Generation with Unix Timestamps")
    print("=" * 70)

    client = SimpleUDPClient("127.0.0.1", 8000)

    # Generate clean PPG signal
    samples = generate_clean_ppg(600, bpm=60)

    print("Sending 600 samples (12 seconds of data)...")
    print("Expected: Beats detected with Unix timestamps")
    print("\nWatch processor output for:")
    print("  - BEAT messages with Unix timestamps (e.g., 1762825xxx.xxxs)")
    print("  - Timestamps should be close to current time")
    print("  - Each beat should have different timestamp")
    print("  - BPM should be ~60")

    timestamp_ms = 0
    for i in range(0, len(samples), 5):
        bundle = samples[i:i+5]
        if len(bundle) < 5:
            bundle = list(bundle) + [samples[-1]] * (5 - len(bundle))
        bundle = [int(s) for s in bundle]

        client.send_message("/ppg/0", bundle + [timestamp_ms])
        timestamp_ms += 100  # 100ms between bundles (5 samples at 50Hz)
        time.sleep(0.1)

    print("\nDone sending samples. Check processor output above.")


def main():
    """Run verification tests."""
    print("\n" + "=" * 70)
    print("KARL'S BUG FIX VERIFICATION")
    print("=" * 70)
    print("\nEnsure sensor_processor.py is running on port 8000")
    print("\nThis will send test data and you should verify output manually.")
    print("\nPress Enter to continue...")
    input()

    # Test beat generation (verify Unix timestamps)
    test_beat_generation()
    time.sleep(2)

    # Test out-of-order detection
    test_out_of_order()
    time.sleep(2)

    # Test gap detection
    test_gap_detection()

    print("\n" + "=" * 70)
    print("TESTS COMPLETE")
    print("=" * 70)
    print("\nVerify in sensor_processor output:")
    print("1. Beat timestamps are Unix time (large numbers ~1762825xxx)")
    print("2. Each beat has different timestamp")
    print("3. Out-of-order warning appeared")
    print("4. Gap detection warning appeared")


if __name__ == "__main__":
    main()
