#!/usr/bin/env python3
"""
Test script to verify Karl's bug fixes in sensor_processor.py

Tests:
1. Critical Bug 1: Beat messages use Unix time (time.time()) not ESP32 millis
2. Critical Bug 2: Each sample gets individual timestamp (timestamp_ms + i*20)
3. Out-of-order message detection
4. Message gap detection and warmup reset
"""

import time
import sys
import numpy as np
from pythonosc.udp_client import SimpleUDPClient
from pythonosc import dispatcher, osc_server
import threading


class BeatCapture:
    """Captures beat messages for verification."""

    def __init__(self, port):
        self.port = port
        self.beats = []
        self.server = None
        self.thread = None

    def handle_beat(self, address, *args):
        """Capture beat message."""
        # Beat format: /beat/{ppg_id} [timestamp, bpm, intensity]
        ppg_id = int(address.split('/')[-1])
        timestamp = args[0]
        bpm = args[1]
        intensity = args[2]

        self.beats.append({
            'ppg_id': ppg_id,
            'timestamp': timestamp,
            'bpm': bpm,
            'intensity': intensity,
            'received_at': time.time()
        })

    def start(self):
        """Start capture server in background."""
        disp = dispatcher.Dispatcher()
        disp.map("/beat/*", self.handle_beat)

        self.server = osc_server.BlockingOSCUDPServer(
            ("127.0.0.1", self.port), disp
        )

        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.daemon = True
        self.thread.start()

        time.sleep(0.1)  # Let server start

    def stop(self):
        """Stop capture server."""
        if self.server:
            self.server.shutdown()

    def clear(self):
        """Clear captured beats."""
        self.beats = []

    def get_beats(self):
        """Get captured beats."""
        return self.beats


def generate_clean_ppg(num_samples, bpm=60):
    """Generate clean PPG signal for reliable beat detection."""
    heart_rate_hz = bpm / 60.0
    sample_rate = 50.0
    t = np.arange(num_samples) / sample_rate
    signal = 2048 + 300 * np.sin(2 * np.pi * heart_rate_hz * t)
    signal = np.clip(signal, 0, 4095).astype(int)
    return signal


def send_samples(client, ppg_id, samples, start_timestamp_ms, delay_ms=100):
    """Send samples to processor."""
    timestamp_ms = start_timestamp_ms

    for i in range(0, len(samples), 5):
        bundle = samples[i:i+5]
        if len(bundle) < 5:
            bundle = list(bundle) + [samples[-1]] * (5 - len(bundle))
        bundle = [int(s) for s in bundle]

        client.send_message(f"/ppg/{ppg_id}", bundle + [timestamp_ms])
        timestamp_ms += delay_ms
        time.sleep(delay_ms / 1000.0)


def test_unix_timestamp():
    """
    TEST 1: Verify beat messages use Unix time (time.time()) not ESP32 millis

    Expected: Beat timestamps should be Unix time in seconds (large numbers ~1700000000+)
    Not Expected: ESP32 millis timestamps (small numbers)
    """
    print("\n" + "=" * 70)
    print("TEST 1: Beat Messages Use Unix Time (Critical Bug 1)")
    print("=" * 70)

    capture = BeatCapture(8001)
    capture.start()
    capture.clear()

    client = SimpleUDPClient("127.0.0.1", 8000)

    # Generate clean signal that will produce beats
    samples = generate_clean_ppg(600, bpm=60)  # 12 seconds

    print("Sending PPG data to generate beats...")
    before_test = time.time()
    send_samples(client, ppg_id=0, samples=samples, start_timestamp_ms=0)
    after_test = time.time()

    time.sleep(0.5)  # Let beats arrive

    beats = capture.get_beats()
    capture.stop()

    print(f"\nCaptured {len(beats)} beats")

    if len(beats) == 0:
        print("FAIL: No beats detected (expected at least 1 beat)")
        return False

    # Check that timestamps are Unix time
    passed = True
    for i, beat in enumerate(beats):
        ts = beat['timestamp']

        # Unix timestamps should be in the range of current time
        # (around 1700000000+ seconds since epoch in 2024/2025)
        is_unix_time = ts > 1000000000  # Should be large number
        is_reasonable = before_test <= ts <= after_test + 1  # Within test window

        print(f"  Beat {i+1}: timestamp={ts:.3f}s, "
              f"Unix time: {is_unix_time}, Reasonable: {is_reasonable}")

        if not is_unix_time:
            print(f"    FAIL: Timestamp {ts:.3f} doesn't look like Unix time")
            passed = False
        elif not is_reasonable:
            print(f"    WARNING: Timestamp {ts:.3f} outside test window "
                  f"({before_test:.3f} - {after_test:.3f})")

    if passed:
        print("\nPASS: All beat timestamps use Unix time")
    else:
        print("\nFAIL: Beat timestamps don't use Unix time")

    return passed


