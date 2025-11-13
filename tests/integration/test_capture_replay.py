"""Integration tests for PPG Capture/Replay cycle.

Tests validate end-to-end data recording and playback pipeline:
1. Capture module records PPG data to binary files
2. Replay module reads binary files and replays data
3. Processor detects beats from replayed data
4. Binary file format compatibility and timing accuracy

Reference: docs/integration-test-ideas.md:45-50
"""

import time
import struct
import pytest
from pathlib import Path
from amor import osc
from tests.integration.utils import OSCMessageCapture


class TestCaptureRecording:
    """Test capture module records PPG data correctly."""

    def test_capture_creates_binary_file(self, temp_sampler_dir, component_manager):
        """Verify capture creates binary file with PPGL format."""
        capture_dir = temp_sampler_dir / "capture"
        capture_dir.mkdir(exist_ok=True)

        # Start PPG emulator and capture
        component_manager.add_ppg_emulator(ppg_id=0, bpm=75)
        component_manager.add_capture(ppg_id=0, output_dir=str(capture_dir))
        component_manager.start_all()

        # Let it record for 2 seconds
        time.sleep(2.0)

        # Stop capture cleanly
        component_manager.stop_all()

        # Verify file created
        files = list(capture_dir.glob("ppg_*.bin"))
        assert len(files) == 1, f"Expected 1 capture file, found {len(files)}"

        # Verify file has content
        capture_file = files[0]
        assert capture_file.stat().st_size > 8, "File should have header + records"

    def test_capture_records_multiple_messages(self, temp_sampler_dir, component_manager):
        """Verify capture records multiple PPG messages with correct format."""
        capture_dir = temp_sampler_dir / "capture"
        capture_dir.mkdir(exist_ok=True)

        # Start PPG emulator and capture
        component_manager.add_ppg_emulator(ppg_id=0, bpm=75)
        component_manager.add_capture(ppg_id=0, output_dir=str(capture_dir))
        component_manager.start_all()

        # Record for 3 seconds (should get ~30 records at 10Hz)
        time.sleep(3.0)
        component_manager.stop_all()

        # Read and validate file structure
        files = list(capture_dir.glob("ppg_*.bin"))
        assert len(files) == 1

        with open(files[0], 'rb') as f:
            # Validate header (8 bytes)
            header = f.read(8)
            assert len(header) == 8, "Header should be 8 bytes"

            magic, version, ppg_id, reserved = struct.unpack('<4sBBH', header)
            assert magic == b'PPGL', f"Invalid magic: {magic}"
            assert version == 1, f"Invalid version: {version}"
            assert ppg_id == 0, f"Invalid PPG ID: {ppg_id}"

            # Count records (24 bytes each)
            record_count = 0
            while True:
                record = f.read(24)
                if len(record) < 24:
                    break

                timestamp_ms, s0, s1, s2, s3, s4 = struct.unpack('<i5i', record)

                # Validate timestamp is positive
                assert timestamp_ms > 0, f"Invalid timestamp: {timestamp_ms}"

                # Validate samples are in 12-bit ADC range
                for sample in [s0, s1, s2, s3, s4]:
                    assert 0 <= sample <= 4095, \
                        f"Sample {sample} out of 12-bit ADC range (0-4095)"

                record_count += 1

            # Should have ~20-40 records (3s at 10Hz ±timing variance)
            assert 15 <= record_count <= 50, \
                f"Expected 15-50 records for 3s recording, got {record_count}"

    def test_capture_filters_correct_ppg_id(self, temp_sampler_dir, component_manager):
        """Verify capture only records specified PPG ID."""
        capture_dir = temp_sampler_dir / "capture"
        capture_dir.mkdir(exist_ok=True)

        # Start two PPG emulators but only capture PPG 1
        component_manager.add_ppg_emulator(ppg_id=0, bpm=75)
        component_manager.add_ppg_emulator(ppg_id=1, bpm=80)
        component_manager.add_capture(ppg_id=1, output_dir=str(capture_dir))
        component_manager.start_all()

        time.sleep(2.0)
        component_manager.stop_all()

        # Verify file has PPG ID 1 in header
        files = list(capture_dir.glob("ppg_*.bin"))
        assert len(files) == 1

        with open(files[0], 'rb') as f:
            header = f.read(8)
            magic, version, ppg_id, reserved = struct.unpack('<4sBBH', header)
            assert ppg_id == 1, f"Expected PPG ID 1, got {ppg_id}"


