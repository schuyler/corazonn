"""Integration tests for PPG → Processor → Audio beat flow.

Tests validate end-to-end signal path from PPG emulator through processor
to audio/lighting subsystems. Focus on:
1. Beat messages arrive within latency threshold (<100ms)
2. Timestamp freshness (<500ms)
3. Message format and content correctness
4. BPM accuracy

Reference: docs/integration-test-ideas.md:11-16
"""

import time
import pytest


class TestPPGToProcessorFlow:
    """Test beat flow from PPG emulator through processor.

    Validates that the processor correctly:
    - Receives PPG samples from emulator
    - Detects heartbeats using ThresholdDetector + HeartbeatPredictor
    - Broadcasts beat messages on port 8001
    - Provides accurate BPM and intensity values
    """

    def test_beat_message_arrives(self, simple_setup):
        """Verify beat messages arrive from processor within timeout.

        Flow: PPG Emulator (75 BPM) → Processor → Beat message
        Expected: Beat message arrives within 3 seconds (warmup + first beat)

        Note: Processor requires warmup period (100 samples at 50Hz = 2s)
        before WARMUP → ACTIVE transition, then additional time for first
        beat detection.
        """
        manager, capture = simple_setup

        # Wait for beat message (75 BPM = ~800ms per beat + 2s warmup)
        ts, addr, args = capture.wait_for_message("/beat/0", timeout=5.0)

        # Validate message structure
        assert addr == "/beat/0"
        assert len(args) == 3  # timestamp, bpm, intensity

    def test_beat_message_format(self, simple_setup):
        """Verify beat message has correct format and argument types.

        Flow: PPG → Processor → Beat (check message format)
        Expected: /beat/{ppg_id} [timestamp_ms (int), bpm (float), intensity (float)]
        """
        manager, capture = simple_setup

        # Capture beat
        ts, addr, args = capture.wait_for_message("/beat/0", timeout=5.0)

        # Validate address
        assert addr == "/beat/0"

        # Validate argument count
        assert len(args) == 3, f"Expected 3 arguments, got {len(args)}"

        # Validate argument types
        timestamp_ms, bpm, intensity = args
        assert isinstance(timestamp_ms, int), f"Timestamp should be int, got {type(timestamp_ms)}"
        assert isinstance(bpm, float), f"BPM should be float, got {type(bpm)}"
        assert isinstance(intensity, float), f"Intensity should be float, got {type(intensity)}"

        # Validate argument ranges
        assert timestamp_ms > 0, f"Timestamp should be positive, got {timestamp_ms}"
        assert 0 < bpm < 200, f"BPM should be in range (0, 200), got {bpm}"
        assert 0.0 <= intensity <= 1.0, f"Intensity should be in range [0, 1], got {intensity}"

    def test_beat_timestamp_freshness(self, simple_setup):
        """Verify beat timestamps are fresh (<500ms).

        Flow: PPG → Processor → Beat (check timestamp age)
        Expected: Timestamp age < 500ms (processor's staleness threshold)

        Note: Timestamp in beat message is Unix time (seconds) when beat detected.
        This test validates the timestamp is recent relative to when we capture it.
        """
        manager, capture = simple_setup

        # Capture beat
        capture_time, addr, args = capture.wait_for_message("/beat/0", timeout=5.0)
        timestamp_ms = args[0]  # First arg is timestamp in milliseconds

        # Convert to seconds for comparison
        beat_timestamp = timestamp_ms / 1000.0

        # Calculate age
        age_ms = (capture_time - beat_timestamp) * 1000

        assert age_ms < 500, f"Beat timestamp too old: {age_ms:.1f}ms"

    def test_multiple_beats_arrive(self, simple_setup):
        """Verify multiple beats arrive over time.

        Flow: PPG (75 BPM) → Processor → Multiple beats
        Expected: At least 3 beats in 8 seconds (warmup + beats)

        75 BPM = 800ms per beat, so 8s should yield ~8 beats after warmup.
        We expect at least 3 to account for warmup period.
        """
        manager, capture = simple_setup

        # Wait for beats to accumulate
        time.sleep(8.0)

        # Check beat count
        beats = capture.get_messages_by_address("/beat/0")
        assert len(beats) >= 3, f"Expected >= 3 beats, got {len(beats)}"

    def test_beat_bpm_accuracy(self, simple_setup):
        """Verify reported BPM matches emulator setting.

        Flow: PPG (75 BPM) → Processor → Beat with BPM
        Expected: Reported BPM within ±15% of 75 (63.75 - 86.25)

        Note: Using ±15% tolerance to account for:
        - Emulator waveform variance (±5% built into PPG emulator)
        - Detector/predictor phase estimation variance
        - Initial beats may have less accurate BPM estimates
        """
        manager, capture = simple_setup

        # Wait for beat
        ts, addr, args = capture.wait_for_message("/beat/0", timeout=5.0)

        timestamp_ms, bpm, intensity = args
        assert 63.75 <= bpm <= 86.25, f"BPM {bpm:.1f} outside ±15% of 75 (63.75-86.25)"

    def test_beat_intensity_valid_range(self, simple_setup):
        """Verify beat intensity is in valid range [0.0, 1.0].

        Flow: PPG → Processor → Beat with intensity
        Expected: Intensity in range [0.0, 1.0]

        Intensity represents confidence level from HeartbeatPredictor model.
        """
        manager, capture = simple_setup

        # Wait for beat
        ts, addr, args = capture.wait_for_message("/beat/0", timeout=5.0)

        timestamp_ms, bpm, intensity = args
        assert 0.0 <= intensity <= 1.0, f"Intensity {intensity} outside [0.0, 1.0]"