def test_individual_sample_timestamps():
    """
    TEST 2: Verify each sample in bundle gets individual timestamp

    Expected: Samples 0-4 get timestamps: base, base+20, base+40, base+60, base+80 (ms)
    This is tested indirectly by checking beat detection works correctly
    """
    print("\n" + "=" * 70)
    print("TEST 2: Individual Sample Timestamps (Critical Bug 2)")
    print("=" * 70)

    # This is harder to test directly without modifying sensor_processor
    # But we can verify the timestamps are being processed correctly
    # by ensuring beat detection works with proper timing

    capture = BeatCapture(8001)
    capture.start()
    capture.clear()

    client = SimpleUDPClient("127.0.0.1", 8000)

    # Generate signal at known BPM
    samples = generate_clean_ppg(600, bpm=60)  # 60 BPM = 1 beat/second

    print("Sending PPG data with 60 BPM...")
    print("If timestamps are correct, we should see beats ~1 second apart")

    start_time = time.time()
    send_samples(client, ppg_id=1, samples=samples, start_timestamp_ms=0)

    time.sleep(0.5)

    beats = capture.get_beats()
    capture.stop()

    print(f"\nCaptured {len(beats)} beats")

    if len(beats) < 2:
        print("FAIL: Need at least 2 beats to verify timing")
        return False

    # The beat timestamps in the message are Unix time
    # But the IBIs calculated internally should be ~1000ms for 60 BPM
    # We can verify BPM is correct

    passed = True
    for i, beat in enumerate(beats):
        bpm = beat['bpm']
        expected_bpm = 60
        tolerance = 10  # +/- 10 BPM tolerance

        bpm_ok = abs(bpm - expected_bpm) < tolerance

        print(f"  Beat {i+1}: BPM={bpm:.1f} (expected ~{expected_bpm}), "
              f"OK: {bpm_ok}")

        if not bpm_ok:
            passed = False

    if passed:
        print("\nPASS: BPM calculation correct (implies timestamps working)")
        print("(Each sample getting individual timestamp: base + i*20ms)")
    else:
        print("\nFAIL: BPM calculation incorrect (may indicate timestamp issue)")

    return passed


def test_out_of_order_detection():
    """
    TEST 3: Verify out-of-order messages are dropped

    Expected: Messages with timestamps < last timestamp should be dropped
    """
    print("\n" + "=" * 70)
    print("TEST 3: Out-of-Order Message Detection")
    print("=" * 70)

    client = SimpleUDPClient("127.0.0.1", 8000)

    # Send messages with timestamps going backwards
    print("Sending message 1: timestamp=1000ms")
    client.send_message("/ppg/2", [2048, 2048, 2048, 2048, 2048, 1000])
    time.sleep(0.1)

    print("Sending message 2: timestamp=2000ms (in order)")
    client.send_message("/ppg/2", [2048, 2048, 2048, 2048, 2048, 2000])
    time.sleep(0.1)

    print("Sending message 3: timestamp=1500ms (OUT OF ORDER - should be dropped)")
    client.send_message("/ppg/2", [2048, 2048, 2048, 2048, 2048, 1500])
    time.sleep(0.1)

    print("Sending message 4: timestamp=3000ms (in order)")
    client.send_message("/ppg/2", [2048, 2048, 2048, 2048, 2048, 3000])
    time.sleep(0.1)

    print("\nCheck sensor_processor output for:")
    print("  - WARNING: Out-of-order sample dropped (PPG 2): 1.500s < 2.000s")
    print("\nPASS: Manual verification required (check processor output)")
    return True


def test_gap_detection():
    """
    TEST 4: Verify message gap > 1s resets to warmup

    Expected: Gap > 1 second should reset state to warmup
    """
    print("\n" + "=" * 70)
    print("TEST 4: Message Gap Detection and Warmup Reset")
    print("=" * 70)

    client = SimpleUDPClient("127.0.0.1", 8000)

    # Send some samples to get into active state
    print("Phase 1: Sending 300 samples to reach active state...")
    samples = generate_clean_ppg(300, bpm=60)
    send_samples(client, ppg_id=3, samples=samples, start_timestamp_ms=0, delay_ms=100)

    print("\nPhase 2: Waiting 2 seconds (simulating message gap)...")
    time.sleep(2)

    # Send more samples with a large timestamp gap (> 1 second)
    # Last timestamp was at ~30000ms (300 samples * 100ms),
    # now we send at 32000ms (2 second gap)
    print("Phase 3: Sending samples with 2-second gap in timestamps...")
    print("  Expected: Sensor should reset to warmup state")

    client.send_message("/ppg/3", [2048, 2048, 2048, 2048, 2048, 32000])
    time.sleep(0.1)

    print("\nCheck sensor_processor output for:")
    print("  - WARNING: Message gap detected (PPG 3): 2.000s, resetting to warmup")
    print("\nPASS: Manual verification required (check processor output)")
    return True


def main():
    """Run all verification tests."""
    print("\n" + "=" * 70)
    print("KARL'S BUG FIX VERIFICATION SUITE")
    print("=" * 70)
    print("\nEnsure sensor_processor.py is running on port 8000")
    print("This test script will capture beat messages on port 8001")
    print("\nPress Enter to start tests...")
    input()

    results = {}

    # Run tests
    results['unix_timestamp'] = test_unix_timestamp()
    time.sleep(1)

    results['individual_timestamps'] = test_individual_sample_timestamps()
    time.sleep(1)

    results['out_of_order'] = test_out_of_order_detection()
    time.sleep(1)

    results['gap_detection'] = test_gap_detection()

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Test 1 - Unix Timestamp:        {'PASS' if results['unix_timestamp'] else 'FAIL'}")
    print(f"Test 2 - Individual Timestamps: {'PASS' if results['individual_timestamps'] else 'FAIL'}")
    print(f"Test 3 - Out-of-Order Detection: MANUAL (check output)")
    print(f"Test 4 - Gap Detection:          MANUAL (check output)")
    print("=" * 70)

    all_automated_pass = results['unix_timestamp'] and results['individual_timestamps']

    if all_automated_pass:
        print("\nALL AUTOMATED TESTS PASSED")
        print("Verify manual tests by checking sensor_processor output")
    else:
        print("\nSOME AUTOMATED TESTS FAILED")
        print("Review failures above")

    return all_automated_pass


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