class TestReplayPlayback:
    """Test replay module plays back recorded data."""

    def test_replay_sends_ppg_messages(self, temp_sampler_dir, component_manager):
        """Verify replay sends PPG messages to port 8000."""
        capture_dir = temp_sampler_dir / "capture"
        capture_dir.mkdir(exist_ok=True)

        # Step 1: Capture some data
        component_manager.add_ppg_emulator(ppg_id=0, bpm=75)
        component_manager.add_capture(ppg_id=0, output_dir=str(capture_dir))
        component_manager.start_all()
        time.sleep(2.0)
        component_manager.stop_all()

        # Find captured file
        files = list(capture_dir.glob("ppg_*.bin"))
        assert len(files) == 1
        capture_file = files[0]

        # Step 2: Set up capture to monitor replayed messages
        ppg_capture = OSCMessageCapture(port=osc.PORT_PPG)
        ppg_capture.start()

        # Step 3: Replay the file
        component_manager.add_replay(log_file=str(capture_file), loop=False)
        component_manager.start_all()

        # Wait for first PPG message
        try:
            ts, addr, args = ppg_capture.wait_for_message("/ppg/0", timeout=3.0)

            # Validate message format
            assert addr == "/ppg/0"
            assert len(args) == 6, f"Expected 6 args (5 samples + timestamp), got {len(args)}"

            # Validate samples and timestamp
            samples = args[0:5]
            timestamp_ms = args[5]

            for sample in samples:
                assert 0 <= sample <= 4095, \
                    f"Sample {sample} out of 12-bit ADC range"

            assert timestamp_ms > 0, f"Invalid timestamp: {timestamp_ms}"

        finally:
            ppg_capture.stop()
            component_manager.stop_all()

    def test_replay_timing_preserves_rate(self, temp_sampler_dir, component_manager):
        """Verify replay sends messages at correct rate (~10Hz)."""
        capture_dir = temp_sampler_dir / "capture"
        capture_dir.mkdir(exist_ok=True)

        # Capture 3 seconds of data
        component_manager.add_ppg_emulator(ppg_id=0, bpm=75)
        component_manager.add_capture(ppg_id=0, output_dir=str(capture_dir))
        component_manager.start_all()
        time.sleep(3.0)
        component_manager.stop_all()

        files = list(capture_dir.glob("ppg_*.bin"))
        capture_file = files[0]

        # Monitor replay messages
        ppg_capture = OSCMessageCapture(port=osc.PORT_PPG)
        ppg_capture.start()

        try:
            component_manager.add_replay(log_file=str(capture_file), loop=False)
            component_manager.start_all()

            # Wait for replay to complete
            time.sleep(4.0)

            # Get all PPG messages
            messages = ppg_capture.get_messages_by_address("/ppg/0")

            # Should have ~20-40 messages (3s at 10Hz ±variance)
            assert len(messages) >= 15, \
                f"Expected at least 15 messages, got {len(messages)}"

        finally:
            ppg_capture.stop()
            component_manager.stop_all()


