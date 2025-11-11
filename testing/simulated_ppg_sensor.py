#!/usr/bin/env python3
"""
Simulated PPG Sensor - Amor Testing Infrastructure

Generates realistic PPG waveforms and sends via OSC for testing the processor.

USAGE:
    # Single sensor broadcast to network
    python3 testing/simulated_ppg_sensor.py --ppg-id 0

    # Send to localhost
    python3 testing/simulated_ppg_sensor.py --ppg-id 0 --host 127.0.0.1

    # Custom noise/dropout settings
    python3 testing/simulated_ppg_sensor.py --ppg-id 0 --noise-level 10 --dropout-rate 0.08

TESTING:
    Terminal 1: python3 testing/simulated_ppg_sensor.py --ppg-id 0
    Terminal 2: python3 testing/ppg_receiver.py --port 8000
    Terminal 3: python3 -m amor.processor  # Test beat detection

Press Ctrl+C to stop.
"""

import argparse
import numpy as np
import time
from pythonosc import udp_client


class PPGWaveformGenerator:
    """
    Generates realistic PPG waveform with configurable parameters.

    Features:
    - Realistic cardiac waveform (systolic peak, dicrotic notch, diastolic trough)
    - Smooth BPM ramping (60-90 BPM) with random direction changes
    - Gaussian noise + 12-bit ADC quantization
    - Random dropouts (1-2 beats, outputs baseline noise only)

    Signal characteristics:
    - Baseline: 1950 ADC counts
    - Systolic peak: up to 4000
    - Diastolic trough: down to 1500
    - 12-bit ADC range: 0-4095
    """

    def __init__(self,
                 baseline=1950,
                 systolic_peak=4000,
                 diastolic_trough=1500,
                 noise_level=8.0,
                 dropout_rate=0.05,
                 bpm_ramp_rate=0.4):
        """
        Initialize waveform generator.

        Args:
            baseline: Baseline ADC value (default: 1950)
            systolic_peak: Peak systolic value (default: 4000)
            diastolic_trough: Diastolic trough value (default: 1500)
            noise_level: Gaussian noise standard deviation (default: 8.0)
            dropout_rate: Probability of dropout per beat (default: 0.05)
            bpm_ramp_rate: BPM change rate per second (default: 0.4)
        """
        self.baseline = baseline
        self.systolic_peak = systolic_peak
        self.diastolic_trough = diastolic_trough
        self.noise_level = noise_level
        self.dropout_rate = dropout_rate
        self.bpm_ramp_rate = bpm_ramp_rate

        # Calculate amplitude from peak/trough
        self.amplitude = systolic_peak - baseline

        # BPM state
        self.current_bpm = np.random.uniform(60, 90)
        self.bpm_direction = np.random.choice([-1, 1])
        self.last_direction_change = time.time()
        self.next_direction_change_time = np.random.uniform(20, 50)

        # Phase accumulator for continuous waveform
        self.phase = 0.0
        self.sample_rate_hz = 50.0

        # Dropout state
        self.in_dropout = False
        self.dropout_samples_remaining = 0
        self.last_beat_phase = 0.0
        self.dropout_count = 0

        # Statistics
        self.sample_count = 0
        self.last_stats_time = time.time()

    def generate_sample(self) -> int:
        """
        Generate next sample at 50 Hz.

        Returns:
            12-bit ADC value (0-4095)
        """
        self.sample_count += 1

        # Update BPM with smooth ramping
        self._update_bpm()

        # Check for dropout at beat boundaries
        if self._is_beat_boundary():
            self._check_dropout()

        # Generate waveform sample or dropout noise
        if self.in_dropout:
            # Output baseline noise during dropout
            sample = self.baseline + np.random.normal(0, self.noise_level)
            self.dropout_samples_remaining -= 1
            if self.dropout_samples_remaining <= 0:
                self.in_dropout = False
        else:
            # Generate realistic cardiac waveform
            sample = self._generate_cardiac_waveform(self.phase)

            # Add Gaussian noise
            sample += np.random.normal(0, self.noise_level)

        # Advance phase
        phase_increment = (self.current_bpm / 60.0) / self.sample_rate_hz
        self.phase = (self.phase + phase_increment) % 1.0

        # Quantize to 12-bit ADC and clamp
        sample = int(np.round(sample))
        sample = np.clip(sample, 0, 4095)

        return sample

    def _generate_cardiac_waveform(self, phase):
        """
        Generate single cardiac cycle sample at given phase (0.0-1.0).

        Model combines:
        - Primary sinusoid for main cardiac cycle
        - 2nd harmonic for sharp systolic peak
        - Gaussian bump for dicrotic notch

        Timing:
        - Systolic peak: ~0.2 phase (20% into cycle)
        - Dicrotic notch: ~0.7 phase (70% into cycle)
        - Diastolic: ~0.0/1.0 phase (start/end of cycle)
        """
        # Primary cardiac waveform (fundamental frequency)
        primary = np.sin(2 * np.pi * phase)

        # Sharp systolic peak (2nd harmonic)
        harmonic = 0.3 * np.sin(4 * np.pi * phase)

        # Dicrotic notch (Gaussian at phase ~0.7)
        dicrotic = 0.2 * np.exp(-((phase - 0.7) ** 2) / 0.01)

        # Combine components
        waveform = primary + harmonic + dicrotic

        # Proper normalization to [0, 1]
        # min(primary + harmonic + dicrotic) = -1 - 0.3 + 0 = -1.3
        # max(primary + harmonic + dicrotic) = 1 + 0.3 + 0.2 = 1.5
        waveform_min = -1.3
        waveform_max = 1.5
        normalized = (waveform - waveform_min) / (waveform_max - waveform_min)

        # Scale to desired amplitude range [diastolic_trough, systolic_peak]
        sample = self.diastolic_trough + (self.systolic_peak - self.diastolic_trough) * normalized

        return sample

    def _update_bpm(self):
        """Update BPM with smooth ramping and random direction changes."""
        now = time.time()

        # Check for random direction change (every 20-50 seconds)
        time_since_change = now - self.last_direction_change
        if time_since_change > self.next_direction_change_time:
            self.bpm_direction *= -1
            self.last_direction_change = now
            self.next_direction_change_time = np.random.uniform(20, 50)

        # Ramp BPM
        dt = 1.0 / self.sample_rate_hz  # Time per sample
        self.current_bpm += self.bpm_direction * self.bpm_ramp_rate * dt

        # Clamp to 60-90 BPM and reverse direction at boundaries
        if self.current_bpm >= 90:
            self.current_bpm = 90
            self.bpm_direction = -1
        elif self.current_bpm <= 60:
            self.current_bpm = 60
            self.bpm_direction = 1

    def _is_beat_boundary(self):
        """Check if we just crossed a beat boundary (phase wrapped around)."""
        is_boundary = self.phase < self.last_beat_phase
        self.last_beat_phase = self.phase
        return is_boundary

    def _check_dropout(self):
        """Randomly trigger dropouts at beat boundaries."""
        if not self.in_dropout and np.random.random() < self.dropout_rate:
            # Trigger dropout for 1-2 beats
            beats_to_drop = np.random.randint(1, 3)
            samples_per_beat = round(60.0 / self.current_bpm * self.sample_rate_hz)
            self.dropout_samples_remaining = beats_to_drop * samples_per_beat
            self.in_dropout = True
            self.dropout_count += 1

    def get_current_bpm(self):
        """Get current BPM for statistics."""
        return self.current_bpm

    def get_dropout_count(self):
        """Get total dropout count for statistics."""
        return self.dropout_count


