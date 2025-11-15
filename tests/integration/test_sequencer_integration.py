"""Integration tests for Launchpad → Sequencer → Audio routing.

Tests validate the control flow from Launchpad emulator through the sequencer
to audio/lighting subsystems. Focus on:
1. PPG button presses trigger sample routing updates
2. LED state reflects current selections
3. Loop toggles control audio playback
4. Full pipeline integration (Launchpad → Sequencer → Audio)

Reference: docs/integration-test-ideas.md:23-35
"""

import time
import pytest
from amor.sequencer import (
    LED_COLOR_SELECTED,
    LED_COLOR_UNSELECTED,
    LED_MODE_PULSE,
    LED_MODE_FLASH,
    LED_COLOR_LOOP_LATCHING,
    LED_MODE_STATIC,
)


class TestLaunchpadToSequencerFlow:
    """Test control flow from Launchpad emulator to Sequencer.

    Validates that sequencer correctly:
    - Receives button press messages from Launchpad
    - Updates internal state (sample_map, loop_status)
    - Broadcasts routing updates
    - Sends LED state updates
    """

    def test_ppg_button_triggers_routing_message(
        self, launchpad_emulator, component_manager, control_capture
    ):
        """Verify PPG button press triggers routing message.

        Flow: Launchpad → /select/{ppg_id} → Sequencer → /route/{ppg_id}
        Expected: Routing message broadcast on PORT_CONTROL (8003)
        """
        # Start sequencer
        component_manager.add_sequencer(state_path="/tmp/test_sequencer_state.json")
        component_manager.start_all()

        # Wait for sequencer to fully initialize and send initial routing
        time.sleep(1.0)

        # Clear any initial routing messages from sequencer startup
        control_capture.clear()

        # Press PPG button (ppg_id=0, column=5)
        launchpad_emulator.press_ppg_button(0, 5)

        # Wait for routing message
        ts, addr, args = control_capture.wait_for_message("/route/0", timeout=2.0)

        # Validate routing message
        assert addr == "/route/0"
        assert len(args) == 1
        assert args[0] == 5  # Sample ID matches column

    def test_ppg_button_updates_led_state(
        self, launchpad_emulator, component_manager
    ):
        """Verify PPG button press updates LED state.

        Flow: Launchpad → Sequencer → LED updates
        Expected: Selected button has pulse LED, previously selected button dims
        """
        # Start sequencer
        component_manager.add_sequencer(state_path="/tmp/test_sequencer_state.json")
        component_manager.start_all()

        # Press PPG button (row 0, column 5)
        launchpad_emulator.press_ppg_button(0, 5)

        # Wait for LED messages to arrive and be processed by emulator
        time.sleep(0.5)

        # Check selected button (0, 5) has pulse mode via emulator LED state
        led_state = launchpad_emulator.get_led_state(0, 5)
        assert led_state is not None, "Expected LED state for selected button"
        color, mode = led_state
        assert color == LED_COLOR_SELECTED, f"Expected color {LED_COLOR_SELECTED}, got {color}"
        assert mode == LED_MODE_PULSE, f"Expected mode {LED_MODE_PULSE}, got {mode}"

        # Check previously selected button (0, 0) is now unselected (off but flashes on beat)
        led_state = launchpad_emulator.get_led_state(0, 0)
        assert led_state is not None, "Expected LED state for previously selected button"
        color, mode = led_state
        assert color == 0, f"Expected color 0 (off), got {color}"
        assert mode == LED_MODE_FLASH, f"Expected mode {LED_MODE_FLASH}, got {mode}"

    def test_loop_toggle_sends_start_stop(
        self, launchpad_emulator, component_manager, control_capture
    ):
        """Verify loop toggle sends start/stop messages.

        Flow: Launchpad → /loop/toggle → Sequencer → /loop/start or /loop/stop
        Expected: Loop toggle broadcasts start/stop on PORT_CONTROL (8003)
        """
        # Start sequencer
        component_manager.add_sequencer(state_path="/tmp/test_sequencer_state.json")
        component_manager.start_all()

        # Wait for sequencer to fully initialize
        time.sleep(1.0)

        # Toggle loop ON (loop_id=3)
        control_capture.clear()
        launchpad_emulator.toggle_loop(3)

        # Wait for start message
        ts, addr, args = control_capture.wait_for_message("/loop/start", timeout=2.0)
        assert addr == "/loop/start"
        assert len(args) == 1
        assert args[0] == 3, f"Expected loop_id 3, got {args[0]}"

        # Toggle loop OFF
        control_capture.clear()
        launchpad_emulator.toggle_loop(3)

        # Wait for stop message
        ts, addr, args = control_capture.wait_for_message("/loop/stop", timeout=2.0)
        assert addr == "/loop/stop"
        assert len(args) == 1
        assert args[0] == 3, f"Expected loop_id 3, got {args[0]}"

    def test_loop_toggle_updates_led_state(
        self, launchpad_emulator, component_manager
    ):
        """Verify loop toggle updates LED state.

        Flow: Launchpad → /loop/toggle → Sequencer → LED update
        Expected: Active loop has green LED, inactive loop has off LED
        """
        # Start sequencer
        component_manager.add_sequencer(state_path="/tmp/test_sequencer_state.json")
        component_manager.start_all()

        # Toggle loop ON (loop_id=3 -> row 4, col 3)
        launchpad_emulator.toggle_loop(3)
        time.sleep(0.3)  # Allow LED message to arrive and be processed

        # Check LED state for active loop via emulator
        led_state = launchpad_emulator.get_led_state(4, 3)
        assert led_state is not None, "Expected LED state for loop button"
        color, mode = led_state
        assert color == LED_COLOR_LOOP_LATCHING, f"Expected color {LED_COLOR_LOOP_LATCHING}, got {color}"
        assert mode == LED_MODE_STATIC, f"Expected mode {LED_MODE_STATIC}, got {mode}"

        # Toggle loop OFF
        launchpad_emulator.toggle_loop(3)
        time.sleep(0.3)

        # Check LED state for inactive loop
        led_state = launchpad_emulator.get_led_state(4, 3)
        assert led_state is not None, "Expected LED state for loop button"
        color, mode = led_state
        assert color == 0, f"Expected color 0 (off), got {color}"
        assert mode == LED_MODE_STATIC, f"Expected mode {LED_MODE_STATIC}, got {mode}"


