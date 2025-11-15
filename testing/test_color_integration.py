#!/usr/bin/env python3
"""
Integration test for semantic color abstraction in LaunchpadBridge.

Tests that the bridge correctly handles semantic color commands,
translates them to hardware values, and manages LED state.
"""

import sys
import os
from unittest.mock import Mock, MagicMock, patch

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from amor.launchpad import (
    Color, _MK1_COLORS, _MK1_PULSE_MAP,
    LaunchpadBridge
)


def test_led_command_semantic_color_translation():
    """Test that _handle_led_command translates semantic colors to hardware."""
    print("Testing LED command semantic color translation...")

    # Create mock MIDI ports
    midi_input = Mock()
    midi_input.iter_pending.return_value = []
    midi_output = Mock()

    # Create bridge
    bridge = LaunchpadBridge(midi_input, midi_output)

    # Mock OSC client
    bridge.control_client = Mock()

    # Test semantic color 0-9 get translated
    test_cases = [
        (Color.OFF, _MK1_COLORS[Color.OFF]),           # 0 → 0
        (Color.GREEN_FULL, _MK1_COLORS[Color.GREEN_FULL]),   # 9 → 48
        (Color.GREEN_LOW, _MK1_COLORS[Color.GREEN_LOW]),     # 7 → 16
        (Color.YELLOW_FULL, _MK1_COLORS[Color.YELLOW_FULL]), # 6 → 51
    ]

    for semantic_color, expected_hw_color in test_cases:
        # Clear state
        bridge.led_colors.clear()
        bridge.led_modes.clear()

        # Send LED command with semantic color
        bridge._handle_led_command("/led/0/0", semantic_color, 0)

        # Verify stored color is hardware value
        stored_color = bridge.led_colors.get((0, 0))
        if stored_color == expected_hw_color:
            print(f"  ✓ Semantic color {semantic_color} → hardware {expected_hw_color}")
        else:
            print(f"  ✗ Semantic color {semantic_color} stored as {stored_color}, "
                  f"expected {expected_hw_color}")
            return False

    # Test passthrough for advanced/direct hardware values (10+)
    bridge.led_colors.clear()
    direct_hw_value = 99
    bridge._handle_led_command("/led/1/1", direct_hw_value, 0)
    stored_color = bridge.led_colors.get((1, 1))
    if stored_color == direct_hw_value:
        print(f"  ✓ Direct hardware value {direct_hw_value} passed through")
    else:
        print(f"  ✗ Direct hardware value {direct_hw_value} stored as {stored_color}")
        return False

    print("  ✓ All LED command translation tests passed\n")
    return True


def test_internal_color_usage():
    """Test that internal LED functions use Color class correctly."""
    print("Testing internal color usage...")

    # Create mock MIDI ports
    midi_input = Mock()
    midi_input.iter_pending.return_value = []
    midi_output = Mock()

    # Create bridge
    bridge = LaunchpadBridge(midi_input, midi_output)

    # Test _initialize_leds uses semantic colors
    bridge._initialize_leds()

    # PPG rows should have green colors
    for row in range(4):
        for col in range(8):
            stored_color = bridge.led_colors.get((row, col))
            if col == 0:
                # Selected column should be GREEN_FULL
                expected = _MK1_COLORS[Color.GREEN_FULL]
                if stored_color == expected:
                    print(f"  ✓ PPG row {row} col {col} (selected) = {stored_color}")
                else:
                    print(f"  ✗ PPG row {row} col {col} = {stored_color}, "
                          f"expected {expected}")
                    return False
            else:
                # Unselected columns should be GREEN_LOW
                expected = _MK1_COLORS[Color.GREEN_LOW]
                if stored_color == expected:
                    print(f"  ✓ PPG row {row} col {col} (unselected) = {stored_color}")
                else:
                    print(f"  ✗ PPG row {row} col {col} = {stored_color}, "
                          f"expected {expected}")
                    return False

    # Loop rows should be OFF
    for row in range(4, 8):
        for col in range(8):
            stored_color = bridge.led_colors.get((row, col))
            expected = _MK1_COLORS[Color.OFF]
            if stored_color == expected:
                print(f"  ✓ Loop row {row} col {col} = {stored_color}")
            else:
                print(f"  ✗ Loop row {row} col {col} = {stored_color}, expected {expected}")
                return False

    print("  ✓ All internal color usage tests passed\n")
    return True


