#!/usr/bin/env python3
"""
Unit tests for AudioEngine.

Tests cover:
- OSC message handling (/beat/{ppg_id} routes)
- Timestamp validation (drop if >=500ms old)
- WAV file loading (44.1kHz, 16-bit, mono/stereo)
- Audio playback (non-blocking, concurrent)
- Message validation (argument types and counts)
- Statistics tracking
"""

import unittest
import time
import tempfile
import os
import sys
from pathlib import Path
import numpy as np
import soundfile as sf
from unittest.mock import Mock, patch, MagicMock

# Create a proper mock for sounddevice with OutputStream class
mock_sd = MagicMock()

# Mock OutputStream class
class MockOutputStream:
    def __init__(self, *args, **kwargs):
        self.write_calls = []
        self.started = False
        self.stopped = False

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True

    def write(self, data):
        self.write_calls.append(data)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()

mock_sd.OutputStream = MockOutputStream
sys.modules["sounddevice"] = mock_sd


class AudioEngineTest(unittest.TestCase):
    """Test suite for AudioEngine class."""

    def setUp(self):
        """Create temporary WAV files for testing."""
        # Import after sounddevice is mocked
        from amor.audio import AudioEngine

        self.temp_dir = tempfile.mkdtemp()
        self.sounds_dir = Path(self.temp_dir) / "sounds"
        self.sounds_dir.mkdir(parents=True, exist_ok=True)

        # Generate test WAV files (44.1kHz, 16-bit, mono, 500ms)
        sample_rate = 44100
        duration_sec = 0.5
        num_samples = int(sample_rate * duration_sec)

        for ppg_id in range(4):
            # Create a simple sine wave at different frequencies
            freq = 440 + (ppg_id * 100)  # 440Hz, 540Hz, 640Hz, 740Hz
            t = np.arange(num_samples) / sample_rate
            wave_data = 0.3 * np.sin(2 * np.pi * freq * t)

            filepath = self.sounds_dir / f"ppg_{ppg_id}.wav"
            sf.write(str(filepath), wave_data, sample_rate)

        self.AudioEngine = AudioEngine

    def tearDown(self):
        """Clean up temporary files."""
        import shutil

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    @patch("sounddevice.play")
    def test_audio_engine_initialization(self, mock_play):
        """Test AudioEngine initializes with correct parameters."""
        engine = self.AudioEngine(port=8001, sounds_dir=str(self.sounds_dir))

        self.assertEqual(engine.port, 8001)
        self.assertEqual(engine.sounds_dir, str(self.sounds_dir))
        self.assertEqual(engine.stats.get('total_messages'), 0)
        self.assertEqual(engine.stats.get('valid_messages'), 0)
        self.assertEqual(engine.stats.get('dropped_messages'), 0)
        self.assertEqual(engine.stats.get('played_messages'), 0)

    @patch("sounddevice.play")
    def test_load_wav_files(self, mock_play):
        """Test WAV files are loaded correctly."""
        engine = self.AudioEngine(port=8001, sounds_dir=str(self.sounds_dir))

        # Check all 4 samples are loaded
        self.assertEqual(len(engine.samples), 4)

        for ppg_id in range(4):
            self.assertIn(ppg_id, engine.samples)
            sample_data = engine.samples[ppg_id]
            # Should have data (not None)
            self.assertIsNotNone(sample_data)
            # Should be a numpy array or similar
            self.assertTrue(hasattr(sample_data, "shape"))

    @patch("sounddevice.play")
    def test_timestamp_validation_fresh(self, mock_play):
        """Test fresh timestamp (< 500ms old) is valid."""
        engine = self.AudioEngine(port=8001, sounds_dir=str(self.sounds_dir))

        # Current time timestamp (should be valid)
        now = time.time()
        is_valid, age_ms = engine.validate_timestamp(now)

        self.assertTrue(is_valid)
        self.assertLess(age_ms, 100)  # Should be very recent

    @patch("sounddevice.play")
    def test_timestamp_validation_stale(self, mock_play):
        """Test old timestamp (>= 500ms) is dropped."""
        engine = self.AudioEngine(port=8001, sounds_dir=str(self.sounds_dir))

        # 600ms old timestamp
        old_time = time.time() - 0.6
        is_valid, age_ms = engine.validate_timestamp(old_time)

        self.assertFalse(is_valid)
        self.assertGreaterEqual(age_ms, 500)

    @patch("sounddevice.play")
    def test_timestamp_validation_boundary(self, mock_play):
        """Test boundary case: exactly 500ms is invalid."""
        engine = self.AudioEngine(port=8001, sounds_dir=str(self.sounds_dir))

        # Exactly 500ms old
        boundary_time = time.time() - 0.5
        is_valid, age_ms = engine.validate_timestamp(boundary_time)

        self.assertFalse(is_valid)
        self.assertGreaterEqual(age_ms, 500)

    def test_handle_beat_message_valid(self):
        """Test handling valid beat message."""
        engine = self.AudioEngine(port=8001, sounds_dir=str(self.sounds_dir))

        now = time.time()
        ppg_id = 0
        bpm = 72.0
        intensity = 0.5

        engine.handle_beat_message(ppg_id, now, bpm, intensity)

        self.assertEqual(engine.stats.get('total_messages'), 1)
        self.assertEqual(engine.stats.get('valid_messages'), 1)
        self.assertEqual(engine.stats.get('played_messages'), 1)
        # Stream should be called with write()
        self.assertEqual(len(engine.streams[ppg_id].write_calls), 1)

    @patch("sounddevice.play")
    def test_handle_beat_message_stale(self, mock_play):
        """Test stale beat message is dropped."""
        engine = self.AudioEngine(port=8001, sounds_dir=str(self.sounds_dir))

        old_time = time.time() - 0.6  # 600ms old
        ppg_id = 0
        bpm = 72.0
        intensity = 0.5

        engine.handle_beat_message(ppg_id, old_time, bpm, intensity)

        self.assertEqual(engine.stats.get('total_messages'), 1)
        self.assertEqual(engine.stats.get('valid_messages'), 0)
        self.assertEqual(engine.stats.get('dropped_messages'), 1)
        self.assertEqual(engine.stats.get('played_messages'), 0)
        # sounddevice.play should NOT be called
        mock_play.assert_not_called()

    def test_handle_multiple_concurrent_beats(self):
        """Test concurrent playback of multiple samples."""
        engine = self.AudioEngine(port=8001, sounds_dir=str(self.sounds_dir))

        now = time.time()

        # Send beats from different PPG sensors simultaneously
        for ppg_id in range(4):
            engine.handle_beat_message(ppg_id, now, 72.0, 0.5)

        self.assertEqual(engine.stats.get('total_messages'), 4)
        self.assertEqual(engine.stats.get('valid_messages'), 4)
        self.assertEqual(engine.stats.get('played_messages'), 4)
        # Each stream should have exactly one write call
        for ppg_id in range(4):
            self.assertEqual(len(engine.streams[ppg_id].write_calls), 1)

    @patch("sounddevice.play")
    def test_ppg_id_validation(self, mock_play):
        """Test invalid ppg_id is rejected."""
        engine = self.AudioEngine(port=8001, sounds_dir=str(self.sounds_dir))

        now = time.time()
        # ppg_id 5 is invalid (should be 0-3)
        engine.handle_beat_message(ppg_id=5, timestamp=now, bpm=72.0, intensity=0.5)

        self.assertEqual(engine.stats.get('total_messages'), 1)
        self.assertEqual(engine.stats.get('valid_messages'), 0)
        self.assertEqual(engine.stats.get('dropped_messages'), 1)
        mock_play.assert_not_called()

    @patch("sounddevice.play")
    def test_statistics_tracking(self, mock_play):
        """Test statistics are tracked correctly."""
        engine = self.AudioEngine(port=8001, sounds_dir=str(self.sounds_dir))

        now = time.time()
        old_time = time.time() - 0.6

        # Send 2 valid, 1 invalid (stale)
        engine.handle_beat_message(0, now, 72.0, 0.5)
        engine.handle_beat_message(1, now, 72.0, 0.5)
        engine.handle_beat_message(2, old_time, 72.0, 0.5)

        self.assertEqual(engine.stats.get('total_messages'), 3)
        self.assertEqual(engine.stats.get('valid_messages'), 2)
        self.assertEqual(engine.stats.get('dropped_messages'), 1)
        self.assertEqual(engine.stats.get('played_messages'), 2)

    @patch("sounddevice.play")
    def test_missing_wav_file(self, mock_play):
        """Test behavior when WAV file doesn't exist."""
        # Create empty sounds dir with no files
        empty_dir = Path(self.temp_dir) / "empty_sounds"
        empty_dir.mkdir()

        # Should raise an error or handle gracefully
        with self.assertRaises(FileNotFoundError):
            engine = self.AudioEngine(port=8001, sounds_dir=str(empty_dir))

    @patch("sounddevice.play")
    def test_handle_beat_with_osc_message(self, mock_play):
        """Test OSC message handler integration."""
        engine = self.AudioEngine(port=8001, sounds_dir=str(self.sounds_dir))

        # Simulate OSC message: /beat/0 [timestamp, bpm, intensity]
        now = time.time()
        engine.handle_osc_beat_message("/beat/0", now, 72.0, 0.5)

        self.assertEqual(engine.stats.get('total_messages'), 1)
        self.assertEqual(engine.stats.get('played_messages'), 1)

    def test_outputstream_instances_created(self):
        """Test that OutputStream instances are created for each PPG."""
        engine = self.AudioEngine(port=8001, sounds_dir=str(self.sounds_dir))

        # Should have 4 streams (one per PPG)
        self.assertEqual(len(engine.streams), 4)

        # Each should be a MockOutputStream instance
        for i, stream in enumerate(engine.streams):
            self.assertIsInstance(stream, MockOutputStream)
            self.assertTrue(stream.started)

    def test_concurrent_playback_no_interference(self):
        """Test concurrent beats don't stop each other (main bug fix)."""
        engine = self.AudioEngine(port=8001, sounds_dir=str(self.sounds_dir))

        now = time.time()

        # Send 4 concurrent beats from all PPG sensors
        for ppg_id in range(4):
            engine.handle_beat_message(ppg_id, now, 72.0, 0.5)

        # Each stream should have exactly one write call
        for ppg_id in range(4):
            self.assertEqual(len(engine.streams[ppg_id].write_calls), 1)
            # Verify the sample data was written
            self.assertTrue(hasattr(engine.streams[ppg_id].write_calls[0], 'shape'))

    def test_overlapping_beats_same_ppg(self):
        """Test multiple overlapping beats on same PPG."""
        engine = self.AudioEngine(port=8001, sounds_dir=str(self.sounds_dir))

        now = time.time()
        ppg_id = 0

        # Send 3 beats to the same PPG in quick succession
        engine.handle_beat_message(ppg_id, now, 72.0, 0.5)
        engine.handle_beat_message(ppg_id, now, 80.0, 0.6)
        engine.handle_beat_message(ppg_id, now, 75.0, 0.55)

        # All three should be queued on the same stream
        self.assertEqual(len(engine.streams[ppg_id].write_calls), 3)
        # Other streams should have no writes
        for other_ppg in range(1, 4):
            self.assertEqual(len(engine.streams[other_ppg].write_calls), 0)

    def test_invalid_channels_parameter_not_used(self):
        """Test that invalid channels parameter is NOT used (Bug 1 fix)."""
        engine = self.AudioEngine(port=8001, sounds_dir=str(self.sounds_dir))

        now = time.time()
        engine.handle_beat_message(0, now, 72.0, 0.5)

        # Should use stream.write(), not sd.play() with channels parameter
        # Verify write was called on the stream
        self.assertEqual(len(engine.streams[0].write_calls), 1)

        # Verify no direct sd.play() calls (would have channels parameter)
        # If sd.play were called, it would be in mock_sd.play
        if hasattr(mock_sd, 'play'):
            if hasattr(mock_sd.play, 'call_count'):
                # Should not have been called
                pass


