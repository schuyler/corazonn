"""Integration tests for Sampler → Sequencer → Virtual Channel flow.

Tests validate the control flow for recording PPG data and playing back
as virtual channels. Focus on:
1. Recording workflow (start/stop, status broadcasts)
2. Assignment mode (timeout, channel assignment)
3. Virtual channel playback (loop timing, concurrent channels)
4. Sequencer integration (scene button control)
5. Beat detection on virtual channels

Reference: docs/amor-sampler-design.md
"""

import time
import pytest
from amor import osc
from tests.integration.utils import OSCMessageCapture


class TestBasicSamplerRecordingPlayback:
    """Test basic sampler recording and playback without sequencer."""

    def test_recording_starts_and_stops(self, temp_sampler_dir, component_manager, control_capture):
        """Verify recording can be started and stopped via OSC."""
        component_manager.add_sampler(output_dir=str(temp_sampler_dir))
        component_manager.add_ppg_emulator(ppg_id=0, bpm=75)
        component_manager.start_all()

        # Clear any startup messages
        time.sleep(1.0)
        control_capture.clear()

        # Start recording
        control_client = osc.BroadcastUDPClient("255.255.255.255", osc.PORT_CONTROL)
        control_client.send_message("/sampler/record/toggle", [0])

        # Wait for recording status
        ts, addr, args = control_capture.wait_for_message("/sampler/status/recording", timeout=2.0)
        assert addr == "/sampler/status/recording"
        assert len(args) == 2
        assert args[0] == 0  # PPG 0
        assert args[1] == 1  # Recording active

        # Stop recording
        control_capture.clear()
        control_client.send_message("/sampler/record/toggle", [0])

        # Wait for recording stopped status
        ts, addr, args = control_capture.wait_for_message("/sampler/status/recording", timeout=2.0)
        assert addr == "/sampler/status/recording"
        assert args[0] == 0  # PPG 0
        assert args[1] == 0  # Recording stopped

    def test_recording_creates_binary_file(self, temp_sampler_dir, component_manager, control_capture):
        """Verify recording creates binary file."""
        component_manager.add_sampler(output_dir=str(temp_sampler_dir))
        component_manager.add_ppg_emulator(ppg_id=0, bpm=75)
        component_manager.start_all()

        time.sleep(1.0)
        control_capture.clear()

        # Start recording
        control_client = osc.BroadcastUDPClient("255.255.255.255", osc.PORT_CONTROL)
        control_client.send_message("/sampler/record/toggle", [0])
        control_capture.wait_for_message("/sampler/status/recording", timeout=2.0)

        # Let it record for 2 seconds
        time.sleep(2.0)

        # Stop recording
        control_client.send_message("/sampler/record/toggle", [0])
        control_capture.wait_for_message("/sampler/status/recording", timeout=2.0)

        # Verify file created
        files = list(temp_sampler_dir.glob("sampler_*_ppg0.bin"))
        assert len(files) == 1, f"Expected 1 recording file, found {len(files)}"
        assert files[0].stat().st_size > 0, "Recording file is empty"

    def test_assignment_mode_entered(self, temp_sampler_dir, component_manager, control_capture):
        """Verify assignment mode entered after stopping recording."""
        component_manager.add_sampler(output_dir=str(temp_sampler_dir))
        component_manager.add_ppg_emulator(ppg_id=0, bpm=75)
        component_manager.start_all()

        time.sleep(1.0)
        control_capture.clear()

        # Start and stop recording
        control_client = osc.BroadcastUDPClient("255.255.255.255", osc.PORT_CONTROL)
        control_client.send_message("/sampler/record/toggle", [0])
        control_capture.wait_for_message("/sampler/status/recording", timeout=2.0)

        time.sleep(1.0)
        control_capture.clear()

        control_client.send_message("/sampler/record/toggle", [0])

        # Wait briefly for both messages to arrive
        time.sleep(0.5)

        # Get all status messages
        messages = control_capture.get_messages_by_address("/sampler/status/")
        assert len(messages) >= 2, f"Expected at least 2 status messages, got {len(messages)}"

        # Extract addresses
        addrs = [msg[1] for msg in messages]  # msg = (timestamp, address, args)
        assert "/sampler/status/recording" in addrs
        assert "/sampler/status/assignment" in addrs

        # Check assignment mode is active
        assignment_msgs = [msg for msg in messages if msg[1] == "/sampler/status/assignment"]
        assert len(assignment_msgs) > 0
        assert assignment_msgs[0][2][0] == 1  # args[0] == 1 (assignment mode active)

    def test_virtual_channel_playback(self, temp_sampler_dir, component_manager, control_capture):
        """Verify virtual channel starts playback after assignment."""
        component_manager.add_sampler(output_dir=str(temp_sampler_dir))
        component_manager.add_ppg_emulator(ppg_id=0, bpm=75)
        component_manager.start_all()

        time.sleep(1.0)
        control_capture.clear()

        # Record and enter assignment mode
        control_client = osc.BroadcastUDPClient("255.255.255.255", osc.PORT_CONTROL)
        control_client.send_message("/sampler/record/toggle", [0])
        control_capture.wait_for_message("/sampler/status/recording", timeout=2.0)

        time.sleep(2.0)

        control_client.send_message("/sampler/record/toggle", [0])
        control_capture.wait_for_message("/sampler/status/assignment", timeout=2.0)

        # Assign to virtual channel 4
        control_capture.clear()
        control_client.send_message("/sampler/assign", [4])

        # Wait for playback status
        ts, addr, args = control_capture.wait_for_message("/sampler/status/playback", timeout=2.0)
        assert addr == "/sampler/status/playback"
        assert len(args) == 2
        assert args[0] == 4  # Channel 4
        assert args[1] == 1  # Playback active

    def test_stop_virtual_channel_playback(self, temp_sampler_dir, component_manager, control_capture):
        """Verify virtual channel playback can be stopped."""
        component_manager.add_sampler(output_dir=str(temp_sampler_dir))
        component_manager.add_ppg_emulator(ppg_id=0, bpm=75)
        component_manager.start_all()

        time.sleep(1.0)
        control_capture.clear()

        # Record, assign, and start playback
        control_client = osc.BroadcastUDPClient("255.255.255.255", osc.PORT_CONTROL)
        control_client.send_message("/sampler/record/toggle", [0])
        control_capture.wait_for_message("/sampler/status/recording", timeout=2.0)

        time.sleep(2.0)

        control_client.send_message("/sampler/record/toggle", [0])
        control_capture.wait_for_message("/sampler/status/assignment", timeout=2.0)

        control_client.send_message("/sampler/assign", [4])
        control_capture.wait_for_message("/sampler/status/playback", timeout=2.0)

        # Stop playback
        control_capture.clear()
        control_client.send_message("/sampler/toggle", [4])

        # Wait for playback stopped status
        ts, addr, args = control_capture.wait_for_message("/sampler/status/playback", timeout=2.0)
        assert addr == "/sampler/status/playback"
        assert args[0] == 4  # Channel 4
        assert args[1] == 0  # Playback stopped

    def test_virtual_channel_loops_continuously(self, temp_sampler_dir, component_manager, control_capture):
        """Verify virtual channel loops recorded data continuously."""
        component_manager.add_sampler(output_dir=str(temp_sampler_dir))
        component_manager.add_ppg_emulator(ppg_id=0, bpm=75)
        component_manager.start_all()

        time.sleep(1.0)  # Allow startup
        control_capture.clear()

        # Record 2 seconds of PPG data
        control_client = osc.BroadcastUDPClient("255.255.255.255", osc.PORT_CONTROL)
        control_client.send_message("/sampler/record/toggle", [0])
        control_capture.wait_for_message("/sampler/status/recording", timeout=2.0)

        time.sleep(2.0)  # Record 2 seconds (~20 PPG messages at 10 msg/sec)

        control_client.send_message("/sampler/record/toggle", [0])
        control_capture.wait_for_message("/sampler/status/assignment", timeout=2.0)

        # Start PPG message capture on PORT_PPG (8000)
        ppg_capture = OSCMessageCapture(osc.PORT_PPG)
        ppg_capture.start()

        try:
            # Assign to virtual channel 4
            control_client.send_message("/sampler/assign", [4])
            control_capture.wait_for_message("/sampler/status/playback", timeout=2.0)

            # Wait for 6 seconds (3x recording length) to allow multiple loops
            time.sleep(6.0)

            # Get all PPG messages sent by virtual channel 4
            ppg_messages = ppg_capture.get_messages_by_address("/ppg/4")

            # If looping works, we should get ~60 messages (6 seconds × 10 msg/sec)
            # If NOT looping, we'd only get ~20 messages (2 seconds × 10 msg/sec)
            # Use threshold of 40 to prove looping occurred
            assert len(ppg_messages) >= 40, \
                f"Expected at least 40 PPG messages (proving loop), got {len(ppg_messages)}"
        finally:
            ppg_capture.stop()


