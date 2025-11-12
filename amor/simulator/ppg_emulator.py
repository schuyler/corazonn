#!/usr/bin/env python3
"""
PPG Sensor Emulator - Integration Testing

Controllable PPG sensor emulator for integration testing.
Supports programmatic control of BPM, dropouts, and signal quality.

Features:
- Configurable BPM (static or ramping)
- Dropout injection on demand
- Signal quality control (noise levels)
- Realistic cardiac waveform generation
- OSC message transmission at 10 Hz
"""

import time
import signal
import sys
import argparse
import threading
import numpy as np
from pythonosc import udp_client
from typing import Optional


class PPGEmulator:
    """Emulated PPG sensor with controllable parameters.

    Args:
        ppg_id: Sensor ID (0-3)
        host: Target OSC host
        port: Target OSC port (default: 8000)
        bpm: Initial BPM (default: 75)
        noise_level: Gaussian noise std dev (default: 8.0)
        baseline: Baseline ADC value (default: 1950, unused - kept for compatibility)
        systolic_peak: Peak systolic value (default: 4000)
        diastolic_trough: Diastolic trough value (default: 1500)
    """

    def __init__(
        self,
        ppg_id: int,
        host: str = "127.0.0.1",
        port: int = 8000,
        bpm: float = 75.0,
        noise_level: float = 8.0,
        baseline: int = 1950,
        systolic_peak: int = 3000,
        diastolic_trough: int = 2000
    ):
        self.ppg_id = ppg_id
        self.host = host
        self.port = port
        self.client = udp_client.SimpleUDPClient(host, port)

        # Waveform parameters (match original simulator)
        self.bpm = bpm
        self.noise_level = noise_level
        self.baseline = baseline
        self.systolic_peak = systolic_peak
        self.diastolic_trough = diastolic_trough
        self.sample_rate_hz = 50.0

        # Thread safety
        self.lock = threading.Lock()

        # Phase accumulator for waveform generation
        self.phase = 0.0

        # Dropout control
        self.in_dropout = False
        self.dropout_samples_remaining = 0

        # Message tracking
        self.message_count = 0
        self.sample_count = 0
        self.start_time = time.time()

        # Control flags
        self.running = False

    def set_bpm(self, bpm: float):
        """Set current BPM (thread-safe)."""
        with self.lock:
            self.bpm = max(40.0, min(180.0, bpm))

    def set_noise_level(self, noise_level: float):
        """Set noise level (std dev, thread-safe)."""
        with self.lock:
            self.noise_level = max(0.0, noise_level)

    def trigger_dropout(self, beats: int = 2):
        """Trigger dropout for specified number of beats (thread-safe)."""
        with self.lock:
            samples_per_beat = round(60.0 / self.bpm * self.sample_rate_hz)
            self.dropout_samples_remaining = beats * samples_per_beat
            self.in_dropout = True

    def _generate_cardiac_waveform(self, phase: float) -> float:
        """Generate cardiac waveform sample at given phase (0.0-1.0).

        Pulse-like waveform matching real PPG sensors:
        - Flat baseline most of the time (low MAD)
        - Sharp systolic peak during ~30% of cycle
        - Ensures threshold crossings with MAD_THRESHOLD_K=4.5

        Real PPG sensors show mostly flat signal with periodic sharp pulses,
        not continuous sinusoids. This produces lower MAD relative to amplitude,
        allowing threshold = median + 4.5*MAD to be crossable by the peak.
        """
        # Cardiac pulse spanning first 60% of cycle
        # Wider pulse increases MAD above MAD_MIN_QUALITY=40 threshold
        if phase < 0.6:
            # Smooth pulse using raised cosine (0 → 1 → 0)
            pulse_phase = phase / 0.6  # Normalize to [0, 1] over pulse duration
            normalized = 0.5 * (1.0 - np.cos(np.pi * pulse_phase))
        else:
            # Baseline for remaining 40% of cycle
            normalized = 0.0

        return normalized

    def generate_sample(self) -> int:
        """Generate single PPG sample (thread-safe)."""
        with self.lock:
            self.sample_count += 1

            if self.in_dropout:
                # Output baseline noise during dropout
                sample = self.baseline + np.random.normal(0, self.noise_level)
                self.dropout_samples_remaining -= 1
                if self.dropout_samples_remaining <= 0:
                    self.in_dropout = False
            else:
                # Generate cardiac waveform (match original simulator amplitude calculation)
                normalized = self._generate_cardiac_waveform(self.phase)
                sample = self.diastolic_trough + (self.systolic_peak - self.diastolic_trough) * normalized

                # Add noise
                sample += np.random.normal(0, self.noise_level)

            # Advance phase
            phase_increment = (self.bpm / 60.0) / self.sample_rate_hz
            self.phase = (self.phase + phase_increment) % 1.0

            # Quantize to 12-bit ADC
            sample = int(np.round(sample))
            sample = int(np.clip(sample, 0, 4095))  # Convert to Python int for OSC compatibility

            return sample

    def send_bundle(self, samples: list[int], timestamp_ms: int):
        """Send 5-sample bundle via OSC."""
        self.client.send_message(f"/ppg/{self.ppg_id}", samples + [timestamp_ms])
        self.message_count += 1

    def run(self):
        """Main emulator loop at 50 Hz."""
        self.running = True

        print(f"PPG Emulator {self.ppg_id} starting...")
        print(f"  Target: {self.host}:{self.port}")
        print(f"  BPM: {self.bpm}")
        print(f"  Noise: {self.noise_level}")

        bundle = []
        sample_interval = 0.020  # 20ms per sample (50 Hz)
        next_sample_time = time.time()
        millis_start = int(time.time() * 1000)

        try:
            while self.running:
                # Generate sample
                sample = self.generate_sample()
                bundle.append(sample)

                # Send bundle every 5 samples (10 Hz)
                if len(bundle) == 5:
                    timestamp_ms = (int(time.time() * 1000) - millis_start) % (2**32)
                    self.send_bundle(bundle, timestamp_ms)
                    bundle = []

                # Sleep with drift compensation
                next_sample_time += sample_interval
                sleep_time = next_sample_time - time.time()
                if sleep_time > 0:
                    time.sleep(sleep_time)

        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def stop(self):
        """Stop the emulator."""
        self.running = False
        elapsed = time.time() - self.start_time
        print(f"\nPPG Emulator {self.ppg_id} stopped.")
        print(f"  Runtime: {elapsed:.1f}s")
        print(f"  Messages: {self.message_count}")
        print(f"  Samples: {self.sample_count}")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="PPG sensor emulator for integration testing")
    parser.add_argument("--ppg-id", type=int, required=True, choices=[0, 1, 2, 3],
                       help="PPG sensor ID (0-3)")
    parser.add_argument("--host", type=str, default="127.0.0.1",
                       help="Target OSC host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000,
                       help="Target OSC port (default: 8000)")
    parser.add_argument("--bpm", type=float, default=75.0,
                       help="BPM (default: 75)")
    parser.add_argument("--noise-level", type=float, default=8.0,
                       help="Noise level (default: 8.0)")

    args = parser.parse_args()

    emulator = PPGEmulator(
        ppg_id=args.ppg_id,
        host=args.host,
        port=args.port,
        bpm=args.bpm,
        noise_level=args.noise_level
    )

    # Signal handlers
    def signal_handler(sig, frame):
        emulator.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    emulator.run()


if __name__ == "__main__":
    main()
