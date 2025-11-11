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
        baseline: Baseline ADC value (default: 1950)
        amplitude: Peak-to-peak amplitude (default: 2050)
    """

    def __init__(
        self,
        ppg_id: int,
        host: str = "127.0.0.1",
        port: int = 8000,
        bpm: float = 75.0,
        noise_level: float = 8.0,
        baseline: int = 1950,
        amplitude: int = 2050
    ):
        self.ppg_id = ppg_id
        self.host = host
        self.port = port
        self.client = udp_client.SimpleUDPClient(host, port)

        # Waveform parameters
        self.bpm = bpm
        self.noise_level = noise_level
        self.baseline = baseline
        self.amplitude = amplitude
        self.sample_rate_hz = 50.0

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
        """Set current BPM."""
        self.bpm = max(40.0, min(180.0, bpm))

    def set_noise_level(self, noise_level: float):
        """Set noise level (std dev)."""
        self.noise_level = max(0.0, noise_level)

    def trigger_dropout(self, beats: int = 2):
        """Trigger dropout for specified number of beats."""
        samples_per_beat = round(60.0 / self.bpm * self.sample_rate_hz)
        self.dropout_samples_remaining = beats * samples_per_beat
        self.in_dropout = True

    def _generate_cardiac_waveform(self, phase: float) -> float:
        """Generate cardiac waveform sample at given phase (0.0-1.0).

        Combines fundamental sinusoid, 2nd harmonic, and dicrotic notch.
        """
        # Primary waveform
        primary = np.sin(2 * np.pi * phase)

        # Sharp systolic peak (2nd harmonic)
        harmonic = 0.3 * np.sin(4 * np.pi * phase)

        # Dicrotic notch (Gaussian at phase ~0.7)
        dicrotic = 0.2 * np.exp(-((phase - 0.7) ** 2) / 0.01)

        # Combine and normalize to [0, 1]
        waveform = primary + harmonic + dicrotic
        waveform_min = -1.3
        waveform_max = 1.5
        normalized = (waveform - waveform_min) / (waveform_max - waveform_min)

        return normalized

    def generate_sample(self) -> int:
        """Generate single PPG sample."""
        self.sample_count += 1

        if self.in_dropout:
            # Output baseline noise during dropout
            sample = self.baseline + np.random.normal(0, self.noise_level)
            self.dropout_samples_remaining -= 1
            if self.dropout_samples_remaining <= 0:
                self.in_dropout = False
        else:
            # Generate cardiac waveform
            normalized = self._generate_cardiac_waveform(self.phase)
            sample = self.baseline + self.amplitude * normalized

            # Add noise
            sample += np.random.normal(0, self.noise_level)

        # Advance phase
        phase_increment = (self.bpm / 60.0) / self.sample_rate_hz
        self.phase = (self.phase + phase_increment) % 1.0

        # Quantize to 12-bit ADC
        sample = int(np.round(sample))
        sample = np.clip(sample, 0, 4095)

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