class TestSequencerToSamplerFlow:
    """Test control flow from Sequencer scene buttons to Sampler."""

    def test_scene_button_triggers_recording(self, launchpad_emulator, temp_sampler_dir,
                                             component_manager, control_capture):
        """Verify scene button press starts recording."""
        component_manager.add_sequencer(state_path="/tmp/test_sequencer_sampler_state.json")
        component_manager.add_sampler(output_dir=str(temp_sampler_dir))
        component_manager.add_ppg_emulator(ppg_id=0, bpm=75)
        component_manager.start_all()

        time.sleep(1.0)
        control_capture.clear()

        # Press scene 0 button (should start recording PPG 0)
        launchpad_emulator.press_scene_button(0)

        # Wait for recording status
        ts, addr, args = control_capture.wait_for_message("/sampler/status/recording", timeout=2.0)
        assert addr == "/sampler/status/recording"
        assert args[0] == 0  # PPG 0
        assert args[1] == 1  # Recording active

    def test_scene_button_stops_recording(self, launchpad_emulator, temp_sampler_dir,
                                          component_manager, control_capture):
        """Verify second scene button press stops recording and enters assignment."""
        component_manager.add_sequencer(state_path="/tmp/test_sequencer_sampler_state2.json")
        component_manager.add_sampler(output_dir=str(temp_sampler_dir))
        component_manager.add_ppg_emulator(ppg_id=0, bpm=75)
        component_manager.start_all()

        time.sleep(1.0)
        control_capture.clear()

        # Start recording
        launchpad_emulator.press_scene_button(0)
        control_capture.wait_for_message("/sampler/status/recording", timeout=2.0)

        time.sleep(1.0)
        control_capture.clear()

        # Stop recording
        launchpad_emulator.press_scene_button(0)

        # Should enter assignment mode
        ts, addr, args = control_capture.wait_for_message("/sampler/status/assignment", timeout=2.0)
        assert args[0] == 1  # Assignment mode active

    def test_assignment_to_virtual_channel(self, launchpad_emulator, temp_sampler_dir,
                                           component_manager, control_capture):
        """Verify scene 4-7 press assigns buffer to virtual channel."""
        component_manager.add_sequencer(state_path="/tmp/test_sequencer_sampler_state3.json")
        component_manager.add_sampler(output_dir=str(temp_sampler_dir))
        component_manager.add_ppg_emulator(ppg_id=1, bpm=75)
        component_manager.start_all()

        time.sleep(1.0)
        control_capture.clear()

        # Record PPG 1
        launchpad_emulator.press_scene_button(1)
        control_capture.wait_for_message("/sampler/status/recording", timeout=2.0)

        time.sleep(2.0)

        # Stop recording and enter assignment
        launchpad_emulator.press_scene_button(1)
        control_capture.wait_for_message("/sampler/status/assignment", timeout=2.0)

        control_capture.clear()

        # Assign to virtual channel 5 (scene button 5)
        launchpad_emulator.press_scene_button(5)

        # Wait for playback status
        ts, addr, args = control_capture.wait_for_message("/sampler/status/playback", timeout=2.0)
        assert addr == "/sampler/status/playback"
        assert args[0] == 5  # Channel 5
        assert args[1] == 1  # Playback active

    def test_scene_button_stops_virtual_playback(self, launchpad_emulator, temp_sampler_dir,
                                                  component_manager, control_capture):
        """Verify pressing scene button on active virtual channel stops playback."""
        component_manager.add_sequencer(state_path="/tmp/test_sequencer_sampler_state4.json")
        component_manager.add_sampler(output_dir=str(temp_sampler_dir))
        component_manager.add_ppg_emulator(ppg_id=0, bpm=75)
        component_manager.start_all()

        time.sleep(1.0)
        control_capture.clear()

        # Record and assign to channel 4
        launchpad_emulator.press_scene_button(0)  # Start recording PPG 0
        control_capture.wait_for_message("/sampler/status/recording", timeout=2.0)

        time.sleep(1.5)  # Record some data

        launchpad_emulator.press_scene_button(0)  # Stop recording, enter assignment
        control_capture.wait_for_message("/sampler/status/assignment", timeout=2.0)

        control_capture.clear()
        launchpad_emulator.press_scene_button(4)  # Assign to channel 4
        control_capture.wait_for_message("/sampler/status/playback", timeout=2.0)

        # Press scene 4 again to stop playback
        control_capture.clear()
        launchpad_emulator.press_scene_button(4)

        # Should receive playback stopped status
        ts, addr, args = control_capture.wait_for_message("/sampler/status/playback", timeout=2.0)
        assert addr == "/sampler/status/playback"
        assert args[0] == 4  # Channel 4
        assert args[1] == 0  # Playback stopped


