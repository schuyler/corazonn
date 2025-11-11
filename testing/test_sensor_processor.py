#!/usr/bin/env python3
"""
Test script for sensor_processor.py
Sends simulated PPG data and verifies beat detection.
"""

import time
import numpy as np
from pythonosc.udp_client import SimpleUDPClient


def generate_ppg_waveform(num_samples, bpm=60, baseline=2048, amplitude=200, noise_level=20):
    """
    Generate synthetic PPG waveform with heartbeats.

    Args:
        num_samples: Number of samples to generate
        bpm: Beats per minute
        baseline: ADC baseline value
        amplitude: Peak-to-peak amplitude
        noise_level: Noise amplitude

    Returns:
        Array of ADC values (integers 0-4095)
    """
    # Calculate heart rate in Hz
    heart_rate_hz = bpm / 60.0

    # Sample rate 50Hz
    sample_rate = 50.0

    # Generate time array
    t = np.arange(num_samples) / sample_rate

    # Generate heartbeat waveform (sine wave approximation)
    signal = baseline + amplitude * np.sin(2 * np.pi * heart_rate_hz * t)

    # Add noise
    noise = np.random.normal(0, noise_level, num_samples)
    signal = signal + noise

    # Clip to ADC range
    signal = np.clip(signal, 0, 4095).astype(int)

    return signal


def send_ppg_samples(client, ppg_id, samples, start_timestamp_ms=0, delay_ms=100):
    """
    Send PPG samples to sensor processor.

    Args:
        client: OSC client
        ppg_id: PPG sensor ID (0-3)
        samples: Array of samples to send
        start_timestamp_ms: Starting timestamp
        delay_ms: Delay between bundles in milliseconds
    """
    timestamp_ms = start_timestamp_ms

    # Send samples in bundles of 5
    for i in range(0, len(samples), 5):
        bundle = samples[i:i+5]

        # Pad if less than 5 samples
        if len(bundle) < 5:
            bundle = list(bundle) + [samples[-1]] * (5 - len(bundle))

        # Convert to list of ints
        bundle = [int(s) for s in bundle]

        # Send OSC message: /ppg/{ppg_id} [s1, s2, s3, s4, s5, timestamp]
        client.send_message(f"/ppg/{ppg_id}", bundle + [timestamp_ms])

        # Increment timestamp
        timestamp_ms += delay_ms

        # Delay to simulate real-time
        time.sleep(delay_ms / 1000.0)


def test_warmup_period():
    """Test that sensor properly warms up before detecting beats."""
    print("\n" + "=" * 60)
    print("TEST 1: Warmup Period")
    print("=" * 60)
    print("Sending 300 samples (6 seconds) to verify warmup...")

    client = SimpleUDPClient("127.0.0.1", 8000)

    # Generate 300 samples (6 seconds at 50Hz) with 60 BPM
    samples = generate_ppg_waveform(300, bpm=60, baseline=2048, amplitude=200)

    send_ppg_samples(client, ppg_id=0, samples=samples, delay_ms=100)

    print("Warmup test complete. Check processor output for beats after 250 samples.")


def test_beat_detection():
    """Test beat detection with known BPM."""
    print("\n" + "=" * 60)
    print("TEST 2: Beat Detection")
    print("=" * 60)
    print("Sending 600 samples (12 seconds) at 60 BPM...")
    print("Expected: ~12 beats detected")

    client = SimpleUDPClient("127.0.0.1", 8000)

    # Generate 600 samples (12 seconds) at 60 BPM
    samples = generate_ppg_waveform(600, bpm=60, baseline=2048, amplitude=300)

    send_ppg_samples(client, ppg_id=1, samples=samples, delay_ms=100)

    print("Beat detection test complete. Check sink for ~12 beats on PPG 1.")


def test_noise_rejection():
    """Test that noisy signal pauses beat detection."""
    print("\n" + "=" * 60)
    print("TEST 3: Noise Rejection")
    print("=" * 60)
    print("Sending clean signal, then noisy signal, then clean again...")

    client = SimpleUDPClient("127.0.0.1", 8000)

    # Phase 1: Clean signal (300 samples, 6 seconds)
    print("Phase 1: Clean signal (6 seconds)...")
    clean_samples = generate_ppg_waveform(300, bpm=60, baseline=2048, amplitude=300, noise_level=20)
    send_ppg_samples(client, ppg_id=2, samples=clean_samples, delay_ms=100)

    # Phase 2: Noisy signal (200 samples, 4 seconds)
    print("Phase 2: Noisy signal (4 seconds) - should pause detection...")
    noisy_samples = generate_ppg_waveform(200, bpm=60, baseline=2048, amplitude=300, noise_level=300)
    send_ppg_samples(client, ppg_id=2, samples=noisy_samples, delay_ms=100)

    # Phase 3: Clean signal again (200 samples, 4 seconds)
    print("Phase 3: Clean signal (4 seconds) - should resume after 2 seconds...")
    clean_samples2 = generate_ppg_waveform(200, bpm=60, baseline=2048, amplitude=300, noise_level=20)
    send_ppg_samples(client, ppg_id=2, samples=clean_samples2, delay_ms=100)

    print("Noise rejection test complete. Check processor for paused/resumed states.")


def test_input_validation():
    """Test input validation and error handling."""
    print("\n" + "=" * 60)
    print("TEST 4: Input Validation")
    print("=" * 60)

    client = SimpleUDPClient("127.0.0.1", 8000)

    # Test 1: Invalid PPG ID
    print("Test 4.1: Invalid PPG ID (should be rejected)...")
    client.send_message("/ppg/5", [2048, 2048, 2048, 2048, 2048, 1000])
    time.sleep(0.1)

    # Test 2: Wrong number of arguments
    print("Test 4.2: Wrong number of arguments (should be rejected)...")
    client.send_message("/ppg/0", [2048, 2048, 2048, 1000])  # Only 4 arguments
    time.sleep(0.1)

    # Test 3: Out of range ADC value
    print("Test 4.3: Out of range ADC value (should be rejected)...")
    client.send_message("/ppg/0", [5000, 2048, 2048, 2048, 2048, 1000])  # 5000 > 4095
    time.sleep(0.1)

    # Test 4: Negative timestamp
    print("Test 4.4: Negative timestamp (should be rejected)...")
    client.send_message("/ppg/0", [2048, 2048, 2048, 2048, 2048, -100])
    time.sleep(0.1)

    # Test 5: Valid message (should be accepted)
    print("Test 4.5: Valid message (should be accepted)...")
    client.send_message("/ppg/0", [2048, 2050, 2048, 2050, 2048, 1000])
    time.sleep(0.1)

    print("Input validation test complete. Check processor warnings.")


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("SENSOR PROCESSOR TEST SUITE")
    print("=" * 60)
    print("\nMake sure sensor_processor.py is running on port 8000")
    print("and ppg_test_sink.py is running on ports 8001 and 8002")
    print("\nPress Enter to start tests...")
    input()

    # Run tests
    test_warmup_period()
    time.sleep(2)

    test_beat_detection()
    time.sleep(2)

    test_noise_rejection()
    time.sleep(2)

    test_input_validation()

    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETE")
    print("=" * 60)
    print("\nCheck the sensor processor and sink outputs to verify:")
    print("1. Warmup period before first beat detection")
    print("2. Beat detection at expected BPM")
    print("3. Pause during noise, resume after stabilization")
    print("4. Proper input validation and error messages")


if __name__ == "__main__":
    main()
