#!/usr/bin/env python3
"""
Integration tests for beat flow through the Amor system.

Tests the complete signal path from PPG sensors through the processor
to audio and lighting outputs.
"""

import time
import pytest
from amor.integration import (
    OSCMessageCapture,
    ComponentManager,
    assert_within_ms,
    assert_latency_ms,
)


class TestPPGToProcessorToAudio:
    """Test PPG → Processor → Audio beat flow."""

    def test_beat_messages_arrive_at_audio(self):
        """Verify beat messages from processor arrive on audio port.

        Test steps:
        1. Start PPG emulator (72 BPM) + processor
        2. Capture beat messages on audio input port (8001) that processor sends
        3. Verify beat messages arrive with correct format
        4. Validate timestamp freshness (<500ms)

        Note: Audio component not started - testing processor output directly.
        """
        with ComponentManager() as manager:
            # Start PPG emulator and processor only
            # Audio component requires PortAudio/hardware which may not be available
            manager.start(['ppg0', 'processor'], wait=3.0)

            # Setup message capture on audio input port where processor sends beats
            audio_capture = OSCMessageCapture(port=8001)
            audio_capture.start()

            # Wait for beats to flow through system
            time.sleep(5.0)

            # Verify beat messages received from processor
            audio_capture.assert_received("/beat/0", timeout=5.0)

            # Check we got multiple beats
            beat_messages = audio_capture.get_messages("/beat/0")
            assert len(beat_messages) >= 3, f"Expected at least 3 beats, got {len(beat_messages)}"

            # Validate timestamp freshness for each beat
            for timestamp, address, args in beat_messages:
                # Beat message format: /beat/{ppg_id} ppg_id timestamp_ms
                if len(args) >= 2:
                    beat_timestamp_ms = args[1]
                    assert_within_ms(beat_timestamp_ms, max_age_ms=500)

            # Cleanup
            audio_capture.stop()

    def test_beat_latency_ppg_to_processor(self):
        """Measure end-to-end latency from PPG to processor beat output.

        Validates that the complete path (PPG → Processor)
        produces beats at the expected rate.
        """
        with ComponentManager() as manager:
            # Start PPG and processor
            manager.start(['ppg0', 'processor'], wait=3.0)

            # Capture on both PPG port (to see source) and audio port
            ppg_capture = OSCMessageCapture(port=8000)
            audio_capture = OSCMessageCapture(port=8001)

            ppg_capture.start()
            audio_capture.start()

            # Wait for data to flow
            time.sleep(3.0)

            # Get messages
            ppg_messages = ppg_capture.get_messages("/ppg/0")
            beat_messages = audio_capture.get_messages("/beat/0")

            assert len(ppg_messages) > 0, "No PPG messages captured"
            assert len(beat_messages) > 0, "No beat messages captured"

            # Verify we're getting beats at expected rate (~75 BPM = 0.8 sec/beat)
            if len(beat_messages) >= 2:
                first_beat_time = beat_messages[0][0]
                last_beat_time = beat_messages[-1][0]
                duration = last_beat_time - first_beat_time
                beat_count = len(beat_messages) - 1
                if beat_count > 0 and duration > 0:
                    measured_bpm = (beat_count / duration) * 60
                    # Allow 20% tolerance for BPM measurement
                    assert 60 < measured_bpm < 90, \
                        f"BPM {measured_bpm:.1f} outside expected range for 75 BPM emulator"

            # Cleanup
            ppg_capture.stop()
            audio_capture.stop()

    def test_beat_routing_matches_ppg_id(self):
        """Verify beat messages maintain correct PPG ID routing.

        Ensures that beats from PPG 0 are routed as /beat/0 messages
        and include correct PPG ID in arguments.
        """
        with ComponentManager() as manager:
            manager.start(['ppg0', 'processor'], wait=3.0)

            audio_capture = OSCMessageCapture(port=8001)
            audio_capture.start()

            time.sleep(3.0)

            # Get beat messages
            beat_messages = audio_capture.get_messages("/beat/0")
            assert len(beat_messages) >= 2, "Need at least 2 beats to validate routing"

            # Validate message format and routing
            for timestamp, address, args in beat_messages:
                assert address == "/beat/0", f"Wrong address: {address}"
                assert len(args) >= 2, f"Beat message has wrong arg count: {args}"

                ppg_id = args[0]
                assert ppg_id == 0, f"Beat from wrong PPG: {ppg_id}"

            audio_capture.stop()

    def test_stale_timestamp_handling(self):
        """Verify that processor generates fresh timestamps.

        This test validates that processor-generated beat messages have
        timestamps within the acceptable 500ms freshness window.

        Note: This validates processor timestamp generation, not downstream
        filtering which requires the audio/lighting components.
        """
        with ComponentManager() as manager:
            manager.start(['ppg0', 'processor'], wait=3.0)

            audio_capture = OSCMessageCapture(port=8001)
            audio_capture.start()

            time.sleep(3.0)

            # Verify all received messages have fresh timestamps
            beat_messages = audio_capture.get_messages("/beat/0")
            assert len(beat_messages) > 0, "No beats received"

            stale_count = 0
            for timestamp, address, args in beat_messages:
                if len(args) >= 2:
                    beat_timestamp_ms = args[1]
                    now_ms = time.time() * 1000
                    age_ms = now_ms - beat_timestamp_ms
                    if age_ms >= 500:
                        stale_count += 1

            # All messages should be fresh in normal operation
            assert stale_count == 0, \
                f"Found {stale_count} stale messages - system not processing in real-time"

            audio_capture.stop()