class TestSamplerBeatDetection:
    """Test virtual channel beats detected by processor."""

    def test_virtual_channel_generates_beats(self, temp_sampler_dir, component_manager,
                                             beat_capture, control_capture):
        """Verify processor detects beats from virtual channel playback."""
        component_manager.add_sampler(output_dir=str(temp_sampler_dir))
        component_manager.add_ppg_emulator(ppg_id=0, bpm=75)
        component_manager.add_processor()
        component_manager.start_all()

        # Wait for warmup
        time.sleep(10.0)

        # Record some beats
        control_client = osc.BroadcastUDPClient("255.255.255.255", osc.PORT_CONTROL)
        control_client.send_message("/sampler/record/toggle", [0])
        control_capture.wait_for_message("/sampler/status/recording", timeout=2.0)

        time.sleep(5.0)  # Record 5 seconds of beats

        control_client.send_message("/sampler/record/toggle", [0])
        control_capture.wait_for_message("/sampler/status/assignment", timeout=2.0)

        # Assign to virtual channel 4
        control_client.send_message("/sampler/assign", [4])
        control_capture.wait_for_message("/sampler/status/playback", timeout=2.0)

        # Clear beat capture and wait for beats on channel 4
        beat_capture.clear()
        time.sleep(3.0)

        # Verify we got beats on channel 4
        beats = beat_capture.get_messages_by_address("/beat/4")
        assert len(beats) >= 2, f"Expected at least 2 beats on virtual channel 4, got {len(beats)}"

        # Validate BPM accuracy (should match recorded 75 BPM ±15%)
        # Beat message format: [timestamp_ms, bpm, intensity]
        _, _, args = beats[0]
        timestamp_ms, bpm, intensity = args
        assert 63.75 <= bpm <= 86.25, \
            f"Virtual channel BPM {bpm:.1f} outside ±15% of recorded 75 BPM (expected 63.75-86.25)"