class TestCaptureReplayCycle:
    """Test end-to-end capture → replay → beat detection flow."""

    def test_replay_enables_beat_detection(self, temp_sampler_dir, component_manager, beat_capture):
        """Verify capture → replay → beat detection cycle works end-to-end."""
        capture_dir = temp_sampler_dir / "capture"
        capture_dir.mkdir(exist_ok=True)

        # Step 1: Capture PPG data
        component_manager.add_ppg_emulator(ppg_id=0, bpm=75)
        component_manager.add_capture(ppg_id=0, output_dir=str(capture_dir))
        component_manager.start_all()

        # Record for 10 seconds (enough for warmup + several beats)
        time.sleep(10.0)
        component_manager.stop_all()
        time.sleep(1.0)  # Extra wait for processes to fully terminate

        # Verify file created
        files = list(capture_dir.glob("ppg_*.bin"))
        assert len(files) == 1, f"Expected 1 capture file, found {len(files)}"
        capture_file = files[0]

        # Step 2: Replay captured data through processor
        beat_capture.clear()
        component_manager.clear()  # Clear old components to prevent restart
        component_manager.add_replay(log_file=str(capture_file), loop=False)
        component_manager.add_processor()
        component_manager.start_all()

        # Step 3: Validate beats detected from replayed data
        # Note: Need warmup time (2s) + time for first beat
        ts, addr, args = beat_capture.wait_for_message("/beat/0", timeout=12.0)

        assert addr == "/beat/0"
        assert len(args) == 3, f"Expected 3 args (timestamp, bpm, intensity), got {len(args)}"

        timestamp_ms, bpm, intensity = args

        # Validate timestamp is recent
        assert timestamp_ms > 0, f"Invalid timestamp: {timestamp_ms}"

        # Validate BPM is reasonable
        assert bpm > 0, f"BPM should be positive, got {bpm}"

        # Validate intensity
        assert 0.0 <= intensity <= 1.0, \
            f"Intensity should be 0-1, got {intensity}"

    def test_replay_preserves_bpm_accuracy(self, temp_sampler_dir, component_manager, beat_capture):
        """Verify replayed beats match original BPM (±15% tolerance)."""
        capture_dir = temp_sampler_dir / "capture"
        capture_dir.mkdir(exist_ok=True)

        # Capture data at known BPM
        target_bpm = 75
        component_manager.add_ppg_emulator(ppg_id=0, bpm=target_bpm)
        component_manager.add_capture(ppg_id=0, output_dir=str(capture_dir))
        component_manager.start_all()
        time.sleep(10.0)  # Longer recording for better BPM accuracy
        component_manager.stop_all()
        time.sleep(1.0)  # Extra wait for processes to fully terminate

        files = list(capture_dir.glob("ppg_*.bin"))
        capture_file = files[0]

        # Replay and measure BPM
        beat_capture.clear()
        component_manager.clear()  # Clear old components to prevent restart
        component_manager.add_replay(log_file=str(capture_file), loop=False)
        component_manager.add_processor()
        component_manager.start_all()

        # Wait for first beat
        beat_capture.wait_for_message("/beat/0", timeout=12.0)

        # Collect multiple beats for BPM averaging
        time.sleep(6.0)

        beats = beat_capture.get_messages_by_address("/beat/0")
        assert len(beats) >= 2, "Need at least 2 beats for BPM validation"

        # Extract BPM values
        bpm_values = [args[1] for ts, addr, args in beats]
        avg_bpm = sum(bpm_values) / len(bpm_values)

        # Validate BPM matches original (±15% tolerance from test_beat_flow.py pattern)
        min_bpm = target_bpm * 0.85
        max_bpm = target_bpm * 1.15

        assert min_bpm <= avg_bpm <= max_bpm, \
            f"Replayed BPM {avg_bpm:.1f} outside ±15% of original {target_bpm} BPM"

    def test_replay_beat_timing_consistency(self, temp_sampler_dir, component_manager, beat_capture):
        """Verify beat timing is consistent across replay."""
        capture_dir = temp_sampler_dir / "capture"
        capture_dir.mkdir(exist_ok=True)

        # Capture data
        component_manager.add_ppg_emulator(ppg_id=0, bpm=75)
        component_manager.add_capture(ppg_id=0, output_dir=str(capture_dir))
        component_manager.start_all()
        time.sleep(10.0)
        component_manager.stop_all()
        time.sleep(1.0)  # Extra wait for processes to fully terminate

        files = list(capture_dir.glob("ppg_*.bin"))
        capture_file = files[0]

        # Replay and monitor beats
        beat_capture.clear()
        component_manager.clear()  # Clear old components to prevent restart
        component_manager.add_replay(log_file=str(capture_file), loop=False)
        component_manager.add_processor()
        component_manager.start_all()

        # Wait for first beat
        beat_capture.wait_for_message("/beat/0", timeout=12.0)

        # Collect beats for several seconds
        time.sleep(6.0)

        beats = beat_capture.get_messages_by_address("/beat/0")
        assert len(beats) >= 3, "Need at least 3 beats for timing validation"

        # Calculate intervals between beats
        timestamps = [ts for ts, addr, args in beats]
        intervals = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps) - 1)]

        # At 75 BPM, interval should be ~0.8s
        # Verify intervals are reasonably consistent (within 50% variance)
        avg_interval = sum(intervals) / len(intervals)
        for interval in intervals:
            variance = abs(interval - avg_interval) / avg_interval
            assert variance < 0.5, \
                f"Beat interval {interval:.3f}s varies >50% from average {avg_interval:.3f}s"