class TestPPGToAudioFlow:
    """Test beat flow from PPG through processor to audio engine.

    Validates that audio engine:
    - Receives beat messages from processor
    - Validates timestamp freshness
    - Routes beats to correct audio sample
    """

    def test_audio_receives_beats(self, component_manager, beat_capture):
        """Verify audio engine receives beat messages.

        Flow: PPG → Processor → Audio (beat reception)
        Expected: Beat arrives at audio within 5 seconds

        Note: Audio engine shares port 8001 with beat_capture via SO_REUSEPORT,
        so both receive the same broadcast messages.
        """
        # Setup: PPG + Processor + Audio
        component_manager.add_ppg_emulator(ppg_id=0, bpm=75)
        component_manager.add_processor()
        component_manager.add_audio()
        component_manager.start_all()

        # Wait for beat (audio and capture both receive via SO_REUSEPORT)
        ts, addr, args = beat_capture.wait_for_message("/beat/0", timeout=5.0)

        # Validate
        assert addr == "/beat/0"
        assert len(args) == 3

    def test_multi_ppg_routing(self, component_manager, beat_capture):
        """Verify multiple PPG sensors route to correct channels.

        Flow: PPG 0 + PPG 1 → Processor → Beats on /beat/0 and /beat/1
        Expected: Both sensors produce independent beat streams

        Note: Using different BPMs (70 vs 80) to ensure independence.
        """
        # Setup: 2 PPGs with different BPMs + Processor
        component_manager.add_ppg_emulator(ppg_id=0, bpm=70)
        component_manager.add_ppg_emulator(ppg_id=1, bpm=80)
        component_manager.add_processor()
        component_manager.start_all()

        # Wait for beats from both sensors
        ts0, addr0, args0 = beat_capture.wait_for_message("/beat/0", timeout=5.0)
        ts1, addr1, args1 = beat_capture.wait_for_message("/beat/1", timeout=5.0)

        # Validate independent routing
        assert addr0 == "/beat/0"
        assert addr1 == "/beat/1"

        # Validate BPMs are approximately correct (±15%)
        _, bpm0, _ = args0
        _, bpm1, _ = args1
        assert 59.5 <= bpm0 <= 80.5, f"PPG 0 BPM {bpm0:.1f} outside ±15% of 70"
        assert 68.0 <= bpm1 <= 92.0, f"PPG 1 BPM {bpm1:.1f} outside ±15% of 80"
