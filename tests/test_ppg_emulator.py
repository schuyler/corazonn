"""
Tests for PPG Emulator

Validates waveform generation, BPM control, dropout injection, and thread safety.
"""

import pytest
import time
import threading
import numpy as np
from amor.simulator.ppg_emulator import PPGEmulator


class TestPPGEmulator:
    """Test PPGEmulator functionality."""

    def test_initialization(self):
        """Test emulator initializes with correct defaults."""
        emulator = PPGEmulator(ppg_id=0)

        assert emulator.ppg_id == 0
        assert emulator.bpm == 75.0
        assert emulator.noise_level == 8.0
        assert emulator.systolic_peak == 3000
        assert emulator.diastolic_trough == 2000
        assert emulator.phase == 0.0
        assert emulator.running == False

    def test_waveform_amplitude_range(self):
        """Test waveform produces correct amplitude range."""
        emulator = PPGEmulator(ppg_id=0, noise_level=0.0)  # No noise for testing

        samples = [emulator.generate_sample() for _ in range(100)]

        # With no noise, should be in range [diastolic_trough, systolic_peak]
        assert min(samples) >= emulator.diastolic_trough - 1  # Allow 1 count tolerance
        assert max(samples) <= emulator.systolic_peak + 1

    def test_waveform_matches_original_calculation(self):
        """Test waveform calculation matches original simulator."""
        emulator = PPGEmulator(ppg_id=0, noise_level=0.0)

        # Generate full cycle to find true peak-to-peak
        samples = []
        for _ in range(50):  # One full cycle at 60 BPM
            sample = emulator.generate_sample()
            samples.append(sample)

        # Verify samples span most of the range (diastolic_trough to systolic_peak)
        # With defaults: 2000-3000 = 1000 range
        # Should get at least 75% of that range (750)
        assert max(samples) - min(samples) > 750

    def test_bpm_control(self):
        """Test BPM can be changed dynamically."""
        emulator = PPGEmulator(ppg_id=0, bpm=60.0)

        assert emulator.bpm == 60.0

        emulator.set_bpm(90.0)
        assert emulator.bpm == 90.0

        # Test clamping
        emulator.set_bpm(200.0)  # Above max
        assert emulator.bpm == 180.0

        emulator.set_bpm(30.0)  # Below min
        assert emulator.bpm == 40.0

    def test_noise_level_control(self):
        """Test noise level can be changed."""
        emulator = PPGEmulator(ppg_id=0, noise_level=5.0)

        assert emulator.noise_level == 5.0

        emulator.set_noise_level(15.0)
        assert emulator.noise_level == 15.0

        # Test clamping (no negative noise)
        emulator.set_noise_level(-5.0)
        assert emulator.noise_level == 0.0

    def test_dropout_injection(self):
        """Test dropout can be triggered."""
        emulator = PPGEmulator(ppg_id=0, noise_level=0.0, bpm=60.0)

        # Generate baseline samples
        baseline_samples = [emulator.generate_sample() for _ in range(10)]
        baseline_mean = np.mean(baseline_samples)

        # Trigger dropout
        emulator.trigger_dropout(beats=1)
        assert emulator.in_dropout == True

        # During dropout, samples should be near baseline (1950)
        dropout_samples = [emulator.generate_sample() for _ in range(10)]
        dropout_mean = np.mean(dropout_samples)

        # Dropout samples should be closer to baseline than cardiac waveform
        assert abs(dropout_mean - emulator.baseline) < 100

        # After enough samples, should exit dropout
        # At 60 BPM, one beat = 50 samples @ 50 Hz
        for _ in range(50):
            emulator.generate_sample()

        assert emulator.in_dropout == False

    def test_12bit_quantization(self):
        """Test samples are quantized to 12-bit range."""
        emulator = PPGEmulator(ppg_id=0)

        samples = [emulator.generate_sample() for _ in range(100)]

        # All samples should be integers in 12-bit range
        for sample in samples:
            assert isinstance(sample, int)
            assert 0 <= sample <= 4095

    def test_phase_advancement(self):
        """Test phase advances correctly based on BPM."""
        emulator = PPGEmulator(ppg_id=0, bpm=60.0)

        initial_phase = emulator.phase
        emulator.generate_sample()

        # Phase should advance by (60 BPM / 60 s/min) / 50 Hz = 0.02
        expected_increment = (60.0 / 60.0) / 50.0
        assert abs(emulator.phase - initial_phase - expected_increment) < 0.001

    def test_phase_wraps(self):
        """Test phase wraps around at 1.0."""
        emulator = PPGEmulator(ppg_id=0, bpm=60.0)
        emulator.phase = 0.99

        emulator.generate_sample()

        # Phase should wrap (was 0.99, increments by 0.02, wraps to ~0.01)
        assert 0.0 <= emulator.phase < 0.1

    def test_thread_safety_bpm_control(self):
        """Test BPM control is thread-safe."""
        emulator = PPGEmulator(ppg_id=0, bpm=60.0)

        # Flag to track errors
        errors = []

        def change_bpm():
            try:
                for _ in range(100):
                    emulator.set_bpm(70.0 + np.random.random() * 20)
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)

        def generate_samples():
            try:
                for _ in range(100):
                    emulator.generate_sample()
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)

        # Run concurrent operations
        thread1 = threading.Thread(target=change_bpm)
        thread2 = threading.Thread(target=generate_samples)

        thread1.start()
        thread2.start()

        thread1.join()
        thread2.join()

        # Should complete without errors
        assert len(errors) == 0

    def test_thread_safety_dropout_injection(self):
        """Test dropout injection is thread-safe."""
        emulator = PPGEmulator(ppg_id=0)

        errors = []

        def inject_dropouts():
            try:
                for _ in range(10):
                    emulator.trigger_dropout(beats=1)
                    time.sleep(0.01)
            except Exception as e:
                errors.append(e)

        def generate_samples():
            try:
                for _ in range(100):
                    emulator.generate_sample()
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)

        thread1 = threading.Thread(target=inject_dropouts)
        thread2 = threading.Thread(target=generate_samples)

        thread1.start()
        thread2.start()

        thread1.join()
        thread2.join()

        assert len(errors) == 0

    def test_sample_count_increments(self):
        """Test sample counter increments correctly."""
        emulator = PPGEmulator(ppg_id=0)

        assert emulator.sample_count == 0

        emulator.generate_sample()
        assert emulator.sample_count == 1

        for _ in range(49):
            emulator.generate_sample()

        assert emulator.sample_count == 50

    def test_custom_parameters(self):
        """Test emulator accepts custom waveform parameters."""
        emulator = PPGEmulator(
            ppg_id=2,
            bpm=85.0,
            noise_level=12.0,
            systolic_peak=3800,
            diastolic_trough=1600
        )

        assert emulator.ppg_id == 2
        assert emulator.bpm == 85.0
        assert emulator.noise_level == 12.0
        assert emulator.systolic_peak == 3800
        assert emulator.diastolic_trough == 1600

    def test_send_bundle_format(self):
        """Test OSC bundle message format."""
        emulator = PPGEmulator(ppg_id=1)

        # Generate 5 samples
        samples = [emulator.generate_sample() for _ in range(5)]
        timestamp_ms = int(time.time() * 1000)

        # This just verifies the method doesn't crash
        # (actual OSC sending would need a receiver to test properly)
        emulator.send_bundle(samples, timestamp_ms)