class TestBinaryFormatCompatibility:
    """Test binary file format compatibility between capture and replay."""

    def test_capture_replay_format_compatibility(self, temp_sampler_dir, component_manager):
        """Verify capture and replay use compatible PPGL formats."""
        capture_dir = temp_sampler_dir / "capture"
        capture_dir.mkdir(exist_ok=True)

        # Capture data
        component_manager.add_ppg_emulator(ppg_id=2, bpm=80)
        component_manager.add_capture(ppg_id=2, output_dir=str(capture_dir))
        component_manager.start_all()
        time.sleep(2.0)
        component_manager.stop_all()
        time.sleep(1.0)  # Extra wait for processes to fully terminate

        files = list(capture_dir.glob("ppg_*.bin"))
        capture_file = files[0]

        # Verify file format manually
        with open(capture_file, 'rb') as f:
            # Header validation
            header = f.read(8)
            magic, version, ppg_id, reserved = struct.unpack('<4sBBH', header)

            assert magic == b'PPGL', "Invalid PPGL magic"
            assert version == 1, "Invalid version"
            assert ppg_id == 2, "PPG ID mismatch"

            # First record validation
            record = f.read(24)
            assert len(record) == 24, "Record size mismatch"

            timestamp_ms, s0, s1, s2, s3, s4 = struct.unpack('<i5i', record)
            assert timestamp_ms > 0, "Invalid timestamp"

            # Store first record for later comparison
            first_record = (timestamp_ms, s0, s1, s2, s3, s4)

        # Now replay and capture the first message
        ppg_capture = OSCMessageCapture(port=osc.PORT_PPG)
        ppg_capture.start()

        try:
            component_manager.clear()  # Clear old components to prevent restart
            component_manager.add_replay(log_file=str(capture_file), loop=False)
            component_manager.start_all()

            # Wait for replay to send messages
            time.sleep(0.5)

            # Get all captured messages and find messages from the replay
            # Replay messages should have timestamps from the file (< 10 seconds)
            all_messages = ppg_capture.get_messages_by_address("/ppg/2")
            assert len(all_messages) > 0, "No /ppg/2 messages captured"

            # Filter for messages with timestamps in expected range (< 10 seconds)
            # File timestamps start around 480ms and go up to ~2000ms
            # This filters out any stray messages from other processes/tests
            replay_messages = [(ts, addr, args) for ts, addr, args in all_messages
                             if len(args) >= 6 and args[5] < 10000]

            assert len(replay_messages) > 0, f"No replay messages found (captured {len(all_messages)} messages, none from replay)"

            # Use the first replay message
            ts, addr, args = replay_messages[0]

            # Verify replayed message matches binary file
            assert addr == "/ppg/2"
            assert len(args) == 6

            replayed_samples = args[0:5]
            replayed_timestamp = args[5]

            # Compare with first record from file
            timestamp_ms, s0, s1, s2, s3, s4 = first_record

            assert replayed_timestamp == timestamp_ms, \
                f"Timestamp mismatch: file={timestamp_ms}, replayed={replayed_timestamp}"

            for i, sample in enumerate([s0, s1, s2, s3, s4]):
                assert replayed_samples[i] == sample, \
                    f"Sample {i} mismatch: file={sample}, replayed={replayed_samples[i]}"

        finally:
            ppg_capture.stop()
            component_manager.stop_all()

    def test_binary_format_structure_validation(self, temp_sampler_dir, component_manager):
        """Verify captured binary file has correct PPGL structure."""
        capture_dir = temp_sampler_dir / "capture"
        capture_dir.mkdir(exist_ok=True)

        # Capture data
        component_manager.add_ppg_emulator(ppg_id=0, bpm=75)
        component_manager.add_capture(ppg_id=0, output_dir=str(capture_dir))
        component_manager.start_all()
        time.sleep(3.0)  # Ensure enough time to capture data
        component_manager.stop_all()

        files = list(capture_dir.glob("ppg_*.bin"))
        assert len(files) == 1

        # Validate complete file structure
        with open(files[0], 'rb') as f:
            # Header
            header = f.read(8)
            assert len(header) == 8, "Header must be exactly 8 bytes"

            magic, version, ppg_id, reserved = struct.unpack('<4sBBH', header)
            assert magic == b'PPGL', f"Magic must be b'PPGL', got {magic}"
            assert version == 1, f"Version must be 1, got {version}"
            assert ppg_id == 0, f"PPG ID must be 0, got {ppg_id}"
            assert reserved == 0, f"Reserved must be 0, got {reserved}"

            # Records - all must be exactly 24 bytes
            record_count = 0
            while True:
                record = f.read(24)
                if len(record) == 0:
                    break  # End of file

                assert len(record) == 24, \
                    f"Record {record_count} must be 24 bytes, got {len(record)}"

                timestamp_ms, s0, s1, s2, s3, s4 = struct.unpack('<i5i', record)

                # Validate all fields
                assert timestamp_ms > 0, f"Record {record_count}: invalid timestamp"

                for i, sample in enumerate([s0, s1, s2, s3, s4]):
                    assert 0 <= sample <= 4095, \
                        f"Record {record_count}, sample {i}: {sample} out of range"

                record_count += 1

            assert record_count > 0, "File must contain at least one record"
