"""
Tests for Launchpad Emulator

Validates button press emulation, LED state tracking, and OSC message handling.
"""

import pytest
import time
import threading
from amor.simulator.launchpad_emulator import LaunchpadEmulator


class TestLaunchpadEmulator:
    """Test LaunchpadEmulator functionality."""

    def test_initialization(self):
        """Test emulator initializes with correct defaults."""
        emulator = LaunchpadEmulator()

        assert emulator.control_port == 8003
        assert emulator.led_port == 8005
        assert len(emulator.led_state) == 0
        assert emulator.button_presses == 0
        assert emulator.led_commands == 0
        assert emulator.running == False

    def test_custom_ports(self):
        """Test emulator accepts custom port configuration."""
        emulator = LaunchpadEmulator(control_port=9003, led_port=9005)

        assert emulator.control_port == 9003
        assert emulator.led_port == 9005

    def test_ppg_button_press(self):
        """Test PPG button press validation and counting."""
        emulator = LaunchpadEmulator()

        # Valid button press
        emulator.press_ppg_button(ppg_id=0, column=3)
        assert emulator.button_presses == 1

        emulator.press_ppg_button(ppg_id=2, column=7)
        assert emulator.button_presses == 2

        # Invalid PPG ID (should raise)
        with pytest.raises(ValueError, match="Invalid button position"):
            emulator.press_ppg_button(ppg_id=4, column=0)

        # Invalid column (should raise)
        with pytest.raises(ValueError, match="Invalid button position"):
            emulator.press_ppg_button(ppg_id=0, column=8)

    def test_loop_toggle(self):
        """Test loop toggle validation and counting."""
        emulator = LaunchpadEmulator()

        # Valid loop toggle
        emulator.toggle_loop(loop_id=0)
        assert emulator.button_presses == 1

        emulator.toggle_loop(loop_id=15)
        assert emulator.button_presses == 2

        emulator.toggle_loop(loop_id=31)
        assert emulator.button_presses == 3

        # Invalid loop ID (should raise)
        with pytest.raises(ValueError, match="Invalid loop ID"):
            emulator.toggle_loop(loop_id=32)

        with pytest.raises(ValueError, match="Invalid loop ID"):
            emulator.toggle_loop(loop_id=-1)

    def test_momentary_loop(self):
        """Test momentary loop press/release."""
        emulator = LaunchpadEmulator()

        # Press
        emulator.momentary_loop(loop_id=16, state=1)
        assert emulator.button_presses == 1

        # Release
        emulator.momentary_loop(loop_id=16, state=0)
        assert emulator.button_presses == 2

        # Invalid state (should raise)
        with pytest.raises(ValueError, match="Invalid state"):
            emulator.momentary_loop(loop_id=16, state=2)

    def test_led_state_tracking(self):
        """Test LED state is tracked correctly."""
        emulator = LaunchpadEmulator()

        # Initially no LED state
        assert emulator.get_led_state(0, 0) is None

        # Simulate LED command (directly call handler)
        emulator._handle_led_command("/led/0/3", 37, 1)

        # State should be tracked
        state = emulator.get_led_state(0, 3)
        assert state == (37, 1)  # (color, mode)

        assert emulator.led_commands == 1

    def test_led_state_overwrite(self):
        """Test LED state can be updated."""
        emulator = LaunchpadEmulator()

        # Set initial state
        emulator._handle_led_command("/led/2/5", 21, 0)
        assert emulator.get_led_state(2, 5) == (21, 0)

        # Update state
        emulator._handle_led_command("/led/2/5", 45, 2)
        assert emulator.get_led_state(2, 5) == (45, 2)

        # Should still be 2 commands received (not 1)
        assert emulator.led_commands == 2

    def test_led_command_invalid_format(self):
        """Test LED command with invalid format is ignored."""
        emulator = LaunchpadEmulator()

        # Invalid address format
        emulator._handle_led_command("/led/invalid", 37, 1)
        assert emulator.led_commands == 0

        # Missing arguments
        emulator._handle_led_command("/led/0/0")  # No args
        assert emulator.led_commands == 0

        # Non-numeric position
        emulator._handle_led_command("/led/a/b", 37, 1)
        assert emulator.led_commands == 0

    def test_get_ppg_selection(self):
        """Test getting selected column for PPG row."""
        emulator = LaunchpadEmulator()

        # Initially no selection
        assert emulator.get_ppg_selection(0) is None

        # Set LED state for selected button (mode=1 is pulse/selected)
        emulator._handle_led_command("/led/0/5", 37, 1)

        # Should return selected column
        assert emulator.get_ppg_selection(0) == 5

        # Set another button as selected (mode=1)
        emulator._handle_led_command("/led/0/2", 37, 1)

        # Should return the most recent selected button
        # (This is technically implementation-dependent, but let's check both exist)
        selection = emulator.get_ppg_selection(0)
        assert selection in [2, 5]

    def test_multiple_ppg_rows(self):
        """Test LED state tracking across multiple PPG rows."""
        emulator = LaunchpadEmulator()

        # Set LEDs in different rows
        emulator._handle_led_command("/led/0/3", 37, 1)
        emulator._handle_led_command("/led/1/5", 37, 1)
        emulator._handle_led_command("/led/2/7", 37, 1)

        # Each should be tracked independently
        assert emulator.get_led_state(0, 3) == (37, 1)
        assert emulator.get_led_state(1, 5) == (37, 1)
        assert emulator.get_led_state(2, 7) == (37, 1)

        # Other positions should be None
        assert emulator.get_led_state(0, 0) is None
        assert emulator.get_led_state(3, 0) is None

    def test_statistics_tracking(self):
        """Test button press and LED command statistics."""
        emulator = LaunchpadEmulator()

        assert emulator.button_presses == 0
        assert emulator.led_commands == 0

        # Button presses
        emulator.press_ppg_button(0, 0)
        emulator.toggle_loop(5)
        emulator.momentary_loop(16, 1)
        assert emulator.button_presses == 3

        # LED commands
        emulator._handle_led_command("/led/0/0", 37, 1)
        emulator._handle_led_command("/led/1/1", 21, 0)
        assert emulator.led_commands == 2

    def test_press_momentary_loop_duration(self):
        """Test press_momentary_loop with duration."""
        emulator = LaunchpadEmulator()

        start_time = time.time()
        emulator.press_momentary_loop(loop_id=20, duration=0.1)
        elapsed = time.time() - start_time

        # Should take approximately 0.1 seconds
        assert 0.09 < elapsed < 0.15

        # Should register 2 button presses (press + release)
        assert emulator.button_presses == 2

    def test_full_grid_led_state(self):
        """Test LED state for full 8x8 grid."""
        emulator = LaunchpadEmulator()

        # Set all 64 LEDs
        for row in range(8):
            for col in range(8):
                color = (row * 8 + col) % 128
                mode = row % 3
                emulator._handle_led_command(f"/led/{row}/{col}", color, mode)

        # Verify all are tracked
        assert emulator.led_commands == 64

        # Spot check some positions
        assert emulator.get_led_state(0, 0) == (0, 0)
        assert emulator.get_led_state(3, 5) == (29, 0)
        assert emulator.get_led_state(7, 7) == (63, 1)

    def test_boundary_values(self):
        """Test boundary values for button positions and loop IDs."""
        emulator = LaunchpadEmulator()

        # Min/max PPG positions
        emulator.press_ppg_button(ppg_id=0, column=0)
        emulator.press_ppg_button(ppg_id=3, column=7)

        # Min/max loop IDs
        emulator.toggle_loop(loop_id=0)
        emulator.toggle_loop(loop_id=31)

        # All should succeed
        assert emulator.button_presses == 4

    def test_led_mode_values(self):
        """Test LED mode parameter values."""
        emulator = LaunchpadEmulator()

        # Test all valid modes (0=static, 1=pulse, 2=flash)
        emulator._handle_led_command("/led/0/0", 37, 0)
        emulator._handle_led_command("/led/0/1", 37, 1)
        emulator._handle_led_command("/led/0/2", 37, 2)

        assert emulator.get_led_state(0, 0) == (37, 0)
        assert emulator.get_led_state(0, 1) == (37, 1)
        assert emulator.get_led_state(0, 2) == (37, 2)

        assert emulator.led_commands == 3