class SimulatedSensor:
    """
    Simulated PPG sensor with OSC output.

    Sends /ppg/{ppg_id} messages at 10 Hz (5 samples per bundle @ 50 Hz).
    Compatible with Amor processor OSC message format.
    """

    def __init__(self, host, port, ppg_id, waveform_gen):
        """
        Initialize simulated sensor.

        Args:
            host: Target IP address (e.g., '127.0.0.1' or '255.255.255.255')
            port: Target OSC port (default: 8000)
            ppg_id: PPG sensor ID (0-3)
            waveform_gen: PPGWaveformGenerator instance
        """
        self.client = udp_client.SimpleUDPClient(host, port)
        self.host = host
        self.port = port
        self.ppg_id = ppg_id
        self.waveform_gen = waveform_gen

        # Message tracking
        self.message_count = 0
        self.start_time = time.time()
        self.last_stats_time = time.time()

        # Simulate ESP32 millis() counter
        self.millis_start = int(time.time() * 1000)

    def run(self):
        """Main simulation loop at 50 Hz."""
        print(f"Simulated PPG Sensor {self.ppg_id}")
        print(f"Target: {self.host}:{self.port}")
        print(f"OSC Address: /ppg/{self.ppg_id}")
        print(f"Sample Rate: 50 Hz (20ms per sample)")
        print(f"Message Rate: 10 Hz (5-sample bundles)")
        print(f"BPM Range: 60-90 (ramping)")
        print("Press Ctrl+C to stop\n")

        bundle = []
        sample_interval = 0.020  # 20ms per sample at 50 Hz
        next_sample_time = time.time()

        try:
            while True:
                # Generate sample at 50 Hz
                sample = self.waveform_gen.generate_sample()
                bundle.append(sample)

                # Send bundle every 5 samples (10 Hz message rate)
                if len(bundle) == 5:
                    # Simulate ESP32 millis() timestamp (wraps at 2^32 for unsigned 32-bit)
                    timestamp_ms = (int(time.time() * 1000) - self.millis_start) % (2**32)

                    # Send OSC message: /ppg/{id} [s0, s1, s2, s3, s4, timestamp_ms]
                    self.client.send_message(f"/ppg/{self.ppg_id}", bundle + [timestamp_ms])

                    self.message_count += 1
                    bundle = []

                    # Print statistics every 5 seconds
                    if time.time() - self.last_stats_time >= 5.0:
                        self._print_statistics()
                        self.last_stats_time = time.time()

                # Sleep with drift compensation to maintain 50 Hz
                next_sample_time += sample_interval
                sleep_time = next_sample_time - time.time()
                if sleep_time > 0:
                    time.sleep(sleep_time)

        except KeyboardInterrupt:
            print("\n\nShutting down...")
            self._print_final_statistics()

    def _print_statistics(self):
        """Print periodic statistics."""
        current_bpm = self.waveform_gen.get_current_bpm()
        dropout_count = self.waveform_gen.get_dropout_count()
        elapsed = time.time() - self.start_time
        msg_rate = self.message_count / elapsed if elapsed > 0 else 0

        print(f"[PPG {self.ppg_id}] Messages: {self.message_count:6d} | "
              f"Rate: {msg_rate:5.1f} msg/s | "
              f"BPM: {current_bpm:5.1f} | "
              f"Dropouts: {dropout_count:3d}")

    def _print_final_statistics(self):
        """Print final statistics on shutdown."""
        elapsed = time.time() - self.start_time
        total_samples = self.message_count * 5
        dropout_count = self.waveform_gen.get_dropout_count()

        print("\n" + "="*60)
        print(f"Simulated PPG Sensor {self.ppg_id} - Final Statistics")
        print("="*60)
        print(f"Runtime:        {elapsed:.1f} seconds")
        print(f"Messages sent:  {self.message_count} bundles")
        print(f"Samples sent:   {total_samples} samples")
        print(f"Message rate:   {self.message_count/elapsed:.1f} bundles/sec")
        print(f"Sample rate:    {total_samples/elapsed:.1f} samples/sec")
        print(f"Dropouts:       {dropout_count}")
        print("="*60)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Simulated PPG sensor for Amor testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Broadcast to local network (default)
  python3 testing/simulated_ppg_sensor.py --ppg-id 0

  # Send to localhost
  python3 testing/simulated_ppg_sensor.py --ppg-id 0 --host 127.0.0.1

  # Custom noise and dropout rate
  python3 testing/simulated_ppg_sensor.py --ppg-id 0 --noise-level 10 --dropout-rate 0.1

  # Run 4 sensors simultaneously (in separate terminals)
  python3 testing/simulated_ppg_sensor.py --ppg-id 0
  python3 testing/simulated_ppg_sensor.py --ppg-id 1
  python3 testing/simulated_ppg_sensor.py --ppg-id 2
  python3 testing/simulated_ppg_sensor.py --ppg-id 3
        """
    )

    parser.add_argument(
        '--host',
        type=str,
        default='255.255.255.255',
        help='Target IP address (default: 255.255.255.255 for broadcast)'
    )

    parser.add_argument(
        '--port',
        type=int,
        default=8000,
        help='Target OSC port (default: 8000)'
    )

    parser.add_argument(
        '--ppg-id',
        type=int,
        required=True,
        choices=[0, 1, 2, 3],
        help='PPG sensor ID (0-3)'
    )

    parser.add_argument(
        '--noise-level',
        type=float,
        default=8.0,
        help='Gaussian noise standard deviation (default: 8.0)'
    )

    parser.add_argument(
        '--dropout-rate',
        type=float,
        default=0.05,
        help='Dropout probability per beat (default: 0.05 = 5%%)'
    )

    parser.add_argument(
        '--bpm-ramp-rate',
        type=float,
        default=0.4,
        help='BPM change rate per second (default: 0.4)'
    )

    args = parser.parse_args()

    # Validate input parameters
    if args.noise_level < 0:
        parser.error("--noise-level must be non-negative")
    if not 0 <= args.dropout_rate <= 1:
        parser.error("--dropout-rate must be between 0 and 1")
    if args.bpm_ramp_rate < 0:
        parser.error("--bpm-ramp-rate must be non-negative")

    # Create waveform generator
    waveform_gen = PPGWaveformGenerator(
        noise_level=args.noise_level,
        dropout_rate=args.dropout_rate,
        bpm_ramp_rate=args.bpm_ramp_rate
    )

    # Create and run simulated sensor
    sensor = SimulatedSensor(args.host, args.port, args.ppg_id, waveform_gen)
    sensor.run()


if __name__ == "__main__":
    main()