class TestSamplerErrorHandling:
    """Test error conditions and edge cases."""

    def test_concurrent_recording_prevention(self, temp_sampler_dir, component_manager, control_capture):
        """Verify second recording attempt is ignored during active recording."""
        component_manager.add_sampler(output_dir=str(temp_sampler_dir))
        component_manager.add_ppg_emulator(ppg_id=0, bpm=75)
        component_manager.add_ppg_emulator(ppg_id=1, bpm=80)
        component_manager.start_all()

        time.sleep(1.0)
        control_capture.clear()

        # Start recording PPG 0
        control_client = osc.BroadcastUDPClient("255.255.255.255", osc.PORT_CONTROL)
        control_client.send_message("/sampler/record/toggle", [0])
        control_capture.wait_for_message("/sampler/status/recording", timeout=2.0)

        control_capture.clear()

        # Try to start recording PPG 1 (should be ignored)
        control_client.send_message("/sampler/record/toggle", [1])

        # Should not get a new recording status message
        time.sleep(1.0)
        messages = control_capture.get_messages_by_address("/sampler/status/recording")
        assert len(messages) == 0, "Concurrent recording was not prevented"

    def test_recording_ignored_during_assignment(self, temp_sampler_dir, component_manager, control_capture):
        """Verify recording attempt is ignored during assignment mode."""
        component_manager.add_sampler(output_dir=str(temp_sampler_dir))
        component_manager.add_ppg_emulator(ppg_id=0, bpm=75)
        component_manager.add_ppg_emulator(ppg_id=1, bpm=80)
        component_manager.start_all()

        time.sleep(1.0)
        control_capture.clear()

        # Start recording PPG 0, stop to enter assignment mode
        control_client = osc.BroadcastUDPClient("255.255.255.255", osc.PORT_CONTROL)
        control_client.send_message("/sampler/record/toggle", [0])
        control_capture.wait_for_message("/sampler/status/recording", timeout=2.0)

        time.sleep(1.0)

        control_client.send_message("/sampler/record/toggle", [0])
        control_capture.wait_for_message("/sampler/status/assignment", timeout=2.0)

        # Try to start recording PPG 1 during assignment mode (should be ignored)
        control_capture.clear()
        control_client.send_message("/sampler/record/toggle", [1])

        # Should not get a new recording status message
        time.sleep(1.0)
        messages = control_capture.get_messages_by_address("/sampler/status/recording")
        assert len(messages) == 0, "Recording during assignment mode was not prevented"

    def test_reassign_active_virtual_channel(self, temp_sampler_dir, component_manager, control_capture):
        """Verify reassigning to active virtual channel stops old playback."""
        component_manager.add_sampler(output_dir=str(temp_sampler_dir))
        component_manager.add_ppg_emulator(ppg_id=0, bpm=75)
        component_manager.start_all()

        time.sleep(1.0)
        control_client = osc.BroadcastUDPClient("255.255.255.255", osc.PORT_CONTROL)

        # Record first buffer and assign to channel 4
        control_capture.clear()
        control_client.send_message("/sampler/record/toggle", [0])
        control_capture.wait_for_message("/sampler/status/recording", timeout=2.0)

        time.sleep(1.0)

        control_client.send_message("/sampler/record/toggle", [0])
        control_capture.wait_for_message("/sampler/status/assignment", timeout=2.0)

        control_client.send_message("/sampler/assign", [4])
        control_capture.wait_for_message("/sampler/status/playback", timeout=2.0)

        # Record second buffer
        control_capture.clear()
        control_client.send_message("/sampler/record/toggle", [0])
        control_capture.wait_for_message("/sampler/status/recording", timeout=2.0)

        time.sleep(1.0)

        control_client.send_message("/sampler/record/toggle", [0])
        control_capture.wait_for_message("/sampler/status/assignment", timeout=2.0)

        # Assign to channel 4 again - should get stop then start messages
        control_capture.clear()
        control_client.send_message("/sampler/assign", [4])

        # Wait for messages to arrive
        time.sleep(1.0)

        # Get all playback status messages
        playback_messages = control_capture.get_messages_by_address("/sampler/status/playback")
        assert len(playback_messages) == 2, \
            f"Expected exactly 2 playback messages (stop old, start new), got {len(playback_messages)}"

        # Verify first message is stop for channel 4
        ts1, addr1, args1 = playback_messages[0]
        assert addr1 == "/sampler/status/playback"
        assert args1[0] == 4, f"Stop message should be for channel 4, got {args1[0]}"
        assert args1[1] == 0, f"First message should be stop (0), got {args1[1]}"

        # Verify second message is start for channel 4
        ts2, addr2, args2 = playback_messages[1]
        assert addr2 == "/sampler/status/playback"
        assert args2[0] == 4, f"Start message should be for channel 4, got {args2[0]}"
        assert args2[1] == 1, f"Second message should be start (1), got {args2[1]}"

    @pytest.mark.slow
    def test_assignment_timeout_30s(self, temp_sampler_dir, component_manager, control_capture):
        """Verify assignment mode times out after 30 seconds."""
        component_manager.add_sampler(output_dir=str(temp_sampler_dir))
        component_manager.add_ppg_emulator(ppg_id=0, bpm=75)
        component_manager.start_all()

        time.sleep(1.0)
        control_capture.clear()

        # Record and enter assignment mode
        control_client = osc.BroadcastUDPClient("255.255.255.255", osc.PORT_CONTROL)
        control_client.send_message("/sampler/record/toggle", [0])
        control_capture.wait_for_message("/sampler/status/recording", timeout=2.0)

        time.sleep(1.0)

        control_client.send_message("/sampler/record/toggle", [0])
        ts, addr, args = control_capture.wait_for_message("/sampler/status/assignment", timeout=2.0)
        assert args[0] == 1  # Assignment mode entered

        control_capture.clear()

        # Wait for timeout (30s + buffer)
        time.sleep(31.0)

        # Should receive assignment mode exited
        ts, addr, args = control_capture.wait_for_message("/sampler/status/assignment", timeout=2.0)
        assert args[0] == 0  # Assignment mode exited

    @pytest.mark.slow
    def test_recording_duration_limit_60s(self, temp_sampler_dir, component_manager, control_capture):
        """Verify recording auto-stops at 60 seconds."""
        component_manager.add_sampler(output_dir=str(temp_sampler_dir))
        component_manager.add_ppg_emulator(ppg_id=0, bpm=75)
        component_manager.start_all()

        time.sleep(1.0)
        control_capture.clear()

        # Start recording
        control_client = osc.BroadcastUDPClient("255.255.255.255", osc.PORT_CONTROL)
        control_client.send_message("/sampler/record/toggle", [0])
        control_capture.wait_for_message("/sampler/status/recording", timeout=2.0)

        control_capture.clear()

        # Wait for auto-stop (60s + buffer)
        time.sleep(61.0)

        # Should receive recording stopped status
        ts, addr, args = control_capture.wait_for_message("/sampler/status/recording", timeout=2.0)
        assert args[0] == 0  # PPG 0
        assert args[1] == 0  # Recording stopped

        # Should enter assignment mode after 60s auto-stop
        ts, addr, args = control_capture.wait_for_message("/sampler/status/assignment", timeout=2.0)
        assert args[0] == 1  # Assignment mode entered

    def test_multiple_virtual_channels_concurrent(self, temp_sampler_dir, component_manager, control_capture):
        """Verify all 4 virtual channels (4-7) can play concurrently."""
        component_manager.add_sampler(output_dir=str(temp_sampler_dir))
        component_manager.add_ppg_emulator(ppg_id=0, bpm=75)
        component_manager.start_all()

        time.sleep(1.0)
        control_client = osc.BroadcastUDPClient("255.255.255.255", osc.PORT_CONTROL)

        # Record and assign to all 4 virtual channels (4-7)
        for channel in [4, 5, 6, 7]:
            control_capture.clear()
            control_client.send_message("/sampler/record/toggle", [0])
            control_capture.wait_for_message("/sampler/status/recording", timeout=2.0)

            time.sleep(1.0)  # Record 1 second of data

            control_client.send_message("/sampler/record/toggle", [0])
            control_capture.wait_for_message("/sampler/status/assignment", timeout=2.0)

            control_client.send_message("/sampler/assign", [channel])
            control_capture.wait_for_message("/sampler/status/playback", timeout=2.0)

        # Verify all 4 channels are sending PPG messages concurrently
        ppg_capture = OSCMessageCapture(osc.PORT_PPG)
        ppg_capture.start()

        try:
            time.sleep(2.0)  # Collect messages for 2 seconds

            # Verify each virtual channel is sending messages
            for channel in [4, 5, 6, 7]:
                msgs = ppg_capture.get_messages_by_address(f"/ppg/{channel}")
                assert len(msgs) >= 10, \
                    f"Channel {channel} should be sending messages (expected ≥10, got {len(msgs)})"
        finally:
            ppg_capture.stop()