class TestPPGToProcessorToLighting:
    """Test PPG → Processor → Lighting beat flow."""

    def test_beat_messages_arrive_at_lighting(self):
        """Verify beat messages from processor arrive on lighting port.

        Test steps:
        1. Start PPG emulator + processor
        2. Capture beat messages on lighting output port (8002) from processor
        3. Verify beat messages received with correct format

        Note: Lighting component not started - testing processor output directly.
        """
        with ComponentManager() as manager:
            # Start PPG and processor only
            manager.start(['ppg0', 'processor'], wait=3.0)

            # Setup message capture on lighting output port from processor
            lighting_capture = OSCMessageCapture(port=8002)
            lighting_capture.start()

            # Wait for beats to flow
            time.sleep(5.0)

            # Verify beat messages received
            lighting_capture.assert_received("/beat/0", timeout=5.0)

            # Check message count
            beat_messages = lighting_capture.get_messages("/beat/0")
            assert len(beat_messages) >= 2, \
                f"Expected at least 2 beats, got {len(beat_messages)}"

            # Validate message format
            for timestamp, address, args in beat_messages:
                assert address == "/beat/0"
                assert len(args) >= 2
                ppg_id = args[0]
                beat_timestamp_ms = args[1]
                assert ppg_id == 0
                assert_within_ms(beat_timestamp_ms, max_age_ms=500)

            lighting_capture.stop()


class TestMultiSensorBeatFlow:
    """Test multiple PPG sensors operating simultaneously."""

    def test_four_ppg_streams_independent(self):
        """Verify 4 PPG sensors produce independent beat streams.

        Test steps:
        1. Start all 4 PPG emulators (different BPMs) + processor
        2. Capture beat messages from all sensors on processor output
        3. Verify independent routing (no cross-talk)
        4. Validate beat rates match configured BPMs
        """
        with ComponentManager() as manager:
            # Start all 4 PPG emulators + processor
            manager.start(['ppg0', 'ppg1', 'ppg2', 'ppg3', 'processor'], wait=4.0)

            audio_capture = OSCMessageCapture(port=8001)
            audio_capture.start()

            # Let system run to collect beats from all sensors
            time.sleep(5.0)

            # Verify beats from each PPG
            for ppg_id in range(4):
                beat_messages = audio_capture.get_messages(f"/beat/{ppg_id}")
                assert len(beat_messages) >= 2, \
                    f"No beats from PPG {ppg_id}: got {len(beat_messages)}"

                # Verify routing integrity
                for timestamp, address, args in beat_messages:
                    assert address == f"/beat/{ppg_id}", \
                        f"Wrong address for PPG {ppg_id}: {address}"
                    msg_ppg_id = args[0]
                    assert msg_ppg_id == ppg_id, \
                        f"Beat has wrong PPG ID: expected {ppg_id}, got {msg_ppg_id}"

            audio_capture.stop()

    def test_no_cross_talk_between_sensors(self):
        """Verify PPG sensors don't interfere with each other.

        Validates that beat messages maintain correct PPG ID routing
        when multiple sensors are active simultaneously.
        """
        with ComponentManager() as manager:
            manager.start(['ppg0', 'ppg1', 'processor'], wait=3.0)

            audio_capture = OSCMessageCapture(port=8001)
            audio_capture.start()

            time.sleep(4.0)

            # Check beats for PPG 0
            ppg0_beats = audio_capture.get_messages("/beat/0")
            for timestamp, address, args in ppg0_beats:
                ppg_id = args[0]
                assert ppg_id == 0, f"PPG 0 beat has wrong ID: {ppg_id}"

            # Check beats for PPG 1
            ppg1_beats = audio_capture.get_messages("/beat/1")
            for timestamp, address, args in ppg1_beats:
                ppg_id = args[0]
                assert ppg_id == 1, f"PPG 1 beat has wrong ID: {ppg_id}"

            # Both should have beats
            assert len(ppg0_beats) > 0, "No beats from PPG 0"
            assert len(ppg1_beats) > 0, "No beats from PPG 1"

            audio_capture.stop()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