class TestSequencerToAudioRouting:
    """Test audio routing from Sequencer through to Audio engine.

    Validates end-to-end pipeline:
    - Launchpad button press → Sequencer state update → Audio routing change
    - PPG beat arrives → Audio plays sample from correct routing
    - Loop toggles control audio playback
    """

    def test_ppg_beat_plays_selected_sample(
        self, launchpad_emulator, component_manager, control_capture, beat_capture
    ):
        """Verify full pipeline from button press to beat reception.

        Flow: Launchpad → Sequencer → Audio + PPG → Processor → Beat → Audio
        Expected: Routing message reaches audio, beat arrives at audio

        Note: This test validates the integration but doesn't directly observe
        audio sample playback (which would require audio output capture). It
        validates that routing updates arrive and beats arrive at audio engine.
        """
        # Setup all components
        component_manager.add_sequencer(state_path="/tmp/test_sequencer_state.json")
        component_manager.add_audio()
        component_manager.add_ppg_emulator(ppg_id=0, bpm=75)
        component_manager.add_processor()
        component_manager.start_all()

        # Change routing (ppg_id=0 -> column=5)
        launchpad_emulator.press_ppg_button(0, 5)

        # Verify routing message (captured via SO_REUSEPORT on PORT_CONTROL)
        ts, addr, args = control_capture.wait_for_message("/route/0", timeout=2.0)
        assert addr == "/route/0"
        assert args[0] == 5, f"Expected sample_id 5, got {args[0]}"

        # Verify beat arrives at audio engine (captured via SO_REUSEPORT on PORT_BEATS)
        ts, addr, args = beat_capture.wait_for_message("/beat/0", timeout=10.0)
        assert addr == "/beat/0"
        assert len(args) == 3  # timestamp, bpm, intensity

    def test_multiple_ppg_independent_routing(
        self, launchpad_emulator, component_manager, control_capture
    ):
        """Verify multiple PPG sensors have independent routing.

        Flow: Launchpad → Sequencer with multiple PPG selections
        Expected: Each PPG sensor can have different sample routing
        """
        # Start sequencer
        component_manager.add_sequencer(state_path="/tmp/test_sequencer_state.json")
        component_manager.start_all()

        # Set PPG 0 → column 3
        control_capture.clear()
        launchpad_emulator.press_ppg_button(0, 3)
        ts, addr, args = control_capture.wait_for_message("/route/0", timeout=2.0)
        assert args[0] == 3

        # Set PPG 1 → column 5
        control_capture.clear()
        launchpad_emulator.press_ppg_button(1, 5)
        ts, addr, args = control_capture.wait_for_message("/route/1", timeout=2.0)
        assert args[0] == 5

        # Verify PPG 0 routing unchanged by pressing again
        control_capture.clear()
        launchpad_emulator.press_ppg_button(0, 7)
        ts, addr, args = control_capture.wait_for_message("/route/0", timeout=2.0)
        assert args[0] == 7  # Updated to column 7