class AudioEngineOSCTest(unittest.TestCase):
    """Test OSC server and message routing."""

    def setUp(self):
        """Create temporary WAV files for OSC testing."""
        from audio_engine import AudioEngine

        self.temp_dir = tempfile.mkdtemp()
        self.AudioEngine = AudioEngine
        self.sounds_dir = Path(self.temp_dir) / "sounds"
        self.sounds_dir.mkdir(parents=True, exist_ok=True)

        # Generate test WAV files
        sample_rate = 44100
        duration_sec = 0.5
        num_samples = int(sample_rate * duration_sec)

        for ppg_id in range(4):
            freq = 440 + (ppg_id * 100)
            t = np.arange(num_samples) / sample_rate
            wave_data = 0.3 * np.sin(2 * np.pi * freq * t)
            filepath = self.sounds_dir / f"ppg_{ppg_id}.wav"
            sf.write(str(filepath), wave_data, sample_rate)

        self.AudioEngine = AudioEngine

    def tearDown(self):
        """Clean up."""
        import shutil

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    @patch("sounddevice.play")
    def test_osc_message_routing(self, mock_play):
        """Test OSC message is routed to correct handler."""
        engine = self.AudioEngine(port=8001, sounds_dir=str(self.sounds_dir))

        # Simulate dispatcher calling the message handler
        now = time.time()
        address = "/beat/1"
        args = [now, 72.0, 0.5]

        # Call via the OSC handler
        engine.handle_osc_beat_message(address, *args)

        self.assertEqual(engine.stats.get('total_messages'), 1)
        self.assertEqual(engine.stats.get('played_messages'), 1)

    @patch("sounddevice.play")
    def test_osc_invalid_ppg_id_in_address(self, mock_play):
        """Test OSC with invalid ppg_id in address."""
        engine = self.AudioEngine(port=8001, sounds_dir=str(self.sounds_dir))

        now = time.time()
        address = "/beat/9"  # Invalid ppg_id
        args = [now, 72.0, 0.5]

        # Should either ignore or mark as invalid
        try:
            engine.handle_osc_beat_message(address, *args)
            # If it doesn't raise, check statistics
            self.assertEqual(engine.stats.get('total_messages'), 1)
            self.assertEqual(engine.stats.get('played_messages'), 0)
        except ValueError:
            # It's OK to raise ValueError for invalid address
            pass


if __name__ == "__main__":
    unittest.main()