def test_pulse_color_mapping():
    """Test that pulse colors are calculated correctly."""
    print("Testing pulse color mapping...")

    # Create mock MIDI ports
    midi_input = Mock()
    midi_input.iter_pending.return_value = []
    midi_output = Mock()

    # Create bridge
    bridge = LaunchpadBridge(midi_input, midi_output)

    # Test pulse color calculation
    test_cases = [
        (0, 0),        # Off stays off
        (16, 32),      # Green low -> green med
        (32, 48),      # Green med -> green full
        (48, 51),      # Green full -> yellow full
        (51, 51),      # Yellow full stays max
    ]

    for base_color, expected_pulse_color in test_cases:
        pulse_color = bridge._calculate_pulse_color(base_color)
        if pulse_color == expected_pulse_color:
            print(f"  ✓ Pulse({base_color}) = {pulse_color}")
        else:
            print(f"  ✗ Pulse({base_color}) = {pulse_color}, expected {expected_pulse_color}")
            return False

    print("  ✓ All pulse color mapping tests passed\n")
    return True


def test_color_mode_combinations():
    """Test that color/mode combinations work correctly."""
    print("Testing color/mode combinations...")

    # Create mock MIDI ports
    midi_input = Mock()
    midi_input.iter_pending.return_value = []
    midi_output = Mock()

    # Create bridge
    bridge = LaunchpadBridge(midi_input, midi_output)

    # Test that PPG selection uses correct colors and modes
    bridge._initialize_leds()
    bridge._handle_ppg_selection(0, 3)

    # Old selected column should be GREEN_LOW with FLASH mode
    old_color = bridge.led_colors[(0, 0)]
    old_mode = bridge.led_modes[(0, 0)]
    if old_color == _MK1_COLORS[Color.GREEN_LOW] and old_mode == 2:
        print(f"  ✓ Deselected PPG: color={old_color}, mode={old_mode} (FLASH)")
    else:
        print(f"  ✗ Deselected PPG: color={old_color} (expected "
              f"{_MK1_COLORS[Color.GREEN_LOW]}), mode={old_mode} (expected 2)")
        return False

    # New selected column should be GREEN_FULL with PULSE mode
    new_color = bridge.led_colors[(0, 3)]
    new_mode = bridge.led_modes[(0, 3)]
    if new_color == _MK1_COLORS[Color.GREEN_FULL] and new_mode == 1:
        print(f"  ✓ Selected PPG: color={new_color}, mode={new_mode} (PULSE)")
    else:
        print(f"  ✗ Selected PPG: color={new_color} (expected "
              f"{_MK1_COLORS[Color.GREEN_FULL]}), mode={new_mode} (expected 1)")
        return False

    print("  ✓ All color/mode combination tests passed\n")
    return True


def main():
    """Run all integration tests."""
    print("=" * 70)
    print("SEMANTIC COLOR ABSTRACTION INTEGRATION TEST SUITE")
    print("=" * 70)
    print()

    success = True
    success = test_led_command_semantic_color_translation() and success
    success = test_internal_color_usage() and success
    success = test_pulse_color_mapping() and success
    success = test_color_mode_combinations() and success

    if success:
        print("=" * 70)
        print("ALL INTEGRATION TESTS PASSED")
        print("=" * 70)
        return 0
    else:
        print("=" * 70)
        print("SOME INTEGRATION TESTS FAILED")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
